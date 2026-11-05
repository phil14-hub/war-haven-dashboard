import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM,VirtualConsole} from 'jsdom';
import {runInContext} from 'node:vm';
const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(readFileSync(process.env.WAR_HAVEN_DASHBOARD_FIXTURE,'utf8'),{url:'https://portal.warhavenclan.com/members/leadership',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc}),w=dom.window,$=id=>w.document.getElementById(id),calls=[];
w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};
w.fetch=async(input,options={})=>{const url=new URL(input,'https://portal.warhavenclan.com');calls.push(url.pathname+url.search);return new Response(JSON.stringify(url.pathname.endsWith('admin/operations')?{checkedAt:'2030-01-01',backup:{createdAt:'2030-01-01'},updates:{},health:[]}:url.pathname.endsWith('admin/recovery-backup')?{backup:{createdAt:'2030-01-01'},envelope:{format:'synthetic'}}:{version:1,preferences:{},notifications:[],records:[]}));};
try{
 for(const script of w.document.querySelectorAll('script:not([type])'))if(script.textContent.trim())runInContext(script.textContent,dom.getInternalVMContext());await new Promise(r=>setTimeout(r,30));
 const before=calls.filter(p=>p.includes('notifications?scope=leadership')).length;await w.eval('openLeadershipNotifications()');assert.equal(calls.filter(p=>p.includes('notifications?scope=leadership')).length-before,1,'Opening the bell uses one read');
 let read=false;Object.defineProperty($('file'),'files',{value:[{size:21*1024*1024,text:async()=>{read=true;return '{}';}}]});await $('file').onchange({target:$('file')});assert.equal(read,false,'Reject oversized files before reading/parsing');
 w.eval("setTab('operations')");await new Promise(r=>setTimeout(r,20));assert.match($('operations-content').textContent,/Website recovery backup/);await $('create-recovery-backup').onclick({currentTarget:$('create-recovery-backup')});assert.match($('recovery-backup-status').textContent,/saved/);
 const form=$('download-recovery-backup');form.elements.backupPassphrase.value='synthetic long passphrase';form.elements.backupPassphraseAgain.value='different long passphrase';const count=calls.length;await form.onsubmit({preventDefault(){},currentTarget:form});assert.equal(calls.length,count);assert.match($('recovery-backup-status').textContent,/do not match/);
 form.elements.backupPassphraseAgain.value='synthetic long passphrase';w.eval('download=()=>{}');await form.onsubmit({preventDefault(){},currentTarget:form});assert.match($('recovery-backup-status').textContent,/downloaded/);assert.equal(form.elements.backupPassphrase.value,'');assert.equal(form.querySelector('button').disabled,false);assert.deepEqual(errors,[]);
 console.log('Audit UI passed: one notification read, oversized import rejected before file read, recovery status/create/download, mismatch validation, secret clearing and re-enabled controls.');
}finally{dom.window.close();}
