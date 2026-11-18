import copy
import json
import unittest
from scripts.audit_storage import summarize


class StorageAuditTests(unittest.TestCase):
    def test_report_measures_sections_without_mutation_or_private_values(self):
        state = {'clanName': 'private-clan-name', 'roster': [{'tag': '#PRIVATE'}],
                 'profiles': {'#PRIVATE': {'name': 'private-player-name', 'townHallLevel': 14}},
                 'wars': [], 'raids': [], 'recruiter': {'files': {
                     'detected_leavers.json': {'players': {'#OTHER': {
                         'name': 'private-candidate-name', 'lifecycle': 'ARCHIVED',
                         'lastVerifiedAt': '2000-01-01T00:00:00Z'}}}}}}
        before = copy.deepcopy(state)
        report = summarize(state)
        expected = len(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode())
        self.assertEqual(report['total']['bytes'], expected)
        self.assertEqual(report['oldNeverJoinedCandidates']['90']['neverJoinedRecords'], 1)
        self.assertEqual(state, before)
        result = json.dumps(report)
        for private in ('#PRIVATE', '#OTHER', 'private-clan-name', 'private-player-name', 'private-candidate-name'):
            self.assertNotIn(private, result)


if __name__ == '__main__':
    unittest.main()
