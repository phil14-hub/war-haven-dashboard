import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM,VirtualConsole} from 'jsdom';

const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,$=id=>w.document.getElementById(id);
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.fetch=async()=>new Response(JSON.stringify({version:1,preferences:{},notifications:[],records:[]}));
try {
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
 await new Promise(r=>setTimeout(r,40));
 w.eval(`
   data.roster[0].donations=1026;data.roster[1].donations=0;delete data.roster[2].donations;
   data.memberHistory['#P0Q']={since:'2026-10-14T00:00:00Z',lastSeen:'2026-10-19T10:00:00Z',inClan:true};
   const receipt={tag:'#P0Q',name:'Omid fixture',title:'1,000,000 lifetime gold looted',category:'Game achievement',observedAt:'2026-10-17T09:00:00Z',previousObservedAt:'2026-10-16T09:00:00Z',detail:'Threshold crossed',source:'Saved API profile',alreadyReached:false};
   data.honors={baseline:{...receipt,id:'baseline',alreadyReached:true},earned:{...receipt,id:'earned'},outside:{...receipt,id:'outside',previousObservedAt:'2026-10-13T00:00:00Z'},unknown:{...receipt,id:'unknown',previousObservedAt:null}};
   render();setTab('achievements');
 `);
 assert.deepEqual(Array.from(w.eval('ClanHonors.forData(data,edits).filter(a=>a.source==="Saved API profile").map(a=>a.id)')),['earned']);
 assert.equal($('achievements').querySelectorAll('.honor-card').length,1);
 assert.match($('achievements').textContent,/Earlier lifetime progress counts toward the threshold/);
 assert.doesNotMatch($('achievements').textContent,/Already reached when first recorded/);
 w.eval("setTab('donations')");
 const panel=$('donations').querySelector('.season-donations-panel'),points=[...panel.querySelectorAll('[data-donation-tag]')];
 assert.equal($('donations').firstElementChild,panel);assert.equal(points.length,3);assert.match(panel.querySelector('.wh-chart-caption').textContent,/≥ 1,026/);
 assert.deepEqual(points.map(p=>p.dataset.donationTag),['#P0Q','#P0Y','#P0U']);
 assert.match(points[1].getAttribute('aria-label'),/0 troops/);assert.match(points[2].getAttribute('aria-label'),/unknown/);
 assert.equal(points[0].querySelector('.wh-hit').getAttribute('r'),'22');
 const host=panel.querySelector('.wh-chart'),tip=host.querySelector('[role=tooltip]');
 const pointer=(point,type,pointerType)=>{const event=new w.Event(type,{bubbles:true});Object.defineProperty(event,'pointerType',{value:pointerType});point.dispatchEvent(event);};
 for(const pointerType of ['mouse','pen']){pointer(points[0],'pointerenter',pointerType);assert.equal(tip.hidden,false);assert.match(tip.textContent,/1,026 troops/);pointer(points[0],'pointerleave',pointerType);assert.equal(tip.hidden,true);}
 pointer(points[1],'pointerenter','touch');points[1].dispatchEvent(new w.MouseEvent('click',{bubbles:true}));pointer(points[1],'pointerleave','touch');assert.equal(tip.hidden,false);assert.match(tip.textContent,/0 troops/);
 w.document.body.dispatchEvent(new w.Event('pointerdown',{bubbles:true}));assert.equal(tip.hidden,true);
 points[0].focus();assert.equal(tip.hidden,false);points[0].dispatchEvent(new w.KeyboardEvent('keydown',{key:'End',bubbles:true}));assert.equal(w.document.activeElement,points[2]);assert.match(tip.textContent,/unknown/);
 points[2].dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(tip.hidden,true);
 assert.equal(host.querySelectorAll('[data-wh-inspect][tabindex="0"]').length,1);
 for(const [label,value,options,expected] of [['Percent',14.459235332888888,{percent:true},'14.5%'],['Stars per attack',2.8888888888888,{precision:2},'2.89'],['XP',1026,{},'1,026'],['Average Town Hall',14.459235332888888,{},'14.46']]){
  const holder=w.document.createElement('div');holder.innerHTML=w.WarHavenUI.chart(label,[{at:'2026-10-17T10:00:00Z',value}],options);
  assert.match(holder.textContent,new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
  assert.ok(holder.querySelector('[data-wh-inspect]').dataset.whDetail.includes(expected));
  for(const item of holder.querySelectorAll('.wh-chart-caption strong,svg text,tbody td'))assert.equal(/\d+\.\d{4,}/.test(item.textContent),false,label+': '+item.textContent);
  assert.equal(/\d+\.\d{4,}/.test(holder.querySelector('[data-wh-inspect]').getAttribute('aria-label')),false);
 }
 assert.deepEqual(errors,[]);
 console.log('Clan achievements and charts passed: baseline suppression, in-clan evidence, all roster members including zero/unknown counts, totals, mouse/pen/touch and keyboard inspection, 44px targets, and rounded percent/star/count/average chart values.');
} finally {dom.window.close();}
