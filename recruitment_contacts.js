const RecruitmentContacts=(()=>{
 const history=new Map(),cacheKey='war-haven-recruit-visits:'+data.clanTag;
 let pending=[],started=false,dialog=null,saving=false,rerender=()=>{},lastLoad=0;
 const persist=()=>LeaderCache.set(cacheKey,pending);
 const valid=p=>p&&typeof p.id==='string'&&/^#[0289PYLQGRJCUV]{3,20}$/.test(p.tag)&&Number.isFinite(Date.parse(p.openedAt));
 function remember(contact){
  const rows=history.get(contact.player_tag)||[];
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
  node.innerHTML='<h2 id="recruit-invite-title">Did you invite '+esc(visit.name)+'?</h2><p class="tag">'+esc(visit.tag)+'</p><p class="small muted">Save what happened during your visit to Clash. Your response is shared with clan leadership.</p><p id="recruit-invite-status" role="status"></p><div class="dialog-actions"><button id="recruit-invite-yes" class="primary">Yes</button><button id="recruit-invite-no">No</button></div>';
  document.body.append(node);node.oncancel=e=>{if(saving){e.preventDefault();return;}node.remove();dialog=null;};
  const choose=async invited=>{
   if(saving)return;saving=true;visit.answer=invited;persist();
   const buttons=[...node.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);$('recruit-invite-status').textContent='Saving response…';
   try{
    const result=await memberFeatureRequest('admin/recruitment-invitations',{id:visit.id,playerTag:visit.tag,playerName:visit.name,openedAt:visit.openedAt,invited});
    remember(result.contact);pending=pending.filter(p=>p.id!==visit.id);persist();node.close();node.remove();dialog=null;saving=false;rerender();toast(invited?'Invitation saved for '+visit.name+'.':'Saved: no invitation sent to '+visit.name+'.');show();
   }catch(error){saving=false;buttons.forEach(b=>b.disabled=false);$('recruit-invite-status').textContent='Could not save: '+error.message+'. Choose Yes or No to retry.';}
  };
  $('recruit-invite-yes').onclick=()=>choose(true);$('recruit-invite-no').onclick=()=>choose(false);node.showModal();$('recruit-invite-no').focus();
 }
 function away(){if(pending.length){pending.forEach(p=>p.away=true);persist();}}
 function returned(){if(!document.hidden)show();}
 function start(render){
  rerender=render;if(started)return;started=true;
  window.addEventListener('blur',away);window.addEventListener('focus',returned);window.addEventListener('pageshow',returned);
  document.addEventListener('visibilitychange',()=>document.hidden?away():returned());
  LeaderCache.ready().then(()=>{const saved=LeaderCache.get(cacheKey);if(Array.isArray(saved)){for(const p of saved.filter(valid))if(!pending.some(v=>v.id===p.id))pending.push({...p,away:true});}show();});
 }
 function wire(root){
  root.querySelectorAll('[data-recruit-open]').forEach(a=>a.onclick=()=>{
   const visit={id:crypto.randomUUID(),tag:a.dataset.recruitOpen,name:a.dataset.recruitName||a.dataset.recruitOpen,openedAt:new Date().toISOString(),away:false};
   if(valid(visit)){pending.push(visit);persist();}
  });
 }
 async function load(tags){
  if(Date.now()-lastLoad<60000)return;lastLoad=Date.now();
  try{const result=await memberFeatureRequest('admin/recruitment-invitations',{read:true,tags:[...new Set(tags)].slice(0,1000)});for(const row of result.contacts)remember(row);if($('recruit-contact-status'))$('recruit-contact-status').textContent='Invitation responses are shared across leaders and kept through recruiting scans.';rerender();}
  catch(error){lastLoad=0;if($('recruit-contact-status'))$('recruit-contact-status').textContent='Invitation history could not load: '+error.message;}
 }
 return {start,wire,load,status};
})();
