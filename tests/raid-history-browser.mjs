import assert from 'node:assert/strict';
import {readFileSync, mkdirSync} from 'node:fs';
import {createServer} from 'node:http';
import {chromium} from 'playwright';

const fixture=readFileSync('tests/fixtures/leadership.html','utf8');
const server=createServer((request,response)=>{
  if(request.url?.startsWith('/members/leadership')){
    response.writeHead(200,{'content-type':'text/html; charset=utf-8'});response.end(fixture);
  } else {response.writeHead(404);response.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:390,height:850}});
const dates=Array.from({length:15},(_,i)=>new Date(Date.UTC(2026,7,i+1)).toISOString());
const raids=dates.map((startTime,i)=>({
  id:'history-'+i,startTime,endTime:startTime,state:'ended',
  capitalTotalLoot:120000+i*21567,raidsCompleted:4,totalAttacks:54,members:[],
  offensiveReward:100,defensiveReward:50
}));
raids.push({id:'live-raid',startTime:'2026-09-05T00:00:00Z',
  endTime:'2026-09-06T00:00:00Z',state:'ongoing',capitalTotalLoot:999999,
  members:[]});
try {
  await page.addInitScript(()=>{
    window.warHavenIndividual=true;
    window.warHavenSession={proof:async()=>''};
    window.fetch=async()=>new Response(JSON.stringify({version:1,preferences:{},notifications:[],records:[]}),{
      status:200,headers:{'content-type':'application/json'}
    });
  });
  await page.route('**/*',route=>{
    if(route.request().url().startsWith(origin))return route.continue();
    return route.abort();
  });
  await page.goto(origin+'/members/leadership',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof window.renderCapital==='function',{timeout:15000});
  await page.evaluate(raids=>{
    window.eval('data.raids='+JSON.stringify(raids)+'; renderCapital(); setTab("capital")');
  },raids);
  mkdirSync('tests/screenshots',{recursive:true});
  for(const theme of ['dark','light']){
    await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
    for(const width of [320,360,375,390,430,768,1024,1440]){
      await page.setViewportSize({width,height:900});
      await page.locator('#raid-history-window').selectOption('all');
      const sizes=await page.evaluate(()=>{
        const filter=document.getElementById('raid-history-window');
        const panel=document.querySelector('.capital-history-panel');
        const chart=document.getElementById('raid-history-chart');
        const whole=document.documentElement;
        const rect=panel.getBoundingClientRect(),control=filter.getBoundingClientRect();
        return {
          viewport:whole.clientWidth,bodyScrollWidth:whole.scrollWidth,
          panelLeft:rect.left,panelRight:rect.right,
          chartRight:chart.getBoundingClientRect().right,
          controlRight:control.right,controlHeight:control.height,
          count:chart.querySelectorAll('.chart-row').length
        };
      });
      assert.equal(sizes.count,15,theme+' / '+width+' all historical weekends');
      assert.ok(sizes.bodyScrollWidth<=sizes.viewport+2,theme+' / '+width+' page overflow '+JSON.stringify(sizes));
      assert.ok(sizes.panelLeft>=-2&&sizes.panelRight<=sizes.viewport+2,theme+' / '+width+' panel clipped '+JSON.stringify(sizes));
      assert.ok(sizes.chartRight<=sizes.viewport+2,theme+' / '+width+' chart clipped '+JSON.stringify(sizes));
      assert.ok(sizes.controlRight<=sizes.viewport+2&&sizes.controlHeight>=44,theme+' / '+width+' touch target '+JSON.stringify(sizes));
      if([320,390,768,1440].includes(width))
        await page.screenshot({path:'tests/screenshots/capital-'+theme+'-'+width+'.png',animations:'disabled'});
    }
  }
  console.log('Browser responsive checks passed: 320, 360, 375, 390, 430, 768, 1024, 1440 pixels; dark/light; complete raid history.');
}finally{
  await browser.close();await new Promise(resolve=>server.close(resolve));
}
