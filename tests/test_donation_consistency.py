import contextlib
import copy
import io
import unittest
from unittest.mock import patch

import Clash_War_Tracker as tracker
import member_exports
import snapshot_audit


class DonationConsistencyTests(unittest.TestCase):
    def state(self):
        state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        state.update(lastSuccessfulSync='2026-10-19T21:00:00Z', clanProfile={'members': 3}, roster=[
            {'tag':'#P0Q', 'name':'BOBY fixture', 'townHallLevel':18, 'role':'member', 'donations':1026, 'donationsReceived':320, 'trophies':3000},
            {'tag':'#P0Y', 'name':'Zero fixture', 'townHallLevel':14, 'role':'admin', 'donations':0, 'donationsReceived':0},
            {'tag':'#P0U', 'name':'Unknown fixture', 'townHallLevel':12, 'role':'member'}])
        state['profiles']['#P0Q'] = {'townHallLevel':18, 'donations':709, 'donationsReceived':100, 'trophies':2000}
        state['memberHistory'] = {'#P0Q': {'since':'2026-10-14T17:59:45Z', 'lastSeen':state['lastSuccessfulSync'],
            'donationIntervals':[{'start':'2026-10-14T17:59:45Z', 'end':state['lastSuccessfulSync'], 'count':317}],
            'capitalSamples':[{'at':'2026-10-14T17:59:45Z', 'total':208000}, {'at':state['lastSuccessfulSync'], 'total':208000}]},
            '#P0Y': {'since':'2026-10-19T20:00:00Z', 'lastSeen':state['lastSuccessfulSync']}}
        state['wars'] = [{'id':'war', 'kind':'Regular', 'final':True, 'rosterComplete':True, 'attacksPerMember':2,
            'endTime':'2026-10-18T21:00:00Z', 'participants':[
                {'tag':'#P0Q','attacksUsed':2,'attacks':[{'order':1,'stars':3,'destructionPercentage':100}, {'order':1,'stars':3,'destructionPercentage':100}, {'order':2,'stars':2,'destructionPercentage':70}]},
                {'tag':'#P0Y','attacksUsed':0}]}]
        state['edits']['exceptions']['war::#P0Y'] = {'value':True}
        return state

    def test_boby_scope_difference_keeps_game_counter_and_observed_history(self):
        view = member_exports.build_snapshot(self.state(), tracker)['members']['#P0Q']
        self.assertEqual(view['seasonDonations'], 1026)
        self.assertEqual(view['donationsReceived'], 320)
        self.assertEqual(view['trophies'], 3000)
        self.assertEqual(view['observedDonations'], {'total':317, 'since':'2026-10-14T17:59:45Z'})
        self.assertEqual(view['capitalGold'], 0)

    def test_tracked_zero_and_missing_history_are_distinct(self):
        views = member_exports.build_snapshot(self.state(), tracker)['members']
        self.assertEqual(views['#P0Y']['observedDonations']['total'], 0)
        self.assertIsNone(views['#P0U']['observedDonations']['total'])
        self.assertIsNone(views['#P0U']['seasonDonations'])

    def test_independent_audit_covers_entire_roster_and_other_metrics(self):
        with contextlib.redirect_stdout(io.StringIO()):
            result = snapshot_audit.verify(self.state(), tracker)
        self.assertEqual(result, {'members':3, 'checkedFields':51, 'scopeDifferences':1})

    def test_audit_rejects_a_different_season_value_in_a_profile(self):
        state = self.state()
        broken = member_exports.build_snapshot(state, tracker)
        broken['members']['#P0Q']['seasonDonations'] = 317
        with patch.object(member_exports, 'build_snapshot', return_value=broken), self.assertRaisesRegex(ValueError, 'season donations'):
            snapshot_audit.verify(state, tracker)

    def test_season_reset_preserves_observed_donations_and_new_game_counter(self):
        state = self.state()
        prior = {p['tag']:copy.deepcopy(p) for p in state['roster']}
        state['roster'][0]['donations'] = 10
        tracker.update_member_history(state, prior, state['roster'], '2026-10-20T21:00:00Z')
        state['lastSuccessfulSync'] = '2026-10-20T21:00:00Z'
        view = member_exports.build_snapshot(state, tracker)['members']['#P0Q']
        self.assertEqual(view['seasonDonations'], 10)
        self.assertEqual(view['observedDonations']['total'], 327)
        with contextlib.redirect_stdout(io.StringIO()):
            snapshot_audit.verify(state, tracker)


if __name__ == '__main__':
    unittest.main()
