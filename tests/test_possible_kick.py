import json
import subprocess
import unittest

import Clash_War_Tracker as tracker


class PossibleKickTests(unittest.TestCase):
    def test_repeat_misses_require_confirmed_unexcused_participation_and_honor_review(self):
        program = r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const context = {};
vm.runInNewContext(JSON.parse(fs.readFileSync(0, 'utf8')).source, context);
const T = context.WarTracker, asOf = Date.UTC(2026, 10, 1), tag = '#P0Q';
const dataFor = uses => ({clanTag:'#P0Y', policyStart:'2026-10-01', roster:[{tag, name:'Repeat fixture', warPreference:'in'}], wars:uses.map((used, i) => ({id:'w'+i, kind:'Regular', state:'warEnded', final:true, rosterComplete:true, attacksPerMember:2, endTime:new Date(Date.UTC(2026, 9, i+2)).toISOString(), participants:used === null ? [] : [{tag, attacksUsed:used}]}))});
const row = (data, edits = {}) => T.playersFor(data, edits, asOf).find(p => p.tag === tag);
for (const uses of [[0,0], [0,null,0], [2,0,0]]) {
 const p=row(dataFor(uses));assert.equal(p.status,'Kick');assert.equal(p.kick,true);assert.equal(p.possibleKick,false);assert.match(p.reason,/consecutive war appearances/);
 assert.equal(p.kickEvidence.length,2);
}
for (const uses of [[0,2,0], [0,1,0], [0,2,2,0], [0,null,2,null,0], [1,2,0]]) {
 const p=row(dataFor(uses));assert.equal(p.status,'Bench',JSON.stringify(uses));assert.equal(p.kick,false);assert.equal(p.possibleKick,false);
}
for (const uses of [[1,2,1], [0,2,1], [0,0,1], [0,2,0,2,2], [0,null], [1,1]]) {
 const p=row(dataFor(uses));assert.equal(p.status,'Eligible',JSON.stringify(uses));assert.equal(p.kick,false);assert.equal(p.possibleKick,false);
}
const hard=row(dataFor([0,0])),repeat=dataFor([1,2,0]);
assert.equal(row(dataFor([0,0,0]),{exceptions:{['w1::'+tag]:{value:true}}}).status,'Bench');
for(const index of [0,1]){const incomplete=dataFor([0,0]);incomplete.wars[index].final=false;assert.equal(row(incomplete).kick,false);}
const league=dataFor([0,1,0]);league.wars[1].kind='CWL';league.wars[1].attacksPerMember=1;
assert.equal(row(league).status,'Bench');
const mixed=dataFor([0,0]);mixed.wars[0].kind='CWL';mixed.wars[0].attacksPerMember=1;assert.equal(row(mixed).status,'Kick');
const future=dataFor([0,0]);future.wars[1].state='inWar';future.wars[1].endTime='2026-11-02';future.wars[1].final=false;
assert.equal(row(future).status,'Bench');
const reviewed={flagResolutions:{[tag]:{through:repeat.wars[2].endTime}}},cleared=row(repeat,reviewed);
assert.equal(cleared.possibleKick,false);assert.equal(cleared.kick,false);assert.equal(cleared.used,3);assert.equal(cleared.allowed,6);
const restart=dataFor([1,2,0,0]);assert.equal(row(restart,reviewed).streak,1);assert.equal(row(restart,reviewed).status,'Bench');
const benched=row(repeat),departed={...benched,status:'Departed',inClan:false};
assert.equal(T.rosterView([hard,benched,departed],{status:'Kick'}).length,1);
assert.equal(T.rosterView([hard,benched,departed],{status:'Bench'}).length,1);
assert.doesNotMatch(T.csv([benched]),/Possible kick/);
assert.match(T.csv([benched]),/Consecutive zero-attack appearances/);
assert.equal(context.Leadership.eligibility(benched,'Regular',true),'Regular-war bench');
assert.equal(context.Leadership.eligibility(benched,'CWL',true),'CWL bench');
assert.equal(T.rosterView([row(dataFor([1,2,0,2]))],{status:'Bench'}).length,0);
console.log('Repeat-miss policy passed: partial/full participation, sit-outs, severity, excuses, unknown finals, CWL, live wars, review, grouping and planning.');
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
