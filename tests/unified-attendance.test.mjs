import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createContext,runInContext} from 'node:vm';
const context=createContext({});runInContext(readFileSync('shared/dashboard-model.js','utf8'),context);
const tag='#P0Q',at=day=>`2026-11-${String(day).padStart(2,'0')}T10:00:00Z`;
const war=(kind,used,day,extra={})=>({id:'war-'+day,kind,state:'warEnded',final:true,rosterComplete:true,endTime:at(day),participants:[{tag,attacksUsed:used}],...extra});
const fixture=wars=>({policyStart:at(1),lastSuccessfulSync:at(19),roster:[{tag,name:'Fixture',warPreference:'in'}],wars});
for(const engine of [context.WarTracker.playersFor]){
 const player=(wars,edits={})=>engine(fixture(wars),edits,Date.parse(at(19)))[0];
 for(const wars of [[war('CWL',0,2),war('CWL',0,3)],[war('Regular',0,2),war('CWL',0,3)],[war('CWL',0,2),war('Regular',0,3)],[war('Regular',0,2),war('Regular',0,3)]]){
  const p=player(wars);assert.equal(p.status,'Kick');assert.equal(p.streak,2);
  assert.deepEqual(Array.from(p.kickEvidence,h=>h.war.id),wars.map(w=>w.id));
 }
 assert.equal(player([war('CWL',0,2)]).status,'Bench');
 assert.equal(player([war('Regular',0,2)]).status,'Bench');
 assert.equal(player([war('CWL',0,2),war('Regular',0,3)],{exceptions:{['war-2::'+tag]:{value:true}}}).status,'Bench');
 assert.equal(player([war('CWL',0,2),war('Regular',0,3)],{flagResolutions:{[tag]:{through:at(3)}}}).kick,false);
 assert.equal(player([war('CWL',0,2),war('CWL',0,3,{final:false})]).kick,false);
 assert.equal(player([war('Regular',1,2),war('Regular',1,3)]).status,'Eligible');
 for(const kind of ['Regular','CWL'])for(const used of kind==='CWL'?[1]:[1,2]){
  const wars=[war('Regular',0,2),war(kind,used,3),war('CWL',0,4)];
  assert.equal(player(wars).status,'Bench');assert.equal(player(wars).kick,false);
  assert.equal(player(wars).possibleKick,false,'Nonconsecutive or partial misses never create a possible-kick flag');
  assert.equal(player([war('Regular',0,2),war('CWL',0,3),war(kind,used,4)]).status,'Eligible','A later attack clears the old kick sequence');
 }
 const sitOut=war('Regular',0,5,{participants:[]});
 assert.equal(player([war('CWL',0,2),sitOut]).status,'Eligible','A completed sit-out serves the bench');
 assert.equal(player([war('CWL',0,2),sitOut,war('Regular',0,6)]).status,'Kick','The last two participated appearances count even with a sit-out between them');
 assert.equal(player([war('Regular',0,2),war('CWL',0,3),sitOut]).kick,true);
 const unknown=war('CWL',0,3,{final:false});
 assert.equal(player([war('Regular',0,2),unknown,war('Regular',0,4)]).kick,false,'Unknown results cannot bridge misses');
 assert.equal(player([war('Regular',0,2),war('CWL',0,3),war('Regular',0,4,{final:false})]).status,'Review');
 assert.equal(player([war('Regular',0,2),war('CWL',0,3,{participants:[],rosterComplete:false}),war('Regular',0,4)]).kick,false,'An unknown lineup cannot establish non-selection');
 assert.equal(player([war('Regular',0,2),war('CWL',0,3),war('Regular',0,4)],{exceptions:{['war-3::'+tag]:{value:true}}}).status,'Bench','An approved excuse breaks the sequence');
 const barbrian=[war('CWL',0,5),war('CWL',1,9),war('CWL',1,10),war('CWL',1,11),war('Regular',0,13),...([15,17,19].map(day=>war('Regular',0,day,{participants:[]})))];
 const barbrianData=fixture(barbrian);barbrianData.roster[0].warPreference='out';
 const actual=engine(barbrianData,{},Date.parse(at(20)))[0];
 assert.equal(actual.status,'Opted out');assert.equal(actual.kick,false);assert.equal(actual.bench,false);assert.equal(actual.possibleKick,false);assert.equal(actual.missedAppearances,2,'History remains recorded');
 const before=JSON.stringify(fixture([war('Regular',0,2)]));engine(JSON.parse(before),{},Date.parse(at(19)));assert.equal(JSON.stringify(JSON.parse(before)),before);
}

console.log('Consecutive attendance passed: Regular/CWL combinations, attack breaks, bench service, sit-outs, exceptions, resolutions, unknown-result barriers, partial attacks and Barbrian regression.');
