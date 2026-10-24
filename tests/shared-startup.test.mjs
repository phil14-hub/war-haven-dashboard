import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {webcrypto} from 'node:crypto';
import {runInContext} from 'node:vm';
import {JSDOM} from 'jsdom';

async function fixture({cached={},snapshot={},saved=[],drafts=[],recovery=[]}={}){
 const dom=new JSDOM('<body><main><div id="overview"></div></main><p id="howto-saving"></p><p id="shared-storage-info"></p><dialog id="player-dialog"></dialog></body>',{url:'https://portal.warhavenclan.com/members/leadership',runScripts:'outside-only'}),w=dom.window;
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 Object.defineProperty(w,'crypto',{value:webcrypto});Object.assign(w,{TextEncoder,TextDecoder,AbortSignal,Response});
 const cache=new Map([['war-haven-pending-shared:#P0Y',drafts],['war-haven-recovered-shared:#P0Y',recovery]]),records=[],writes=[];
 const data={clanTag:'#P0Y',edits:{notes:snapshot},sharedActions:{enabled:true,url:'https://shared.invalid',encryptionKey:Buffer.alloc(64,42).toString('base64')}},edits={notes:structuredClone(cached)};
 Object.assign(w,{data,edits,selectedTag:'',date:v=>v,$:id=>w.document.getElementById(id),LeaderCache:{ready:async()=>{},get:key=>cache.get(key),set:(key,value)=>cache.set(key,structuredClone(value)),warning:()=>''},WarTracker:{mergeEdits:(a,b)=>({...a,...b})},WarHavenUI:{captureDraft:()=>null,restoreDraft(){}},persist(){},render(){},openPlayer(){},setTimeout:()=>1,clearTimeout(){},setInterval(){}});
 w.warHavenSession={proof:async()=>''};let offline=false;
 w.fetch=async(url,options)=>{
  if(offline)throw Error('Offline fixture');
  const body=JSON.parse(options.body),path=new URL(url).pathname;
  if(path==='/v1/challenge')return new Response(JSON.stringify({salt:'fixture',rounds:1}));
  if(path==='/v1/records')return new Response(JSON.stringify({records}));
  if(path==='/v1/record'){
   writes.push(body);const index=records.findIndex(r=>r.id===body.id),prior=records[index];
   if((prior?.revision||null)!==body.expectedRevision)return new Response(JSON.stringify({record:prior}),{status:409});
   const record={...body,revision:'saved-'+writes.length,updatedAt:'2030-01-01T01:00:00Z'};if(index<0)records.push(record);else records[index]=record;
   return new Response(JSON.stringify({record}));
  }
  throw Error(path);
 };
 const source=readFileSync('shared_dashboard.js','utf8').replace('wireRefresh();','/* Unrelated refresh controls are omitted in this fixture. */').replace('return {start,changed,mergeSnapshotEdits,trackEdits};','return {start,changed,load,pending,recovered,flush,identifier,encrypt,reviewConflicts};');
 const app=runInContext(source+';SharedDashboardSync',dom.getInternalVMContext());
 const record=async(key,value,revision='r1')=>({id:await app.identifier('notes',key),kind:'notes',revision,updatedAt:'2030-01-01T00:00:00Z',envelope:await app.encrypt({category:'notes',key,value})});
 for(const [key,value,revision] of saved)records.push(await record(key,value,revision));
 const edit=(key,value)=>{edits.notes[key]=value;app.changed('notes',key,value);};
 const click=async label=>{const button=[...w.document.querySelectorAll('dialog button')].find(b=>b.textContent===label);assert.ok(button,label);await button.onclick();};
 return {app,dom,w,cache,records,writes,edits,record,edit,click,offline:value=>offline=value};
}

