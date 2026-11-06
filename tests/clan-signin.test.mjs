import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {JSDOM} from 'jsdom';
const result=spawnSync('python',['-c',"import Clash_War_Tracker as t; print(t.protected_dashboard('<html><body>Synthetic fixture</body></html>', 'synthetic test passphrase', rounds=100000))"],{encoding:'utf8'});
assert.equal(result.status,0,result.stderr);
const dom=new JSDOM(result.stdout,{url:'https://warhavenclan.com/',pretendToBeVisual:true,runScripts:'dangerously'}),document=dom.window.document;
try{
 const links=[...document.querySelectorAll('a')];assert.equal(links.length,1,'The main website has one account sign-in path');
 const link=links[0];assert.equal(link.textContent.trim(),'Sign in');assert.equal(link.href,'https://portal.warhavenclan.com/members/');assert.equal(new URL(link.href).search,'','The entrance does not preselect a dashboard or role');
 assert.doesNotMatch(document.body.textContent,/Leader \/ Co-Leader Sign In|Member Sign In/);
 assert.equal(document.querySelector('#legacy-access').hidden,true);assert.equal(document.querySelector('#legacy-access').open,false);assert.ok(document.querySelector('#legacy-access #unlock-form'));assert.ok(document.querySelector('#legacy-access .lock-foot'),'Passphrase instructions belong to the collapsed recovery entrance');
 assert.equal(dom.window.getComputedStyle(link).minHeight,'48px');link.focus();assert.equal(document.activeElement,link);
 const payload=JSON.parse(document.querySelector('#protected-payload').textContent);assert.equal(payload.version,1);assert.ok(payload.ciphertext,'Encrypted offline recovery is preserved');
 const recovery=new JSDOM(result.stdout,{url:'https://warhavenclan.com/?legacy=1',runScripts:'dangerously'});assert.equal(recovery.window.document.querySelector('#legacy-access').hidden,false);assert.equal(recovery.window.document.querySelector('#legacy-access').open,true);recovery.window.close();
 console.log('Clan entrance passed: one common account link, no role URL, 48px keyboard-accessible button, explicit recovery URL and intact encrypted payload.');
}finally{dom.window.close();}
