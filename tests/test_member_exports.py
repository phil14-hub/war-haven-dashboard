import copy
import json
import unittest
import Clash_War_Tracker as tracker
import member_exports


class MemberExportTests(unittest.TestCase):
 def state(self):
  state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
  state.update(lastSuccessfulSync='2030-01-03T00:00:00Z',clanName='War Haven',clanProfile={'members':1,'clanLevel':3},roster=[{'tag':'#P0Y','name':'Player','townHallLevel':12,'donations':100,'role':'member'}])
  state['edits']['notes']['#P0Y']={'text':'PRIVATE NOTE'}
  state['recruiter']={'secret':'PRIVATE RECRUITER'}
  state['sharedActions']={'encryptionKey':'PRIVATE KEY'}
  state['memberHistory']['#P0Y']={'since':'2030-01-01T00:00:00Z','capitalSamples':[{'at':'2030-01-01T00:00:00Z','total':200},{'at':'2030-01-02T00:00:00Z','total':250},{'at':'2030-01-03T00:00:00Z','total':300}], 'donationIntervals':[{'start':'2030-01-01T00:00:00Z','end':'2030-01-02T00:00:00Z','count':30},{'start':'2030-01-01T12:00:00Z','end':'2030-01-03T00:00:00Z','count':100}]}
  return state

 def test_member_export_has_no_private_leadership_data(self):
  result=member_exports.build_snapshot(self.state(),tracker)
  self.assertNotIn('PRIVATE',json.dumps(result))
  self.assertEqual(result['members']['#P0Y']['capitalGold'],100)
  self.assertEqual(result['members']['#P0Y']['donationSeries'][-1]['value'],30)
  self.assertEqual(result['comparisons'][0]['tag'],'#P0Y')

 def test_incomplete_roster_never_revokes_members(self):
  state=self.state();state['clanProfile']['members']=2
  with self.assertRaises(ValueError):member_exports.build_snapshot(state,tracker)
  state=self.state();state['roster']=[]
  with self.assertRaises(ValueError):member_exports.build_snapshot(state,tracker)

 def test_capital_baselines_do_not_attribute_other_clans_or_bridge_unknown_samples(self):
  state=self.state();history=state['memberHistory']['#P0Y']
  history['capitalSamples'].insert(0,{'at':'2029-12-31T00:00:00Z','total':0})
  history['capitalSamples'].insert(2,{'at':'2030-01-01T12:00:00Z','total':None})
  result=member_exports.build_snapshot(state,tracker)['members']['#P0Y']
  self.assertEqual(result['capitalGold'],50)

 def test_war_rates_use_complete_results_and_respect_excused_appearances(self):
  state=self.state();base={'id':'war','kind':'Regular','endTime':'2030-01-02T00:00:00Z','state':'warEnded','final':True,'rosterComplete':True,'attacksPerMember':2,'participants':[{'tag':'#P0Y','attacksUsed':2,'starsEarned':5,'attacks':[{'stars':2},{'stars':3}]}]}
  state['wars']=[base,{**copy.deepcopy(base),'id':'incomplete','final':False}]
  result=member_exports.build_snapshot(state,tracker)['members']['#P0Y']['warStats']
  self.assertEqual(result,{'used':2,'allowed':2,'appearances':1,'stars':5,'attacks':2,'triples':1,'destruction':0,'destructionAttacks':0})
  state['edits']['exceptions']['war::#P0Y']={'value':True}
  self.assertEqual(member_exports.build_snapshot(state,tracker)['members']['#P0Y']['warStats']['allowed'],0)


 def test_overview_summarizes_verified_wars_and_unknown_metrics(self):
  state=self.state()
  known={'id':'complete','kind':'Regular','endTime':'2030-01-02T20:00:00Z',
         'state':'warEnded','final':True,'rosterComplete':True,'result':'win',
         'attacksPerMember':2,'opponent':{'name':'Test Clan'},
         'participants':[{'tag':'#P0Y','attacksUsed':2,'starsEarned':5,
                          'attacks':[{'stars':2,'destructionPercentage':80},
                                     {'stars':3,'destructionPercentage':100}]}]}
  unfinished={**copy.deepcopy(known),'id':'not-final','final':False,'result':'lose'}
  state['wars']=[known,unfinished]
  player=member_exports.build_snapshot(state,tracker)['members']['#P0Y']
  overview=player['overview']
  self.assertEqual(overview['updatedAt'],state['lastSuccessfulSync'])
  self.assertEqual(overview['war']['victories'],1)
  self.assertEqual(overview['war']['defeats'],0)
  self.assertEqual(overview['war']['confirmedAppearances'],1)
  self.assertEqual(overview['war']['attackUsePercent'],100.0)
  self.assertEqual(overview['war']['averageStars'],2.5)
  self.assertEqual(overview['war']['threeStarPercent'],50.0)
  self.assertEqual(overview['war']['averageDestructionPercent'],90.0)
  self.assertEqual(overview['war']['latestConfirmed']['opponent'],'Test Clan')
  self.assertIsNone(overview['army']['completionPercent'])
  self.assertFalse(overview['army']['available'])
  self.assertEqual(overview['activity']['seasonDonations'],100)
  self.assertNotIn('PRIVATE',json.dumps(overview))

 def test_overview_does_not_invent_zero_attacks_or_outcomes(self):
  state=self.state()
  player=member_exports.build_snapshot(state,tracker)['members']['#P0Y']
  overview=player['overview']
  self.assertEqual(overview['war']['confirmedAppearances'],0)
  self.assertIsNone(overview['war']['averageStars'])
  self.assertIsNone(overview['war']['attackUsePercent'])
  self.assertIsNone(overview['war']['threeStarPercent'])
  self.assertIsNone(overview['war']['latestConfirmed'])
  self.assertIsNone(overview['army']['completionPercent'])

if __name__=='__main__':unittest.main()
