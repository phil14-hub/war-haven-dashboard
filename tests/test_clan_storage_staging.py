import base64
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

import clan_storage
import github_collector
import github_recruitment_collector
import github_render_dashboard
import github_stage_pages
import github_sync_portal
import github_war_check
import member_exports
import raid_history_recovery
import shared_actions
import tracker_core as tracker
from war_end_updates import iso


SOURCE = 'a' * 40
PASSWORD = 'synthetic staging passphrase'
ENV = {'GITHUB_REPOSITORY': 'phil14-hub/war-haven-dashboard', 'DASHBOARD_PASSWORD': PASSWORD,
       'DASHBOARD_PUBLISH_TOKEN': 'fixture', 'COC_API_TOKEN': 'fixture', 'WAR_HAVEN_CLAN_STORAGE_STAGE': 'true'}


class MemoryStorage:
    def __init__(self, *, production=False):
        self.path = shared_actions.CLAN_STORAGE_PATH if production else shared_actions.CLAN_STORAGE_STAGING_PATH
        self.backup_path = shared_actions.CLAN_STORAGE_BACKUP_PATH if production else shared_actions.CLAN_STORAGE_STAGING_BACKUP_PATH
        self.production = production
        self.publication_source = None
        self.index = None
        self.releases = {}
        self.passwords = {}
        self.objects = {}
        self.backup = None
        self.events = []
        self.timeout_after_commit = False

    def request(self, path, payload=None, *, method='POST', body=None, extra_headers=None):
        endpoint, _, raw = path.partition('?')
        self.events.append((method, endpoint, raw, len(body or b'')))
        if endpoint == self.backup_path:
            if method == 'HEAD':
                return self.backup is not None
            if method == 'GET':
                return self.backup
            self.backup = dict(body=body, sha256=extra_headers['X-Archive-SHA256'],
                               source=extra_headers['X-Archive-Source'], revision=extra_headers['X-Archive-Revision'])
            return {k: v for k, v in self.backup.items() if k != 'body'} | dict(status='saved', reused=False, bytes=len(body), day='2030-01-01')
        if self.production and endpoint == '/members/api/publication-source':
            if payload.get('read'):
                return {'source': self.publication_source}
            self.publication_source = {**payload['source'], 'publication': payload['publication']}
            return {'source': self.publication_source}
        if self.production and endpoint == '/v1/refresh/reconcile':
            return {}
        if endpoint != self.path:
            raise AssertionError('Staging must not send requests to live dashboard routes.')
        if raw:
            pairs = parse_qs(raw)
            if 'revision' in pairs:
                return {'index': self.releases[pairs['revision'][0]]}
            if 'credential' in pairs:
                selected = pairs['credential'][0]
                return {'revision': selected, 'password': self.passwords[selected]}
            key = (pairs['kind'][0], pairs['sha256'][0])
            if method == 'HEAD':
                return key in self.objects
            if method == 'PUT':
                self.objects[key] = body
                return clan_storage.reference(body)
            return {'body': self.objects[key], 'sha256': key[1]}
        if method == 'GET':
            if self.index is None:
                raise shared_actions.SharedActionsError('Missing staged release', status=404)
            return {'index': self.index}
        previous = self.index['revision'] if self.index else None
        if previous != payload['expectedRevision']:
            raise shared_actions.SharedActionsError('Concurrent update', status=409)
        value = dict(version=1, previousRevision=previous, source=payload['source'], nextWarUpdateAt=payload['nextWarUpdateAt'],
                     archive=payload['archive'], page=payload['page'])
        value['revision'] = hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()
        self.index = value
        self.releases[value['revision']] = value
        if self.timeout_after_commit:
            self.timeout_after_commit = False
            raise shared_actions.SharedActionsError('Lost response')
        return {'index': value}


