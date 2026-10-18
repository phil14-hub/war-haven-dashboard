import copy
import unittest
import Clash_War_Tracker as tracker


def plan(count, size='10', committed=False):
    tags=['#P0Q','#P0Y','#P0L','#P0V','#P0G'][:count]
    return {'tags':tags,'options':{'mode':'Regular','size':size,'balance':'representative','includeUnknown':False},'updatedAt':'2026-10-18T00:00:00Z',**({'committed':True} if committed else {})}


class ExperienceTests(unittest.TestCase):
    def test_old_incomplete_lineup_is_preserved_as_a_draft(self):
        original=plan(2)
        state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        tracker.apply_snapshot(state,{'clanTag':state['clanTag'],'edits':{'lineupPlans':{'Regular':copy.deepcopy(original)}}})
        self.assertEqual(state['edits']['lineupDrafts']['Regular']['tags'],original['tags'])
        self.assertTrue(state['edits']['lineupPlans']['Regular']['deleted'])

    def test_complete_legacy_lineup_keeps_its_team_and_freezes_size(self):
        edits={'lineupPlans':{'Regular':plan(5,'max')}}
        tracker.validate_lineup_edits(edits)
        saved=edits['lineupPlans']['Regular']
        self.assertEqual(saved['options']['size'],'5')
        self.assertEqual(len(saved['tags']),5)
        self.assertTrue(saved['committed'])

    def test_new_commits_reject_partial_teams_but_drafts_allow_them(self):
        with self.assertRaises(ValueError):
            tracker.validate_lineup_edits({'lineupPlans':{'Regular':plan(2,committed=True)}})
        tracker.validate_lineup_edits({'lineupDrafts':{'Regular':plan(2)}})

    def test_drafts_survive_merging_without_replacing_the_commit(self):
        saved=plan(5,'5',True)
        merged=tracker.merge_edits({'lineupPlans':{'Regular':saved}}, {'lineupDrafts':{'Regular':plan(2)}})
        self.assertEqual(merged['lineupPlans']['Regular']['tags'],saved['tags'])
        self.assertEqual(len(merged['lineupDrafts']['Regular']['tags']),2)


if __name__=='__main__':unittest.main()
