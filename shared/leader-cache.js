// Private drafts are encrypted with a purpose-specific key, available only after unlock.
const LeaderCache=(()=>{
 const memory=new Map(),versions=new Map(),pending=new Set();let key=null,ready=Promise.resolve(),warning='',locked=false;
 const enc=new TextEncoder(),dec=new TextDecoder();
 const b64=v=>btoa(String.fromCharCode(...v)),raw=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
 const prefix='war-haven-private:v1:';
 async function init(data){ready=(async()=>{
  if(!data.sharedActions?.encryptionKey){warning='Private browser storage is unavailable. Export unfinished work before closing.';return;}
  const material=await crypto.subtle.importKey('raw',raw(data.sharedActions.encryptionKey),'HKDF',false,['deriveKey']);key=await crypto.subtle.deriveKey({name:'HKDF',hash:'SHA-256',salt:enc.encode(data.clanTag),info:enc.encode('WarHavenPrivateDrafts:v1')},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
  for(const name of ['clash-war-tracker-edits:'+data.clanTag,'war-haven-pending-shared:'+data.clanTag,'war-haven-recruit-visits:'+data.clanTag]){
   const legacy=localStorage.getItem(name),stored=localStorage.getItem(prefix+name);
   if(stored){try{const e=JSON.parse(stored),clear=await crypto.subtle.decrypt({name:'AES-GCM',iv:raw(e.iv),additionalData:enc.encode(name)},key,raw(e.cipher));memory.set(name,JSON.parse(dec.decode(clear)));}catch{warning='A private draft could not be decrypted. Keep the saved backup before changing shared access.';}}
   if(legacy){const value=JSON.parse(legacy);if(!memory.has(name))memory.set(name,value);await save(name,memory.get(name));localStorage.removeItem(name);}
  }
 })().catch(()=>{warning='Private storage could not be opened. Export unfinished work before closing.';});return ready;}
 async function save(name,value){if(!key)return;const n=(versions.get(name)||0)+1;versions.set(name,n);const iv=crypto.getRandomValues(new Uint8Array(12)),cipher=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:enc.encode(name)},key,enc.encode(JSON.stringify(value)));if(versions.get(name)===n)localStorage.setItem(prefix+name,JSON.stringify({v:1,iv:b64(iv),cipher:b64(new Uint8Array(cipher))}));}
 function set(name,value){if(locked)return;memory.set(name,JSON.parse(JSON.stringify(value)));const task=ready.then(()=>save(name,value)).catch(()=>warning='Private drafts could not be saved. Keep this page open or export a backup.');pending.add(task);task.finally(()=>pending.delete(task));}
 async function lock(){locked=true;await ready;await Promise.allSettled([...pending]);memory.clear();key=null;}
 function clearLegacy(){for(let i=localStorage.length-1;i>=0;i--){const name=localStorage.key(i);if(name?.startsWith('clash-war-tracker-edits:')||name?.startsWith('war-haven-pending-shared:'))localStorage.removeItem(name);}}
 return {init,ready:()=>ready,get:name=>memory.get(name),set,warning:()=>warning,clearLegacy,lock};
})();
