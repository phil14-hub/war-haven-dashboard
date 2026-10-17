const DashboardLiveUpdates=(()=>{
 let etag=null,checking=null,latestToken=window.warHavenEnvelope?.tag||null;
 const pendingEdits=incoming=>typeof SharedDashboardSync!=='undefined'?SharedDashboardSync.mergeSnapshotEdits(incoming):WarTracker.mergeEdits(incoming,edits);
 function notice(message){const banner=$('publication-update');if(!banner)return;banner.hidden=!message;banner.dataset.tone='warning';if(message)$('publication-message').textContent=message;}
 function captureView(){
  const controls=[];
  document.querySelectorAll('input[id],select[id],textarea[id]').forEach(el=>{
   if(['password','file','hidden'].includes(el.type)||el.id==='player-notes')return;
   controls.push({id:el.id,value:el.value,checked:el.checked,type:el.type});
  });
  const active=document.activeElement;
  return {controls,page:document.body.dataset.page,player:$('player-dialog')?.open?selectedTag:null,
   focus:active?.id,start:active?.selectionStart,end:active?.selectionEnd,
   x:window.scrollX||0,y:window.scrollY||0,
   dialogs:[...document.querySelectorAll('dialog[open]')].map(el=>({id:el.id,top:el.scrollTop,left:el.scrollLeft}))};
 }
 function restoreView(view){
  for(const saved of view.controls){
   const el=$(saved.id);if(!el)continue;
   if(el.tagName==='SELECT'&&![...el.options].some(option=>option.value===saved.value))continue;
   const changed=el.value!==saved.value||el.checked!==saved.checked;
   el.value=saved.value;if(['checkbox','radio'].includes(saved.type))el.checked=saved.checked;
   // Reapply a rebuilt filter without dispatching the shared editing listeners.
   if(changed){const callback=el.tagName==='SELECT'||saved.type==='checkbox'?el.onchange:el.oninput;if(typeof callback==='function')callback({target:el});}
  }
  const focus=$(view.focus);if(focus){focus.focus({preventScroll:true});if(view.start!=null)try{focus.setSelectionRange(view.start,view.end);}catch{}}
  const restore=()=>{for(const saved of view.dialogs){const el=$(saved.id);if(el){el.scrollTop=saved.top;el.scrollLeft=saved.left;}}window.scrollTo?.({left:view.x,top:view.y,behavior:'instant'});};
  restore();if(typeof requestAnimationFrame==='function')requestAnimationFrame(restore);
 }
 function applySnapshot(snapshot,report){
  if(snapshot.schemaVersion!==1||WarTracker.tag(snapshot.clanTag)!==WarTracker.tag(data.clanTag)||!Array.isArray(snapshot.roster)||!Array.isArray(snapshot.wars))throw Error('The new snapshot could not be verified. Your current dashboard is still available.');
  if(data.sharedActions?.encryptionKey&&snapshot.sharedActions?.encryptionKey!==data.sharedActions.encryptionKey)throw Error('Shared access settings changed. Reopen the dashboard when convenient to use the new settings.');
  const view=captureView(),prior={data,edits,report:recruiterReport};
  // Start with the publication so current metadata wins while saved history is retained.
  const combined=WarTracker.mergeData(snapshot,data),nextEdits=pendingEdits(snapshot.edits||{});
  try{
   data={...snapshot,...combined,edits:snapshot.edits,automaticUpdates:snapshot.automaticUpdates,
    recruiterSummary:snapshot.recruiterSummary,recruiterStatus:snapshot.recruiterStatus,sharedActions:snapshot.sharedActions};
   edits=nextEdits;recruiterReport=report||{};
   RecruitmentDashboard.invalidate();render();
   if(view.page==='recruiter')openRecruiter();
   if(view.player&&rows.some(player=>player.tag===view.player))openPlayer(view.player);
   restoreView(view);persist();
  }catch(error){data=prior.data;edits=prior.edits;recruiterReport=prior.report;RecruitmentDashboard.invalidate();try{render();if(view.page==='recruiter')openRecruiter();if(view.player)openPlayer(view.player);restoreView(view);}catch{}throw error;}
 }
 async function readPublication(){
  const url=new URL(location.href);url.hash='';url.searchParams.set('_snapshot',Date.now());
  const response=await fetch(url.href,{cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(30000)});
  if(response.status===401||response.status===403||response.redirected&&new URL(response.url).pathname!==url.pathname)throw Error('Your sign-in expired. Sign in again to receive updates; your current dashboard remains open.');
  if(!response.ok)throw Error('Could not load the latest snapshot. It will retry automatically.');
  const documentHTML=new DOMParser().parseFromString(await response.text(),'text/html');
  const payloadNode=documentHTML.getElementById('protected-payload');
  if(!payloadNode)throw Error('The update service did not return a dashboard snapshot. Your current dashboard remains open; updates will retry automatically.');
  const payload=JSON.parse(payloadNode.textContent);
  const nextEtag=response.headers.get('etag')||response.headers.get('last-modified');
  if(payload.tag===latestToken){etag=nextEtag||etag;return false;}
  const clear=await window.warHavenSession.decrypt(payload),parsed=new DOMParser().parseFromString(clear,'text/html');
  const source=parsed.getElementById('war-data'),report=parsed.getElementById('recruiter-data');
  if(!source)throw Error('The published update is missing its snapshot. Your current dashboard remains open.');
  applySnapshot(JSON.parse(source.textContent),report?JSON.parse(report.textContent):{});
  latestToken=payload.tag;window.warHavenEnvelope=payload;etag=nextEtag||etag;
  return true;
 }
 async function check({force=false}={}){
  if(checking)return checking;
  if(!/^https?:$/.test(location.protocol)||document.hidden||!window.warHavenSession?.decrypt)return false;
  checking=(async()=>{
   try{
    if(!force&&etag){
     const head=await fetch(location.href.split('#')[0],{method:'HEAD',cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(15000)});
     if(!head.ok)throw Error('Could not check the latest snapshot. It will retry automatically.');
     const current=head.headers.get('etag')||head.headers.get('last-modified');
     if(current&&current===etag){notice('');return false;}
    }
    const changed=await readPublication();notice('');if(changed)toast('Dashboard updated automatically.');return changed;
   }catch(error){notice(error.message||'The latest data will load automatically when the connection returns.');return false;}
  })().finally(()=>checking=null);
  return checking;
 }
 return {check,applySnapshot};
})();

