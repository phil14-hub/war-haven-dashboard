/* War Haven upgrade model. Catalog source and revision are included with the data. */
(function(root,factory){const api=factory();root.WarHavenUpgrades=api;})(globalThis,()=>{
'use strict';
const compact=points=>{const out=[];for(const p of points||[]){if(!out.length||JSON.stringify([p.value,p.townHall])!==JSON.stringify([out.at(-1).value,out.at(-1).townHall]))out.push(p);}return out;};
const int=v=>Number.isInteger(v)&&v>=0;
function create(catalog){
 const units=new Map(catalog.units.map(u=>[u.id,u])),structures=new Map([...catalog.buildings,...catalog.traps].map(u=>[u.id,u]));
 function parseVillage(input,expectedTag,now=Date.now()){
  const raw=typeof input==='string'?JSON.parse(input):input;
  const normalize=v=>'#'+String(v||'').trim().toUpperCase().replace(/^#/,'');
  if(!raw||Array.isArray(raw)||normalize(raw.tag)!==normalize(expectedTag))throw Error('The export tag must match the selected approved village.');
  if(!Number.isInteger(raw.timestamp)||raw.timestamp<1577836800||raw.timestamp*1000>now+300000)throw Error('The export timestamp is missing or invalid.');
  if(!Array.isArray(raw.buildings)||!raw.buildings.length||raw.buildings.length>2000)throw Error('Paste a complete in-game village export, including buildings.');
  const townHall=raw.buildings.find(b=>b.data===1000001)?.lvl;
  if(!int(townHall)||townHall<1||townHall>catalog.maxTownHall)throw Error('This Town Hall is outside the supported upgrade catalog.');
  const rows=[],active=[],issues=[],unsupported=new Set(),actual=new Map(),virtual=new Map();
  const addVirtual=(id,level,count)=>{virtual.set(id,(virtual.get(id)||0)+count);const unit=structures.get(id);if(unit)rows.push({id,name:unit.name,category:unit.type==='Trap'?'Traps':unit.id===1000010?'Walls':unit.type==='Defense'?'Defenses':'Buildings',level,maximum:unit.caps[townHall-1],count,consumed:true});};
  for(const field of ['buildings','traps','units','siege_machines','heroes','spells','pets','equipment']){
   const values=raw[field];if(values===undefined){if(['traps'].includes(field))issues.push('Trap data was not included in this export.');continue;}
   if(!Array.isArray(values)||values.length>3000)throw Error('Invalid '+field+' collection.');
   for(const [index,item] of values.entries()){
    const location=field+'['+index+']';
    if(!item||!int(item.data))throw Error(location+' has an invalid game data ID. Copy a fresh complete village export.');
    const u=structures.get(item.data)||units.get(item.data);
    // Containers, temporary game entries and future IDs are not necessarily
    // levelled upgrades. Do not reject an otherwise usable export for them.
    if(!u){unsupported.add(item.data);continue;}
    if(item.data===1000097&&Array.isArray(item.types)){issues.push('Crafting Station contains nested defenses; their progress is not included in the catalog totals.');continue;}
    if(item.cnt!==undefined&&(!int(item.cnt)||item.cnt>1000))throw Error(location+' ('+u.name+') has an invalid count. Copy a fresh complete village export.');
    const count=item.cnt??1;
    if(count===0)continue; // Explicitly empty inventory entries are not owned.
    const level=item.lvl==null?null:item.lvl;
    if(level!==null&&(!int(level)||level>200))throw Error(location+' ('+u.name+') has an invalid level. Copy a fresh complete village export.');
    if(level===null)issues.push(u.name+' in '+location+' has no level; its progress is unknown.');
    const maximum=u.caps[townHall-1];
    if(level!==null&&level>maximum){issues.push(u.name+' level exceeds the catalog cap; its progress is unknown.');}
    const isStructure=structures.has(item.data),category=isStructure?(u.type==='Trap'?'Traps':u.id===1000010?'Walls':u.type==='Defense'?'Defenses':'Buildings'):({troops:'Laboratory',spells:'Laboratory',siege:'Laboratory',heroes:'Heroes',pets:'Pets',equipment:'Equipment'})[u.group];
    const row={id:u.id,name:u.name,category,level,maximum:maximum||null,count,remaining:level!==null&&maximum>=level?maximum-level:null};
    rows.push(row);
    if(isStructure){actual.set(u.id,(actual.get(u.id)||0)+count);virtual.set(u.id,(virtual.get(u.id)||0)+count);}
    if(item.timer!==undefined){
     if(!int(item.timer)||item.timer>366*86400||count!==1)throw Error('An upgrade timer must describe one active upgrade.');
     if(item.timer>0)active.push({name:u.name,category,level,target:level!==null&&level<maximum&&!item.supercharge&&!item.gear_up?level+1:null,endsAt:new Date((raw.timestamp+item.timer)*1000).toISOString(),supercharge:item.supercharge??null});
    }
    if(isStructure&&level>0)for(const req of u.levels?.[0]?.merge_requirement||[])addVirtual(req.id??req._id,req.level,count);
   }
  }
  for(const unlock of catalog.townHallUnlocks.filter(t=>t.townHall<=townHall))for(const req of unlock.mergeRequirements||[])addVirtual(req.id??req._id,req.level,1);
  for(const u of structures.values()){
   if(u.id===1000015||u.id===1000064||u.type==='Helper'||!u.caps[townHall-1])continue; // Optional builder huts are reported only when present.
   const missing=Math.max(0,(u.unlockedQuantity?.[townHall-1]||0)-(virtual.get(u.id)||0));
   if(missing&&!(u.type==='Trap'&&!Array.isArray(raw.traps)))rows.push({id:u.id,name:u.name,category:u.type==='Trap'?'Traps':u.id===1000010?'Walls':u.type==='Defense'?'Defenses':'Buildings',level:0,maximum:u.caps[townHall-1],count:missing,missing:true,remaining:u.caps[townHall-1]});
  }
  if(unsupported.size)issues.push('Unsupported export IDs: '+[...unsupported].join(', ')+'. Their progress is not estimated.');
  const categories={};
  for(const row of rows.filter(r=>!r.consumed)){
   const c=categories[row.category]??={count:0,maxed:0,remainingLevels:0,known:true};c.count+=row.count;
   if(row.maximum==null||row.level===null||row.level>row.maximum)c.known=false;else{c.maxed+=row.level===row.maximum?row.count:0;c.remainingLevels+=(row.maximum-row.level)*row.count;}
  }
  return {tag:normalize(raw.tag),townHall,exportedAt:new Date(raw.timestamp*1000).toISOString(),importedAt:new Date(now).toISOString(),catalogVersion:catalog.catalogVersion,rows:rows.filter(r=>!r.consumed),categories,active,issues};
 }
 return {parseVillage};
}
return {compact,create};
});
