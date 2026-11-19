import copy
import unittest
import tracker_core as tracker


class ClanContributionRetentionTests(unittest.TestCase):
    def state(self):
        state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        state.update(lastSuccessfulSync='2026-11-18T10:00:00Z', roster=[
            {'tag':'#P0Q','name':'One','donations':100,'donationsReceived':50},
            {'tag':'#P0Y','name':'Two','donations':200,'donationsReceived':30}])
        for player in state['roster']:
            state['memberHistory'][player['tag']] = {'since':'2026-11-01T10:00:00Z',
                'lastSeen':state['lastSuccessfulSync'],'inClan':True,'donationIntervals':[]}
        return state

    def scan(self, state, roster, at):
        tracker.update_member_history(state, {p['tag']:p for p in state['roster']}, roster, at)
        state.update(roster=copy.deepcopy(roster),lastSuccessfulSync=at)

    def test_departure_preserves_counters_and_does_not_reset_season(self):
        state=self.state()
        self.scan(state,[dict(state['roster'][0],donations=120,donationsReceived=57)],'2026-11-18T11:00:00Z')
        departed=state['memberHistory']['#P0Y']
        self.assertFalse(departed['inClan'])
        self.assertEqual(departed['donationCounterSamples'][0]['donations'],200)
        self.assertEqual(state['memberHistory']['#P0Q']['receivedIntervals'][0]['count'],7)
        self.assertEqual(state.get('donationSeasonResets',[]),[])

    def test_rejoin_starts_new_baseline_without_crediting_time_away(self):
        state=self.state()
        self.scan(state,[state['roster'][0]],'2026-11-18T11:00:00Z')
        self.scan(state,[state['roster'][0],{'tag':'#P0Y','name':'Two','donations':900,'donationsReceived':99}],
                  '2026-11-18T12:00:00Z')
        returned=state['memberHistory']['#P0Y']
        self.assertEqual(returned['donationIntervals'],[])
        self.assertEqual(len(returned['pastStints']),1)
        self.assertEqual(returned['pastStints'][0]['donationCounterSamples'][0]['donations'],200)
        self.scan(state,[state['roster'][0],dict(state['roster'][1],donations=920)],'2026-11-18T13:00:00Z')
        self.assertEqual(returned['donationIntervals'][0]['count'],20)

    def test_shared_counter_reset_retains_old_history_and_is_idempotent(self):
        state=self.state()
        roster=[dict(p,donations=3,donationsReceived=1) for p in state['roster']]
        self.scan(state,roster,'2026-12-01T10:00:00Z')
        self.assertEqual(len(state['donationSeasonResets']),1)
        self.assertEqual(state['donationSeasonResets'][0]['countersReset'],2)
        self.assertEqual(state['memberHistory']['#P0Q']['donationIntervals'][0]['count'],3)
        self.scan(state,roster,'2026-12-01T11:00:00Z')
        self.assertEqual(len(state['donationSeasonResets']),1)
        self.assertEqual(len(state['memberHistory']['#P0Q']['donationCounterSamples']),2)

    def test_single_decrease_among_many_donors_does_not_reset_the_clan(self):
        state=self.state()
        state['roster'].append({'tag':'#P0U','name':'Three','donations':50})
        roster=[dict(p) for p in state['roster']]
        roster[0]['donations']=0
        self.scan(state,roster,'2026-11-18T11:00:00Z')
        self.assertEqual(state.get('donationSeasonResets',[]),[])

    def test_archive_merges_keep_receipts_and_readings_without_duplication(self):
        state=self.state()
        self.scan(state,[dict(p,donations=p['donations']+2,donationsReceived=p['donationsReceived']+1)
                         for p in state['roster']], '2026-11-18T11:00:00Z')
        backup=copy.deepcopy(state)
        tracker.apply_snapshot(state,backup)
        merged=copy.deepcopy(state['memberHistory'])
        tracker.apply_snapshot(state,backup)
        self.assertEqual(state['memberHistory'],merged)
        self.assertEqual(len(merged['#P0Q']['receivedIntervals']),1)
        self.assertEqual(len(merged['#P0Q']['donationCounterSamples']),2)


if __name__=='__main__':
    unittest.main()
