import copy
import unittest
import Clash_War_Tracker as tracker
import member_exports
from tests.test_upgrade_progress import profile

class CleanupMetricsTests(unittest.TestCase):
 def test_unchanged_clan_scans_only_update_sync_not_graph_points(self):
  s=tracker.new_state('#2PQQJ0GR0');s.update(clanProfile={'clanLevel':3,'clanPoints':100,'members':1},lastSuccessfulSync='2026-10-17T01:00:00Z',roster=[{'tag':'#P0Y','name':'P','townHallLevel':14,'trophies':100,'donations':5,'leagueTier':{'id':105000001}}],profiles={'#P0Y':profile(14,13)})
  tracker.capture_leadership(s);self.assertEqual(len(s['clanHistory']),1)
  s['lastSuccessfulSync']='2026-10-17T02:00:00Z';tracker.capture_leadership(s)
  self.assertEqual(len(s['clanHistory']),1);self.assertEqual(len(s['leagueHistory']),1)
  s['roster'][0]['leagueTier']={'id':105000002};tracker.capture_leadership(s)
  self.assertEqual(len(s['leagueHistory']),2);self.assertEqual(len(s['clanHistory']),2)
  self.assertEqual(s['clanHistory'][-1]['leaguePoints'],200)
 def test_destruction_average_counts_actual_known_attacks_only(self):
  s=tracker.new_state('#2PQQJ0GR0');s.update(lastSuccessfulSync='2026-10-17T01:00:00Z',clanProfile={'members':1},roster=[{'tag':'#P0Y','name':'P','townHallLevel':14}],profiles={'#P0Y':profile(14)})
  war={'id':'one','kind':'Regular','endTime':'2026-10-16T01:00:00Z','final':True,'rosterComplete':True,'attacksPerMember':2,'participants':[{'tag':'#P0Y','attacksUsed':2,'attacks':[{'order':1,'stars':3,'destructionPercentage':100},{'order':1,'stars':3,'destructionPercentage':100},{'order':2,'stars':1,'destructionPercentage':50}]}]}
  missed=copy.deepcopy(war);missed['id']='missed';missed['participants'][0].update(attacksUsed=0,attacks=[])
  unknown=copy.deepcopy(war);unknown['id']='unknown';unknown['participants'][0]['attacks']=[{'stars':1}]
  s['wars']=[war,missed,unknown]
  r=member_exports.build_snapshot(s,tracker)['comparisons'][0]
  self.assertEqual(r['averageDestruction'],75);self.assertEqual(r['destructionAttacks'],2)

if __name__=='__main__':unittest.main()
