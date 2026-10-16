import ast
import base64
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import Clash_War_Tracker as tracker
import github_collector
import shared_actions

class DashboardTests(unittest.TestCase):
 def test_browser_cipher_is_verified_by_the_cloud_collector(self):
  result=subprocess.run(['node','tests/shared_dashboard.test.cjs'],cwd=ROOT,text=True,capture_output=True,check=True)
  fixture=json.loads(result.stdout)
  clear=shared_actions.decrypt_record(fixture['envelope'],fixture['key'],tracker)
  self.assertEqual(clear['value']['text'],'Shared fixture')
  broken={**fixture['envelope'],'tag':base64.b64encode(bytes(32)).decode()}
  with self.assertRaises(shared_actions.SharedActionsError):shared_actions.decrypt_record(broken,fixture['key'],tracker)

 def test_shared_key_survives_archive_merge_and_encrypted_round_trip(self):
  state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
  with patch.object(shared_actions,'ENABLED',True):shared_actions.prepare(state)
  state['lastSuccessfulSync']='2030-01-01T00:00:00Z'
  archive=tracker.encrypt_history(state,'fixture-passphrase-only')
  self.assertNotIn(state['sharedActions']['encryptionKey'],json.dumps(archive))
  restored=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
  tracker.apply_snapshot(restored,tracker.decrypt_history(archive,'fixture-passphrase-only'))
  self.assertEqual(restored['sharedActions'],state['sharedActions'])

 def test_daily_clan_update_does_not_call_recruiter(self):
  from test_war_end_updates import CollectorTests,fixture
  state=fixture();state['recruiter']={'preserved':'same scan'}
  helper=CollectorTests();fake,published,calls=helper.fake_tracker(state)
  with patch.dict(sys.modules,{'github_recruiter':SimpleNamespace(refresh=lambda *a:self.fail('Recruiter called'))}),contextlib.redirect_stdout(io.StringIO()):
   github_collector.run(helper.ENV,fake)
  self.assertEqual(calls,['refresh']);self.assertEqual(published[0]['recruiter'],state['recruiter'])

 def test_recruitment_update_does_not_collect_clan_data(self):
  from test_war_end_updates import CollectorTests,fixture
  helper=CollectorTests();fake,published,calls=helper.fake_tracker(fixture())
  def refresh(state,*a):state.update(recruiter={'version':'next'},recruiterStatus={'ok':True})
  with patch.dict(sys.modules,{'github_recruiter':SimpleNamespace(refresh=refresh)}):
   sys.modules.pop('github_recruitment_collector',None)
   import github_recruitment_collector as recruitment
   with contextlib.redirect_stdout(io.StringIO()):recruitment.run(helper.ENV,fake)
  self.assertEqual(calls,[]);self.assertEqual(published[0]['recruiter'],{'version':'next'})

 def test_generated_javascript_is_valid_and_native_recruitment_has_no_frame(self):
  from html.parser import HTMLParser
  class Scripts(HTMLParser):
   def __init__(self):super().__init__();self.scripts=[];self.current=None
   def handle_starttag(self,tag,attrs):
    if tag=='script':self.current=[] if dict(attrs).get('type')!='application/json' else None
   def handle_data(self,data):
    if self.current is not None:self.current.append(data)
   def handle_endtag(self,tag):
    if tag=='script' and self.current is not None:self.scripts.append(''.join(self.current));self.current=None
  with tempfile.TemporaryDirectory() as folder:
   output=Path(folder)/'index.html';tracker.write_dashboard(tracker.new_state(tracker.DEFAULT_CLAN_TAG),output)
   html=output.read_text();self.assertNotIn('<iframe',html);self.assertNotIn('__RECRUITMENT',html);self.assertNotIn('__SHARED_DASHBOARD',html)
   self.assertIn('How to Use',html);self.assertIn('prefers-reduced-motion',html)
   parser=Scripts();parser.feed(html)
   for index,script in enumerate(parser.scripts):
    path=Path(folder)/f'script-{index}.js';path.write_text(script)
    result=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
    self.assertEqual(result.returncode,0,result.stderr)

 def test_native_cards_escape_names_and_build_only_valid_clash_links(self):
  source=(ROOT/'recruitment_dashboard.js').read_text()
  esc_source=next(line for line in tracker.HTML_TEMPLATE.splitlines() if line.startswith('const $=')).split(',esc=',1)[1]
  program="const window={},data={},esc="+esc_source+"const date=s=>s||'Unknown',WarTracker={tag:s=>String(s||'').toUpperCase()},townHallIcon=n=>'<i>'+n+'</i>',formatNumber=n=>n??'—',icon=()=>'';"+source+";const card=RecruitmentDashboard.candidate({name:'<img src=x>',tag:'javascript:alert(1)',townHallLevel:11},'new');if(card.includes('<img src=x>')||card.includes('href='))throw Error('Unsafe candidate');if(!card.includes('&lt;img'))throw Error('Escaping missing');"
  result=subprocess.run(['node','-e',program],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
