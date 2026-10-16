const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const raw=Buffer.alloc(64,42),key=raw.toString('base64'),nodes={};
const node=id=>nodes[id]||=({textContent:'',hidden:false,value:'',querySelector(){return node('message');}});
let server=null,lostReply=false,writes=0;
const edits={notes:{'#P0Y':{text:'original'}}},context={data:{clanTag:'#P0Y',sharedActions:{enabled:true,encryptionKey:key,url:'https://example.invalid'}},window:{warHavenSession:{proof:async()=>''}},crypto:webcrypto,TextEncoder,TextDecoder,atob,btoa,console,Map,Date,JSON,Uint8Array,setTimeout:()=>1,clearTimeout(){},setInterval(){},localStorage:{getItem:()=>null,setItem(){}},document:{body:{dataset:{}},hidden:false},$:node,persist(){},edits,selectedTag:'',fetch:async(url,options)=>{
 const body=JSON.parse(options.body),path=new URL(url).pathname;
 const response=(status,value)=>({status,ok:status<400,json:async()=>value});
 if(path==='/v1/challenge')return response(200,{salt:Buffer.alloc(16).toString('base64'),rounds:600000});
 if(path==='/v1/records')return response(200,{records:server?[server]:[]});
 if(path==='/v1/record'){
  if(server?.operationId===body.operationId)return response(200,{record:server});
  if((server?.revision||null)!==(body.expectedRevision||null))return response(409,{error:'conflict',record:server});
  writes++;server={...body,revision:'r'+writes,updatedAt:'2030-01-01T00:00:00Z'};
  if(lostReply){lostReply=false;throw Error('Reply lost');}return response(200,{record:server});
 }
 throw Error(path);
}};
let source=fs.readFileSync('shared_dashboard.js','utf8').replace('return {start,changed};','return {start,changed,encrypt,decrypt,flush,accept,pending,updateProgress,seedDrafts};');
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
 console.log(JSON.stringify({envelope,key,checks:'encryption, tamper detection, concurrent edits, retained drafts, idempotent retry and honest completion'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