def git_record(data):
    digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    return {'sha': digest, 'content': base64.encodebytes(data).decode(), 'encoding': 'base64'}


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.transport = MemoryStorage()
        self.storage = clan_storage.StagedClanStorage(self.transport)
        candidate = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        candidate.update(lastSuccessfulSync='2030-01-01T11:00:00Z', clanProfile={'tag': tracker.DEFAULT_CLAN_TAG, 'members': 1},
                         roster=[{'name': 'Fixture player', 'tag': '#P0Y', 'role': 'member', 'townHallLevel': 13, 'donations': 10}])
        candidate['edits']['notes']['#P0Y'] = {'text': 'Saved fixture note'}
        candidate['raids'] = [{'id': 'prior-raid', 'state': 'ended', 'startTime': '2029-12-29T08:00:00Z',
                               'endTime': '2029-12-31T08:00:00Z', 'members': [{'tag': '#P0Y', 'attacks': 5, 'capitalResourcesLooted': 8800}]}]
        candidate['recruiterStatus'] = {'ok': True, 'lastAttemptAt': '2030-01-01T10:00:00Z'}
        tracker_api = patch.object(tracker, 'github_request', side_effect=AssertionError('Unexpected Git request.'))
        tracker_api.start()
        self.addCleanup(tracker_api.stop)
        for module in (github_collector, github_recruitment_collector, github_render_dashboard, github_sync_portal, github_war_check):
            context = patch.object(module, 'StagedClanStorage', return_value=self.storage)
            context.start()
            self.addCleanup(context.stop)
        for module, key in ((tracker, 'publish_dashboard'), (member_exports, 'publish'), (shared_actions, 'UpdateRequest')):
            context = patch.object(module, key, side_effect=AssertionError('Staging must not modify live publication or progress.'))
            context.start()
            self.addCleanup(context.stop)
        recovery = patch.object(raid_history_recovery, 'recover', return_value=0)
        recovery.start()
        self.addCleanup(recovery.stop)
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / 'index.html'
            tracker.write_dashboard(candidate, page, password=PASSWORD)
            self.page = page.read_bytes()
        self.original = candidate
        self.archive = json.dumps(tracker.encrypt_history(candidate, PASSWORD, rounds=100000)).encode()

    def seed(self):
        git_archive, git_page = git_record(self.archive), git_record(self.page)
        lookup = {'/git/ref/heads/main': {'object': {'sha': SOURCE}},
                  '/contents/index.html?ref=' + SOURCE: git_page,
                  '/git/blobs/' + git_archive['sha']: git_archive, '/git/blobs/' + git_page['sha']: git_page}
        prefix = '/repos/' + ENV['GITHUB_REPOSITORY']

        def git(_config, method, path):
            self.assertEqual(method, 'GET')
            return lookup[path.removeprefix(prefix)]

        with patch.object(tracker, 'github_request', side_effect=git), patch.object(tracker, 'github_history_record', return_value=git_archive) as history:
            result = github_sync_portal.run(ENV, tracker, seed_staging=True)
            self.assertEqual(history.call_args.kwargs['ref'], SOURCE)
        return result

    def test_collectors_retry_and_daily_restore_preserve_the_saved_data(self):
        self.transport.timeout_after_commit = True
        initial = self.seed()
        self.assertEqual(len(self.transport.objects), 2)
        self.assertEqual(self.storage.restore(tracker, PASSWORD)[2], self.original)
        self.assertEqual(github_sync_portal.run(ENV, tracker), initial)
        self.assertEqual(github_sync_portal.run(ENV, tracker, seed_staging=True), initial)
        self.assertEqual(len(self.transport.objects), 2)

        def refresh(state, _api):
            state['roster'][0]['donations'] += 7
            state['lastSuccessfulSync'] = '2030-01-01T12:00:00Z'

        def recruit(state, *_args):
            state['recruiterStatus']['lastAttemptAt'] = '2030-01-01T13:00:00Z'

        with patch.object(tracker, 'refresh', side_effect=refresh) as clash, patch.object(github_recruitment_collector.github_recruiter, 'refresh', side_effect=recruit) as recruiter:
            clan = github_collector.run(ENV, tracker)
            recruiter.assert_not_called()
            _, _, after_clan = self.storage.restore(tracker, PASSWORD)
            self.assertEqual(after_clan['roster'][0]['donations'], 17)
            self.assertEqual(after_clan['recruiterStatus'], self.original['recruiterStatus'])
            recruit_run = github_recruitment_collector.run(ENV, tracker)
            _, _, after_recruiter = self.storage.restore(tracker, PASSWORD)
            self.assertEqual(after_recruiter['roster'], after_clan['roster'])
            self.assertEqual(after_recruiter['recruiterStatus']['lastAttemptAt'], '2030-01-01T13:00:00Z')
            self.assertNotEqual(recruit_run['stagedRevision'], clan['stagedRevision'])
            for key in ('raids', 'edits'):
                self.assertEqual(after_recruiter[key], self.original[key])
            before_rebuild = self.storage.current()
            github_render_dashboard.run(ENV, tracker)
            self.assertEqual(self.storage.current()['archive'], before_rebuild['archive'])
            objects = len(self.transport.objects)
            for _ in range(2):
                github_sync_portal.run(ENV, tracker)
                github_sync_portal.run(ENV, tracker, verify_backup=True)
            self.assertEqual(len(self.transport.objects), objects)
            self.assertEqual(sum(method == 'POST' and endpoint == shared_actions.CLAN_STORAGE_STAGING_BACKUP_PATH
                                 for method, endpoint, *_ in self.transport.events), 1)
            clash.assert_called_once()
            recruiter.assert_called_once()

    def test_watcher_uses_only_small_index_and_capture_rechecks_archive(self):
        self.seed()
        current = self.storage.current()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.storage.store(current, SOURCE, now + timedelta(minutes=3), self.archive, self.page)
        self.transport.events.clear()
        self.assertTrue(github_war_check.check(ENV, now=lambda: now))
        self.assertEqual(self.transport.events, [('GET', shared_actions.CLAN_STORAGE_STAGING_PATH, '', 0)])
        self.assertFalse(github_war_check.check(ENV, wait=True, now=lambda: now))
        self.assertTrue(any('kind=archive' in raw for _, _, raw, _ in self.transport.events))
        with patch.object(tracker, 'refresh', side_effect=AssertionError('No due capture.')):
            self.assertTrue(github_collector.run(ENV, tracker, post_war=True)['skipped'])

        ready = copy.deepcopy(self.original)
        ready['lastSuccessfulSync'] = iso(now)
        ready['wars'] = [dict(id='due-war', kind='Regular', source='API', state='inWar', endTime=iso(now - timedelta(minutes=6)),
                              attacksPerMember=2, participants=[], rosterComplete=False, final=False)]
        archive = json.dumps(tracker.encrypt_history(ready, PASSWORD, rounds=100000)).encode()
        self.storage.store(self.storage.current(), SOURCE, now - timedelta(minutes=1), archive, self.page)
        self.assertTrue(github_war_check.check(ENV, wait=True, now=lambda: now))

        def finish_war(state, _api):
            state['wars'][0].update(state='warEnded', observedAt=iso(now), rosterComplete=True, final=True)

        with patch.object(tracker, 'refresh', side_effect=finish_war) as clash:
            github_collector.run(ENV, tracker, post_war=True)
            self.assertTrue(github_collector.run(ENV, tracker, post_war=True)['skipped'])
            clash.assert_called_once()
        _, _, restored = self.storage.restore(tracker, PASSWORD)
        self.assertTrue(restored['wars'][0]['final'])
        self.assertEqual(restored['raids'], ready['raids'])

    def test_wrong_password_or_damaged_content_fails_before_collection(self):
        self.seed()
        with patch.object(tracker, 'refresh', side_effect=AssertionError('Collection preceded archive verification.')):
            with self.assertRaisesRegex(ValueError, 'passphrase'):
                github_collector.run({**ENV, 'DASHBOARD_PASSWORD': 'wrong fixture password'}, tracker)
            saved = self.storage.current()
            self.transport.objects['archive', saved['archive']['sha256']] += b' '
            with self.assertRaisesRegex(ValueError, 'failed verification'):
                github_collector.run(ENV, tracker)

    def test_pages_build_reuses_a_pinned_release_after_the_current_release_changes(self):
        original = self.seed()['stagedRevision']
        next_page = self.page + b'\n'
        next_release = self.storage.store(self.storage.current(), SOURCE, None, self.archive, next_page)
        with tempfile.TemporaryDirectory() as folder:
            exact = Path(folder) / 'exact'
            self.assertEqual(github_stage_pages.stage_pages(exact, original, self.storage), original)
            self.assertEqual((exact / 'index.html').read_bytes(), self.page)
            self.assertEqual({path.name for path in exact.iterdir()}, {'index.html', '.nojekyll'})
            latest = Path(folder) / 'latest'
            self.assertEqual(github_stage_pages.stage_pages(latest, storage=self.storage), next_release['revision'])
            self.assertEqual((latest / 'index.html').read_bytes(), next_page)
            self.transport.objects['page', next_release['page']['sha256']] = b'invalid'
            with self.assertRaisesRegex(ValueError, 'failed verification'):
                github_stage_pages.stage_pages(Path(folder) / 'invalid', storage=self.storage)
            self.assertFalse((Path(folder) / 'invalid').exists())

    def test_production_pages_requires_the_exact_verified_release(self):
        revision = 'a' * 64
        client = Mock()
        response = {'body': self.page, 'sha256': hashlib.sha256(self.page).hexdigest(), 'revision': revision}
        client.request.return_value = response
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'verified'
            self.assertEqual(github_stage_pages.stage_production_pages(out, revision, client), revision)
            client.request.assert_called_once_with(shared_actions.CLAN_STORAGE_PAGES_PATH + '?revision=' + revision, method='GET')
            self.assertEqual((out / 'index.html').read_bytes(), self.page)
            self.assertEqual({path.name for path in out.iterdir()}, {'index.html', '.nojekyll'})
            invalid = Path(folder) / 'invalid'
            for mismatch in ({'sha256': 'b' * 64}, {'revision': 'b' * 64}):
                client.request.return_value = {**response, **mismatch}
                with self.assertRaisesRegex(ValueError, 'did not verify'):
                    github_stage_pages.stage_production_pages(invalid, revision, client)
                self.assertFalse(invalid.exists())
            for unpinned in (None, 'main'):
                with self.assertRaisesRegex(ValueError, 'exact R2 release'):
                    github_stage_pages.stage_production_pages(invalid, unpinned, client)

    def test_production_collectors_complete_independently_of_pages_and_retry_from_r2(self):
        env = {**ENV, 'WAR_HAVEN_CLAN_STORAGE_STAGE': 'false', 'WAR_HAVEN_CLAN_STORAGE_R2': 'true'}
        transport = MemoryStorage(production=True)
        storage = clan_storage.StagedClanStorage(transport, production=True)
        storage.store(None, SOURCE, None, self.archive, self.page)
        request = Mock()
        request.client = transport

        def clan_refresh(state, _api):
            state['roster'][0]['donations'] += 7
            state['lastSuccessfulSync'] = '2030-01-01T12:00:00Z'

        def recruiter_refresh(state, *_args):
            state['recruiterStatus']['lastAttemptAt'] = '2030-01-01T13:00:00Z'

        def factories(module):
            return patch.object(module, 'StagedClanStorage', return_value=storage)

        with (factories(github_collector), factories(github_recruitment_collector),
              factories(github_render_dashboard), factories(github_sync_portal),
              patch.object(shared_actions, 'Client', return_value=transport),
              patch.object(shared_actions, 'pending', return_value=None),
              patch.object(shared_actions, 'UpdateRequest', return_value=request),
              patch.object(shared_actions, 'pull'),
              patch.object(tracker, 'refresh', side_effect=clan_refresh) as clash,
              patch.object(github_recruitment_collector.github_recruiter, 'refresh', side_effect=recruiter_refresh) as recruit,
              patch.object(member_exports, 'publish', side_effect=[shared_actions.SharedActionsError('Offline'),
                           {'publication': 'recovered'}, {'publication': 'recruited'}, {'publication': 'rebuilt'}]) as publish):
            result = github_collector.run(env, tracker)
            self.assertEqual(result['components'], {'backup': True, 'github': False, 'portal': False})
            self.assertTrue(result['partial'])
            request.finish.assert_called_with(result)
            self.assertEqual(storage.current()['revision'], result['r2Revision'])
            self.assertEqual(storage.restore(tracker, PASSWORD)[2]['roster'][0]['donations'], 17)
            self.assertEqual(github_sync_portal.run(env, tracker)['publication'], 'recovered')
            self.assertTrue(github_sync_portal.run(env, tracker)['reused'])
            self.assertEqual(publish.call_count, 2)
            self.assertEqual(transport.publication_source['r2Revision'], result['r2Revision'])
            recruited = github_recruitment_collector.run(env, tracker)
            self.assertEqual(recruited['components'], {'backup': True, 'github': False, 'portal': True})
            self.assertFalse(recruited['partial'])
            before = storage.current()
            self.assertTrue(github_render_dashboard.run(env, tracker)['components']['portal'])
            self.assertEqual(storage.current()['archive'], before['archive'])
            for _ in range(2):
                github_sync_portal.run(env, tracker, verify_backup=True)
            self.assertEqual(transport.backup['revision'], storage.current()['revision'])
            self.assertEqual(sum(event[:2] == ('POST', transport.backup_path) for event in transport.events), 1)
            self.assertEqual(storage.restore(tracker, PASSWORD)[2]['raids'], self.original['raids'])
            clash.assert_called_once()
            recruit.assert_called_once()

    def test_production_seed_checks_the_pinned_git_head_and_never_replaces_r2(self):
        env = {**ENV, 'WAR_HAVEN_CLAN_STORAGE_STAGE': 'false', 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_EVENT_NAME': 'workflow_dispatch'}
        transport = MemoryStorage(production=True)
        storage = clan_storage.StagedClanStorage(transport, production=True)
        archive, page = git_record(self.archive), git_record(self.page)
        endings = {f'/contents/index.html?ref={SOURCE}': page,
                   f"/git/blobs/{archive['sha']}": archive, f"/git/blobs/{page['sha']}": page}
        head = [SOURCE, 'b' * 40]

        def git(_config, method, path):
            self.assertEqual(method, 'GET')
            if path.endswith('/git/ref/heads/main'):
                return {'object': {'sha': head.pop(0) if len(head) > 1 else head[0]}}
            return endings[path.removeprefix('/repos/' + ENV['GITHUB_REPOSITORY'])]

        with (patch.object(github_sync_portal, 'StagedClanStorage', return_value=storage),
              patch.object(tracker, 'github_request', side_effect=git),
              patch.object(tracker, 'github_history_record', return_value=archive)):
            with self.assertRaisesRegex(ValueError, 'Main advanced'):
                github_sync_portal.run(env, tracker, seed_revision=SOURCE)
            self.assertIsNone(storage.current(allow_empty=True))
            self.assertFalse(transport.objects)
            head[:] = [SOURCE]
            seeded = github_sync_portal.run(env, tracker, seed_revision=SOURCE)
            self.assertEqual(github_sync_portal.run(env, tracker, seed_revision=SOURCE), seeded)
            advanced = storage.store(seeded, SOURCE, None, self.archive, self.page + b'\n')
            with self.assertRaisesRegex(ValueError, 'differs from the checkpoint'):
                github_sync_portal.run(env, tracker, seed_revision=SOURCE)
            self.assertEqual(storage.current(), advanced)
            with self.assertRaisesRegex(ValueError, 'manually dispatched main'):
                github_sync_portal.run({**env, 'GITHUB_EVENT_NAME': 'schedule'}, tracker, seed_revision=SOURCE)

    def test_rotated_release_keeps_collector_and_historical_backup_credentials_separate(self):
        original = self.seed()['stagedRevision']
        github_sync_portal.run(ENV, tracker, verify_backup=True)
        new_password = 'replacement synthetic passphrase'
        rotated = json.dumps(tracker.encrypt_history(self.original, new_password, rounds=100000)).encode()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'index.html'
            tracker.write_dashboard(copy.deepcopy(self.original), path, password=new_password)
            index = self.storage.store(self.storage.current(), SOURCE, None, rotated, path.read_bytes())
        index.pop('revision')
        index['collectorCredential'] = {'rotationOf': original, 'sealed': 'A' * 60}
        index['revision'] = hashlib.sha256(json.dumps(index, separators=(',', ':')).encode()).hexdigest()
        self.transport.index = index
        self.transport.releases[index['revision']] = index
        self.transport.passwords[index['revision']] = new_password
        self.assertEqual(self.storage.restore(tracker, PASSWORD)[2], self.original)
        self.assertEqual(github_sync_portal.run(ENV, tracker)['stagedRevision'], index['revision'])
        self.assertEqual(github_sync_portal.read_clan_archive_backup(ENV | {'password': PASSWORD}, tracker,
                          self.storage.client, staged=True), self.archive)
