import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM,VirtualConsole} from 'jsdom';
const file=process.env.WAR_HAVEN_DASHBOARD_FIXTURE;if(!file)throw Error('Leadership fixture required');
const wait=async test=>{for(let i=0;i<200;i++){if(test())return;await new Promise(r=>setTimeout(r,3));}throw Error('Leadership experience did not settle');};
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(file,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership#page=roster&player=%23P0Q&section=upgrades',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,$=id=>w.document.getElementById(id);
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.crypto.randomUUID=()=>crypto.randomUUID();w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.confirm=()=>true;w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.fetch=async(input)=>{const path=new URL(input,w.location.href).pathname;return new Response(JSON.stringify(path.endsWith('/list')?{accounts:[],counts:{pending:0,active:0,suspended:0},capabilities:{individual:true}}:path.endsWith('/announcements')?{announcements:[]}:path.endsWith('/notifications')?{notifications:[]}:path.endsWith('/preferences/clan')?{version:0,preferences:{}}:{records:[],items:[]}));};
try{
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());await wait(()=>w.document.body.classList.contains('app-ready'));
 assert.equal(w.document.body.dataset.page,'roster');assert.ok($('player-dialog').open);assert.equal($('player-profile').querySelector('[data-profile-panel="upgrades"]').classList.contains('hidden'),false);
 $('player-dialog').querySelector('[data-close="player-dialog"]').click();assert.equal($('player-dialog').open,false);assert.doesNotMatch(w.location.hash,/player=/);
 w.eval("setTab('planner')");assert.match(w.location.hash,/page=planner/);w.history.back();await wait(()=>w.document.body.dataset.page==='roster');
 $('search').value='Omid';$('search').dispatchEvent(new w.Event('input'));assert.match(w.location.hash,/q=Omid/);w.eval("openPlayer('#P0Q')");assert.match(w.location.hash,/player=%23P0Q/);$('player-profile').querySelector('[data-profile-tab="contributions"]').click();assert.match(w.location.hash,/section=contributions/);$('player-dialog').querySelector('[data-close="player-dialog"]').click();await wait(()=>!$('player-dialog').open);assert.equal($('search').value,'Omid');
 w.eval("setTab('more')");assert.match($('more').textContent,/Account access/);assert.match($('more').textContent,/Clan communications/);assert.equal($('hub-nav').children.length,0);w.eval("setTab('communications')");await wait(()=>$('member-news-form'));assert.equal($('member-news-form').closest('section').id,'');assert.equal($('clan-communications').contains($('member-news-form')),true);
 // Populate enough available synthetic players to commit a supported regular team.
 w.eval("data.roster.push(...['#P0L','#P0V','#P0G'].map((tag,i)=>({tag,name:'Reserve '+i,townHallLevel:14,warPreference:'in',role:'member'})));render();setTab('planner');");
 $('planner-suggest').click();assert.equal(w.eval('Object.values(edits.lineupPlans).filter(p=>!p.deleted).length'),0);assert.equal(w.eval('edits.lineupDrafts.Regular.tags.length'),5);
 $('planner-save').click();const committed=w.eval('JSON.stringify(edits.lineupPlans.Regular)');assert.equal(JSON.parse(committed).tags.length,5);assert.equal(JSON.parse(committed).options.size,'5');
 const check=$('planner').querySelector('[data-lineup-player]:checked');check.checked=false;check.dispatchEvent(new w.Event('change'));assert.equal(w.eval('edits.lineupDrafts.Regular.tags.length'),4);assert.equal(w.eval('JSON.stringify(edits.lineupPlans.Regular)'),committed);$('planner-save').click();assert.equal(w.eval('JSON.stringify(edits.lineupPlans.Regular)'),committed);
 w.eval("edits.lineupPlans.Regular={...edits.lineupPlans.Regular,commitId:'another-leader'};renderWarPlanner();");assert.ok($('planner-review-latest'));$('planner-save').click();assert.equal(w.eval('edits.lineupPlans.Regular.commitId'),'another-leader');
 assert.deepEqual(errors,[]);
 console.log('Leadership experience passed: deep profiles, close/Back, filters, announcement navigation, collaborative drafts, validated commits and changed-plan review.');
}finally{await new Promise(r=>setTimeout(r,30));dom.window.close();}
