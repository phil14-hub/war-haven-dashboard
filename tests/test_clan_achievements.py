import copy
import unittest

import Clash_War_Tracker as tracker


class ClanAchievementTests(unittest.TestCase):
    def setUp(self):
        self.state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        self.state['roster'] = [{'tag':'#P0Q','name':'OMID fixture'}]
        self.state['memberHistory']['#P0Q'] = {'since':'2026-10-19T10:00:00Z','inClan':True,'lastSeen':'2026-10-20T10:00:00Z'}
        self.before = {'tag':'#P0Q','name':'OMID fixture','clan':{'tag':self.state['clanTag']},
            'profileCheckedAt':'2026-10-19T11:00:00Z','warStars':999,
            'achievements':[{'name':'Gold Grab','stars':1,'value':500000,'target':100000000}]}
        self.after = copy.deepcopy(self.before)
        self.after.update(profileCheckedAt='2026-10-20T09:00:00Z',warStars=1000)
        self.after['achievements'][0]['value'] = 1000000

    def record(self, before=None):
        tracker.record_profile_honors(self.state, before, self.after)
        return self.state['honors']

    def test_joining_with_existing_achievements_only_establishes_baseline(self):
        self.after['achievements'][0].update(stars=3,value=5000000000,target=100000000)
        self.after.update(warStars=20000,league={'name':'Legend League'},heroes=[{'name':'Hero','level':100,'maxLevel':100}])
        self.assertEqual(self.record(), {})

    def test_prejoin_progress_counts_toward_threshold_crossed_here(self):
        awards = self.record(self.before)
        self.assertEqual(set(awards), {'#P0Q::warStars:1000','#P0Q::counter:gold grab:1000000'})
        for award in awards.values():
            self.assertTrue(award['earnedInClan'])
            self.assertEqual(award['clanTag'], self.state['clanTag'])
            self.assertFalse(award['alreadyReached'])
        self.assertIn('1,000,000',awards['#P0Q::counter:gold grab:1000000']['title'])

    def test_repeat_scans_do_not_duplicate_or_redate_an_achievement(self):
        self.record(self.before)
        original = copy.deepcopy(self.state['honors'])
        tracker.record_profile_honors(self.state,self.after,self.after)
        self.after['profileCheckedAt'] = '2026-10-21T09:00:00Z'
        self.record(self.before)
        self.assertEqual(self.state['honors'],original)

    def test_preexisting_milestone_does_not_become_new_on_later_scan(self):
        self.before.update(warStars=1000)
        self.before['achievements'][0]['value'] = 1000000
        self.assertEqual(self.record(self.before), {})

    def test_departure_return_and_other_clan_break_the_window(self):
        for change in ['new_stint','departed','outside_before','outside_after','new_roster_member']:
            with self.subTest(change=change):
                self.setUp()
                if change=='new_stint':self.state['memberHistory']['#P0Q']['since']='2026-10-19T12:00:00Z'
                if change=='departed':self.state['memberHistory']['#P0Q']['inClan']=False
                if change=='outside_before':self.before['clan']['tag']='#P0Y'
                if change=='outside_after':self.after['clan']['tag']='#P0Y'
                if change=='new_roster_member':self.state['roster']=[]
                self.assertEqual(self.record(self.before),{})

    def test_missing_or_same_time_comparisons_do_not_invent_crossing(self):
        for value in [None,'not a date',self.after['profileCheckedAt'],'2027-01-01T00:00:00Z']:
            with self.subTest(value=value):
                self.before['profileCheckedAt']=value
                self.assertEqual(self.record(self.before),{})

    def test_newly_earned_record_can_replace_an_old_baseline_receipt(self):
        self.state['honors']['#P0Q::warStars:1000']={'alreadyReached':True,'observedAt':'2026-01-01T00:00:00Z'}
        self.record(self.before)
        self.assertTrue(self.state['honors']['#P0Q::warStars:1000']['earnedInClan'])


if __name__ == '__main__':
    unittest.main()
