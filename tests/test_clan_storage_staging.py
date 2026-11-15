import base64
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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
    def __init__(self):
        self.index = None
        self.releases = {}
        self.objects = {}
        self.backup = None
        self.events = []
        self.timeout_after_commit = False

    def request(self, path, payload=None, *, method='POST', body=None, extra_headers=None):
        endpoint, _, raw = path.partition('?')
        self.events.append((method, endpoint, raw, len(body or b'')))
        if endpoint == shared_actions.CLAN_STORAGE_STAGING_BACKUP_PATH:
            if method == 'HEAD':
                return self.backup is not None
            if method == 'GET':
                return self.backup
            self.backup = dict(body=body, sha256=extra_headers['X-Archive-SHA256'],
                               source=extra_headers['X-Archive-Source'], revision=extra_headers['X-Archive-Revision'])
            return {k: v for k, v in self.backup.items() if k != 'body'} | dict(status='saved', reused=False, bytes=len(body), day='2030-01-01')
        if endpoint != shared_actions.CLAN_STORAGE_STAGING_PATH:
            raise AssertionError('Staging must not send requests to live dashboard routes.')
        if raw:
            pairs = parse_qs(raw)
            if 'revision' in pairs:
                return {'index': self.releases[pairs['revision'][0]]}
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
