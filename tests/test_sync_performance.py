import contextlib
import base64
import hashlib
import io
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import tracker_core as tracker
import github_collector
import github_recruitment_collector
import github_render_dashboard
import github_dispatch
import github_sync_portal
import shared_actions


class SyncPerformance(unittest.TestCase):
    def test_cwl_requests_overlap_are_bounded_deduplicated_and_keep_failures(self):
        for module in (tracker, __import__('Clash_War_Tracker')):
            state=module.new_state(module.DEFAULT_CLAN_TAG)
            state['leagueWarSummaries']['#FAIL']={'state':'inWar','saved':True}
            gate=threading.Barrier(4);lock=threading.Lock();active=peak=0;seen=[]
            def get(path):
                nonlocal active,peak
                if path.endswith('/leaguegroup'):
                    return {'season':'2030-01','rounds':[{'warTags':['#A','#B','#C','#D','#E','#F','#G','#FAIL','#A','#0']}]}
                if path.startswith('/clanwarleagues/wars/'):
                    with lock:active+=1;peak=max(peak,active);seen.append(path)
                    try:
                        gate.wait(timeout=3)
                        if path.endswith('FAIL'):raise module.APIError(520)
                        return {'state':'inWar','clan':{'tag':'#OTHER'},'opponent':{'tag':'#ANOTHER'}}
                    finally:
                        with lock:active-=1
                if path.endswith('/currentwar'):return {'state':'notInWar'}
                if '?' in path:return {'items':[]}
                return {'tag':state['clanTag'],'name':'Fixture','members':1,'memberList':[{'tag':'#P0Y','name':'Fixture','townHallLevel':12}]}
            with contextlib.redirect_stdout(io.StringIO()):module.refresh(state,SimpleNamespace(get=get),profiles=False)
            self.assertEqual(peak,4);self.assertEqual(len(seen),8)
            self.assertEqual(state['leagueWarSummaries']['#FAIL']['saved'],True)
            self.assertTrue(any('CWL round' in w for w in state['warnings']))

    def test_stale_dispatch_never_creates_another_collection(self):
        env={'GITHUB_REPOSITORY':'phil14-hub/war-haven-dashboard','COC_API_TOKEN':'fixture','DASHBOARD_PASSWORD':'fixture password','DASHBOARD_PUBLISH_TOKEN':'fixture','DASHBOARD_REQUEST_ID':'already-handled'}
        fake=SimpleNamespace(new_state=lambda tag:{},DEFAULT_CLAN_TAG=tracker.DEFAULT_CLAN_TAG,pull_github_history=lambda *a:None)
        client=SimpleNamespace(request=lambda *a:{'request':None})
        for module in (github_collector,github_recruitment_collector):
            with patch.object(shared_actions,'Client',return_value=client),patch.object(shared_actions,'pending',return_value=None),patch.object(module,'collect',side_effect=AssertionError('Duplicate collection')),contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(module.run(env,fake)['skipped'])

    def test_finished_portal_and_backup_do_not_wait_for_pages(self):
        calls=[];u=shared_actions.UpdateRequest.__new__(shared_actions.UpdateRequest)
        u.lease='lease';u.kind='clan';u.request={'id':'request'};u.client=SimpleNamespace(request=lambda path,body:calls.append(body))
        with contextlib.redirect_stdout(io.StringIO()):u.finish({'published':False,'commit':'a'*40,'partial':False,'components':{'backup':True,'portal':True,'github':False}})
        self.assertTrue(calls[0]['ok']);self.assertFalse(calls[0]['partial']);self.assertFalse(calls[0]['components']['github'])

    def test_slow_code_verification_cannot_roll_back_newer_source(self):
        def api(config,method,path):return {'tree':[{'path':'tracker_core.py','type':'blob','sha':'old' if '/checked?' in path else 'new'}]}
        self.assertFalse(github_render_dashboard.source_is_current({'GITHUB_SHA':'checked'},SimpleNamespace(github_request=api),{'repository':'fixture'}))
        def same(config,method,path):return {'tree':[{'path':'tracker_core.py','type':'blob','sha':'same'},{'path':'data/history.json','type':'blob','sha':path}]}
        self.assertTrue(github_render_dashboard.source_is_current({'GITHUB_SHA':'checked'},SimpleNamespace(github_request=same),{'repository':'fixture'}))

    def test_workflows_keep_write_lock_and_move_maintenance_and_checks_outside(self):
        root=Path(__file__).resolve().parents[1]/'.github/workflows'
        for kind in ('clan','recruitment'):
            text=(root/('update-'+kind+'.yml')).read_text()
            self.assertIn('types: [war-haven-refresh-'+kind+']',text);self.assertIn('DASHBOARD_REQUEST_ID:',text)
            self.assertIn('group: war-haven-clan-update',text)
        text=(root/'sync-portal.yml').read_text();maintenance=text.split('  maintenance:',1)[1].split('  synchronize:',1)[0]
        self.assertIn('--maintenance-only',maintenance);self.assertNotIn('group: war-haven-clan-update',maintenance)
        text=(root/'rebuild-dashboard.yml').read_text();verify=text.split('  verify:',1)[1].split('  publish-code:',1)[0]
        self.assertIn('check-release',verify);self.assertNotIn('group: war-haven-clan-update',verify)
        self.assertIn('requests==2.34.2',text.split('  publish-code:',1)[1],'The isolated publisher needs its own recruitment report dependency')

    def test_credential_setup_uses_collector_authorization_without_logging_token(self):
        calls=[];client=SimpleNamespace(request=lambda path,body:calls.append((path,body)) or {'configured':True})
        with patch.object(shared_actions,'Client',return_value=client),contextlib.redirect_stdout(io.StringIO()) as out:
            github_dispatch.configure({'GITHUB_REPOSITORY':'phil14-hub/war-haven-dashboard','DASHBOARD_PUBLISH_TOKEN':'secret-fixture'})
        self.assertEqual(calls,[('/members/api/refresh-dispatch',{'token':'secret-fixture'})]);self.assertNotIn('secret-fixture',out.getvalue())

    def test_private_backup_uploads_the_exact_verified_archive_once_per_day(self):
        config = {'repository': 'fixture', 'password': 'fixture-passphrase'}
        state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        body = json.dumps(tracker.encrypt_history(state, config['password'], rounds=100000)).encode()
        sha = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        checksum = hashlib.sha256(body).hexdigest()
        commit = 'a' * 40
        calls = []

        def request(path, *, method='POST', **options):
            calls.append((path, method, options))
            if method == 'HEAD':
                return len(calls) > 2
            return {'status': 'saved', 'day': '2030-01-01', 'bytes': len(body), 'sha256': checksum, 'source': commit}

        client = SimpleNamespace(request=request)
        blob = {'sha': sha, 'encoding': 'base64', 'content': base64.encodebytes(body).decode()}
        with patch.object(tracker, 'github_request', return_value=blob) as api, contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                github_sync_portal.backup_clan_archive(config, tracker, client, commit, sha)
        api.assert_called_once_with(config, 'GET', '/repos/fixture/git/blobs/' + sha)
        endpoint = '/members/api/clan-archive-backup'
        self.assertEqual(calls, [(endpoint, 'HEAD', {}), (endpoint, 'POST', {'body': body, 'extra_headers': {
            'X-Archive-SHA256': checksum, 'X-Archive-Source': commit}}), (endpoint, 'HEAD', {})])

        wrong = {**blob, 'content': base64.b64encode(body + b' ').decode()}
        calls.clear()
        with patch.object(tracker, 'github_request', return_value=wrong), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'did not match'):
                github_sync_portal.backup_clan_archive(config, tracker, client, commit, sha)
        self.assertEqual(calls, [(endpoint, 'HEAD', {})])


if __name__=='__main__':unittest.main()
