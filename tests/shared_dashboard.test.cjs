const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const raw=Buffer.alloc(64,42),key=raw.toString('base64'),nodes={};
const node=id=>nodes[id]||=({textContent:'',hidden:false,value:'',attrs:{},classes:new Set(),classList:{toggle(name,enabled){enabled?node(id).classes.add(name):node(id).classes.delete(name);}},setAttribute(name,value){this.attrs[name]=value;},querySelector(selector){return node(id+selector);}});
let server=null,lostReply=false,writes=0,publicationChecks=0;
const refreshRequests={};
const edits={notes:{'#P0Y':{text:'original'}}},context={data:{clanTag:'#P0Y',lastSuccessfulSync:'2030-01-01T01:00:00Z',sharedActions:{enabled:true,encryptionKey:key,url:'https://example.invalid'}},WarTracker:{mergeEdits:(a,b)=>({notes:{...a.notes,...b.notes}})},recruiterReport:{updatedAt:'2030-01-01T01:00:00Z'},checkPublishedUpdate:async options=>{assert.equal(options.force,true);publicationChecks++;},window:{warHavenSession:{proof:async()=>''}},crypto:webcrypto,TextEncoder,TextDecoder,atob,btoa,console,Map,Date,JSON,Uint8Array,setTimeout:()=>1,clearTimeout(){},setInterval(){},localStorage:{getItem:()=>null,setItem(){}},WarHavenUI:{captureDraft:()=>null,restoreDraft(){}},render(){},openPlayer(){},AbortSignal,LeaderCache:{set(){},get(){return []},ready:async()=>{}},document:{body:{dataset:{}},hidden:false},$:node,persist(){},edits,selectedTag:'',fetch:async(url,options)=>{
 const body=JSON.parse(options.body),path=new URL(url).pathname;
 const response=(status,value)=>({status,ok:status<400,json:async()=>value});
 if(path==='/v1/challenge')return response(200,{salt:Buffer.alloc(16).toString('base64'),rounds:600000});
 if(path==='/v1/records')return response(200,{records:server?[server]:[]});
 if(path==='/v1/refresh/status')return response(200,{request:refreshRequests[body.kind]||null});
 if(path==='/v1/record'){
  if(server?.operationId===body.operationId)return response(200,{record:server});
  if((server?.revision||null)!==(body.expectedRevision||null))return response(409,{error:'conflict',record:server});
  writes++;server={...body,revision:'r'+writes,updatedAt:'2030-01-01T00:00:00Z'};
  if(lostReply){lostReply=false;throw Error('Reply lost');}return response(200,{record:server});
 }
 throw Error(path);
}};
let source=fs.readFileSync('shared_dashboard.js','utf8').replace('return {start,changed,mergeSnapshotEdits,trackEdits};','return {start,changed,mergeSnapshotEdits,encrypt,decrypt,flush,accept,pending,updateProgress,seedDrafts,setBusy,refreshStatus};');
const app=vm.runInNewContext(source+';SharedDashboardSync',context);
(async()=>{
 const clear={category:'notes',key:'#P0Y',value:{text:'Shared fixture'}};
 const envelope=await app.encrypt(clear);assert.equal((await app.decrypt(envelope)).value.text,'Shared fixture');
 const corrupt={...envelope,tag:Buffer.alloc(32).toString('base64')};await assert.rejects(app.decrypt(corrupt));
 const id=Buffer.from(await webcrypto.subtle.sign('HMAC',await webcrypto.subtle.importKey('raw',raw.subarray(32),{name:'HMAC',hash:'SHA-256'},false,['sign']),new TextEncoder().encode('notes:#P0Y'))).toString('hex');
 context.data.edits={notes:{'#P0Y':{text:'original'}}};app.seedDrafts();assert.equal(app.pending.size,0);edits.notes['#P0Y']={text:'Legacy local draft'};app.seedDrafts();assert.equal(app.pending.size,1);app.pending.clear();
 app.accept({id,revision:'r1',updatedAt:'2030-01-01T00:00:00Z'},clear);
 edits.notes['#P0Y']={text:'My local draft'};app.changed('notes','#P0Y',edits.notes['#P0Y']);
 server={id,kind:'notes',revision:'r2',operationId:'other-leader',updatedAt:'2030-01-01T00:01:00Z',envelope:await app.encrypt({...clear,value:{text:'Their edit'}})};
 await app.flush();assert.equal(app.pending.size,1);assert.equal(app.pending.get('notes:#P0Y').conflict,true);assert.equal(edits.notes['#P0Y'].text,'My local draft');assert.equal(writes,0);
 app.pending.clear();server=null;edits.notes['#P0Y']={text:'Retry fixture'};
 app.changed('notes','#P0Y',edits.notes['#P0Y']);app.pending.get('notes:#P0Y').baseRevision=null;lostReply=true;
 await app.flush();assert.equal(app.pending.size,1);assert.equal(writes,1);
 await app.flush();assert.equal(app.pending.size,0);assert.equal(writes,1);
 app.updateProgress({status:'running',phase:'collecting',startedAt:'2000-01-01T00:00:00Z',estimateSeconds:10,progress:20});assert.equal(node('shared-update-bar').value,90);
 app.updateProgress({status:'completed',phase:'completed'});assert.equal(node('shared-update-bar').value,100);
 app.changed('notes','#P0Y',{text:'Pending snapshot draft'});
 const merged=app.mergeSnapshotEdits({notes:{'#P0Y':{text:'Published value'}}});assert.equal(merged.notes['#P0Y'].text,'Pending snapshot draft');app.pending.clear();
 refreshRequests.clan={id:'clan-run',status:'running',startedAt:'2030-01-01T00:00:00Z'};await app.refreshStatus('clan');
 assert.equal(node('refresh-data').classes.has('is-refreshing'),true);assert.equal(node('refresh-data').attrs['aria-busy'],'true');assert.equal(node('refresh-data[data-refresh-label]').textContent,'Refreshing…');assert.equal(node('refresh-recruiter').classes.has('is-refreshing'),false);
 refreshRequests.recruitment={id:'recruit-run',status:'pending'};await app.refreshStatus('recruitment');assert.equal(node('refresh-recruiter').classes.has('is-refreshing'),true);
 refreshRequests.clan.status='completed';await app.refreshStatus('clan');assert.equal(node('refresh-data').classes.has('is-refreshing'),false);assert.equal(node('refresh-recruiter').classes.has('is-refreshing'),true);assert.equal(publicationChecks,1);
 await app.refreshStatus('clan');assert.equal(publicationChecks,1);
 refreshRequests.recruitment.status='completed';await app.refreshStatus('recruitment');assert.equal(publicationChecks,2);assert.equal(node('refresh-recruiter').classes.has('is-refreshing'),false);
 console.log(JSON.stringify({envelope,key,checks:'encryption, tamper detection, concurrent edits, retained drafts, idempotent retry and honest completion'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
