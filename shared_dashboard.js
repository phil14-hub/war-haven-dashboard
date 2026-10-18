const SharedDashboardSync=(()=>{
 const config=data.sharedActions,enabled=Boolean(config?.enabled&&window.warHavenSession?.proof);
 const pending=new Map(),versions=new Map(),recordIds=new Map();
 const pendingStorage='war-haven-pending-shared:'+data.clanTag;
 const categories=['notes','lineupPlans','lineupDrafts','exceptions','manualWars','xpCheckpoints','villageProgress','flagResolutions'],known=new Map();
 function keepDrafts(){LeaderCache.set(pendingStorage,[...pending]);}

 const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true});
 const decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
 const encode=value=>{let text='';for(let i=0;i<value.length;i+=8192)text+=String.fromCharCode(...value.subarray(i,i+8192));return btoa(text);};
 const combine=(...parts)=>{const result=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let at=0;for(const p of parts){result.set(p,at);at+=p.length;}return result;};
 const context=encoder.encode('WarHavenSharedEdit:v1');
 let keys=null,proof=null,proofUntil=0,loading=null,flushing=false,saveTimer=null,refreshKind='clan',refreshTimer=null;
 const requests=new Map(),completedRequests=new Set();
 let lastStatusCheck=0,needsRender=false;
 async function cryptoKeys(){
  if(keys)return keys;const raw=decode(config.encryptionKey);if(raw.length!==64)throw Error('Shared editing configuration needs to be refreshed.');
  keys={enc:await crypto.subtle.importKey('raw',raw.slice(0,32),'AES-CBC',false,['encrypt','decrypt']),mac:await crypto.subtle.importKey('raw',raw.slice(32),{name:'HMAC',hash:'SHA-256'},false,['sign','verify'])};raw.fill(0);return keys;
 }
 async function identifier(category,key){const k=await cryptoKeys();return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',k.mac,encoder.encode(category+':'+key))),b=>b.toString(16).padStart(2,'0')).join('');}
 async function encrypt(value){const k=await cryptoKeys(),iv=crypto.getRandomValues(new Uint8Array(16)),cipher=new Uint8Array(await crypto.subtle.encrypt({name:'AES-CBC',iv},k.enc,encoder.encode(JSON.stringify(value)))),tag=new Uint8Array(await crypto.subtle.sign('HMAC',k.mac,combine(context,iv,cipher)));return {version:1,iv:encode(iv),ciphertext:encode(cipher),tag:encode(tag)};}
 async function decrypt(envelope){
  const k=await cryptoKeys(),iv=decode(envelope.iv),cipher=decode(envelope.ciphertext),tag=decode(envelope.tag);
  if(envelope.version!==1||iv.length!==16||tag.length!==32||cipher.length>64000||!await crypto.subtle.verify('HMAC',k.mac,tag,combine(context,iv,cipher)))throw Error('A shared change could not be verified. Your local changes are retained.');
  const value=JSON.parse(decoder.decode(await crypto.subtle.decrypt({name:'AES-CBC',iv},k.enc,cipher)));
  if(!categories.includes(value.category)||typeof value.key!=='string'||!value.value||typeof value.value!=='object')throw Error('Invalid shared change.');
  return value;
 }
 async function api(path,body={},retry=true){
  if(!proof||Date.now()>=proofUntil){
   const challengeResponse=await fetch(config.url+'/v1/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',cache:'no-store',signal:AbortSignal.timeout(20000)});
   if(!challengeResponse.ok)throw Error('Shared saving is temporarily unavailable.');
   const challenge=await challengeResponse.json();proof=await window.warHavenSession.proof(challenge.salt,challenge.rounds);proofUntil=Date.now()+60000;
  }
  const response=await fetch(config.url+path,{method:'POST',headers:{'Content-Type':'application/json','X-War-Haven-Proof':proof},body:JSON.stringify(body),cache:'no-store',signal:AbortSignal.timeout(20000)});
  const result=await response.json();
  if(response.status===401&&retry){proof=null;return api(path,body,false);}
  if(!response.ok){const error=Error(response.status===401?'Reload and unlock the current dashboard to restore shared access.':result.error||'Shared saving is temporarily unavailable.');error.status=response.status;error.result=result;throw error;}
  return result;
 }
 function status(message){const el=$('shared-save-status');if(el)el.querySelector('[data-shared-message]').textContent=message;}
 function conflictControls(){const found=[...pending.values()].some(p=>p.conflict);$('shared-use-latest').hidden=!found;$('shared-keep-draft').hidden=!found;}
 function accept(record,clear){
  if(['lineupPlans','lineupDrafts'].includes(clear.category))WarTracker.validateLineupPlans({[clear.category]:{[clear.key]:JSON.parse(JSON.stringify(clear.value))}});
  const token=clear.category+':'+clear.key;versions.set(record.id,record.revision);recordIds.set(token,record.id);
  const draft=pending.get(token);
  if(draft?.migration&&JSON.stringify({...draft.value,updatedAt:null})===JSON.stringify({...clear.value,updatedAt:null})){pending.delete(token);keepDrafts();}
  if(pending.has(token))return;if(JSON.stringify(edits[clear.category]?.[clear.key])===JSON.stringify({...clear.value,updatedAt:record.updatedAt}))return;
  edits[clear.category]||={};known.set(token,JSON.stringify({...clear.value,updatedAt:record.updatedAt}));edits[clear.category][clear.key]={...clear.value,updatedAt:record.updatedAt};if(['lineupPlans','lineupDrafts'].includes(clear.category))edits=WarTracker.mergeEdits(edits,{});needsRender=true;persist();
  if(clear.category==='notes'&&selectedTag===clear.key&&$('player-dialog').open&&$('player-notes').value!==(clear.value.text||''))$('player-notes').value=clear.value.text||'';
  if(['lineupPlans','lineupDrafts'].includes(clear.category)&&document.body.dataset.page==='planner'){lineupLoaded='';lineupSelection=null;renderWarPlanner();}
 }
 async function load(){
  if(loading)return loading;
  loading=(async()=>{const result=await api('/v1/records');for(const record of result.records||[]){const clear=await decrypt(record.envelope);if(record.id!==await identifier(clear.category,clear.key))throw Error('A shared record failed identity verification.');accept(record,clear);}if(needsRender){needsRender=false;const draft=WarHavenUI.captureDraft(document.body),player=$('player-dialog')?.open?selectedTag:null;render();if(player)openPlayer(player);WarHavenUI.restoreDraft(document.body,draft);}if(!pending.size)status('Shared leadership edits are up to date.');})().finally(()=>loading=null);
  return loading;
 }
 function changed(category,key,value){
  if(!enabled)return;
  const token=category+':'+key;
  const previous=pending.get(token),id=recordIds.get(token);
  pending.set(token,{category,key,value:JSON.parse(JSON.stringify(value)),baseRevision:previous?previous.baseRevision:(versions.get(id)||null),operationId:crypto.randomUUID()});keepDrafts();
  status('Saving shared changes…');clearTimeout(saveTimer);saveTimer=setTimeout(flush,700);
 }
 async function flush(){
  if(flushing||!enabled)return;flushing=true;
  try{
   await load();
   for(const [token,entry]of pending){
    if(entry.conflict)continue;
    const id=recordIds.get(token)||await identifier(entry.category,entry.key);recordIds.set(token,id);
    entry.envelope||=await encrypt({category:entry.category,key:entry.key,value:entry.value});
    try{
     const result=await api('/v1/record',{id,kind:entry.category,operationId:entry.operationId,expectedRevision:entry.baseRevision||null,envelope:entry.envelope});
     versions.set(id,result.record.revision);
     if(pending.get(token)===entry){pending.delete(token);edits[entry.category][entry.key].updatedAt=result.record.updatedAt;known.set(token,JSON.stringify(edits[entry.category][entry.key]));persist();}else if(pending.get(token)?.baseRevision===entry.baseRevision)pending.get(token).baseRevision=result.record.revision;keepDrafts();
    }catch(error){
     if(error.status===409){entry.conflict=true;entry.remote=error.result.record;keepDrafts();status('Another leader saved a change to the same item. Your draft is kept.');conflictControls();}
     else throw error;
    }
   }
   if(!pending.size)status('Shared changes saved.');
  }catch(error){status(error.message+' Your draft is saved on this device.');}
  finally{flushing=false;if([...pending.values()].some(p=>!p.conflict)){clearTimeout(saveTimer);saveTimer=setTimeout(flush,5000);}}
 }
 function seedDrafts(){
  for(const category of categories)for(const[key,value]of Object.entries(edits[category]||{})){
   if(!pending.has(category+':'+key)&&JSON.stringify(value)!==JSON.stringify(data.edits?.[category]?.[key])){changed(category,key,value);pending.get(category+':'+key).migration=true;keepDrafts();}
  }
 }
 function lineupChanged(){
  if(!enabled||!lineupSelection)return;
  const mode=lineupOptions.mode,value={options:{...lineupOptions},tags:[...lineupSelection],baseCommitId:lineupBaseCommitId,updatedAt:new Date().toISOString()};
  edits.lineupDrafts||={};edits.lineupDrafts[mode]=value;persist();changed('lineupDrafts',mode,value);
 }
 function mergeSnapshotEdits(incoming){
  const merged=WarTracker.mergeEdits(incoming,edits);
  for(const entry of pending.values()){merged[entry.category]||={};merged[entry.category][entry.key]=JSON.parse(JSON.stringify(entry.value));}
  return merged;
 }
 function setBusy(kind,request){
  const button=$(kind==='clan'?'refresh-data':'refresh-recruiter');if(!button)return;
  const busy=Boolean(request&&['pending','running'].includes(request.status));
  button.classList.toggle('is-refreshing',busy);button.setAttribute('aria-busy',String(busy));
  const label=button.querySelector('[data-refresh-label]');
  if(label)label.textContent=busy?(request.status==='pending'?'Update queued':'Refreshing…'):(kind==='clan'?'Refresh data':'Refresh recruiting candidates');
 }
 function snapshotContains(request,kind){
  if(!request?.startedAt)return true;
  const captured=kind==='clan'?data.lastSuccessfulSync:recruiterReport.updatedAt;
  return (Date.parse(captured)||0)>=(Date.parse(request.startedAt)||0);
 }
 function updateProgress(request){
  const progress=$('shared-update-bar'),label=$('shared-update-label'),estimate=$('shared-update-estimate');
  if(!request){progress.value=0;label.textContent='Ready to start';estimate.textContent='';return;}
  const active=request.status==='running',queued=request.status==='pending',elapsed=active?Math.max(0,(Date.now()-Date.parse(request.startedAt))/1000):0,duration=request.estimateSeconds||120;
  const percent=request.status==='completed'?100:queued?0:Math.min(95,Math.max(request.progress||0,Math.round(5+85*Math.min(1,elapsed/duration))));
  progress.value=percent;label.textContent=percent+'% · '+({pending:'Waiting to start',starting:'Starting',collecting:'Collecting data',publishing:'Saving encrypted data',deploying:'Publishing website',completed:'Complete',failed:'Update failed',partial:'Portal sync pending'}[request.phase||request.status]||'Updating');
  const minutes=seconds=>Math.max(1,Math.ceil(seconds/60))+' min';
  estimate.textContent=request.status==='partial'?'GitHub is published. Portal synchronization is pending and will retry independently.':queued?'Usually starts within 5 minutes, then about '+minutes(duration)+'. Cloud scheduling can take longer.':active?(elapsed<duration?'Estimated '+minutes(duration-elapsed)+' remaining.':'Taking longer than estimated. The update is still running.'):request.status==='completed'?'Complete. New data appears automatically while this dashboard stays open.':'Your previous dashboard is still available.';
 }
 async function refreshStatus(kind=refreshKind){
  try{const request=(await api('/v1/refresh/status',{kind})).request;if(request)requests.set(kind,request);else requests.delete(kind);
   setBusy(kind,request);
   if(kind===refreshKind){updateProgress(request);$('website-update-submit').disabled=Boolean(request&&['pending','running'].includes(request.status));}
   const completedKey=kind+':'+request?.id;
   if(request?.status==='completed'&&!completedRequests.has(completedKey)){
    await checkPublishedUpdate({force:true});
    if(snapshotContains(request,kind))completedRequests.add(completedKey);
   }
  }catch(error){if(kind===refreshKind)$('website-update-error').textContent=error.message;}
 }
 function showRefresh(kind='clan'){
  refreshKind=kind;const recruitment=kind==='recruitment';
  $('refresh-title').textContent=recruitment?'Refresh recruitment':'Update clan dashboard';
  $('shared-update-description').textContent=recruitment?'Scan tracked clans and verify recruiting candidates. This does not refresh clan wars, members or Capital data.':'Collect clan, war, member and Capital data. This does not scan recruiting candidates.';
  $('website-update-submit').textContent=recruitment?'Start recruitment scan':'Start clan update';
  $('website-update-error').textContent='';$('website-update-submit').disabled=false;updateProgress(requests.get(kind));
  $('refresh-snapshot').textContent='Last successful '+(recruitment?'recruitment scan: '+date(recruiterReport.updatedAt):'clan snapshot: '+date(data.lastSuccessfulSync));
  $('automated-refresh-status').textContent='After your request is accepted, you can leave or exit the browser. The update continues in the cloud.';
  refreshStatus(kind);if(!$('refresh-dialog').open)$('refresh-dialog').showModal();
 }
 function wireRefresh(){
  const form=$('website-update-form');
  form.innerHTML='<p id="shared-update-description" class="small muted"></p><p class="notice">Once your request is accepted, you can close this window, leave the page or exit the browser. The update continues in the cloud. If you keep this dashboard open, new data appears automatically without signing you out.</p><button id="website-update-submit" class="primary full-width" type="submit">Start clan update</button><div class="shared-update-meter"><div id="shared-update-label" role="status">Ready to start</div><progress id="shared-update-bar" value="0" max="100" aria-label="Estimated update progress"></progress><p id="shared-update-estimate" class="small muted"></p></div>';
  form.onsubmit=async event=>{event.preventDefault();const kind=refreshKind;$('website-update-error').textContent='';$('website-update-submit').disabled=true;try{const result=await api('/v1/refresh/request',{kind});requests.set(kind,result.request);setBusy(kind,result.request);if(kind===refreshKind)updateProgress(result.request);}catch(error){$('website-update-error').textContent=error.message;$('website-update-submit').disabled=false;}};
  $('refresh-data').onclick=()=>showRefresh('clan');$('refresh-recruiter').onclick=()=>showRefresh('recruitment');$('settings-refresh').onclick=()=>{$('settings-dialog').close();showRefresh('clan');};
  // These controls supersede the owner-token flow after the shared service is available.
  $('refresh-dialog').querySelectorAll('[data-legacy-update]').forEach(node=>node.hidden=true);
  $('howto-refresh').textContent='Use Update dashboard for clan, war, member and Capital data. Use Management → Recruiter → Refresh recruiting candidates for recruitment only. Each runs independently. The estimate includes a cloud queue and a running progress bar; 100% means publication is confirmed. You can leave or exit after the request is accepted. If the dashboard stays open, the new data appears automatically and you stay unlocked.';
  const poll=()=>{
   if(document.hidden)return;
   const active=[...requests.values()].some(request=>['pending','running'].includes(request.status));
   if(!$('refresh-dialog').open&&!active&&Date.now()-lastStatusCheck<15000)return;
   lastStatusCheck=Date.now();refreshStatus('clan');refreshStatus('recruitment');
  };
  clearInterval(refreshTimer);refreshTimer=setInterval(poll,5000);poll();
 }
 async function start(){
  if(!enabled)return;await LeaderCache.ready();try{for(const[token,entry]of LeaderCache.get(pendingStorage)||[])if(categories.includes(entry.category)&&typeof entry.key==='string'&&entry.value)pending.set(token,entry);}catch{}
  for(const category of categories)for(const[key,value]of Object.entries(edits[category]||{}))known.set(category+':'+key,JSON.stringify(value));
  const banner=document.createElement('div');banner.id='shared-save-status';banner.className='notice';banner.setAttribute('role','status');banner.innerHTML='<span data-shared-message>Loading shared leadership edits…</span> <button id="shared-use-latest" hidden>Load their change</button> <button id="shared-keep-draft" hidden>Save my draft</button>';
  $('overview').parentElement.prepend(banner);
  $('howto-saving').textContent='Leadership edits save automatically for every leader using this dashboard. Working lineup drafts are separate from committed lineups. Wait for Shared changes saved before closing. If two leaders edit the same item, your draft is kept and you can load their change or save yours. Offline drafts stay on this device and retry when connected. Captured history can still be exported with Management → Export private backup.';
  $('shared-storage-info').textContent='Leadership edits save automatically and sync between leaders. Attendance exceptions, completed-war corrections, XP checkpoints, reviewed flags and imports are included.';
  $('shared-use-latest').onclick=async()=>{const found=[...pending].find(([,v])=>v.conflict);if(!found)return;const[token,entry]=found;pending.delete(token);keepDrafts();if(entry.remote)accept(entry.remote,await decrypt(entry.remote.envelope));conflictControls();status('Loaded the other leader’s saved change.');};
  $('shared-keep-draft').onclick=()=>{const entry=[...pending.values()].find(v=>v.conflict);if(!entry)return;if(entry.remote){versions.set(entry.remote.id,entry.remote.revision);entry.baseRevision=entry.remote.revision;}entry.conflict=false;entry.remote=null;entry.operationId=crypto.randomUUID();keepDrafts();conflictControls();flush();};
  document.addEventListener('input',event=>{if(event.target.id!=='player-notes'||!selectedTag)return;const value={text:event.target.value.slice(0,6000),updatedAt:new Date().toISOString()};edits.notes[selectedTag]=value;persist();changed('notes',selectedTag,value);});
  document.addEventListener('change',event=>{if(event.target.matches('[data-lineup-player],#planner-mode,#planner-size,#planner-balance,#planner-unknown'))lineupChanged();});
  document.addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;if(['planner-suggest','planner-save'].includes(button.id))lineupChanged();if(button.id==='save-note'&&selectedTag&&edits.notes[selectedTag])changed('notes',selectedTag,edits.notes[selectedTag]);});
  window.addEventListener('online',flush);
  seedDrafts();wireRefresh();
  try{await load();conflictControls();for(const category of categories)for(const [key,value]of Object.entries(edits[category]||{}))if(!recordIds.has(category+':'+key)&&!pending.has(category+':'+key))changed(category,key,value);}
  catch(error){status(error.message+' Local notes remain available.');}
  setInterval(()=>{if(!document.hidden)load().catch(error=>status(error.message));if(pending.size)flush();},20000);
 }
 function trackEdits(){if(!enabled)return;for(const category of categories){for(const[key,value]of Object.entries(edits[category]||{})){const token=category+':'+key,encoded=JSON.stringify(value);if(known.has(token)&&known.get(token)!==encoded){known.set(token,encoded);changed(category,key,value);}else if(!known.has(token)) {known.set(token,encoded);changed(category,key,value);}}for(const token of [...known.keys()].filter(t=>t.startsWith(category+':'))){const key=token.slice(category.length+1);if(!(key in (edits[category]||{}))){const tombstone={deleted:true,updatedAt:new Date().toISOString()};edits[category][key]=tombstone;known.set(token,JSON.stringify(tombstone));changed(category,key,tombstone);}}}}
 return {start,changed,mergeSnapshotEdits,trackEdits};
})();
