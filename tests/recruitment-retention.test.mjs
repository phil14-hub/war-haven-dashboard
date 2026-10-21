import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {webcrypto} from 'node:crypto';
import {JSDOM,VirtualConsole} from 'jsdom';

const base=Date.now(),day=86400000,tag=i=>'#P'+i.toString(2).padStart(9,'0').replaceAll('0','P').replaceAll('1','Q');
const candidate=(i,age=1)=>({tag:tag(i),name:'Recruit '+i,townHallLevel:14,warStars:400,detectedAt:new Date(base-age*day).toISOString(),lastVerifiedAt:new Date(base).toISOString(),lifecycle:'STILL_CLANLESS'});
const report={updatedAt:new Date(base).toISOString(),groups:{new:[candidate(0)],still:Array.from({length:204},(_,i)=>candidate(i+1)),joined_my:[candidate(400,8)],no_longer:[candidate(401,8),candidate(1)]}};
report.groups.still.push(candidate(402,6.9));
const shared=[{id:crypto.randomUUID(),player_tag:tag(0),invited:0,answered_at:new Date(base).toISOString(),actor_name:'Fixture'}],invited=new Set([tag(0)]);
let failReads=true,failSaves=false,readBatches=[];
const wait=async check=>{for(let i=0;i<350;i++){if(check())return;await new Promise(r=>setTimeout(r,4));}throw Error('Recruit UI did not settle');};
async function app(initial=report){
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership#page=recruiter',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,$=id=>w.document.getElementById(id);
 let clock=base;w.Date.now=()=>clock;w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;Object.defineProperty(w,'crypto',{value:webcrypto});w.AbortSignal=AbortSignal;
 w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 w.warHavenSession={proof:async()=>'',decrypt:async()=>''};w.warHavenIndividual=true;
 $('recruiter-data').textContent=JSON.stringify(initial);
 w.fetch=async(input,options={})=>{
  const path=new URL(input,w.location.href).pathname,body=JSON.parse(options.body||'{}');let value={};
  if(path.endsWith('/me'))value={account:{id:'fixture-leader',role:'owner'},eligible:true};
  if(path.endsWith('/preferences/clan'))value={version:1,preferences:{theme:'light'}};
  if(path.endsWith('/notifications'))value={notifications:[]};
  if(path.endsWith('/recruitment-invitations')){
   if(body.read){readBatches.push(body.tags);assert.ok(body.tags.length<=100);if(failReads)return new Response(JSON.stringify({error:'Fixture outage'}),{status:503});value={contacts:shared.filter(r=>body.tags.includes(r.player_tag)),invitedTags:[...invited].filter(t=>body.tags.includes(t))};}
   else{if(failSaves)return new Response(JSON.stringify({error:'Fixture save outage'}),{status:503});const contact={id:body.id,player_tag:body.playerTag,player_name:body.playerName,opened_at:body.openedAt,answered_at:new Date(clock).toISOString(),invited:body.invited?1:0,actor_name:'Fixture leader'};shared.push(contact);if(body.invited)invited.add(body.playerTag);value={contact};}
  }
  return new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
 };
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
 await wait(()=>w.document.body.classList.contains('app-ready')&&$('recruitment-results'));
 return {dom,w,$,errors,advance(ms){clock+=ms;}};
}
let a=await app();
try{
 const {w,$}=a;
 await wait(()=>$('recruit-contact-status').textContent.includes('could not load'));
 assert.equal($('recruitment-results').querySelectorAll('.recruit-card').length,0,'Do not flash already invited cards before shared history loads');
 failReads=false;$('recruit-history-retry').click();await wait(()=>$('recruitment-results').querySelectorAll('.recruit-card').length===205);
 assert.ok(readBatches.length>=4);assert.equal($('recruitment-results').querySelector('[data-recruit-open="'+tag(0)+'"]'),null);
 assert.match($('recruitment-count').textContent,/205 matching players/);
 const visit=async i=>{const link=$('recruitment-results').querySelector('[data-recruit-open="'+tag(i)+'"]');assert.ok(link);link.addEventListener('click',e=>e.preventDefault(),{once:true});link.click();w.dispatchEvent(new w.Event('blur'));w.dispatchEvent(new w.Event('focus'));await wait(()=>$('recruit-invite-dialog')?.open);};
 await visit(1);$('recruit-invite-no').click();await wait(()=>!$('recruit-invite-dialog'));assert.ok($('recruitment-results').querySelector('[data-recruit-open="'+tag(1)+'"]'));
 await visit(1);failSaves=true;$('recruit-invite-yes').click();await wait(()=>$('recruit-invite-status')?.textContent.includes('Could not save'));assert.ok($('recruitment-results').querySelector('[data-recruit-open="'+tag(1)+'"]'),'A failed Yes keeps the card');
 failSaves=false;$('recruit-invite-yes').click();await wait(()=>!$('recruit-invite-dialog'));assert.equal($('recruitment-results').querySelector('[data-recruit-open="'+tag(1)+'"]'),null);assert.equal(shared.filter(r=>r.player_tag===tag(1)).length,2);
 invited.add(tag(2));await w.eval('RecruitmentContacts.load('+JSON.stringify(report.groups.new.concat(report.groups.still).map(r=>r.tag))+',{force:true})');assert.equal($('recruitment-results').querySelector('[data-recruit-open="'+tag(2)+'"]'),null,'Other leaders’ Yes removes cards');
 const next={...report,groups:{...report.groups,new:[candidate(500)],still:[...report.groups.new,...report.groups.still]}};
 w.eval('DashboardLiveUpdates.applySnapshot(data,'+JSON.stringify(next)+')');await wait(()=>$('recruitment-results').querySelector('[data-recruit-open="'+tag(500)+'"]'));
 assert.ok($('recruitment-results').querySelector('[data-recruit-open="'+tag(3)+'"]'),'A new scan retains yesterday’s candidates');assert.equal($('recruitment-results').querySelector('[data-recruit-open="'+tag(1)+'"]'),null);
 a.advance(.2*day);w.eval('openRecruiter()');assert.equal($('recruitment-results').querySelector('[data-recruit-open="'+tag(402)+'"]'),null,'Verification never renews card age');
 assert.equal(shared.filter(r=>r.player_tag===tag(1)).length,2);assert.deepEqual(a.errors,[]);
}finally{await a.w.eval('RecruitmentContacts.load([])');a.dom.window.close();}
a=await app();
try{await wait(()=>a.$('recruitment-count').textContent.includes('203 matching players'));assert.equal(a.$('recruitment-results').querySelector('[data-recruit-open="'+tag(1)+'"]'),null,'Fresh sign-in reads saved Yes before showing cards');assert.deepEqual(a.errors,[]);}finally{await a.w.eval('RecruitmentContacts.load([])');a.dom.window.close();}
console.log('Recruitment retention passed: weekly accumulation beyond 50, deduplication, age-based expiry, history gating/retry, batches over 200, Yes/No and failed saves, live scans, other leaders and fresh sign-in.');
