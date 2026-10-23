import base64
import contextlib
import copy
import hashlib
import hmac
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import Clash_War_Tracker as tracker
import shared_actions
import war_end_updates as timing
from tests.test_war_end_updates import NOW, fixture


class AuditFixTests(unittest.TestCase):
    def test_one_bad_shared_record_does_not_block_valid_records(self):
        output=subprocess.run(['node','tests/shared_dashboard.test.cjs'],capture_output=True,text=True,check=True)
        values=json.loads(output.stdout);key=base64.b64decode(values['key'])
        good={'id':hmac.new(key[32:],b'notes:#P0Y',hashlib.sha256).hexdigest(),'kind':'notes','envelope':values['envelope'],'updatedAt':'2030-01-01T00:00:00Z'}
        bad={**good,'id':'a'*64,'envelope':{**good['envelope'],'tag':base64.b64encode(bytes(32)).decode()}}
        state=tracker.new_state(tracker.DEFAULT_CLAN_TAG);state['sharedActions']={'encryptionKey':values['key']};state['edits']['notes']['#P0Q']={'text':'Retain previous saved evidence'}
        client=SimpleNamespace(request=lambda path:{'records':[bad,good]})
        with contextlib.redirect_stdout(io.StringIO()),patch.object(shared_actions,'ENABLED',True):shared_actions.pull(state,client,tracker)
        self.assertEqual(state['edits']['notes']['#P0Y']['text'],'Shared fixture')
        self.assertEqual(state['edits']['notes']['#P0Q']['text'],'Retain previous saved evidence')
        self.assertEqual(state['sharedActions']['skippedRecords'],1)

    def test_recent_profile_cache_cannot_hide_changed_or_missing_town_hall_data(self):
        for saved in ({'tag':'#P0Y','townHallLevel':13,'heroes':[],'troops':[]},None):
            state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
            state['roster']=[{'tag':'#P0Y','name':'Fixture','townHallLevel':13,'warPreferenceCheckedAt':tracker.now_iso()}]
            if saved:state['profiles']['#P0Y']=saved
            calls=[]
            def get(path):
                if '/players/' in path:
                    calls.append(path);return {'tag':'#P0Y','name':'Fixture','townHallLevel':14,'heroes':[],'troops':[],'spells':[],'warPreference':'in'}
                if path.endswith('/currentwar'):return {'state':'notInWar'}
                if '/warlog' in path or '/capitalraidseasons' in path:return {'items':[]}
                if path.endswith('/leaguegroup'):return {}
                return {'tag':tracker.DEFAULT_CLAN_TAG,'name':'War Haven','members':1,'memberList':[{'tag':'#P0Y','name':'Fixture','townHallLevel':14,'role':'member'}]}
            with contextlib.redirect_stdout(io.StringIO()):tracker.refresh(state,SimpleNamespace(get=get))
            self.assertEqual(len(calls),1);self.assertEqual(state['profiles']['#P0Y']['townHallLevel'],14)

    def test_stale_or_future_final_capture_never_completes_a_watch(self):
        from datetime import timedelta
        state=fixture(final=True,observed=NOW-timedelta(minutes=1))
        self.assertNotIn('completedAt',timing.record_update(state,NOW+timedelta(minutes=6))['watches']['Regular:fixture'])
        state['wars'][0].update(endTime=timing.iso(NOW+timedelta(minutes=30)),observedAt=timing.iso(NOW+timedelta(minutes=6)))
        self.assertNotIn('completedAt',timing.record_update(state,NOW+timedelta(minutes=6))['watches']['Regular:fixture'])
        state['wars'][0].update(observedAt=timing.iso(NOW+timedelta(minutes=36)))
        self.assertIn('completedAt',timing.record_update(state,NOW+timedelta(minutes=36))['watches']['Regular:fixture'])

    def test_unchanged_archive_reuses_verified_blob_but_every_changed_field_reencrypts(self):
        initial=tracker.new_state(tracker.DEFAULT_CLAN_TAG);initial['recruiterBaseline']={'keep':'full recovery field'}
        for change,rotating in ((None,False),('notes',False),('recruiterBaseline',False),(None,True)):
            state=copy.deepcopy(initial)
            if change=='notes':state['edits']['notes']['#P0Y']={'text':'New evidence'}
            if change=='recruiterBaseline':state['recruiterBaseline']['keep']='Changed baseline'
            config={'repository':'fixture/repo','password':'synthetic archive passphrase','_history_checked':True,'_history_sha':'archive-sha','_history_fingerprint':tracker.archive_fingerprint(initial)}
            if rotating:config['_history_password']='previous archive passphrase'
            uploads=[]
            def request(config,method,path,payload=None):
                if path.endswith('/git/ref/heads/main'):return {'object':{'sha':'parent'}}
                if path.endswith('/git/commits/parent'):return {'tree':{'sha':'base-tree'}}
                if path.endswith('/git/blobs'):uploads.append(payload);return {'sha':'blob-'+str(len(uploads))}
                if path.endswith('/git/trees'):return {'sha':'new-tree'}
                if path.endswith('/git/commits'):return {'sha':'new-commit'}
                if path.endswith('/git/refs/heads/main'):return {'object':{'sha':'new-commit'}}
                raise AssertionError(path)
            with tempfile.TemporaryDirectory() as folder:
                page=Path(folder)/'index.html';page.write_text('<script id="protected-payload">{}</script>')
                with patch.object(tracker,'github_history_record',return_value={'sha':'archive-sha'}),patch.object(tracker,'github_request',side_effect=request),contextlib.redirect_stdout(io.StringIO()):
                    tracker.publish_history_commit(config,page,state,'main')
            archives=[json.loads(x['content']) for x in uploads if x['content'].startswith('{')]
            self.assertEqual(len(archives),int(change is not None or rotating))
            if archives:self.assertEqual(tracker.decrypt_history(archives[0],config['password']),state)

    def test_compression_keeps_complete_html_and_legacy_crypto_context(self):
        import gzip,re
        document='<main>'+('Retain every history item. '*5000)+'</main>'
        protected=tracker.protected_dashboard(document,'synthetic archive passphrase',100000)
        payload=json.loads(re.search(r'id="protected-payload">(.*?)</script>',protected).group(1));salt=base64.b64decode(payload['salt']);iv=base64.b64decode(payload['iv']);cipher=base64.b64decode(payload['ciphertext']);raw=hashlib.pbkdf2_hmac('sha256',b'synthetic archive passphrase',salt,payload['rounds'],64)
        self.assertTrue(hmac.compare_digest(base64.b64decode(payload['tag']),hmac.new(raw[32:],b'WarHavenDashboard:v1'+salt+iv+cipher,hashlib.sha256).digest()))
        clear=tracker.aes_cbc_decrypt(raw[:32],iv,cipher);clear=clear[:-clear[-1]]
        self.assertEqual(gzip.decompress(clear).decode(),document);self.assertLess(len(cipher),len(document.encode())/5)


if __name__=='__main__':unittest.main()
