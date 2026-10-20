const LeadershipSession=(()=>{
 if(!window.warHavenIndividual||!location.pathname.startsWith('/members/'))return {check:async()=>true};
 const originalFetch=window.fetch.bind(window);let checking=null,expired=false,accountId=window.warHavenAccountId||null;
 const channel=typeof BroadcastChannel==='function'?new BroadcastChannel('war-haven-account-session'):null;
 async function expire(navigate=true){
  if(expired&&navigate)return;expired=true;window.warHavenLeadershipExpired=true;
  document.querySelectorAll('dialog').forEach(dialog=>dialog.remove());
  const panel=document.createElement('main');panel.className='panel';panel.innerHTML='<h1>Sign in to continue</h1><p>Your leadership session changed or expired. Private information has been cleared. Encrypted drafts remain available after an authorized sign-in.</p><a class="button" href="/members/?portal=leader">Leadership sign in</a>';
  document.body.replaceChildren(panel);
  if(typeof data!=='undefined')data={};if(typeof edits!=='undefined')edits={};if(typeof rows!=='undefined')rows=[];if(typeof recruiterReport!=='undefined')recruiterReport={};
  window.warHavenEnvelope=null;window.warHavenSession=null;
  if(typeof LeaderCache!=='undefined')await LeaderCache.lock();
  if(navigate)location.replace('/members/?portal=leader');
 }
 async function check(){
  if(expired)return false;if(checking)return checking;
  checking=(async()=>{try{const response=await originalFetch('/members/api/me',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(15000)});
   if(response.status===401||response.status===403){await expire();return false;}if(!response.ok)return true;
   const value=await response.json();if(!value.account||!value.eligible||!['owner','leader','co_leader'].includes(value.account.role)||accountId&&value.account.id!==accountId){await expire();return false;}accountId=value.account.id;return true;
  }catch{return !expired;}})().finally(()=>checking=null);return checking;
 }
 window.fetch=async function(input,options){
  if(expired)throw Object.assign(Error('Sign in again to continue.'),{status:401});
  const response=await originalFetch(input,options),url=new URL(typeof input==='string'?input:input.url||String(input),location.href);
  if(url.origin===location.origin&&(url.pathname.startsWith('/members/api/')||url.pathname.startsWith('/v1/'))){
   if([401,403].includes(response.status))void check();
   if(response.ok&&url.pathname==='/members/api/logout')channel?.postMessage({type:'session-changed'});
  }
  return response;
 };
 if(channel)channel.onmessage=event=>{if(event.data?.type==='session-changed')void check();};
 window.addEventListener('focus',()=>void check());
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)void check();});
 window.addEventListener('pagehide',event=>{if(event.persisted)void expire(false);});
 window.addEventListener('pageshow',event=>{if(event.persisted)location.replace('/members/?portal=leader');});
 setInterval(()=>{if(!document.hidden)void check();},30000);
 queueMicrotask(()=>void check());
 return {check,expire};
})();
