import json
import subprocess
import unittest

import Clash_War_Tracker as tracker


class CWLBenchTests(unittest.TestCase):
    def test_regular_and_cwl_share_attendance_flags(self):
        program = r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const scope = {};
vm.runInNewContext(JSON.parse(fs.readFileSync(0,'utf8')).source, scope);
const T=scope.WarTracker, Leadership=scope.Leadership;
const player='#P0Q', now=Date.UTC(2026,10,5);
const war=(id,kind,used,options={})=>({
 id,kind,state:'warEnded',final:true,rosterComplete:true,
 attacksPerMember:kind==='CWL'?1:2,
 endTime:new Date(Date.UTC(2026,10,1+Number(id.slice(1)))).toISOString(),
 participants:used===null?[]:[{tag:player,attacksUsed:used}],...options
});
const sample=(wars,edits={})=>T.playersFor({
 clanTag:'#P0Y',policyStart:'2026-11-01',roster:[{tag:player,name:'War Haven fixture',warPreference:'in'}],wars
},edits,now).find(p=>p.tag===player);
const missed=war('w0','CWL',0),played=war('w1','CWL',1);
const p=sample([missed]);
assert.equal(p.status,'Bench');
assert.equal(p.bench,true);
assert.equal(p.cwlMissed,1);
assert.match(p.reason,/CWL attack \(0\/1\)/);
assert.equal(Leadership.eligibility(p,'Regular',true),'Regular-war bench');
assert.equal(Leadership.eligibility(p,'CWL',true),'CWL bench');
assert.equal(Leadership.suggest([p],{mode:'CWL',includeUnknown:true}).selected.length,0);
assert.equal(Leadership.suggest([p],{mode:'Regular',includeUnknown:true}).selected.length,0);
assert.equal(p.attendanceHistory.length,1);
assert.equal(p.attendanceHistory[0].complete,true);
assert.equal(p.attendanceHistory[0].player.attacksUsed,0);
assert.equal(sample([war('w0','CWL',1)]).bench,false);
assert.equal(sample([missed],{exceptions:{['w0::'+player]:{value:true}}}).bench,false);
assert.equal(sample([missed],{flagResolutions:{[player]:{through:missed.endTime}}}).bench,false);
assert.equal(sample([war('w0','CWL',0,{final:false})]).bench,false);
assert.equal(sample([war('w0','CWL',0,{rosterComplete:false})]).bench,false);
assert.equal(sample([war('w0','CWL',2)]).bench,false);
assert.equal(sample([missed,war('w1','CWL',null)]).bench,false);
assert.equal(sample([missed,played]).bench,false);
assert.equal(sample([war('w0','Regular',0)]).bench,true);
assert.equal(sample([war('w0','Regular',0),played]).bench,false);
const violation=sample([missed,war('w1','CWL',0,{state:'inWar',final:false,endTime:'2026-11-10'})]);
assert.equal(violation.bench,true);
assert.equal(violation.benchViolation,true);
assert.equal(p.kick,false);
assert.equal(p.possibleKick,false);
assert.equal(p.streak,1);
for (const [first,second] of [['CWL','CWL'],['Regular','CWL'],['CWL','Regular'],['Regular','Regular']]) {
 const older=war('w0',first,0),newer=war('w1',second,0);
 const combined=sample([newer,older]);
 assert.equal(combined.status,'Kick',`${first} then ${second}`);
 assert.equal(combined.streak,2);
 assert.equal(combined.bench,false);
 assert.equal(combined.allowed,2*[first,second].filter(kind=>kind==='Regular').length);
 assert.equal(Leadership.eligibility(combined,'Regular',true),'Kick flag');
 assert.equal(Leadership.eligibility(combined,'CWL',true),'Kick flag');
 assert.equal(sample([older,newer],{exceptions:{['w0::'+player]:{value:true}}}).status,'Bench');
 assert.equal(sample([older,newer],{flagResolutions:{[player]:{through:older.endTime}}}).status,'Bench');
 assert.equal(sample([older,{...newer,final:false}]).kick,false);
 assert.equal(sample([older,{...newer,rosterComplete:false}]).kick,false);
}
const regularMiss=war('w0','Regular',0);
assert.equal(sample([regularMiss,war('w1','CWL',null),war('w2','CWL',0)]).status,'Kick','A sit-out does not reset the shared streak');
assert.equal(sample([regularMiss,war('w1','CWL',1)]).streak,0);
assert.equal(sample([missed,war('w1','Regular',1)]).streak,0);
assert.equal(sample([regularMiss,war('w1','CWL',1),war('w2','CWL',0)]).status,'Possible kick');
assert.equal(sample([regularMiss,war('w1','CWL',null,{rosterComplete:false}),war('w2','CWL',0)]).kick,false,'An unknown round cannot establish consecutive misses');
assert.equal(sample([regularMiss,war('w1','CWL',0,{state:'inWar',final:false,endTime:'2026-11-10'})]).status,'Bench');
console.log('Shared attendance passed: both miss orders, same-type pairs, bench, recovery, exceptions, reviews, sit-outs and incomplete results.');
'''
        result = subprocess.run(
            ['node', '-e', program],
            input=json.dumps({'source': tracker.TRACKER_JS}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
