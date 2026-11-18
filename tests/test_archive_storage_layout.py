"""Lossless, self-contained packing of all recruiting evidence and derived caches."""
import copy
import json
import unittest
import tracker_core as tracker
from github_recruiter import compact_report


class ArchiveStorageLayoutTests(unittest.TestCase):
    def fixture(self):
        state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        state['recruiter'] = {'format': 1, 'files': {'detected_leavers.json': {'players': {
            '#P0Y': {'lifecycle': 'ARCHIVED', 'joinedMyClanAt': '2026-01-01T00:00:00Z',
                      'events': [{'at': '2026-01-01', 'type': 'verification', 'detail': 'full evidence ' * 50} for _ in range(100)]}}}},
                              'unknownFutureField': ['retain this too']}
        state['memberProgress'] = {'#P0Y': {'legacyCalculation': list(range(2500))}}
        state['wars'] = [{'final': True, 'stars': 54, 'opponentStars': 46, 'reportedAttacks': 33, 'expEarned': 350}]
        state['memberHistory'] = {'departed': {'capital': 123456, 'donations': [10, 20]}}
        return state

    def test_complete_round_trip_no_mutation_and_size_reduction(self):
        state = self.fixture()
        before = copy.deepcopy(state)
        packed = tracker.archive_document(state)
        self.assertEqual(state, before)
        self.assertLess(len(json.dumps(packed)), len(json.dumps(state)) / 3)
        self.assertEqual(tracker.restore_archive_document(packed), before)
        encrypted = tracker.encrypt_history(state, 'fixture-passphrase', rounds=100000)
        self.assertEqual(encrypted['version'], 2)
        self.assertEqual(tracker.decrypt_history(encrypted, 'fixture-passphrase'), before)
        self.assertEqual(state, before)

    def test_checksums_and_expansion_bounds_fail_closed(self):
        for field in ('sha256', 'bytes'):
            packed = tracker.archive_document(self.fixture())
            packed['_archiveStorage']['sections']['recruiter'][field] = '0' * 64 if field == 'sha256' else 1
            with self.assertRaises(ValueError):
                tracker.restore_archive_document(packed)
        packed = tracker.archive_document(self.fixture())
        packed['_archiveStorage']['sections']['recruiter']['bytes'] = tracker.MAX_STATE_BYTES + 1
        with self.assertRaises(ValueError):
            tracker.restore_archive_document(packed)

    def test_old_archive_is_still_supported(self):
        # The cryptographic v1 envelope uses identical authenticated clear bytes.
        old = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        envelope = tracker.encrypt_history(old, 'fixture-passphrase', rounds=100000)
        envelope['version'] = 1
        self.assertEqual(tracker.decrypt_history(envelope, 'fixture-passphrase'), old)

    def test_relative_words_are_not_persisted_as_history(self):
        report = {'version': 1, 'groups': {'new': [{'detectedAt': '2026-11-17T00:00:00Z', 'detectedAgo': 'one day', 'freshness': 'new', 'lastVerifiedAt': '2026-11-18T00:00:00Z'}], 'still': [], 'joined_my': [], 'no_longer': []}}
        before = copy.deepcopy(report)
        compact = compact_report(report)
        self.assertNotIn('detectedAgo', compact['groups']['new'][0])
        self.assertNotIn('freshness', compact['groups']['new'][0])
        self.assertEqual(compact['groups']['new'][0]['lastVerifiedAt'], report['groups']['new'][0]['lastVerifiedAt'])
        self.assertEqual(report, before)


if __name__ == '__main__':
    unittest.main()
