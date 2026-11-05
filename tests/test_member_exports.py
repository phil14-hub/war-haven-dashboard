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


 def test_comparison_evidence_includes_cwl_and_breaks_average_ties_by_samples(self):
  state=self.state()
  tags=['#P0Y','#P0U','#P0C','#P0Q']
  state['roster']=[{'tag':tag,'name':name,'townHallLevel':12} for tag,name in zip(tags,['Fifteen','One','Ninety five','Unknown'])]
  state['clanProfile']['members']=len(tags)
  state['lastSuccessfulSync']='2030-03-01T00:00:00Z'
  wars=[]
  for n in range(16):
   kind='CWL' if n%2 else 'Regular'
   first='#P0Y' if n<15 else '#P0U'
   players=[{'tag':first,'attacksUsed':1,'attacks':[{'order':1,'stars':3,'destructionPercentage':100}]}]
   if n<3:
    players.append({'tag':'#P0C','attacksUsed':1,'attacks':[{'order':1,'stars':2,'destructionPercentage':95}]})
   wars.append({'id':'war-'+str(n),'kind':kind,'endTime':'2030-02-%02dT00:00:00Z'%(n+1),
                'state':'warEnded','final':True,'rosterComplete':True,
                'attacksPerMember':1 if kind=='CWL' else 2,'participants':players})
  state['wars']=wars
  result=member_exports.build_snapshot(state,tracker)
  comparison=result['comparisons']
  self.assertEqual([v['tag'] for v in comparison],['#P0Y','#P0U','#P0C','#P0Q'])
  self.assertEqual([v['destructionAttacks'] for v in comparison],[15,1,3,0])
  self.assertEqual([v['averageDestruction'] for v in comparison],[100,100,95,None])
  self.assertEqual([v['destructionRank'] for v in comparison],[1,1,3,None])
  history=result['members']['#P0Y']['warDestructionSeries']
  self.assertEqual(len(history),15)
  self.assertEqual(sum(v['kind']=='CWL' for v in history),7)
  self.assertTrue(all(v['value']==100 and v['attacks']==1 for v in history))

 def test_raid_loot_retains_prior_completed_weekends_in_order(self):
  state=self.state()
  state['lastSuccessfulSync']='2030-03-01T00:00:00Z'
  def raid(key,date,loot,status='ended'):
   return {'id':key,'startTime':date+'T00:00:00Z','endTime':date+'T23:00:00Z',
           'state':status,'members':[{'tag':'#P0Y','attacks':6,'capitalResourcesLooted':loot}]}
  state['raids']=[raid('new','2030-02-22',2000),
                  raid('current','2030-02-28',500,'ongoing'),
                  raid('old','2030-02-01',1000)]
  view=member_exports.build_snapshot(state,tracker)['members']['#P0Y']
  self.assertEqual([v['id'] for v in view['raids']],['old','new','current'])
  self.assertEqual(view['raidLoot'],3000)
  self.assertEqual([v['raidId'] for v in view['raidLootSeries']],['old','new'])
  self.assertEqual([v['value'] for v in view['raidLootSeries']],[1000,2000])
  self.assertTrue(all(v['at'] for v in view['raidLootSeries']))

if __name__=='__main__':unittest.main()
