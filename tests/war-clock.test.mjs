import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM,VirtualConsole} from 'jsdom';
const base=Date.parse('2030-01-01T12:00:00Z');let elapsed=0,deviceOffset=30*60000,failTime=false;
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window;
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.AbortSignal=AbortSignal;w.Date.now=()=>base+elapsed+deviceOffset;Object.defineProperty(w.performance,'now',{value:()=>elapsed});
w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.fetch=async url=>{if(String(url).endsWith('/time')){if(failTime)throw Error('offline');return new Response(JSON.stringify({serverNow:new Date(base+elapsed).toISOString()}));}return new Response(JSON.stringify({preferences:{},records:[],notifications:[],history:[],invitedTags:[]}));};
try{
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
 for(let i=0;i<100&&!w.document.body.classList.contains('app-ready');i++)await new Promise(r=>setTimeout(r,3));
 await w.WarHavenUI.syncClock();assert.equal(w.WarHavenUI.now(),base);
 const war={id:'live',kind:'Regular',source:'API',state:'inWar',final:false,rosterComplete:true,startTime:new Date(base-86400000).toISOString(),endTime:new Date(base+38*60000).toISOString(),opponent:{name:'Clock fixture'},attacksPerMember:2,teamSize:1,participants:[{tag:'#P0Q',attacksUsed:0}],stars:0,opponentStars:0};
 w.eval('data.wars='+JSON.stringify([war])+';data.lastSuccessfulSync='+JSON.stringify(new Date(base).toISOString())+';setTab("current");renderCurrent();tickWarClocks();');
 const value=()=>w.document.querySelector('[data-clock-value]').textContent,phase=()=>w.document.querySelector('[data-war-status]').textContent;
 assert.equal(value(),'00:38:00','Thirty-minute device skew must not shorten the timer');
 elapsed+=1000;deviceOffset=-120*60000;w.eval('tickWarClocks()');assert.equal(value(),'00:37:59','Device clock changes must not change a running countdown');
 failTime=true;assert.equal(await w.WarHavenUI.syncClock(),false);elapsed+=1000;w.eval('tickWarClocks()');assert.equal(value(),'00:37:58','Offline sync keeps the last server anchor');
 elapsed=38*60000;const unchanged=w.eval('JSON.stringify(data.wars)');w.eval('tickWarClocks()');assert.equal(phase(),'Awaiting war update');assert.equal(value(),'—');assert.match(w.document.querySelector('[data-clock-date]').textContent,/in-game timer/);assert.equal(w.WarTracker.isClosed(war,base+elapsed),true);assert.equal(w.eval('JSON.stringify(data.wars)'),unchanged);
 w.eval('data.wars[0].endTime='+JSON.stringify(new Date(base+elapsed+30*60000).toISOString())+';renderCurrent();tickWarClocks()');assert.equal(value(),'00:30:00');assert.equal(phase(),'In progress');
 // Old provisional captures must still break attendance streaks and stay out
 // of the current-war list after the six-hour final-capture retry window.
 const old={...war,id:'old-incomplete',startTime:new Date(base-2*86400000).toISOString(),endTime:new Date(base-86400000).toISOString()};
 const row=w.WarTracker.playersFor({wars:[old],roster:[{tag:'#P0Q',name:'Late attacker'}],policyStart:new Date(base-3*86400000).toISOString()}, {}, base)[0];
 assert.equal(row.uncertain,true);assert.equal(row.played,0);assert.equal(row.kick,false);assert.deepEqual(Array.from(row.gaps),['old-incomplete']);
 w.eval('data.wars.push('+JSON.stringify(old)+');renderCurrent();tickWarClocks()');assert.equal(w.document.querySelectorAll('[data-war-clock]').length,1);
 assert.equal(w.WarTracker.warTiming({...war,state:'warEnded'},base).label,'War ended');
 assert.equal(w.WarTracker.warTiming({...war,final:true},base).label,'War ended');
 assert.deepEqual(errors,[]);
 console.log('War clock passed: server clock, 30-minute device skew, device time changes, offline sync, stale deadline, corrected time and API-only ended confirmation.');
}finally{w.close();}
