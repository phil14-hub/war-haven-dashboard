import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM, VirtualConsole} from 'jsdom';

const errors=[],vc=new VirtualConsole();
vc.on('jsdomError',error=>errors.push(error.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'), {
  url:'https://portal.warhavenclan.com/members/leadership',
  runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc
});
const w=dom.window,$=id=>w.document.getElementById(id);
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;
w.matchMedia=()=>({matches:false,addEventListener(){}});
w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
w.HTMLDialogElement.prototype.showModal=function(){this.open=true};
w.HTMLDialogElement.prototype.close=function(){this.open=false};
w.fetch=async()=>new Response(JSON.stringify({version:1,preferences:{},notifications:[],records:[]}));
try {
  for(const script of w.document.querySelectorAll('script:not([type])'))
    if(script.textContent.trim()) runInContext(script.textContent,dom.getInternalVMContext());
  await new Promise(resolve=>setTimeout(resolve,40));
  w.eval(`
    data.memberHistory['#P0Q']={
      since:'2026-10-12T00:00:00Z',inClan:true,lastSeen:'2026-10-17T10:00:00Z',
      capitalSamples:[
        {at:'2026-10-13T00:00:00Z',total:100},
        {at:'2026-10-16T00:00:00Z',total:300}
      ],
      pastStints:[{
        since:'2026-10-01T00:00:00Z',leftAt:'2026-10-08T00:00:00Z',
        capitalSamples:[
          {at:'2026-10-02T00:00:00Z',total:500},
          {at:'2026-10-07T00:00:00Z',total:1500}
        ]
      }]
    };
    data.memberHistory['#ZX9']={
      name:'Former fixture',since:'2026-10-01T00:00:00Z',
      inClan:false,leftAt:'2026-10-16T10:00:00Z',
      lastSeen:'2026-10-16T10:00:00Z',
      capitalSamples:[
        {at:'2026-10-02T00:00:00Z',total:200},
        {at:'2026-10-15T00:00:00Z',total:9200}
      ]
    };
    data.wars[0].participants.push({
      tag:'#ZX9',name:'Former fixture',attacksUsed:2,townHallLevel:18,
      attacks:[{order:1,stars:3},{order:2,stars:3}]
    });
    data.raids=[{
      id:'saved-raid',startTime:'2026-10-15T07:00:00Z',
      endTime:'2026-10-16T20:00:00Z',state:'ended',
      capitalTotalLoot:20000,totalAttacks:8,raidsCompleted:3,
      members:[
        {tag:'#P0Q',name:'Omid fixture',capitalResourcesLooted:5000,attacks:3,attackLimit:5,bonusAttackLimit:1},
        {tag:'#ZX9',name:'Former fixture',capitalResourcesLooted:15000,attacks:5,attackLimit:5,bonusAttackLimit:1}
      ]
    }];
    render();setTab('capital');
  `);
  const capital=()=>$('capital'),total=()=>capital().querySelector('.capital-total').textContent;
  const ranked=()=>[...capital().querySelectorAll('.clan-contributor')].map(x=>x.dataset.extendedPlayer);
  assert.match(total(),/10,200/,'all recorded clan stints, including the former member, contribute');
  assert.equal(w.eval("rows.find(p=>p.tag==='#P0Q').contributions.allCapital"),1200);
  assert.equal(w.eval("rows.find(p=>p.tag==='#ZX9').contributions.allCapital"),9000);
  assert.ok(ranked().includes('#P0Q'),'active contributor appears');
  assert.ok(!ranked().includes('#ZX9'),'former member does not rank');
  assert.equal(capital().querySelectorAll('#raid-detail .raid-member').length,1);
  assert.equal(capital().querySelector('#raid-detail .raid-member').dataset.extendedPlayer,'#P0Q');
  assert.match($('raid-detail').textContent,/20,000/,'historical raid total includes all participants');
  w.eval("setTab('performance')");
  const attackers=[...$('performance').querySelectorAll('.leaderboard-row')];
  assert.equal(attackers.length,1);
  assert.equal(attackers[0].dataset.extendedPlayer,'#P0Y');
  assert.match($('performance').querySelector('.compact-cards').textContent,/2.75/,'history aggregates retain former members attack stars');
  w.eval(`data.roster.push({tag:'#ZX9',name:'Former fixture',townHallLevel:18,role:'member',donations:0});render();setTab('capital');`);
  assert.ok(ranked().includes('#ZX9'),'player immediately ranks again after rejoining');
  assert.match(total(),/10,200/,'rejoining does not change historical clan total');
  w.eval(`data.roster=data.roster.filter(p=>p.tag!=='#ZX9');render();setTab('capital');`);
  assert.ok(!ranked().includes('#ZX9'),'departure immediately removes current-member rank');
  assert.match(total(),/10,200/,'departure never removes recorded lifetime donations');
  assert.deepEqual(errors,[]);
  console.log('Current-member leaderboards passed: departed players excluded, lifetime current/former stints retained, historical raid totals intact, performance aggregates intact, and membership changes reflected.');
} finally {dom.window.close()}
