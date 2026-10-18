const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const fixture=JSON.parse(fs.readFileSync(0,'utf8')),nodes={};
function node(id,overrides={}){
 return nodes[id]||=(Object.assign({id,dataset:{},type:'text',tagName:'INPUT',value:'',checked:false,hidden:false,open:false,scrollTop:0,scrollLeft:0,focus(){context.document.activeElement=this;},setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end;}},overrides));
}
node('search').value='saved search';node('manual-opponent').value='Unsaved opponent';
node('raid-select',{tagName:'SELECT',options:[{value:'recent'},{value:'older'}],value:'older',onchange(){raidChanges++;}});
node('player-dialog',{tagName:'DIALOG',open:true,scrollTop:95});node('player-notes',{tagName:'TEXTAREA',value:'Pending note',selectionStart:4,selectionEnd:7});
node('publication-update');node('publication-message');node('recruit-search').value='archer';
let renders=0,invalidations=0,raidChanges=0,fetches=[],etag='v1',publicationTag='initial',failFetch=false,failRender=false;
const snapshot=(at,name)=>({...fixture.state,lastSuccessfulSync:at,roster:[{tag:'#P0Y',name}],sharedActions:{enabled:true,encryptionKey:'same-key'},edits:{notes:{'#P0Y':{text:'Published note',updatedAt:at}}}});
const old=snapshot('2030-01-01T00:00:00Z','Old name'),fresh=snapshot('2030-01-01T01:00:00Z','Fresh name');
old.warnings=['Previous warning'];old.leagueWarSummaries={round:{stars:1}};fresh.warnings=[];fresh.leagueWarSummaries={round:{stars:3}};
let publicationSnapshot=fresh,publicationReport={updatedAt:'2030-01-01T01:00:00Z',groups:{new:[{name:'New candidate'}]}};
const context={console,URL,Date,AbortSignal,JSON,Uint8Array,Map,Set,location:{pathname:'/dashboard/',protocol:'https:',href:'https://example.invalid/dashboard/?v=1.20#roster',reload(){throw Error('Must stay unlocked');}},data:old,edits:{notes:{'#P0Y':{text:'Pending note',updatedAt:'2029-01-01T00:00:00Z'}}},rows:[{tag:'#P0Y'}],selectedTag:'#P0Y',recruiterReport:{updatedAt:old.lastSuccessfulSync},$:id=>nodes[id],
 ClanProgress:{merge:(a,b)=>[...a,...b]},Leadership:{mergeHistory:(a,b)=>[...a,...b]},
 document:{hidden:false,body:{dataset:{page:'roster'}},activeElement:nodes['player-notes'],querySelectorAll(selector){return selector==='dialog[open]'?[nodes['player-dialog']]:Object.values(nodes).filter(el=>['INPUT','SELECT','TEXTAREA'].includes(el.tagName));}},
 window:{scrollX:4,scrollY:420,scrollTo({left,top}){this.scrollX=left;this.scrollY=top;},warHavenEnvelope:{tag:'initial'},warHavenSession:{async decrypt(payload){if(payload.tag==='tampered')throw Error('Authentication failed');return '<script id="war-data" type="application/json">'+JSON.stringify(publicationSnapshot)+'</script><script id="recruiter-data" type="application/json">'+JSON.stringify(publicationReport)+'</script><script>globalThis.untrustedScriptExecuted=true</script>';}}},
 requestAnimationFrame:fn=>fn(),persist(){},toast(){},
 RecruitmentDashboard:{invalidate(){invalidations++;}},
 SharedDashboardSync:{mergeSnapshotEdits(incoming){const merged=context.WarTracker.mergeEdits(incoming,context.edits);merged.notes['#P0Y']={text:'Pending note',updatedAt:'2029-01-01T00:00:00Z'};return merged;}},
 render(){renders++;if(failRender){failRender=false;throw Error('Render failed');}context.rows=context.data.roster.map(p=>({...p,notes:context.edits.notes[p.tag]?.text}));nodes['raid-select'].value='recent';context.window.scrollY=0;nodes['player-dialog'].scrollTop=0;},
 openPlayer(tag){assert.equal(tag,'#P0Y');nodes['player-notes'].value=context.edits.notes[tag].text;nodes['player-dialog'].open=true;},
 openRecruiter(){context.renderedRecruit=context.recruiterReport.groups.new[0].name;nodes['recruit-search'].value='';},
 DOMParser:class {parseFromString(html){return {getElementById(id){const content=html.match(new RegExp('<script[^>]*id="'+id+'"[^>]*>([\\s\\S]*?)</script>'));return content?{textContent:content[1]}:null;}};}},
 async fetch(url,options){assert.equal(options.credentials,'same-origin');fetches.push(options.method||'GET');if(failFetch)throw Error('Offline');return {ok:true,headers:{get:name=>name==='etag'?etag:null},text:async()=>'<script id="protected-payload" type="application/json">'+JSON.stringify({tag:publicationTag})+'</script>'};}
};
vm.createContext(context);vm.runInContext(fixture.trackerJS,context);
const app=vm.runInContext(fs.readFileSync('live_dashboard.js','utf8')+';DashboardLiveUpdates',context);
(async()=>{
 app.applySnapshot(fresh,publicationReport);
 assert.equal(context.data.roster[0].name,'Fresh name');assert.equal(context.data.lastSuccessfulSync,fresh.lastSuccessfulSync);
 assert.equal(context.data.warnings.length,0);assert.equal(context.data.leagueWarSummaries.round.stars,3);
 assert.equal(context.edits.notes['#P0Y'].text,'Pending note');assert.equal(nodes['player-notes'].value,'Pending note');
 assert.equal(context.document.body.dataset.page,'roster');assert.equal(nodes['player-dialog'].open,true);
 assert.equal(nodes.search.value,'saved search');assert.equal(nodes['manual-opponent'].value,'Unsaved opponent');assert.equal(nodes['raid-select'].value,'older');assert.equal(raidChanges,1);
 assert.equal(context.document.activeElement,nodes['player-notes']);assert.equal(nodes['player-notes'].selectionStart,4);assert.equal(nodes['player-notes'].selectionEnd,7);
 assert.equal(context.window.scrollY,420);assert.equal(nodes['player-dialog'].scrollTop,95);
 context.document.body.dataset.page='recruiter';const report2={updatedAt:'2030-01-01T02:00:00Z',groups:{new:[{name:'Independent recruit'}]}};
 app.applySnapshot({...fresh,recruiterSummary:{scannedClans:42}},report2);
 assert.equal(context.renderedRecruit,'Independent recruit');assert.equal(context.data.recruiterSummary.scannedClans,42);assert.equal(nodes['recruit-search'].value,'archer');assert.equal(context.data.lastSuccessfulSync,fresh.lastSuccessfulSync);
 assert.throws(()=>app.applySnapshot({...fresh,clanTag:'#WRONG'},report2),/verified/);assert.throws(()=>app.applySnapshot({...fresh,sharedActions:{encryptionKey:'changed'}},report2),/access settings/);
 const before=context.data;failRender=true;assert.throws(()=>app.applySnapshot(snapshot('2030-01-01T03:00:00Z','Bad render'),report2),/Render failed/);assert.equal(context.data,before);assert.equal(context.window.scrollY,420);
 assert.equal(await app.check(),false);assert.deepEqual(fetches,['GET']);
 fetches=[];assert.equal(await app.check(),false);assert.deepEqual(fetches,['HEAD']);
 publicationTag='next';etag='v2';publicationSnapshot=snapshot('2030-01-01T04:00:00Z','Automatic name');
 fetches=[];assert.equal(await app.check(),true);assert.deepEqual(fetches,['HEAD','GET']);assert.equal(context.data.roster[0].name,'Automatic name');assert.equal(context.untrustedScriptExecuted,undefined);
 fetches=[];assert.equal(await app.check({force:true}),false);assert.deepEqual(fetches,['GET']);
 const retained=context.data;publicationTag='tampered';etag='v3';assert.equal(await app.check({force:true}),false);assert.equal(context.data,retained);assert.equal(nodes['publication-update'].hidden,false);
 publicationTag='next';etag='v2';assert.equal(await app.check(),false);assert.equal(nodes['publication-update'].hidden,true);
 failFetch=true;assert.equal(await app.check({force:true}),false);assert.equal(context.data,retained);failFetch=false;
 context.document.hidden=true;fetches=[];assert.equal(await app.check({force:true}),false);assert.deepEqual(fetches,[]);
 assert.ok(invalidations>=3);console.log('Authenticated data-only updates, independent recruitment, retained drafts, page, player report, controls, focus, scroll, retries and rollback passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});

