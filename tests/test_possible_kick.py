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
for (const uses of [[0,2,0], [0,1,0], [0,2,2,0], [0,null,2,null,0]]) {
  const p = row(dataFor(uses));
  assert.equal(p.status, 'Possible kick', JSON.stringify(uses));
  assert.equal(p.possibleKick, true);
  assert.equal(p.kick, false);
  assert.match(p.reason, /participated.*missed both again/);
}
for (const uses of [[0], [0,2], [2,0,2], [2,1,2]]) assert.equal(row(dataFor(uses)).possibleKick, false);
const hard = row(dataFor([0,0]));
assert.equal(hard.status, 'Kick');assert.equal(hard.possibleKick, false);
assert.equal(row(dataFor([0,0,2,0])).status, 'Kick');
// A confirmed pattern remains a warning until leadership reviews it.
assert.equal(row(dataFor([0,2,0,2,2])).status, 'Possible kick');
const repeat = dataFor([0,2,0]);
for (const id of ['w0', 'w2']) {
  assert.equal(row(repeat, {exceptions:{[id+'::'+tag]:{value:true}}}).possibleKick, false);
}
const excusedReturn = row(repeat, {exceptions:{['w1::'+tag]:{value:true}}});
assert.equal(excusedReturn.status, 'Kick');assert.equal(excusedReturn.possibleKick, false);
for (const index of [0,1,2]) {
  const incomplete = dataFor([0,2,0]);incomplete.wars[index].final = false;
  assert.equal(row(incomplete).possibleKick, false, 'Incomplete appearance '+index);
}
const unknownRoster = dataFor([0,null,2,0]);unknownRoster.wars[1].rosterComplete = false;
assert.equal(row(unknownRoster).possibleKick, false);
const league = dataFor([0,2,0]);league.wars[1].kind = 'CWL';league.wars[1].attacksPerMember = 1;league.wars[1].participants[0].attacksUsed = 1;
assert.equal(row(league).possibleKick, false);
const future = dataFor([0,2,0]);future.wars[2].state='inWar';future.wars[2].endTime='2026-11-02';future.wars[2].final=false;
assert.equal(row(future).possibleKick, false);
const reviewed = {flagResolutions:{[tag]:{through:repeat.wars[2].endTime}}};
const cleared = row(repeat, reviewed);
assert.equal(cleared.possibleKick, false);assert.equal(cleared.kick, false);
assert.equal(cleared.used, 2);assert.equal(cleared.allowed, 6);
const restart = dataFor([0,2,0,0]);
assert.equal(row(restart, reviewed).possibleKick, false);assert.equal(row(restart, reviewed).streak, 1);
// Both severities share Kick flags; a possible flag retains its pending bench.
const possible = row(repeat), departed = {...possible, status:'Departed', inClan:false};
assert.equal(T.rosterView([hard, possible, departed], {status:'Kick'}).length, 2);
assert.equal(T.rosterView([hard, possible, departed], {status:'Bench'}).length, 1);
assert.match(T.csv([possible]), /Possible kick/);
assert.match(context.Leadership.eligibility(possible, 'Regular', true), /Possible kick/);
assert.match(context.Leadership.eligibility(possible, 'CWL', true), /Possible kick/);
assert.equal(T.rosterView([row(dataFor([0,2,0,2]))], {status:'Bench'}).length, 0);
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
