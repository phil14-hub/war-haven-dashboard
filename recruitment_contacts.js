const RecruitmentContacts=(()=>{
 const history=new Map(),invitedTags=new Set(),dismissedTags=new Set(),loaded=new Map(),cacheKey='war-haven-recruit-visits:'+data.clanTag,dismissKey='war-haven-recruit-dismissed:'+data.clanTag;
 let pending=[],started=false,dialog=null,saving=false,dismissalsReady=false,rerender=()=>{},loading=null,watched=[];
 const persist=()=>LeaderCache.set(cacheKey,pending);
 const valid=p=>p&&typeof p.id==='string'&&/^#[0289PYLQGRJCUV]{3,20}$/.test(p.tag)&&Number.isFinite(Date.parse(p.openedAt));
 const invited=tag=>invitedTags.has(tag),dismissed=tag=>dismissedTags.has(tag),ready=tag=>dismissalsReady&&(loaded.has(tag)||invited(tag));
 const persistDismissals=()=>LeaderCache.set(dismissKey,[...dismissedTags]);
 function dismiss(tag){
  tag=WarTracker.tag(tag);
  if(!dismissalsReady||!/^#[0289PYLQGRJCUV]{3,20}$/.test(tag)||dismissedTags.has(tag))return false;
  dismissedTags.add(tag);
  pending=pending.filter(visit=>visit.tag!==tag);persist();
  persistDismissals();rerender();
  toast('Player removed from this recruiter. No invitation was recorded.');
  return true;
 }
 function restoreDismissed(){
  if(!dismissalsReady||!dismissedTags.size)return;
  dismissedTags.clear();persistDismissals();rerender();
  toast('Dismissed recruiter candidates restored on this device.');
 }
 function remember(contact){
  const rows=history.get(contact.player_tag)||[];
  if(contact.invited)invitedTags.add(contact.player_tag);
  history.set(contact.player_tag,[contact,...rows.filter(r=>r.id!==contact.id)].sort((a,b)=>Date.parse(b.answered_at)-Date.parse(a.answered_at)).slice(0,20));
 }
 function status(tag){
  const rows=history.get(tag)||[],last=rows[0];
  if(!last)return '<p class="small muted recruit-contact-status">No saved invitation response.</p>';
  return '<p class="recruit-contact-status"><b>'+ (last.invited?'Invited':'No invitation sent')+'</b> · '+esc(date(last.answered_at))+'</p><details class="recruit-history"><summary>Invitation history ('+rows.length+')</summary>'+rows.slice(0,5).map(r=>'<p class="small muted"><b>'+(r.invited?'Invited':'No invitation sent')+'</b> · '+esc(date(r.answered_at))+' · '+esc(r.actor_name)+'</p>').join('')+'</details>';
 }
 function show(){
  if(document.hidden||dialog?.open||saving)return;
  const visit=pending.find(p=>p.away);if(!visit)return;
  const node=document.createElement('dialog');dialog=node;node.id='recruit-invite-dialog';node.className='settings-dialog';node.setAttribute('aria-labelledby','recruit-invite-title');
  node.innerHTML='<h2 id="recruit-invite-title">Did you invite '+esc(visit.name)+'?</h2><p class="tag">'+esc(visit.tag)+'</p><p class="small muted">Yes removes this player’s card and saves the invitation for all leaders. No keeps the card until it is a week old.</p><p id="recruit-invite-status" role="status"></p><div class="dialog-actions"><button id="recruit-invite-yes" class="primary">Yes</button><button id="recruit-invite-no">No</button></div>';
  document.body.append(node);node.oncancel=e=>{if(saving){e.preventDefault();return;}node.remove();dialog=null;};
  const choose=async invited=>{
   if(saving)return;saving=true;visit.answer=invited;persist();
   const buttons=[...node.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);$('recruit-invite-status').textContent='Saving response…';
   try{
    const result=await memberFeatureRequest('admin/recruitment-invitations',{id:visit.id,playerTag:visit.tag,playerName:visit.name,openedAt:visit.openedAt,invited});
    remember(result.contact);pending=pending.filter(p=>p.id!==visit.id);persist();node.close();node.remove();dialog=null;saving=false;rerender();toast(invited?'Invitation saved. '+visit.name+' was removed from the list.':'Saved: no invitation sent to '+visit.name+'.');show();
   }catch(error){saving=false;buttons.forEach(b=>b.disabled=false);$('recruit-invite-status').textContent='Could not save: '+error.message+'. Choose Yes or No to retry.';}
  };
  $('recruit-invite-yes').onclick=()=>choose(true);$('recruit-invite-no').onclick=()=>choose(false);node.showModal();$('recruit-invite-no').focus();
 }
 function away(){if(pending.length){pending.forEach(p=>p.away=true);persist();}}
 function returned(){if(!document.hidden){show();if(document.body.dataset.page==='recruiter'){rerender();void load(watched);}}}
 function start(render){
  rerender=render;if(started)return;started=true;
  window.addEventListener('blur',away);window.addEventListener('focus',returned);window.addEventListener('pageshow',returned);
  document.addEventListener('visibilitychange',()=>document.hidden?away():returned());
  // Expire cards on an open page and receive invitations saved by other leaders.
  setInterval(()=>{if(!document.hidden&&document.body.dataset.page==='recruiter'){rerender();void load(watched);}},60000);
  LeaderCache.ready().then(()=>{
   const savedDismissals=LeaderCache.get(dismissKey);
   if(Array.isArray(savedDismissals))for(const tag of savedDismissals)if(typeof tag==='string'&&/^#[0289PYLQGRJCUV]{3,20}$/.test(tag))dismissedTags.add(tag);
   dismissalsReady=true;
   const saved=LeaderCache.get(cacheKey);
   if(Array.isArray(saved))for(const p of saved.filter(valid))if(!pending.some(v=>v.id===p.id)&&!dismissed(p.tag))pending.push({...p,away:true});
   rerender();show();
  });
 }
 function wire(root){
  root.querySelectorAll('[data-recruit-dismiss]').forEach(button=>button.onclick=()=>dismiss(button.dataset.recruitDismiss));
  root.querySelectorAll('[data-recruit-open]').forEach(a=>a.onclick=()=>{
   const visit={id:crypto.randomUUID(),tag:a.dataset.recruitOpen,name:a.dataset.recruitName||a.dataset.recruitOpen,openedAt:new Date().toISOString(),away:false};
   if(valid(visit)){pending.push(visit);persist();}
  });
 }
 async function load(tags,{force=false}={}){
  watched=[...new Set(tags)].filter(t=>/^#[0289PYLQGRJCUV]{3,20}$/.test(t));
  if(loading){await loading;return load(tags,{force:false});}
  const needed=watched.filter(t=>force||!loaded.has(t)||Date.now()-loaded.get(t)>=60000);if(!needed.length)return;
  loading=(async()=>{
   try{
    // Short batches fit the API request size even for hundreds of weekly cards.
    for(let i=0;i<needed.length;i+=100){
     const batch=needed.slice(i,i+100),result=await memberFeatureRequest('admin/recruitment-invitations',{read:true,tags:batch});
     for(const tag of result.invitedTags||[])invitedTags.add(tag);
     for(const row of result.contacts)remember(row);
     for(const tag of batch)loaded.set(tag,Date.now());
    }
    if($('recruit-contact-status'))$('recruit-contact-status').textContent='Invitation records stay saved across scans. Invited players are hidden for all leaders.';
   }catch(error){if($('recruit-contact-status'))$('recruit-contact-status').textContent='Invitation history could not load: '+error.message+'. Use Retry invitation history.';}
   finally{rerender();}
  })();
  try{await loading;}finally{loading=null;}
 }
 return {start,wire,load,status,invited,dismissed,dismiss,restoreDismissed,dismissedCount:()=>dismissedTags.size,ready};
})();
