import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createContext,runInContext} from 'node:vm';

const context=createContext({});
for(const name of ['dashboard-model','clan-contributions'])runInContext(readFileSync('shared/'+name+'.js','utf8'),context);
const {ClanContributions:C,WarTracker:T}=context;
const at=day=>'2026-11-'+String(day).padStart(2,'0')+'T10:00:00Z';
const interval=(start,end,count)=>({start:at(start),end:at(end),count});
const samples=(values)=>values.map(([day,donations,donationsReceived])=>({at:at(day),donations,donationsReceived}));
const data={schemaVersion:1,clanTag:'#P0Q',lastSuccessfulSync:at(3),roster:[{tag:'#P0Q',donations:130}],
  clanHistory:[{at:at(1),members:2,seasonDonations:300},{at:at(2),members:2,seasonDonations:340},{at:at(3),members:1,seasonDonations:130}],
  memberHistory:{
    '#P0Q':{since:at(1),lastSeen:at(3),inClan:true,donationIntervals:[interval(1,2,20),interval(2,3,10)],
      receivedIntervals:[interval(1,2,5)],donationCounterSamples:samples([[1,100,50],[2,120,55],[3,130,55]]),
      capitalSamples:[{at:at(1),total:100},{at:at(2),total:200}]},
    '#P0Y':{since:at(1),lastSeen:at(2),leftAt:at(3),inClan:false,donationIntervals:[interval(1,2,20)],
      receivedIntervals:[interval(1,2,8)],donationCounterSamples:samples([[1,200,30],[2,220,38]]),
      capitalSamples:[{at:at(1),total:1000},{at:at(2),total:1500}]}
  }};
assert.equal(C.summary(data).seasonDonations,350,'departure retains the entire initial season baseline and both donors’ later increases');
assert.equal(C.summary(data).observedDonations,50);
assert.equal(C.summary(data).observedReceived,13);
assert.equal(C.summary(data).capitalDonations,600);
assert.equal(C.growth(data).at(-1).rosterSeasonDonations,130,'original roster measurement stays separate');
const before=JSON.stringify(data);
C.history(data);C.history(data);
assert.equal(JSON.stringify(data),before,'derived graphs do not rewrite saved evidence');

const reset=structuredClone(data), resetAt='2026-12-01T10:00:00Z';
reset.lastSuccessfulSync=resetAt;reset.roster[0].donations=3;
reset.donationSeasonResets=[{at:resetAt,previousAt:at(3)}];
reset.clanHistory.push({at:resetAt,members:1,seasonDonations:3});
reset.memberHistory['#P0Q'].lastSeen=resetAt;
reset.memberHistory['#P0Q'].donationIntervals.push({start:at(3),end:resetAt,count:3});
reset.memberHistory['#P0Q'].donationCounterSamples.push({at:resetAt,donations:3,donationsReceived:0});
assert.equal(C.summary(reset).seasonDonations,3,'an observed reset starts the next season');
assert.equal(C.summary(reset).observedDonations,53,'lifetime contributions survive season resets');
assert.equal(C.history(reset).find(p=>Date.parse(p.at)===Date.parse(at(3))).seasonDonations,350,'previous season remains saved');

const rejoin=structuredClone(data), returned='2026-11-04T10:00:00Z', increased='2026-11-05T10:00:00Z';
const old=rejoin.memberHistory['#P0Y'];
rejoin.memberHistory['#P0Y']={since:returned,lastSeen:increased,inClan:true,pastStints:[old],
  donationIntervals:[{start:returned,end:increased,count:15}],
  donationCounterSamples:[{at:returned,donations:900},{at:increased,donations:915}],
  capitalSamples:[{at:returned,total:5000},{at:increased,total:5100}]};
