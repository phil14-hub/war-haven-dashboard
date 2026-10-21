import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {webcrypto} from 'node:crypto';
import {JSDOM,VirtualConsole} from 'jsdom';

const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership#page=progress&growth=xp&xp_entry=1',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,$=id=>w.document.getElementById(id);
const wait=async check=>{for(let i=0;i<250;i++){if(check())return;await new Promise(r=>setTimeout(r,3));}throw Error('Follow-up UI did not settle');};
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;Object.defineProperty(w,'crypto',{value:webcrypto});w.AbortSignal=AbortSignal;
w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};w.prompt=()=>{throw Error('Attendance review must not prompt to clear flags');};
w.warHavenSession={proof:async()=>''};w.warHavenIndividual=true;
const state=JSON.parse($('war-data').textContent);state.sharedActions={enabled:true,url:w.location.origin,encryptionKey:Buffer.alloc(64,42).toString('base64')};$('war-data').textContent=JSON.stringify(state);
$('recruiter-data').textContent=JSON.stringify({updatedAt:state.lastSuccessfulSync,groups:{new:[{tag:'#P0C',name:'Recruit fixture',townHallLevel:14,lifecycle:'NEW',detectedAt:new Date().toISOString()}],still:[],joined_my:[],no_longer:[]}});
let readXp=false,request=null,failContact=false;const contacts=[];
w.fetch=async(input,options={})=>{
 const path=new URL(input,w.location.href).pathname,body=JSON.parse(options.body||'{}');let value={};
 if(path.endsWith('/me'))value={account:{id:'fixture-leader',role:'owner'},eligible:true};
 if(path.endsWith('/preferences/clan'))value={version:1,preferences:{theme:'light'}};
 if(path.endsWith('/notifications')){if(body.id||body.all)readXp=true;value={notifications:[{id:'clan-xp:2026-10-19',action:'clan-xp',title:"Add this week's Clan XP",created_at:'2026-10-19T15:00:00Z',read_at:readXp?'2026-10-19T22:00:00Z':null}]};}
 if(path.endsWith('/recruitment-invitations')){
  if(body.read)value={contacts};else{if(failContact){failContact=false;return new Response(JSON.stringify({error:'Fixture temporary outage'}),{status:503});}const contact={id:body.id,player_tag:body.playerTag,player_name:body.playerName,opened_at:body.openedAt,answered_at:new Date().toISOString(),invited:body.invited?1:0,actor_name:'Fixture leader'};if(!contacts.some(c=>c.id===contact.id))contacts.push(contact);value={contact};}
 }
 if(path==='/v1/challenge')value={salt:Buffer.alloc(16).toString('base64'),rounds:600000};
 if(path==='/v1/records')value={records:[]};
 if(path==='/v1/refresh/status')value={request:body.kind==='clan'?request:null};
 if(path==='/v1/refresh/request'){request={id:'fixture-update',status:'pending',requestedAt:new Date().toISOString(),estimateSeconds:120};value={request};}
 return new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
};
try{
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
 await wait(()=>w.document.body.classList.contains('app-ready')&&$('shared-update-description'));
 assert.equal(w.document.body.dataset.page,'progress');assert.equal($('xp-entry-details').open,true);assert.equal(w.document.activeElement.id,'xp-amount');
 $('xp-amount').value='1250';await w.eval('loadSharedPreferences()');assert.equal($('xp-entry-details').open,true);assert.equal($('xp-amount').value,'1250');
 for(const theme of ['dark','light']){w.WarHavenUI.apply({theme});for(const page of ['overview','weekly','progress','roster','townhalls','donations','achievements','current','planner','performance','history']){w.eval('setTab('+JSON.stringify(page)+')');const selected=$('hub-nav').querySelectorAll('[aria-current="page"]');assert.equal(selected.length,1);assert.equal(selected[0].dataset.hubTab,page);assert.equal(w.getComputedStyle(selected[0]).fontWeight,'750');}}
 for(const id of ['status','roster-sort','roster-hall','roster-attack-min','roster-attack-max','roster-reset']){assert.equal(w.getComputedStyle($(id)).height,'46px');assert.equal(w.getComputedStyle($(id)).fontSize,'14px');}assert.ok($('status').closest('label'));assert.equal(w.getComputedStyle($('roster-sort').closest('.roster-options')).display,'grid');
 w.eval("openPlayer('#P0Q')");$('player-profile').querySelector('[data-profile-tab="contributions"]').click();const before=w.eval('JSON.stringify(edits)');$('review-attendance-flag').click();assert.equal($('player-profile').querySelector('[data-profile-tab="war"]').getAttribute('aria-selected'),'true');assert.equal(w.eval('JSON.stringify(edits)'),before);$('player-dialog').close();
 $('leadership-bell').click();await wait(()=>$('leadership-notifications')?.open);$('leadership-notifications').querySelector('[data-leadership-news]').click();await wait(()=>!$('leadership-notifications').open);assert.equal(readXp,true);assert.equal(w.document.body.dataset.page,'progress');assert.equal($('xp-entry-details').open,true);
 $('leadership-bell').click();await wait(()=>$('leadership-notifications')?.open);assert.equal($('mark-leadership-news').hidden,true);$('close-leadership-news').click();
 $('refresh-data').click();await wait(()=>$('refresh-dialog').open);assert.equal($('website-update-submit').textContent,'Start clan update');assert.equal($('website-update-background').hidden,true);
 $('website-update-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));assert.match($('website-update-submit').textContent,/Working/);await wait(()=>!$('website-update-background').hidden);assert.equal($('website-update-submit').disabled,true);assert.ok($('website-update-submit').querySelector('.working-spinner'));assert.match($('website-update-background').textContent,/close this tab.*keep running/);assert.doesNotMatch($('refresh-dialog').textContent,/One-time automatic update setup/);$('refresh-dialog').close();
 w.eval("setTab('recruiter')");await wait(()=>$('recruitment-results').querySelector('[data-recruit-open]'));
 const open=()=>{const link=$('recruitment-results').querySelector('[data-recruit-open]');link.addEventListener('click',e=>e.preventDefault(),{once:true});link.click();};
 open();assert.equal($('recruit-invite-dialog'),null);w.dispatchEvent(new w.Event('blur'));w.dispatchEvent(new w.Event('focus'));await wait(()=>$('recruit-invite-dialog')?.open);assert.match($('recruit-invite-title').textContent,/Recruit fixture/);$('recruit-invite-no').click();await wait(()=>!$('recruit-invite-dialog'));assert.equal(contacts.length,1);assert.equal(contacts[0].invited,0);assert.match($('recruitment-results').textContent,/No invitation sent/);
 open();w.dispatchEvent(new w.Event('blur'));w.dispatchEvent(new w.Event('focus'));await wait(()=>$('recruit-invite-dialog')?.open);failContact=true;$('recruit-invite-yes').click();await wait(()=>$('recruit-invite-status')?.textContent.includes('Could not save'));assert.equal($('recruit-invite-dialog').open,true);$('recruit-invite-yes').click();await wait(()=>!$('recruit-invite-dialog'));assert.equal(contacts.length,2);assert.equal(contacts[1].invited,1);assert.equal($('recruitment-results').querySelector('[data-recruit-open]'),null);
 assert.deepEqual(errors,[]);
 console.log('Follow-up UI passed: all selected section tabs in both themes, direct/notification XP entry, preserved form draft, review-only attendance, Working spinner and close-tab notice, recruit return prompt, Yes/No history and failed-save retry.');
}finally{dom.window.close();}
