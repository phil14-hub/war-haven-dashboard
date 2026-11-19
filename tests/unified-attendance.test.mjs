import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createContext,runInContext} from 'node:vm';
const context=createContext({});runInContext(readFileSync('shared/dashboard-model.js','utf8'),context);
const tag='#P0Q',at=day=>`2026-11-${String(day).padStart(2,'0')}T10:00:00Z`;
const war=(kind,used,day,extra={})=>({id:'war-'+day,kind,state:'warEnded',final:true,rosterComplete:true,endTime:at(day),participants:[{tag,attacksUsed:used}],...extra});
const fixture=wars=>({policyStart:at(1),lastSuccessfulSync:at(19),roster:[{tag,name:'Fixture',warPreference:'in'}],wars});
for(const engine of [context.WarTracker.playersFor]){
 const player=(wars,edits={})=>engine(fixture(wars),edits,Date.parse(at(19)))[0];
 for(const wars of [[war('CWL',0,2),war('CWL',0,3)],[war('Regular',0,2),war('CWL',0,3)],[war('CWL',0,2),war('Regular',0,3)],[war('Regular',0,2),war('Regular',2,3),war('Regular',0,4)]])assert.equal(player(wars).status,'Kick');
 assert.equal(player([war('CWL',0,2)]).status,'Bench');
 assert.equal(player([war('Regular',0,2)]).status,'Bench');
 assert.equal(player([war('CWL',0,2),war('Regular',0,3)],{exceptions:{['war-2::'+tag]:{value:true}}}).status,'Bench');
 assert.equal(player([war('CWL',0,2),war('Regular',0,3)],{flagResolutions:{[tag]:{through:at(3)}}}).kick,false);
 assert.equal(player([war('CWL',0,2),war('CWL',0,3,{final:false})]).kick,false);
 assert.equal(player([war('Regular',1,2),war('Regular',1,3)]).status,'Possible kick');
 const before=JSON.stringify(fixture([war('Regular',0,2)]));engine(JSON.parse(before),{},Date.parse(at(19)));assert.equal(JSON.stringify(JSON.parse(before)),before);
}

console.log('Unified attendance passed: Regular/CWL combinations, nonconsecutive misses, exceptions, resolutions, incomplete results and partial-attack warnings.');
