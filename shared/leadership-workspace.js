const LeadershipWorkspace=(()=>{
 let lastOperations=null,loadingOperations=false;
 const escape=value=>WarHavenUI.esc(value);
 const timestamp=value=>value?WarHavenUI.date(value):'Not reported yet';
 const names={clan:'Clan collection',recruitment:'Recruiter scan',portal:'Portal synchronization',code:'Dashboard release','war-watch':'Final-war watcher','war-capture':'Final-war capture'};
 const runLink=id=>/^\d{1,20}$/.test(String(id||''))?'https://github.com/phil14-hub/war-haven-dashboard/actions/runs/'+id:null;
 const freshness=(value,now)=>!value?'Not captured':now-Date.parse(value)>36*3600000?'Needs refresh':'Current';
 function drawOperations(value,error=''){
  const host=$('operations-content');if(!host)return;
  const p=value?.publication||{},now=Date.parse(value?.checkedAt)||Date.now(),updates=value?.updates||{};
  host.innerHTML=`<p class="notice">Data stays available from the last successful capture. Workflow completion and data freshness are shown separately.</p>${error?'<p class="warning" role="alert">'+escape(error)+'</p>':''}<div class="wh-operations-grid">${[['Clan data',p.clanCapturedAt||p.updatedAt],['Recruiter data',p.recruiterCapturedAt],['Final war capture',p.lastFinalWarCaptureAt],['Portal publication',p.publishedAt]].map(([label,at])=>`<article class="panel"><small>${label}</small><h3>${escape(timestamp(at))}</h3><p>${escape(freshness(at,now))}</p></article>`).join('')}</div><section class="panel"><div class="section-heading"><h2>Update requests</h2><button id="operations-refresh">Refresh status</button></div>${['clan','recruitment'].map(kind=>{const job=updates[kind];return `<div class="item-row"><span><b>${names[kind]}</b><small>Last finished ${escape(timestamp(job?.finishedAt))}</small></span><span class="pill">${escape(job?.stuck?'Needs attention · update may be stuck':job?.status||'No request recorded')}</span></div>${job?.components&&job.components.portal===false?'<p class="warning">Portal synchronization is pending. The previous complete publication is retained.</p>':''}`;}).join('')}<p class="small muted">Queued jobs over 30 minutes and expired running leases need review. Check Actions before requesting another update.</p><a class="button" href="https://github.com/phil14-hub/war-haven-dashboard/actions" target="_blank" rel="noopener noreferrer">Open workflow history</a></section><section class="panel"><h2>Successful updates and failures</h2><div class="table-wrap"><table><thead><tr><th>Workflow</th><th>Latest state</th><th>Last successful run</th><th>Last failure or cancellation</th></tr></thead><tbody>${Object.entries(names).map(([kind,label])=>{const row=value?.health?.find(v=>v.kind===kind),failure=runLink(row?.lastFailureRunId),current=runLink(row?.runId);return `<tr><td>${label}</td><td>${current?'<a href="'+current+'" target="_blank" rel="noopener noreferrer">'+escape(row?.stuck?'Needs attention':row?.status||'Not reported')+'</a>':'Not reported yet'}</td><td>${escape(timestamp(row?.lastSuccessfulAt))}</td><td>${failure?'<a href="'+failure+'" target="_blank" rel="noopener noreferrer">'+escape(timestamp(row?.lastFailedAt))+'</a>':'None reported'}</td></tr>`;}).join('')}</tbody></table></div><p class="small muted">Monitoring begins with the updated workflows. A missing report does not confirm that a job succeeded.</p></section><section class="panel"><h2>War capture and maintenance</h2><p>Next recorded final-war check: ${escape(timestamp(p.nextFinalWarCheckAt))}</p><p>Unresolved expired capture attempts: ${escape(p.incompleteFinalCaptures??'Not reported')}</p><p>Last storage maintenance: ${escape(timestamp(value?.maintenance?.completedAt))}</p><p class="small muted">Generated delivery copies keep a seven-day rollback window and at least the current and previous generation. Encrypted archives, war evidence and applied migrations are preserved.</p>${(p.warnings||[]).map(w=>'<p class="warning">'+escape(w)+'</p>').join('')}<small>Checked ${escape(timestamp(value?.checkedAt))} · Dashboard version ${escape(p.sourceBuildVersion||'not reported')}</small></section><section class="panel"><h2>Password changes and recovery</h2><details id="operations-password-help"><summary>Change the shared dashboard password · owner only</summary><ol><li>Open Settings → Leader settings → Change shared password.</li><li>Confirm the current shared password, the new passphrase and GitHub repository-owner authorization.</li><li>Wait for publication, reload the latest dashboard, then update any Pyto collector to the new password.</li></ol><p>This route updates the encrypted website, archive and automatic collector secret together. SMS alerts are disabled.</p><button id="operations-password-change">Open shared password change</button></details><details id="operations-recovery-help"><summary>Recover account or owner access</summary><p>For a personal account, use Forgot password on the sign-in page. If an authenticator is enabled, use your authenticator or a saved recovery code.</p><p>If an approved website owner exists, that owner restores suspended access. If no approved owner exists, sign in with the verified account for the in-game clan leader and use Recover website owner access. Recovery requires the account password, any enabled authenticator and GitHub repository-owner authorization.</p><p>Keep the MFA encryption key and backups safe. Restore a verified archive and database backup before republishing a matched generation.</p><a class="button" href="https://github.com/phil14-hub/war-haven-dashboard/blob/main/SETUP.md#website-owner-recovery" target="_blank" rel="noopener noreferrer">Owner recovery procedure</a></details></section>`;
  $('operations-refresh').onclick=()=>openOperations();
  $('operations-password-change').onclick=()=>openPasswordChange();
  const help=new URLSearchParams(location.hash.slice(1)).get('help');
  if(['password','recovery'].includes(help))$('operations-'+help+'-help').open=true;
 }
 async function openOperations(){
  if(loadingOperations)return;loadingOperations=true;
  if(!lastOperations)$('operations-content').innerHTML='<p class="notice" role="status">Loading update status…</p>';
  try{lastOperations=await memberFeatureRequest('admin/operations',{read:true});drawOperations(lastOperations);}
  catch(error){drawOperations(lastOperations,'Status could not be checked. '+error.message);}
  finally{loadingOperations=false;}
 }
 function openWarEvidence(id){
  $('player-dialog')?.close();$('war-kind').value='';setTab('history');
  const card=[...$('history-list').querySelectorAll('[data-war-id]')].find(node=>node.dataset.warId===id);
  if(card){card.classList.add('attendance-evidence-highlight');card.tabIndex=-1;card.scrollIntoView?.({block:'center',behavior:'auto'});card.focus({preventScroll:true});}
  const route=new URLSearchParams(location.hash.slice(1));route.set('war',id);history.replaceState(history.state,'',location.pathname+location.search+'#'+route);
 }
 function openAttendanceEvidence(tag){
  const player=rows.find(p=>p.tag===tag);if(!player)return;
  profileTabs.set(tag,'war');openPlayer(tag);
  const panel=$('player-profile').querySelector('[data-profile-panel="war"]');if(!panel)return;
  const existing=panel.querySelector('.attendance-evidence');existing?.remove();
  const evidence=(player.history||[]).filter(h=>!h.excused&&(!h.complete||h.player.attacksUsed===0)).slice(-10).reverse();
  panel.insertAdjacentHTML('afterbegin','<section class="notice attendance-evidence"><h3>Attendance flag evidence</h3><p>'+escape(player.reason)+'</p>'+evidence.map(h=>'<p><button data-attendance-war="'+escape(h.war.id)+'">'+escape(h.war.opponent?.name||'Opponent')+' · '+escape(timestamp(h.war.endTime))+' · '+(h.complete?'0 / 2 confirmed attacks':'Final details incomplete')+'</button></p>').join('')+(!evidence.length?'<p>No unexcused missed or incomplete appearance is available in this player’s captured history.</p>':'')+'<p class="small muted">Approved excuses remain excluded. Review the actual capture before making a decision in Clash.</p></section>');
  panel.querySelectorAll('[data-attendance-war]').forEach(button=>button.onclick=()=>openWarEvidence(button.dataset.attendanceWar));
  panel.tabIndex=-1;panel.scrollIntoView?.({block:'start',behavior:'auto'});panel.focus({preventScroll:true});
 }
 function start(){
  document.addEventListener('click',event=>{const button=event.target.closest('[data-attendance-evidence]');if(!button)return;event.preventDefault();event.stopPropagation();openAttendanceEvidence(button.dataset.attendanceEvidence);},true);
  setInterval(()=>{if(!document.hidden&&document.body.dataset.page==='operations')openOperations();},60000);
  const id=new URLSearchParams(location.hash.slice(1)).get('war');if(document.body.dataset.page==='history'&&id)openWarEvidence(id);
 }
 return {start,openOperations,openAttendanceEvidence,openWarEvidence};
})();
