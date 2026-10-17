import copy
import json
from pathlib import Path
import subprocess
import unittest
import Clash_War_Tracker as tracker
from tests.test_upgrade_progress import profile

class CorrectionsTests(unittest.TestCase):
 def test_completion_credits_all_pets_and_preserves_separate_work_score(self):
  p=profile(18)
  for pet in p['troops']:
   if pet['name'] in {'L.A.S.S.I','LASSI'}:pet['level']=3
   if pet['name']=='Mighty Yak':pet['level']=7
   if pet['name']=='Electro Owl':pet['level']=14
  r=tracker.army_progress(p);pets=r['groups']['pets']
  self.assertEqual(pets['count'],12);self.assertEqual(pets['maxed'],9)
  self.assertEqual(pets['percent'],-0.5)
  self.assertEqual(pets['completionPercent'],85.8)
  self.assertGreater(r['completionPercent'],r['percent'])
  self.assertEqual(tracker.army_progress(profile(18))['completionPercent'],100)
  del p['heroes'];self.assertIsNone(tracker.army_progress(p)['completionPercent'])
 def test_catalog_has_no_duplicate_named_upgrades(self):
  from upgrade_progress import CATALOG
  keys=[(u['group'],u['name']) for u in CATALOG['units']]
  self.assertEqual(len(keys),len(set(keys)))
 def test_completion_history_and_member_export_never_relabel_old_scores(self):
  s=tracker.new_state('#2PQQJ0GR0');s.update(lastSuccessfulSync='2026-10-17T10:00:00Z',clanProfile={'members':1,'clanLevel':4},roster=[{'tag':'#P0Q','name':'P','townHallLevel':18}],profiles={'#P0Q':profile(18,17)})
  s['memberProgressHistory']={'#P0Q':[{'method':'th-work-v2','at':'2026-10-16T10:00:00Z','percent':-20,'townHall':18}]}
  tracker.capture_progression(s)
  self.assertIn('completionPercent',s['memberProgressHistory']['#P0Q'][-1])
  import member_exports
  points=member_exports.build_snapshot(s,tracker)['members']['#P0Q']['armySeries']
  self.assertEqual(len(points),1);self.assertGreater(points[0]['value'],0)
 def test_roster_filters_recovery_and_xp_readings(self):
  program=r'''
const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm'),context={};vm.createContext(context);vm.runInContext(JSON.parse(fs.readFileSync(0,'utf8')).source,context);
const T=context.WarTracker,P=context.ClanProgress,players=[{tag:'#P0Q',name:'A',inClan:true,rate:.5,townHallLevel:18,streak:1,attackLikelihood:{probability:.6},performance:{averageStars:2.5}},{tag:'#P0Y',name:'B',inClan:true,rate:1,townHallLevel:14,streak:0},{tag:'#P0U',name:'C',inClan:true,rate:null,townHallLevel:18,streak:0}];
assert.equal(T.rosterView(players,{sort:'attack-asc'}).map(p=>p.name).join(''),'ABC');
assert.equal(T.rosterView(players,{townHall:'18',minimum:'40',maximum:'60'}).map(p=>p.name).join(''),'A');
assert.equal(T.rosterView(players,{search:'#P0Y',minimum:'80'}).length,1);assert.equal(T.rosterView(players,{minimum:'80',maximum:'20'}).length,0);
const war=(i,used,extra={})=>({id:'war'+i,kind:'Regular',state:'warEnded',final:true,rosterComplete:true,attacksPerMember:2,endTime:new Date(Date.UTC(2026,9,i+1)).toISOString(),participants:used===null?[]:[{tag:'#P0Q',attacksUsed:used}],...extra}),data={wars:[war(0,0)]},player=players[0],asOf=Date.UTC(2026,10,1);
assert.equal(T.missedBothRecency(data,{},player,asOf).warsAgo,1);
data.wars.push(war(1,null));assert.equal(T.missedBothRecency(data,{},player,asOf).warsAgo,2);assert.equal(T.missedBothRecency(data,{},player,asOf).recoveryStreak,0);
for(let i=2;i<6;i++)data.wars.push(war(i,1));assert.equal(T.missedBothRecency(data,{},player,asOf).recoveryStreak,4);
data.wars.push(war(6,1,{kind:'CWL',attacksPerMember:1}));assert.equal(T.missedBothRecency(data,{},player,asOf),null);
const recovered=JSON.parse(JSON.stringify(data));recovered.wars.push(war(7,0,{kind:'CWL',attacksPerMember:1}));recovered.wars.push(war(8,0,{final:false}));assert.equal(T.missedBothRecency(recovered,{},player,asOf),null);
data.wars.push(war(7,0));assert.equal(T.missedBothRecency(data,{},player,asOf).warsAgo,1);data.wars.push(war(8,1,{final:false}));assert.equal(T.missedBothRecency(data,{},player,asOf).recoveryStreak,0);
assert.equal(T.missedBothRecency({wars:[war(0,0)]},{exceptions:{'war0::#P0Q':{value:true}}},player,asOf),null);
assert.equal(T.missedBothRecency({wars:[war(0,0,{final:false})]}, {},player,asOf),null);
assert.equal(JSON.stringify(P.screenshotReading('Clan Level 4\n1,250 / 3,100 XP')),JSON.stringify({level:4,xp:1250}));
assert.throws(()=>P.screenshotReading('1,250 / 3,100\n500 / 1,200'),/one clear/);assert.throws(()=>P.screenshotReading('Clan Level 4\n5000 / 3100'),/one clear/);
const xp=P.xpSeries({lastSuccessfulSync:'2026-10-17T10:00:00Z',clanProfile:{clanLevel:4},clanHistory:[{at:'2026-10-15',clanLevel:4}]},{xpCheckpoints:{x:{at:'2026-10-16',level:4,xp:1250}}});assert.equal(xp.manualCurrent,false);assert.equal(xp.total,null);
assert.equal(P.xpRewards({wars:[{...war(1,1),expEarned:120},{...war(1,1),expEarned:120},war(2,1),{...war(3,1,{kind:'Friendly'}),expEarned:999}]}).regular,120);
console.log('Combined roster filters, missing values, recency, sit-outs, five confirmed appearances, CWL recovery, reset, excuses, unknown finals, screenshot parsing and XP freshness passed.');
'''
  result=subprocess.run(['node','-e',program],input=json.dumps({'source':tracker.TRACKER_JS}),text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
