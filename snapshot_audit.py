"""Compare leadership and member calculations over the same saved snapshot.

Runs in GitHub's publishing jobs, where Node is available. No raw clan history,
notes, keys, or per-player results are written to disk or printed to job logs.
"""
import json
import subprocess

import member_exports


PROGRAM = r'''
const fs = require('node:fs'), vm = require('node:vm');
const {source, state, view} = JSON.parse(fs.readFileSync(0, 'utf8')), context = {};
vm.runInNewContext(source, context);
const T = context.WarTracker, edits = state.edits || {}, asOf = T.time(state.lastSuccessfulSync);
const performance = T.performanceFor(state, edits), failures = new Set();
let checkedFields = 0, scopeDifferences = 0;
const count = v => Number.isSafeInteger(v) && v >= 0 ? v : null;
function check(field, actual, expected) {
  checkedFields++;
  if ((actual ?? null) !== (expected ?? null)) failures.add(field);
}
for (const p of state.roster) {
  const tag = T.tag(p.tag), v = view.members[tag], c = T.contributionsFor(state, tag, asOf);
  const s = performance[tag] || {}, w = v.warStats;
  const trends = T.trendsFor(state, edits, {player:tag});
  check('season donations', v.seasonDonations, count(p.donations));
  check('season received', v.donationsReceived, count(p.donationsReceived));
  check('roster trophies', v.trophies, count(p.trophies));
  check('Town Hall', v.townHallLevel, p.townHallLevel || state.profiles?.[tag]?.townHallLevel);
  check('roster role', v.role, p.role);
  check('observed donation total', v.observedDonations.total, c.donations.since ? c.donations.total : null);
  check('donation tracking date', v.observedDonations.since, c.donations.since);
  check('Capital Gold in this clan', v.capitalGold, c.capital.total);
  check('completed raid loot', v.raidLoot, c.raidLoot);
  check('war appearances', w.appearances, trends.length);
  check('war attacks used', w.used, trends.reduce((n, w) => n + w.used, 0));
  check('war attacks allowed', w.allowed, trends.reduce((n, w) => n + w.allowed, 0));
  check('recorded war stars', w.stars, s.stars || 0);
  check('known war attacks', w.attacks, s.knownAttacks || 0);
  check('three-star attacks', w.triples, s.triples || 0);
  check('recorded destruction', w.destruction, s.destruction || 0);
  check('attacks with known destruction', w.destructionAttacks, s.destructionCount || 0);
  if (v.seasonDonations !== null && v.observedDonations.total !== null && v.seasonDonations !== v.observedDonations.total) scopeDifferences++;
}
if (failures.size) throw Error('Snapshot consistency failed: ' + [...failures].join(', '));
process.stdout.write(JSON.stringify({members:state.roster.length, checkedFields, scopeDifferences}));
'''


def verify(state, tracker):
    view = member_exports.build_snapshot(state, tracker)
    # Only send data used by the calculations. Leadership notes and secrets are excluded.
    projection = {key: state.get(key) for key in ('lastSuccessfulSync', 'roster', 'profiles', 'memberHistory', 'wars', 'raids')}
    projection['edits'] = {key: (state.get('edits') or {}).get(key, {}) for key in ('manualWars', 'exceptions')}
    result = subprocess.run(['node', '-e', PROGRAM], input=json.dumps({'source': tracker.TRACKER_JS, 'state': projection, 'view': view}), text=True, capture_output=True, timeout=30)
    if result.returncode:
        # Never echo input or raw values, including when Node cannot parse input.
        fields = next((line for line in result.stderr.splitlines() if line.startswith('Error: Snapshot consistency failed: ')), 'Snapshot consistency verification could not complete.')
        raise ValueError(fields)
    summary = json.loads(result.stdout)
    print('Snapshot consistency verified: {members} members, {checkedFields} field comparisons; {scopeDifferences} members have different season and observed donation totals (expected tracking scopes).'.format(**summary))
    return summary
