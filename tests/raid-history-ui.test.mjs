import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM, VirtualConsole} from 'jsdom';

const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{
  url:'https://portal.warhavenclan.com/members/leadership',
  runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc
}),w=dom.window,$=id=>w.document.getElementById(id);
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;
w.matchMedia=()=>({matches:false,addEventListener(){}});
w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true};
w.HTMLDialogElement.prototype.close=function(){this.open=false};
w.fetch=async()=>new Response(JSON.stringify({version:1,preferences:{},notifications:[],records:[]}));

try {
  for(const script of w.document.querySelectorAll('script:not([type])'))
    if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());
  await new Promise(resolve=>setTimeout(resolve,40));
  const dates=Array.from({length:12},(_,i)=>'2030-01-'+String(i+1).padStart(2,'0'));
  const raids=dates.map((day,i)=>({id:'historic-'+i,startTime:day+'T07:00:00Z',
    endTime:day+'T20:00:00Z',state:'ended',capitalTotalLoot:1000+i,
    members:[],totalAttacks:0,raidsCompleted:0}));
  raids.push({id:'ongoing',startTime:'2030-01-31T07:00:00Z',
    endTime:'2030-02-02T20:00:00Z',state:'ongoing',
    capitalTotalLoot:9999,members:[]});
  w.eval('data.raids='+JSON.stringify(raids)+'; renderCapital()');
  const rows=()=>$('raid-history-chart').querySelectorAll('.chart-row');
  assert.equal($('raid-history-window').value,'all');
  assert.equal(rows().length,12,'all completed weekends shown initially, including older reports');
  assert.equal($('raid-history-chart').textContent.includes('9,999'),false,
    'unfinished raid must not appear in completed history');
  assert.match($('raid-history-chart').textContent,/12 of 12 completed saved weekends/);
  $('raid-history-window').value='8';
  $('raid-history-window').dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(rows().length,8);
  assert.match($('raid-history-chart').textContent,/8 of 12 completed saved weekends/);
  $('raid-history-window').value='26';
  $('raid-history-window').dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(rows().length,12,'range larger than the data still shows all captured history');
  $('raid-history-window').value='all';
  $('raid-history-window').dispatchEvent(new w.Event('change',{bubbles:true}));
  w.eval('renderCapital()');
  assert.equal($('raid-history-window').value,'all');
  assert.equal(rows().length,12,'selection survives rerender');
  assert.equal($('raid-history-window').getAttribute('aria-label'),'Raid loot history period');
  const styles=readFileSync('shared/dashboard-ui.css','utf8');
  assert.match(styles,/capital-history-panel \.chart-row/);
  assert.match(styles,/@media\(max-width:600px\)/);
  assert.deepEqual(errors,[]);
  console.log('Raid history UI passed: all captured completed weekends, 8/26/all filtering, unfinished excluded, preserved selection, and mobile rules.');
} finally {dom.window.close()}