rejoin.roster.push({tag:'#P0Y',donations:915});rejoin.lastSuccessfulSync=increased;
rejoin.clanHistory.push({at:increased,members:2,seasonDonations:1045});
assert.equal(C.summary(rejoin).observedDonations,65,'rejoining counts only new in-clan increases');
assert.equal(C.summary(rejoin).seasonDonations,365,'season total excludes the returning player’s away baseline');
assert.equal(C.summary(rejoin).capitalDonations,700,'both Capital stints persist without counting the time away');
const merged=T.mergeData(rejoin,data), mergedTwice=T.mergeData(merged,data);
assert.equal(C.summary(mergedTwice).seasonDonations,365,'reimporting old backups does not add duplicates');
assert.equal(C.summary(mergedTwice).observedReceived,13);

const legacy=structuredClone(data);
for(const h of Object.values(legacy.memberHistory))delete h.donationCounterSamples;
assert.equal(C.summary(legacy).seasonDonations,350,'legacy departures do not create false season resets');
legacy.lastSuccessfulSync=resetAt;legacy.roster[0].donations=3;
legacy.clanHistory.push({at:resetAt,members:1,seasonDonations:3});
assert.equal(C.summary(legacy).seasonDonations,3,'legacy reset boundaries remain available');
const unknown={lastSuccessfulSync:at(1),roster:[{tag:'#P0Q'}]};
assert.equal(C.summary(unknown).seasonDonations,null);
assert.equal(C.summary(unknown).observedDonations,null);
assert.equal(C.summary(unknown).capitalDonations,null);
const partial={lastSuccessfulSync:at(3),roster:[{tag:'#P0Q',donations:100}],
  clanHistory:[{at:at(2),members:1,seasonDonations:100}],
  memberHistory:{'#P0Q':{since:at(1),lastSeen:at(3),donationIntervals:[interval(1,3,20)],
    donationCounterSamples:samples([[2,100,0],[3,100,0]])}}};
assert.equal(C.summary(partial).seasonDonations,100,'an interval straddling the saved baseline is not added twice');
assert.equal(C.summary(partial).observedDonations,20);
const rollover={clanTag:'#2PQQJ0GR0',lastSuccessfulSync:'2026-11-02T18:42:48Z',roster:[{tag:'#P0Q',donations:718}],
 clanHistory:[{at:'2026-11-01T17:18:28Z',members:47,seasonDonations:26400},{at:'2026-11-02T14:14:17Z',members:49,seasonDonations:331},{at:'2026-11-02T18:42:48Z',members:49,seasonDonations:718}],
 memberHistory:{'#P0Q':{since:'2026-10-15T10:00:00Z',lastSeen:'2026-11-02T18:42:46Z',donationIntervals:[
 {start:'2026-11-01T17:18:26Z',end:'2026-11-02T14:14:16Z',count:258},
 {start:'2026-11-02T14:14:16Z',end:'2026-11-02T18:42:46Z',count:387}]},
 '#P0Y':{since:'2026-10-15T10:00:00Z',leftAt:'2026-11-02T14:14:16Z',inClan:false}}};
assert.equal(C.summary(rollover).seasonDonations,718,'verified legacy rollover survives a simultaneous departure and second-level timestamp skew');
assert.equal(C.history(rollover).filter(p=>p.seasonReset).length,1);
const modernRollover=structuredClone(data);modernRollover.lastSuccessfulSync=resetAt;modernRollover.roster=[{tag:'#P0Q',donations:3}];
modernRollover.donationSeasonResets=[{at:resetAt,previousAt:at(3)}];modernRollover.memberHistory['#P0Y'].leftAt=resetAt;
modernRollover.memberHistory['#P0Q'].donationIntervals.push({start:at(3),end:resetAt,count:3});
assert.equal(C.summary(modernRollover).seasonDonations,3,'a verified modern reset also survives a departure');
assert.equal(C.summary(modernRollover).observedDonations,53);
console.log('Clan contributions passed: departed and returning donors, seasons, archived baselines, received troops, Capital, repeated imports, unknown data and immutable evidence.');
