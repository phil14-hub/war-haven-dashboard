"""War end + five minutes, archive continuity, deduplication and safe retry tests."""
import contextlib
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import Clash_War_Tracker as tracker
import github_collector
import github_war_check
import war_end_updates as timing
import shared_actions

NOW = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)


def fixture(end=NOW, *, kind='Regular', final=False, observed=NOW):
    war = {'id': kind + ':fixture', 'kind': kind, 'source': 'API',
           'state': 'warEnded' if final else 'inWar', 'endTime': timing.iso(end),
           'observedAt': timing.iso(observed), 'final': final,
           'rosterComplete': final}
    state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
    state.update(lastSuccessfulSync=timing.iso(observed),clanProfile={'members':1,'tag':tracker.DEFAULT_CLAN_TAG},
                 roster=[{'tag':'#P0Y','name':'Synthetic member','role':'member','townHallLevel':13}],wars=[war])
    return state


class TimingTests(unittest.TestCase):
    def test_recorded_end_time_arms_exact_five_minute_target(self):
        state = fixture(end=NOW + timedelta(hours=20))
        state['wars'][0]['state'] = 'preparation'
        schedule = timing.record_update(state, NOW)
        self.assertEqual(schedule['nextUpdateAt'], timing.iso(NOW + timedelta(hours=20, minutes=5)))

    def test_no_war_no_target(self):
        self.assertIsNone(timing.next_update({'wars': []}, NOW))

    def test_manual_and_warlog_summaries_do_not_arm_targets(self):
        state = fixture()
        for source in ('Manual', 'War log'):
            state['wars'][0]['source'] = source
            self.assertIsNone(timing.next_update(state, NOW))

    def test_cwl_and_friendly_wars_use_the_same_delay(self):
        for kind in ('CWL', 'Friendly'):
            self.assertEqual(timing.next_update(fixture(kind=kind), NOW), NOW + timedelta(minutes=5))

    def test_early_final_data_still_gets_the_requested_five_minute_update(self):
        state = fixture(final=True, observed=NOW + timedelta(minutes=1))
        self.assertEqual(timing.next_update(state, NOW + timedelta(minutes=2)), NOW + timedelta(minutes=5))

    def test_final_data_already_captured_after_target_does_not_collect_again(self):
        state = fixture(final=True, observed=NOW + timedelta(minutes=6))
        self.assertIsNone(timing.next_update(state, NOW + timedelta(minutes=7)))

    def test_record_update_never_completes_a_check_early(self):
        state = fixture(final=True, observed=NOW + timedelta(minutes=1))
        schedule = timing.record_update(state, NOW + timedelta(minutes=2))
        self.assertNotIn('completedAt', schedule['watches']['Regular:fixture'])

    def test_successful_final_check_completes_once(self):
        state = fixture(final=True, observed=NOW + timedelta(minutes=1))
        schedule = timing.record_update(state, NOW + timedelta(minutes=5))
        self.assertIn('completedAt', schedule['watches']['Regular:fixture'])
        self.assertIsNone(timing.next_update(state, NOW + timedelta(minutes=8)))

    def test_unavailable_final_details_retry_without_claiming_success(self):
        state = fixture()
        schedule = timing.record_update(state, NOW + timedelta(minutes=5))
        self.assertNotIn('completedAt', schedule['watches']['Regular:fixture'])
        self.assertEqual(schedule['nextUpdateAt'], timing.iso(NOW + timedelta(minutes=15)))

    def test_unrecoverable_old_war_does_not_trigger_forever(self):
        state = fixture()
        timing.record_update(state, NOW)
        self.assertIsNone(timing.next_update(state, NOW + timedelta(hours=7)))
        schedule = timing.plan(state, NOW + timedelta(hours=7))
        self.assertIn('expiredAt', schedule['watches']['Regular:fixture'])

    def test_planning_is_read_only(self):
        state = fixture()
        expected = copy.deepcopy(state)
        timing.plan(state, NOW)
        self.assertEqual(state, expected)

    def test_offset_time_is_compared_in_utc(self):
        state = fixture()
        state['wars'][0]['endTime'] = '2030-01-01T05:00:00-07:00'
        self.assertEqual(timing.next_update(state, NOW), NOW + timedelta(minutes=5))

    def test_encrypted_archive_merge_keeps_armed_target(self):
        state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        state.update(fixture(end=NOW + timedelta(hours=2)))
        state['lastSuccessfulSync'] = timing.iso(NOW)
        timing.record_update(state, NOW)
        encrypted = tracker.encrypt_history(state, 'fixture-only-passphrase')
        self.assertNotIn('nextUpdateAt', json.dumps(encrypted))
        decoded = tracker.decrypt_history(encrypted, 'fixture-only-passphrase')
        fresh = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        tracker.apply_snapshot(fresh, decoded)
        self.assertEqual(fresh['automaticUpdates']['postWar'], state['automaticUpdates']['postWar'])


class GateTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(shared_actions, 'ENABLED', False)
        guard.start()
        self.addCleanup(guard.stop)

    def invoke(self, state, now, *, wait=False, sleep=lambda seconds: None):
        fake = SimpleNamespace(DEFAULT_CLAN_TAG=tracker.DEFAULT_CLAN_TAG,
                               decrypt_history=lambda envelope, password: state)
        with patch.object(github_war_check, 'load_tracker', return_value=fake), \
             patch.object(Path, 'read_text', return_value='{}'), \
             contextlib.redirect_stdout(io.StringIO()):
            return github_war_check.check({'DASHBOARD_PASSWORD': 'fixture-only'},
                                          now=now, wait=wait, sleep=sleep)

    def test_gate_skips_distant_target(self):
        self.assertFalse(self.invoke(fixture(end=NOW + timedelta(hours=1)), lambda: NOW))

    def test_gate_can_wake_in_the_five_minute_grace_period(self):
        self.assertTrue(self.invoke(fixture(), lambda: NOW + timedelta(minutes=1)))

    def test_gate_waits_for_target_and_never_sleeps_more_than_thirty_seconds(self):
        clock = [NOW + timedelta(minutes=4)]
        waits = []
        def sleep(seconds):
            waits.append(seconds)
            clock[0] += timedelta(seconds=seconds)
        self.assertTrue(self.invoke(fixture(), lambda: clock[0], wait=True, sleep=sleep))
        self.assertEqual(clock[0], NOW + timedelta(minutes=5))
        self.assertEqual(sum(waits), 60)
        self.assertLessEqual(max(waits), 30)

    def test_wrong_clan_does_not_schedule_collection(self):
        state = fixture()
        state['clanTag'] = '#OTHER'
        with self.assertRaises(ValueError):
            self.invoke(state, lambda: NOW)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(shared_actions, 'ENABLED', False)
        guard.start()
        self.addCleanup(guard.stop)

    ENV = {'COC_API_TOKEN': 'fixture-key', 'DASHBOARD_PASSWORD': 'fixture-passphrase',
           'DASHBOARD_PUBLISH_TOKEN': 'fixture-token',
           'GITHUB_REPOSITORY': 'phil14-hub/war-haven-dashboard'}

    def fake_tracker(self, state):
        published = []
        calls = []
        def refresh(candidate, api):
            calls.append('refresh')
            for war in candidate.get('wars', []):
                war.update(state='warEnded', final=True, rosterComplete=True,
                           observedAt=timing.iso(datetime.now(timezone.utc)))
        def publish(config, path, state):
            published.append(copy.deepcopy(state))
            return {'published': True}
        return SimpleNamespace(
            DEFAULT_CLAN_TAG=tracker.DEFAULT_CLAN_TAG,
            new_state=lambda clan: {'clanTag': clan},
            pull_github_history=lambda fresh, config: fresh.update(copy.deepcopy(state)),
            OfficialAPI=lambda tokens: object(), refresh=refresh,
            now_iso=lambda: timing.iso(datetime.now(timezone.utc)),
            write_dashboard=lambda state, path, password: path.write_text('encrypted fixture'),
            publish_dashboard=publish,
            normalize_tag=tracker.normalize_tag,league_placement=tracker.league_placement,
            army_progress=tracker.army_progress,clan_badge_url=tracker.clan_badge_url,
            TRACKER_JS=tracker.TRACKER_JS,
        ), published, calls

    def test_post_war_run_rechecks_latest_archive_and_skips_duplicate(self):
        now = datetime.now(timezone.utc)
        state = fixture(end=now - timedelta(minutes=10), final=True, observed=now)
        fake, published, calls = self.fake_tracker(state)
        with contextlib.redirect_stdout(io.StringIO()):
            result = github_collector.run(self.ENV, fake, post_war=True)
        self.assertTrue(result['skipped'])
        self.assertEqual(published, [])
        self.assertEqual(calls, [])

    def test_post_war_run_preserves_recruiter_and_saves_final_result(self):
        now = datetime.now(timezone.utc)
        state = fixture(end=now - timedelta(minutes=6), observed=now - timedelta(minutes=8))
        state['recruiter'] = {'retained': 'existing scan'}
        fake, published, calls = self.fake_tracker(state)
        recruiter = SimpleNamespace(refresh=lambda *args: self.fail('Post-war update should retain recruiter'))
        with patch.dict(sys.modules, {'github_recruiter': recruiter}), \
             contextlib.redirect_stdout(io.StringIO()):
            result = github_collector.run(self.ENV, fake, post_war=True)
        self.assertTrue(result['published'])
        self.assertEqual(calls, ['refresh'])
        self.assertEqual(published[0]['recruiter'], state['recruiter'])
        self.assertIsNone(published[0]['automaticUpdates']['postWar']['nextUpdateAt'])
        self.assertEqual(published[0]['automaticUpdates']['lastRunKind'], 'after-war')


if __name__ == '__main__':
    unittest.main()
