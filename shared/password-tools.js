'use strict';
const PasswordTools=(()=>{
  const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true}),limit=50*1024*1024;
  const bytes=value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0));
  function base64(value){let text='';for(let i=0;i<value.length;i+=32768)text+=String.fromCharCode(...value.subarray(i,i+32768));return btoa(text);}
  function combine(...parts){const out=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let at=0;for(const part of parts){out.set(part,at);at+=part.length;}return out;}
  function validate(envelope,context){
    if(!envelope||envelope.version!==1||!Number.isInteger(envelope.rounds)||envelope.rounds<100000||envelope.rounds>2000000)throw Error('Unsupported encryption settings. No password was changed.');
    if(context==='WarHavenState:v1'&&(envelope.format!=='war-haven-state'||envelope.compression!=='gzip'))throw Error('Unsupported history archive. No password was changed.');
    const salt=bytes(envelope.salt),iv=bytes(envelope.iv),ciphertext=bytes(envelope.ciphertext),tag=bytes(envelope.tag);
    if(salt.length!==16||iv.length!==16||tag.length!==32||!ciphertext.length||ciphertext.length%16||ciphertext.length>limit)throw Error('Invalid encrypted file. No password was changed.');
    return {salt,iv,ciphertext,tag};
  }
  async function derive(password,salt,rounds){
    const material=await crypto.subtle.importKey('raw',encoder.encode(password),'PBKDF2',false,['deriveBits']);
    return new Uint8Array(await crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:rounds,hash:'SHA-256'},material,512));
  }
  async function decrypt(envelope,password,context){
    const {salt,iv,ciphertext,tag}=validate(envelope,context),derived=await derive(password,salt,envelope.rounds);
    try{
      const mac=await crypto.subtle.importKey('raw',derived.slice(32),{name:'HMAC',hash:'SHA-256'},false,['verify']);
      if(!await crypto.subtle.verify('HMAC',mac,tag,combine(encoder.encode(context),salt,iv,ciphertext)))throw Error('The current password is incorrect. No password was changed.');
      const key=await crypto.subtle.importKey('raw',derived.slice(0,32),'AES-CBC',false,['decrypt']);
      return new Uint8Array(await crypto.subtle.decrypt({name:'AES-CBC',iv},key,ciphertext));
    }finally{derived.fill(0);}
  }
  async function encrypt(clear,password,context,metadata={version:1}){
    const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(16)),rounds=600000,derived=await derive(password,salt,rounds);
    try{
      const key=await crypto.subtle.importKey('raw',derived.slice(0,32),'AES-CBC',false,['encrypt']);
      const ciphertext=new Uint8Array(await crypto.subtle.encrypt({name:'AES-CBC',iv},key,clear));
      const mac=await crypto.subtle.importKey('raw',derived.slice(32),{name:'HMAC',hash:'SHA-256'},false,['sign']);
      const tag=new Uint8Array(await crypto.subtle.sign('HMAC',mac,combine(encoder.encode(context),salt,iv,ciphertext)));
      return {...metadata,rounds,salt:base64(salt),iv:base64(iv),ciphertext:base64(ciphertext),tag:base64(tag)};
    }finally{derived.fill(0);}
  }
  function validateReplacement(current,replacement,confirmation){
    if(!current)throw Error('Enter your current dashboard password.');
    if(replacement.length<12)throw Error('Use at least 12 characters for the new password.');
    if(replacement!==confirmation)throw Error('The new passwords do not match.');
    if(replacement===current)throw Error('Choose a password different from the current one.');
  }
  async function sodiumReady(){
    if(!globalThis.sodium?.ready){const sodiumSource=document.getElementById('password-sodium'),script=document.createElement('script');script.nonce=window.warHavenScriptNonce||'';
      if(sodiumSource.dataset.src){await new Promise((resolve,reject)=>{script.src=sodiumSource.dataset.src;script.onload=resolve;script.onerror=()=>{script.remove();reject(Error('The password encryption library could not load. Check your connection and retry.'));};document.head.appendChild(script);});}
      else{script.textContent=sodiumSource.textContent;document.head.appendChild(script);}}
    if(!globalThis.sodium?.ready)throw Error('The password encryption library could not load. Reload and retry.');
    await globalThis.sodium.ready;return globalThis.sodium;
  }
  async function sealSecret(password,key){
    const sodium=await sodiumReady();
    return base64(sodium.crypto_box_seal(encoder.encode(password),bytes(key)));
  }
  function apiClient(token){
    return async function request(method,path,body){
      const url=path==='@owner-profile'?'https://api.github.com/user':'https://api.github.com/repos/phil14-hub/war-haven-dashboard'+path;
      const response=await fetch(url,{method,redirect:'error',credentials:'omit',cache:'no-store',headers:{Accept:'application/vnd.github+json',Authorization:'Bearer '+token,'X-GitHub-Api-Version':'2026-03-10','Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
      if(!response.ok){const error=Error(response.status===401?'The GitHub token was not accepted.':response.status===403?'This token needs repository Contents and Secrets read/write permissions.':response.status===409||response.status===422?'Another update changed the repository. Reload the dashboard and try again.':'GitHub could not complete the password change (HTTP '+response.status+').');error.status=response.status;throw error;}
      return response.status===204?{}:await response.json();
    };
  }
  async function blobText(api,sha){const blob=await api('GET','/git/blobs/'+sha);if(blob.encoding!=='base64')throw Error('GitHub did not return the encrypted file.');return decoder.decode(bytes(blob.content.replace(/\s/g,'')));}
  async function rotate({current,replacement,confirmation,token,loadedEnvelope,api=apiClient(token),seal=sealSecret,progress=()=>{}}){
    validateReplacement(current,replacement,confirmation);
    if(!token?.trim())throw Error('Enter your GitHub owner token to publish the password change.');
    if(!loadedEnvelope?.ciphertext&&globalThis.warHavenIndividual&&typeof globalThis.warHavenLoadEnvelope==='function')loadedEnvelope=await globalThis.warHavenLoadEnvelope();
    if(!loadedEnvelope?.ciphertext)throw Error('Open the password-protected shared website to change its password.');
    progress('Checking the current password…');
    // A wrong current password is rejected locally before any GitHub request.
    const verified=await decrypt(loadedEnvelope,current,'WarHavenDashboard:v1');verified.fill(0);
    progress('Loading the latest encrypted website and history…');
    const repo=await api('GET',''),branch=repo.default_branch;
    const identity=await api('GET','@owner-profile');
    if(repo.owner?.login!=='phil14-hub'||identity.login!=='phil14-hub'||repo.permissions?.admin!==true)throw Error('Only the GitHub repository owner can change the shared dashboard password.');
    if(!branch||!/^[\w./-]+$/.test(branch))throw Error('Could not determine the publication branch.');
    const branchPath=branch.split('/').map(encodeURIComponent).join('/'),refPath='/git/refs/heads/'+branchPath,readRef='/git/ref/heads/'+branchPath;
    const head=await api('GET',readRef),parent=head.object?.sha;
    if(!parent)throw Error('Could not read the current publication revision.');
    const commit=await api('GET','/git/commits/'+parent);
    const paths=['index.html','data/war_tracker_state.enc.json'];
    const records=[];for(const path of paths)records.push(await api('GET','/contents/'+path+'?ref='+parent));
    const encryptedPage=await blobText(api,records[0].sha),archive=JSON.parse(await blobText(api,records[1].sha));
    const match=encryptedPage.match(/(<script\b[^>]*\bid="protected-payload"[^>]*>)([\s\S]*?)(<\/script>)/i);
    if(!match)throw Error('The published page is not a supported protected dashboard.');
    const envelope=JSON.parse(match[2]);
    const clearPage=await decrypt(envelope,current,'WarHavenDashboard:v1');
    const clearHistory=await decrypt(archive,current,'WarHavenState:v1');
    // Authenticated clear bytes are re-encrypted without changing any clan record.
    const publicKey=await api('GET','/actions/secrets/public-key');
    if(!publicKey.key||!publicKey.key_id)throw Error('Could not obtain the GitHub Actions encryption key.');
    let secretExisted=true;
    try{await api('GET','/actions/secrets/DASHBOARD_PASSWORD');}catch(error){if(error.status===404)secretExisted=false;else throw error;}
    progress('Encrypting the website and complete history with the new password…');
    let nextPage,nextHistory;
    try{
      nextPage=await encrypt(clearPage,replacement,'WarHavenDashboard:v1');
      nextHistory=await encrypt(clearHistory,replacement,'WarHavenState:v1',{format:'war-haven-state',version:1,compression:'gzip'});
    }finally{clearPage.fill(0);clearHistory.fill(0);}
    const newPage=encryptedPage.replace(match[0],()=>match[1]+JSON.stringify(nextPage)+match[3]);
    const stateBlob=await api('POST','/git/blobs',{content:JSON.stringify(nextHistory),encoding:'utf-8'});
    const pageBlob=await api('POST','/git/blobs',{content:newPage,encoding:'utf-8'});
    const tree=await api('POST','/git/trees',{base_tree:commit.tree.sha,tree:[{path:paths[0],mode:'100644',type:'blob',sha:pageBlob.sha},{path:paths[1],mode:'100644',type:'blob',sha:stateBlob.sha}]});
    const written=await api('POST','/git/commits',{message:'Change dashboard password and re-encrypt saved clan history',tree:tree.sha,parents:[parent]});
    if(!written.sha||!stateBlob.sha||!pageBlob.sha)throw Error('GitHub did not confirm the encrypted update.');
    // Refuse stale publication before changing the automation credential.
    if((await api('GET',readRef)).object?.sha!==parent)throw Error('The dashboard was updated during this change. Reload and try again; the password is unchanged.');
    const newSecret={encrypted_value:await seal(replacement,publicKey.key),key_id:publicKey.key_id};
    const oldSecret=secretExisted?{encrypted_value:await seal(current,publicKey.key),key_id:publicKey.key_id}:null;
    progress('Updating the automatic collector password and publishing…');
    await api('PUT','/actions/secrets/DASHBOARD_PASSWORD',newSecret);
    let published=false;
    try{
      const updated=await api('PATCH',refPath,{sha:written.sha,force:false});
      if(updated.object?.sha!==written.sha)throw Error('Publication could not be confirmed.');
      published=true;
    }catch(error){
      // A lost response can still mean success. Read the archive revision before rollback.
      try{
        const currentRecord=await api('GET','/contents/'+paths[1]);
        published=currentRecord.sha===stateBlob.sha;
      }catch{
        throw Error('GitHub did not confirm publication. The new automatic collector password may already be saved. Check the latest website with your new password before retrying.');
      }
      if(!published){
        try{if(secretExisted)await api('PUT','/actions/secrets/DASHBOARD_PASSWORD',oldSecret);else await api('DELETE','/actions/secrets/DASHBOARD_PASSWORD');}
        catch{throw Error('Publication stopped before the password changed, but the collector secret could not be restored. Set DASHBOARD_PASSWORD back to your current password in GitHub Actions before collecting again.');}
        throw Error('Publication stopped because the repository changed. The collector password was restored. Reload and try again.');
      }
    }
    return {published,commit:written.sha,envelope:nextPage};
  }
  return {encrypt,decrypt,validateReplacement,rotate,sealSecret,base64,bytes};
})();
function openPasswordChange(){if((window.warHavenIndividual&&window.warHavenAccountRole!=='owner')||!document.getElementById('settings-password')||!document.getElementById('password-form')||!document.getElementById('password-dialog'))return;
  $('settings-dialog').close();$('password-form').reset();$('password-result').textContent='';$('password-progress').textContent='';$('password-load').hidden=true;
  $('password-dialog').showModal();
}
function wirePasswordChange(){if((window.warHavenIndividual&&window.warHavenAccountRole!=='owner')||!document.getElementById('settings-password')||!document.getElementById('password-form')||!document.getElementById('password-dialog'))return;
  $('settings-password').onclick=openPasswordChange;
  let changing=false;
  $('password-dialog').addEventListener('cancel',event=>{if(changing)event.preventDefault();});
  $('password-dialog').addEventListener('close',()=>$('password-form').reset());
  $('password-form').onsubmit=async event=>{
    event.preventDefault();if(changing)return;
    changing=true;const button=$('change-password-submit');button.disabled=true;$('close-password').disabled=true;
    const input={current:$('current-password').value,replacement:$('new-password').value,confirmation:$('confirm-password').value,token:$('password-github-token').value.trim(),loadedEnvelope:globalThis.warHavenEnvelope,progress:text=>$('password-progress').textContent=text};
    $('password-result').textContent='';
    try{
      const result=await PasswordTools.rotate(input);
      globalThis.warHavenEnvelope=result.envelope;
      $('password-form').reset();$('password-progress').textContent='Password updated in GitHub. The website is publishing.';
      $('password-result').className='notice';$('password-result').textContent='The shared website, complete history and automatic collector now use your new password. Wait for GitHub Pages to finish, then load the latest dashboard. Update any Pyto collector to the new password before using it again. SMS alerts are disabled.';
      $('password-load').hidden=false;
    }catch(error){$('password-result').className='error-text';$('password-result').textContent=error.message;$('password-progress').textContent='';}
    finally{input.current='';input.replacement='';input.confirmation='';input.token='';$('current-password').value='';$('new-password').value='';$('confirm-password').value='';$('password-github-token').value='';changing=false;button.disabled=false;$('close-password').disabled=false;}
  };
}
