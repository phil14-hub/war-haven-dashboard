import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM, VirtualConsole} from 'jsdom';

const errors=[], vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window;
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.fetch=async()=>new Response(JSON.stringify({version:1,preferences:{},notifications:[],records:[]}),{headers:{'Content-Type':'application/json'}});
for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
await new Promise(r=>setTimeout(r,30));
try {
  w.eval(`data.roster[0].donations=1026;data.roster[0].donationsReceived=320;data.profiles['#P0Q'].donations=709;data.profiles['#P0Q'].trophies=2500;
  data.memberHistory['#P0Q']={since:'2026-10-14T17:59:45Z',lastSeen:data.lastSuccessfulSync,donationIntervals:[{start:'2026-10-14T17:59:45Z',end:data.lastSuccessfulSync,count:317}]};render();setTab('donations');`);
  const $=id=>w.document.getElementById(id);
  const stat=(host,label)=>[...host.querySelectorAll('.card')].find(c=>c.querySelector('.label')?.textContent===label)?.querySelector('strong')?.textContent;
  assert.equal($('donations').querySelector('[data-extended-player="#P0Q"] .donation-grid strong').textContent,'1,026');
  w.eval("openPlayer('#P0Q')");
  const contributions=()=>w.document.querySelector('[data-profile-panel="contributions"]');
  assert.equal(stat(contributions(),'Donated this season'),'1,026');
  assert.equal(stat(contributions(),'Received this season'),'320');
  assert.equal(stat(contributions(),'Observed troop donations'),'317');
  assert.match(contributions().textContent,/after tracking began/);
  assert.equal(stat(w.document.querySelector('[data-profile-panel="profile"]'),'Current trophies'),'3,000');
  for(const p of w.eval('data.roster')) {
    w.eval('openPlayer('+JSON.stringify(p.tag)+')');
    assert.equal(stat(contributions(),'Donated this season'),p.donations.toLocaleString());
  }
  w.eval(`data.edits=edits;edits.exceptions['w1::#P0Q']={value:true};render();openPlayer('#P0Q');`);
  const warUsage=[...contributions().querySelectorAll('.usage-diagram')].find(c=>c.textContent.includes('War attack use'));
  assert.match(warUsage.textContent,/No complete attack counts/);
  w.eval(`data.roster[0].donations=undefined;data.roster[0].donationsReceived=undefined;render();setTab('donations');openPlayer('#P0Q');`);
  assert.equal(stat(contributions(),'Donated this season'),'—');
  assert.equal(stat(contributions(),'Received this season'),'—');
  assert.match($('donations').querySelector('.card strong').textContent,/≥/);
  assert.deepEqual(errors,[]);
  console.log('Donation display passed: every roster profile matches clan season counters, 1,026/317 scopes, missing counters, roster trophies and excused war usage.');
} finally {dom.window.close();}
