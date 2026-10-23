import ast
import json
from pathlib import Path
import re
import subprocess
import unittest

import Clash_War_Tracker as tracker

ROOT=Path(__file__).resolve().parents[1]

class LiveDashboardTests(unittest.TestCase):
 def test_live_snapshot_preserves_view_and_pending_edits(self):
  fixture={'trackerJS':tracker.TRACKER_JS,'state':tracker.new_state('#P0Y')}
  result=subprocess.run(['node','tests/live_dashboard.test.cjs'],cwd=ROOT,input=json.dumps(fixture),capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)

 def test_unlocked_session_decrypts_later_publications_and_rejects_tampering(self):
  password='synthetic-test-passphrase'
  original=tracker.protected_dashboard('<main>Original</main>',password,100000)
  later=tracker.protected_dashboard('<main>Later publication</main>',password,100000)
  changed=tracker.protected_dashboard('<main>Changed access</main>','different-test-passphrase',100000)
  payload=lambda html:json.loads(re.search(r'id="protected-payload">(.*?)</script>',html).group(1))
  script=original.rsplit('<script>',1)[1].split('</script>',1)[0]
  fixture={'script':script,'original':payload(original),'later':payload(later),'changed':payload(changed),'password':password}
  program=r'''
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),{webcrypto}=require('node:crypto');
const f=JSON.parse(fs.readFileSync(0,'utf8')),nodes={'protected-payload':{textContent:JSON.stringify(f.original)},'unlock-form':{},'dashboard-password':{value:f.password,focus(){}},'unlock-button':{},'unlock-error':{textContent:''}};
let documentWrites=0;const context={crypto:webcrypto,Blob,Response,DecompressionStream,URL,location:{href:'https://example.invalid/'},TextEncoder,TextDecoder,Uint8Array,atob,btoa,window:{},document:{getElementById:id=>nodes[id],open(){},write(html){assert.equal(html,'<main>Original</main>');documentWrites++;},close(){}}};
vm.runInNewContext(f.script,context);
(async()=>{
 await nodes['unlock-form'].onsubmit({preventDefault(){}});assert.equal(nodes['unlock-error'].textContent,'');assert.equal(nodes['dashboard-password'].value,'');assert.equal(documentWrites,1);
 const session=context.window.warHavenSession;assert.ok(session);assert.equal(await session.decrypt(f.later),'<main>Later publication</main>');
 assert.equal(documentWrites,1);assert.equal(JSON.stringify(session),'{}');
 await assert.rejects(session.decrypt({...f.later,tag:Buffer.alloc(32).toString('base64')}),/verified/);
 await assert.rejects(session.decrypt(f.changed),/passphrase changed/);
 await assert.rejects(session.decrypt({...f.later,rounds:1}),/Unsupported/);
 assert.equal((await session.proof(f.later.salt,f.later.rounds)).length,44);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
  result=subprocess.run(['node','-e',program],input=json.dumps(fixture),capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)

 def test_portable_tracker_contains_current_client_sources(self):
  for name,filename in [('SHARED_DASHBOARD_JS','shared_dashboard.js'),('LIVE_DASHBOARD_JS','live_dashboard.js')]:
   self.assertEqual(getattr(tracker,name),(ROOT/filename).read_text(),filename)
  self.assertEqual(tracker.RECRUITMENT_JS,(ROOT/'recruitment_contacts.js').read_text()+'\n'+(ROOT/'recruitment_dashboard.js').read_text())
  self.assertNotIn('Load update',tracker.HTML_TEMPLATE)
  self.assertNotIn('Load latest dashboard',tracker.HTML_TEMPLATE)
  self.assertIn('refresh-turn',tracker.HTML_TEMPLATE)
  self.assertIn('You can close this tab and it will keep running',tracker.SHARED_DASHBOARD_JS)

if __name__=='__main__':unittest.main()
