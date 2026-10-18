import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import Clash_War_Tracker as tracker
import Clash_Recruitment as recruiter
import member_exports
import github_collector
import shared_actions
from tests.test_upgrade_progress import profile

class AuditDataTests(unittest.TestCase):
 def test_stale_town_hall_profile_stays_unknown(self):
  state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
  state.update(lastSuccessfulSync='2026-10-17T10:00:00Z',clanProfile={'members':1},roster=[{'tag':'#P0Q','name':'Fixture','townHallLevel':18}],profiles={'#P0Q':profile(17)})
  p=member_exports.build_snapshot(state,tracker)['members']['#P0Q']
  self.assertIsNone(p['armyPercent']);self.assertFalse(p['profileStatus']['available']);self.assertEqual(p['heroes'],[])
  state['profiles']['#P0Q']=profile(18)
  self.assertEqual(member_exports.build_snapshot(state,tracker)['members']['#P0Q']['armyPercent'],100)

 def test_attack_validation_and_noop_war_edits(self):
  program=r'''
const vm=require('node:vm'),assert=require('node:assert/strict'),fs=require('node:fs'),c={};vm.runInNewContext(JSON.parse(fs.readFileSync(0)).source,c);const T=c.WarTracker;
const original={id:'w',kind:'Regular',endTime:'2026-10-16',final:true,rosterComplete:true,expEarned:150,startTime:'2026-10-15',opponent:{name:'Clan',tag:'#P0U'},participants:[{tag:'#P0Q',attacksUsed:2,starsEarned:3,attacks:[{order:1,stars:3,destructionPercentage:100},{order:1,stars:3,destructionPercentage:100},{order:2,stars:2.5,destructionPercentage:999}]}]};
const result=T.mergeManual(original,{id:'w',participants:[{tag:'#P0Q',attacksUsed:2}],opponent:{name:'Clan'}});assert.equal(result.expEarned,150);assert.equal(result.opponent.tag,'#P0U');assert.equal(result.participants[0].attacks.length,3);
const p=T.performanceFor({wars:[result]})['#P0Q'];assert.equal(p.knownAttacks,1);assert.equal(p.averageStars,3);assert.equal(p.averageDestruction,100);
const changed=T.mergeManual(original,{id:'w',participants:[{tag:'#P0Q',attacksUsed:1}]});assert.equal(changed.participants[0].attacks,undefined);assert.equal(changed.participants[0].starsEarned,undefined);
const data={clanTag:'#P0Y',policyStart:'2026-10-01',lastSuccessfulSync:'2026-10-17',roster:[{tag:'#P0Q',name:'Fixture'}],wars:[original]};const edits={exceptions:{'w::#P0Q':{value:true}}};assert.equal(T.playersFor(data,edits)[0].allowed,0);assert.equal(T.trendsFor(data,edits)[0].allowed,0);
'''
  result=subprocess.run(['node','-e',program],input=json.dumps({'source':tracker.TRACKER_JS}),text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)

 def test_new_departure_survives_profile_outage_without_false_verification(self):
  with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
   recruiter.configure_paths(folder)
   store={'players':{}}
   departure={'tag':'#P0Q','detectedAt':recruiter.iso_now(),'previousRosterAt':'2026-10-16T10:00:00Z','sourceClanTag':'#P0Y','sourceClanName':'Fixture','observationWindowSeconds':3600}
   api=SimpleNamespace(get_player=lambda tag:(_ for _ in ()).throw(RuntimeError('fixture outage')))
   recruiter.process_departures(api,[departure],store,{},7,'run',tracker.DEFAULT_CLAN_TAG,profile_workers=1)
   rec=store['players']['#P0Q'];self.assertEqual(rec['previousRosterAt'],departure['previousRosterAt']);self.assertNotIn('lastVerifiedAt',rec);self.assertIn('lastVerificationAttemptAt',rec)
   rec['lastVerifiedAt']='2026-10-01T00:00:00Z'
   recruiter.reverify_active_candidates(api,store,{},30,{},tracker.DEFAULT_CLAN_TAG,profile_workers=1)
   self.assertEqual(rec['lastVerifiedAt'],'2026-10-01T00:00:00Z')

 def test_corruption_and_partial_generation_preserve_saved_recruitment(self):
  with tempfile.TemporaryDirectory() as folder:
   recruiter.configure_paths(folder);recruiter.STATE_DIR.mkdir(parents=True,exist_ok=True)
   path=recruiter.STATE_DIR/'detected_leavers.json';path.write_text('{broken')
   with self.assertRaises(ValueError):recruiter.json_load(path,{})
   self.assertEqual(path.read_text(),'{broken')
   recruiter.save_generation([(path,{'players':{'fixture':{}}})])
   path.write_text('{partial mirror')
   self.assertEqual(recruiter.json_load(path,{})['players'],{'fixture':{}})
   manifest=json.loads((recruiter.STATE_DIR/'generation.json').read_text());(recruiter.STATE_DIR/manifest['directory']/path.name).unlink()
   with self.assertRaises(ValueError):recruiter.json_load(path,{})

 def test_csv_formula_fields_are_escaped(self):
  for value in ['=1+1','+cmd','-1+2','@SUM(A1)','\t=1+1',' \r@x']:
   self.assertTrue(recruiter.csv_safe(value).startswith("'"))
  self.assertEqual(recruiter.csv_safe('Normal name'),'Normal name');self.assertEqual(recruiter.csv_safe(12),12)

 def test_portal_failure_is_partial_and_independent_of_github_success(self):
  from tests.test_war_end_updates import CollectorTests,fixture
  helper=CollectorTests();fake,published,calls=helper.fake_tracker(fixture())
  request=SimpleNamespace(client=object(),lease=None,progress=lambda *args:None,finish=lambda result:None)
  with patch.object(shared_actions,'ENABLED',False),patch.object(member_exports,'publish',side_effect=RuntimeError('portal outage')),contextlib.redirect_stdout(io.StringIO()):
   result=github_collector.collect(helper.ENV,fake,{'password':'fixture password'},'official',fixture(),post_war=False,request=request)
  self.assertTrue(result['partial']);self.assertTrue(result['components']['github']);self.assertFalse(result['components']['portal']);self.assertTrue(published)

 def test_pages_status_failure_retains_the_successfully_committed_revision(self):
  from unittest.mock import MagicMock
  def api(config,method,path,*args):
   if path.endswith('/pages/builds/latest'):raise tracker.PublishError(403)
   if path.endswith('/pages'):return {'html_url':'https://warhavenclan.com/','source':{'branch':'main','path':'/'}}
   return {'default_branch':'main'}
  with patch.object(tracker,'github_request',side_effect=api),patch.object(tracker,'publish_history_commit',return_value='a'*40),contextlib.redirect_stdout(io.StringIO()):
   result=tracker.publish_dashboard({'repository':'fixture/repo'},MagicMock(),state={},wait_seconds=1)
  self.assertFalse(result['published']);self.assertEqual(result['commit'],'a'*40);self.assertIn('confirmation',result['publicationError'])

 def test_source_only_pages_build_can_confirm_the_identical_publication(self):
  import github_sync_portal
  def api(config,method,path):
   if '/actions/runs?' in path:return {'workflow_runs':[{'name':'pages build and deployment','head_sha':'later-source-commit'}]}
   return {'sha':'page-blob'}
  fake=SimpleNamespace(github_request=api,github_history_record=lambda *a,**kw:{'sha':'archive-blob'},PublishError=tracker.PublishError)
  self.assertTrue(github_sync_portal.pages_contains_publication({'repository':'fixture/repo'},fake,'page-blob','archive-blob'))
  self.assertFalse(github_sync_portal.pages_contains_publication({'repository':'fixture/repo'},fake,'other-page','archive-blob'))