// Merely opening a dashboard with seven stale browser copies must not create saves.
{
 const cached={},snapshot={},saved=[];for(let i=0;i<7;i++){cached['player'+i]={text:'Previously saved cache'};snapshot['player'+i]={text:'Older archive'};saved.push(['player'+i,{text:'Latest shared note'}]);}
 const f=await fixture({cached,snapshot,saved});await f.app.start();await f.app.flush();
 assert.equal(f.writes.length,0);assert.equal(f.app.pending.size,0);assert.equal(f.app.recovered.size,0);assert.equal(f.edits.notes.player0.text,'Latest shared note');f.dom.window.close();
}
// Legacy inferred conflicts become encrypted recoverable copies, never silent overwrites.
{
 const draft={category:'notes',key:'p',value:{text:'Older cached note'},baseRevision:null,migration:true,conflict:true,operationId:'legacy'};
 const f=await fixture({cached:{p:draft.value},saved:[['p',{text:'Latest shared note'}]],drafts:[['notes:p',draft]]});await f.app.start();await f.app.flush();
 assert.equal(f.writes.length,0);assert.equal(f.app.pending.size,0);assert.equal(f.app.recovered.size,1);assert.equal(f.edits.notes.p.text,'Latest shared note');assert.equal(f.cache.get('war-haven-recovered-shared:#P0Y')[0][1].value.text,'Older cached note');
 assert.match(f.w.document.getElementById('shared-use-latest').textContent,/older browser copy/);
 await f.app.reviewConflicts();assert.match(f.w.document.querySelector('dialog[open]').textContent,/saved version is already in use/);await f.click('Save my version');
 assert.equal(f.writes.length,1);assert.equal(f.writes[0].expectedRevision,'r1');assert.equal(f.app.recovered.size,0);assert.equal(f.edits.notes.p.text,'Older cached note');f.dom.window.close();
}
// Identical content clears even legacy real drafts, ignoring timestamps and object order.
{
 const value={text:'Already saved',deleted:false},draft={category:'notes',key:'p',value,baseRevision:null,conflict:true};
 const f=await fixture({cached:{p:value},saved:[['p',{deleted:false,updatedAt:'older',text:'Already saved'}]],drafts:[['notes:p',draft]]});await f.app.start();await f.app.flush();assert.equal(f.app.pending.size,0);assert.equal(f.writes.length,0);f.dom.window.close();
}
// Changed revisions with unchanged content may safely accept an offline edit.
{
 const f=await fixture({saved:[['p',{text:'Original'}]]});await f.app.start();f.edit('p',{text:'My edit'});f.records[0]=await f.record('p',{text:'Original'},'r2');await f.app.flush();assert.equal(f.writes.length,1);assert.equal(f.writes[0].expectedRevision,'r2');assert.equal(f.app.pending.size,0);
 // After a successful save, reverting to an older value is a genuine edit.
 f.edit('p',{text:'Original'});await f.app.flush();assert.equal(f.writes.length,2);assert.equal(f.edits.notes.p.text,'Original');f.dom.window.close();
}
// Genuine competing edits remain unsaved and reviewable, with no overwrite request.
{
 const f=await fixture({saved:[['p',{text:'Original'}]]});await f.app.start();f.edit('p',{text:'My unsaved edit'});f.records[0]=await f.record('p',{text:'Other session edit'},'r2');await f.app.flush();assert.equal(f.writes.length,0);assert.equal(f.app.pending.get('notes:p').conflict,true);assert.equal(f.edits.notes.p.text,'My unsaved edit');assert.equal(f.cache.get('war-haven-pending-shared:#P0Y')[0][1].value.text,'My unsaved edit');
 await f.app.reviewConflicts();await f.click('Use saved version');assert.equal(f.edits.notes.p.text,'Other session edit');assert.equal(f.app.pending.size,0);f.dom.window.close();
}
// A first-time local note still migrates, while an offline startup keeps drafts.
{
 const f=await fixture({cached:{p:{text:'First local note'}}});await f.app.start();await f.app.flush();assert.equal(f.writes.length,1);assert.equal(f.writes[0].expectedRevision,null);f.dom.window.close();
 const draft={category:'notes',key:'p',value:{text:'Offline work'},baseRevision:'r1',operationId:'offline'};
 const g=await fixture({cached:{p:draft.value},drafts:[['notes:p',draft]]});g.offline(true);await g.app.start();await g.app.flush();assert.equal(g.writes.length,0);assert.equal(g.app.pending.get('notes:p').value.text,'Offline work');g.dom.window.close();
}
console.log('Shared startup checks passed: seven stale copies, legacy recovery, identical saves, revision rebasing, real conflicts, deliberate recovery, first-time notes and offline drafts.');
