import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {webcrypto} from 'node:crypto';
import {JSDOM,VirtualConsole} from 'jsdom';
const now=Date.parse('2026-11-09T12:00:00Z'),at=days=>new Date(now-days*86400000).toISOString();
const row=(tag,name,lifecycle='STILL_CLANLESS',days=1)=>({tag,name,lifecycle,townHallLevel:14,warStars:100,leagueTierScore:29,leagueTierName:'Dragon League 29',detectedAt:at(days),lastVerifiedAt:at(0)});
const current={...row('#P0J','Joined today','JOINED_MY_CLAN'),joinedMyClanAt:at(1)},old={...row('#P0R','Joined last month','JOINED_MY_CLAN',30),joinedMyClanAt:at(25)},left={...row('#P0U','Former clanmate','JOINED_OTHER_CLAN',40),joinedMyClanAt:at(35)};
const report={groups:{new:[row('#P0Y','New arrival','NEW')],still:[row('#P0Q','Still available')],joined_my:[current],no_longer:[]},joinedHistory:[current,old,left],stats:{everJoinedMyClanCount:3}};
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership#page=recruiter',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,$=s=>w.document.querySelector(s),all=s=>[...w.document.querySelectorAll(s)];
w.Date.now=()=>now;
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.AbortSignal=AbortSignal;Object.defineProperty(w,'crypto',{value:webcrypto});w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};w.warHavenIndividual=true;w.warHavenSession={proof:async()=>''};
$('#recruiter-data').textContent=JSON.stringify(report);
let releaseInvitations;
const delayInvitations=new Promise(resolve=>{releaseInvitations=resolve;});
w.fetch=async(input,options={})=>{const path=new URL(input,w.location.href).pathname;let body={notifications:[],records:[],items:[]};if(path.endsWith('/me'))body={account:{id:'fixture-leader',role:'owner'},eligible:true};if(path.endsWith('/recruitment-invitations')){await delayInvitations;body={contacts:[],invitedTags:['#P0R']};}if(path.endsWith('/preferences/clan'))body={version:1,preferences:{}};return new Response(JSON.stringify(body));};
const wait=async check=>{for(let i=0;i<300;i++){if(check())return;await new Promise(r=>setTimeout(r,3));}throw Error('Recruit filters did not settle');};
try{
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
 await wait(()=>$('#recruitment-loading')?.hidden===false);
 assert.ok($('#recruitment-loading .recruit-loading-spinner'));
 assert.ok($('#recruitment-loading progress:not([value])'));
 assert.ok($('#recruitment-results').hidden);
 releaseInvitations();
 await wait(()=>all('.recruit-card').length===3);await wait(()=>$('#settings-storage')?.textContent.includes('shared with all leaders'));assert.equal(all('[data-recruit-summary]').length,4);
 const click=key=>$('[data-recruit-summary="'+key+'"]').click();
 click('available');assert.equal(all('.recruit-card').length,2);assert.equal($('#recruit-section').value,'available');assert.equal($('[data-recruit-summary="available"]').getAttribute('aria-pressed'),'true');
 click('new');assert.equal(all('.recruit-card').length,1);assert.match($('#recruitment-results').textContent,/New arrival/);assert.doesNotMatch($('#recruitment-results').textContent,/Still available/);
 click('joined_my');assert.equal(all('.recruit-history-card').length,2);assert.match($('#recruitment-results').textContent,/Joined last month/);assert.equal($('[data-recruit-open]'),null,'Historical members do not enter the invitation workflow');assert.equal($('[data-recruit-dismiss]'),null);
 click('ever_joined');assert.equal(all('.recruit-history-card').length,3);assert.match($('#recruitment-results').textContent,/Former clanmate/);assert.match($('#recruitment-count').textContent,/3 matching/);
 $('#recruit-search').value='last month';$('#recruit-search').dispatchEvent(new w.Event('input'));assert.equal(all('.recruit-history-card').length,1);assert.match($('#recruitment-count').textContent,/1 matching/);
 $('#recruit-reset').click();assert.equal($('#recruit-section').value,'all');assert.equal(all('[aria-pressed=true][data-recruit-summary]').length,0);assert.equal(all('.recruit-card').length,3);
 $('#recruit-section').value='ever_joined';$('#recruit-section').dispatchEvent(new w.Event('input'));assert.equal(all('.recruit-history-card').length,3);assert.equal($('[data-recruit-summary="ever_joined"]').getAttribute('aria-pressed'),'true');
 const active=$('[data-recruit-summary="ever_joined"]');active.focus();w.eval('openRecruiter()');assert.equal(w.document.activeElement.dataset.recruitSummary,'ever_joined');
 const beforeReset='2026-11-09T04:59:59Z',afterReset='2026-11-09T05:00:00Z';
 const sample=(at,trophies)=>({at,trophies});
 const snapshot={...report,groups:{...report.groups,new:[],joined_my:[],still:[
  {...row('#P0Y','Week leader'),trophyHistory:[sample(at(0),120),sample(afterReset,30),sample(beforeReset,60)]},
  {...row('#P0Q','Prior leader'),trophies:100,trophyHistory:[sample(beforeReset,250),sample(at(0),100)]},
  {...row('#P0L','Confirmed zero'),trophies:0},
  {...row('#P0P','Missing current'),trophies:900,lastVerifiedAt:beforeReset},
  {...row('#P0C','Unranked player'),leagueTierScore:0,leagueTierName:'Unranked',trophies:999},
  {...row('#P0G','Unknown league'),leagueTierScore:undefined,leagueTierName:undefined,trophies:1000},
 ]}};
 w.eval('DashboardLiveUpdates.applySnapshot(data,'+JSON.stringify(snapshot)+')');
 $('#recruit-reset').click();
 await wait(()=>all('[data-recruit-open]').length===4);
 const select=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new w.Event('input'));};
 const order=()=>all('[data-recruit-open]').map(node=>node.dataset.recruitOpen);
 select('#recruit-sort','trophies');
 assert.equal($('#recruit-week').value,'2026-11-09T05:00:00.000Z');
 assert.deepEqual(order(),['#P0Y','#P0Q','#P0L','#P0P']);
 assert.equal($('#recruitment-loading').hidden,true);
 select('#recruit-week','2026-11-02T05:00:00.000Z');
 assert.deepEqual(order().slice(0,3),['#P0P','#P0Q','#P0Y']);
 assert.doesNotMatch($('#recruitment-results').textContent,/Unranked player|Unknown league/);
 $('#recruit-reset').click();
 assert.ok($('#recruit-week-field').hidden);
 assert.doesNotMatch($('#recruitment-results').textContent,/NaN|undefined|null/);assert.deepEqual(errors,[]);
 console.log('Recruiter filters passed: four clickable/toggleable summary cards, combined available list, matching status selector, query/reset/counts, focus, and complete archived joining history independent of invitation/card expiry.');
}finally{releaseInvitations();await w.eval('RecruitmentContacts.load([])');dom.window.close();}
