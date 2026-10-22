"""Regressions for non-clan publications and the rolling recruitment queue."""
import copy
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import Clash_War_Tracker as tracker
import Clash_Recruitment as recruiter
import github_recruiter
from tests.test_upgrade_progress import profile


class RestoredProgressTests(unittest.TestCase):
    def test_native_report_does_not_duplicate_legacy_card_html(self):
        saved = tracker.new_state('#P0Y')
        report = {'html': '<!doctype html><h1>Legacy report</h1>', 'version': 1,
                  'updatedAt': '2030-01-01T00:00:00Z',
                  'groups': {'new': [{'tag': '#P0Q'}], 'still': [], 'joined_my': [], 'no_longer': []}}
        saved['recruiter'] = {'report': copy.deepcopy(report)}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'dashboard.html'
            tracker.write_dashboard(saved, target)
            content = target.read_text()
        browser = json.loads(re.search(r'id="recruiter-data" type="application/json">(.*?)</script>', content).group(1))
        self.assertNotIn('html', browser)
        self.assertEqual(browser['groups'], report['groups'])
        self.assertEqual(saved['recruiter']['report'], report)

    def test_archive_restore_rebuilds_army_without_api_or_fresh_timestamp(self):
        saved = tracker.new_state('#P0Y')
        saved['profiles'] = {'#P0Q': profile(18), '#P0R': profile(14, 13)}
        tracker.capture_progression(saved)
        expected = copy.deepcopy(saved['memberProgress'])
        restored = tracker.new_state('#P0Y')
        tracker.apply_snapshot(restored, saved)
        self.assertEqual(restored['memberProgress'], expected)
        for _ in range(2):
            next_state = tracker.new_state('#P0Y')
            tracker.apply_snapshot(next_state, restored)
            restored = next_state
        self.assertEqual(restored['memberProgressHistory'], saved['memberProgressHistory'])
        self.assertEqual(restored['memberProgress'], expected)

    def test_render_repairs_legacy_missing_or_stale_derived_progress(self):
        saved = tracker.new_state('#P0Y')
        saved['profiles'] = {'#P0Q': profile(18)}
        saved['memberProgress'] = {'#P0Q': {'method': 'obsolete', 'percent': 0}}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'dashboard.html'
            tracker.write_dashboard(saved, target)
            document = target.read_text()
        data = json.loads(re.search(r'id="war-data" type="application/json">(.*?)</script>', document).group(1))
        self.assertEqual(data['memberProgress']['#P0Q']['completionPercent'], 100)
        self.assertEqual(data['memberProgress']['#P0Q']['at'], saved['profiles']['#P0Q']['profileCheckedAt'])
        self.assertNotIn('#P0R', data['memberProgress'])
        del saved['profiles']['#P0Q']['heroes']
        tracker.capture_progression(saved)
        self.assertIsNone(saved['memberProgress']['#P0Q']['completionPercent'])


class RecruitRetentionTests(unittest.TestCase):
    def test_ever_joined_history_outlives_seven_day_candidate_cards(self):
        joined=self.rec(401,days=30,lifecycle='JOINED_MY_CLAN')
        left=self.rec(402,days=60,lifecycle='JOINED_OTHER_CLAN')
        for row in (joined,left):row['joinedMyClanAt']=(self.now-timedelta(days=20)).isoformat()
        store={'players':{row['tag']:row for row in (joined,left)}}
        before=copy.deepcopy(store)
        with patch.object(recruiter,'utc_now',return_value=self.now):
            groups=recruiter.build_result_groups(store,self.filters,7,7,50)
        self.assertEqual(len(groups['ever_joined']),2)
        self.assertFalse(groups['new'] or groups['still'] or groups['joined_my'] or groups['no_longer'])
        self.assertEqual(store,before)

    def setUp(self):
        self.now = datetime(2030, 1, 10, tzinfo=timezone.utc)
        self.filters = dict(min_th=11, min_war_stars=0, min_best_trophies=0,
                            min_current_trophies=0, min_exp_level=0)

    def rec(self, i, days=1, lifecycle='STILL_CLANLESS'):
        detected = (self.now - timedelta(days=days)).isoformat()
        return {'tag': '#P' + format(i, 'b').replace('0', 'P').replace('1', 'Q'),
                'townHallLevel': 14, 'name': 'Synthetic recruit', 'lifecycle': lifecycle,
                'detectedAt': detected, 'lastDepartureDetectedAt': detected,
                'lastVerifiedAt': self.now.isoformat(), 'lastStatusChangedAt': self.now.isoformat()}

    def test_more_than_fifty_recent_players_stay_and_history_is_not_deleted(self):
        players = {r['tag']: r for r in (self.rec(i, days=1 + i % 6) for i in range(140))}
        for i, lifecycle in enumerate(['NEW', 'STILL_CLANLESS', 'JOINED_MY_CLAN', 'JOINED_OTHER_CLAN', 'VERIFY_ERROR', 'ARCHIVED'], 200):
            r = self.rec(i, days=8, lifecycle=lifecycle)
            players[r['tag']] = r
        edge = self.rec(300, days=7)
        players[edge['tag']] = edge
        store = {'players': players}
        before = copy.deepcopy(store)
        with patch.object(recruiter, 'utc_now', return_value=self.now):
            groups = recruiter.build_result_groups(store, self.filters, 7, 7, 50)
        self.assertEqual(len(groups['still']), 141)
        self.assertFalse(groups['joined_my'])
        self.assertFalse(groups['no_longer'])
        self.assertEqual(store, before)

    def test_code_release_recovers_overflow_from_archive_without_a_scan(self):
        players = {r['tag']: r for r in (self.rec(i) for i in range(125))}
        state = {'recruiter': {'updatedAt': '2030-01-09T00:00:00Z', 'files': {
            'detected_leavers.json': {'players': players},
            'last_run_stats.json': {'filters': self.filters}},
            'report': {'version': 1, 'updatedAt': '2030-01-09T00:00:00Z', 'groups': {'still': []}}}}
        before = copy.deepcopy(state['recruiter']['files'])
        with patch.object(recruiter, 'utc_now', return_value=self.now):
            github_recruiter.rebuild_report(state, module=recruiter)
        self.assertEqual(len(state['recruiter']['report']['groups']['still']), 125)
        self.assertEqual(state['recruiter']['report']['updatedAt'], '2030-01-09T00:00:00Z')
        self.assertEqual(state['recruiter']['files'], before)
        self.assertEqual(state['recruiterSummary']['availableCandidates'], 125)


if __name__ == '__main__':
    unittest.main()
