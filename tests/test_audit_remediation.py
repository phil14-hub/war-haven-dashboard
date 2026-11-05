import base64
import contextlib
import copy
import io
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import Clash_War_Tracker as portable
import tracker_core as core
import github_sync_portal
import raid_history_recovery
import shared_actions

class AuditRemediation(unittest.TestCase):
 def fixture(self):
  s=core.new_state(core.DEFAULT_CLAN_TAG);s['raids']=[{'id':'raid:'+s['clanTag']+':2026-10-23T07:00:00.000Z','state':'ended','startTime':'2026-10-23T07:00:00.000Z','endTime':'2026-10-26T07:00:00.000Z','members':[{'tag':'#P0Y','attacks':6,'capitalResourcesLooted':1234}]}];return s
 def test_portable_and_cloud_storage_preserve_members_without_wrapper(self):
  for t in (core,portable):
   s=self.fixture();t.store_raids(s,{'items':[{'state':'ended','startTime':'20261023T070000.000Z','endTime':'20261026T070000.000Z'}]});self.assertEqual(s['raids'][0]['members'][0]['capitalResourcesLooted'],1234)
   t.store_raids(s,{'items':[{'state':'ended','startTime':'20261023T070000.000Z','endTime':'20261026T070000.000Z','members':[{'tag':'#P0Y','capitalResourcesLooted':2000}]}]});self.assertEqual(s['raids'][0]['members'][0]['capitalResourcesLooted'],2000)
 def test_recovery_markers_survive_encrypted_restore(self):
  s=self.fixture();s['raidMemberRecovery']={'missing':{'version':1,'result':'no-archive','at':'2030-01-01T00:00:00Z','retryAfter':'2030-01-08T00:00:00Z'}}
  with contextlib.redirect_stdout(io.StringIO()):
   restored=core.decrypt_history(core.encrypt_history(s,'fixture long passphrase'),'fixture long passphrase');target=core.new_state(s['clanTag']);core.apply_snapshot(target,restored)
  self.assertEqual(target['raidMemberRecovery'],s['raidMemberRecovery'])
 def test_transient_recovery_failures_remain_retryable(self):
  s=self.fixture();s['raids'][0]['members']=[];fake=SimpleNamespace(GITHUB_HISTORY_PATH=core.GITHUB_HISTORY_PATH,github_request=lambda *a:(_ for _ in ()).throw(OSError('temporary')))
  with contextlib.redirect_stdout(io.StringIO()):raid_history_recovery.recover(s,{'repository':'fixture'},fake)
  self.assertEqual(s['raidMemberRecovery'],{})
 def test_unchanged_verified_pair_skips_archive_content_and_decrypt(self):
  pair={'pageSha':'a'*40,'historySha':'b'*40,'commit':'c'*40,'pagesConfirmed':True,'publication':'saved-generation'};calls=[]
  def api(c,m,p):
   calls.append(p)
   if '/git/ref/' in p:return {'object':{'sha':'c'*40}}
   if '/contents/index.html' in p:return {'sha':'a'*40}
   raise AssertionError('Unnecessary workflow scan or blob read: '+p)
  def history(c,**kw):self.assertFalse(kw.get('include_content'));return {'sha':'b'*40}
  client=SimpleNamespace(request=lambda path,data=None: {'source':pair} if data=={'read':True} else {})
  fake=SimpleNamespace(github_request=api,github_history_record=history,decrypt_history=lambda *a:(_ for _ in ()).throw(AssertionError('Unnecessary decryption')))
  with patch.object(shared_actions,'Client',return_value=client),contextlib.redirect_stdout(io.StringIO()):r=github_sync_portal.run({'GITHUB_REPOSITORY':'phil14-hub/war-haven-dashboard','DASHBOARD_PASSWORD':'fixture','GITHUB_TOKEN':'fixture'},fake)
  self.assertTrue(r['reused']);self.assertEqual(len(calls),2)
 def test_independent_uploads_overlap_and_failure_never_updates_ref(self):
  s=self.fixture();config={'repository':'fixture/repo','password':'fixture password','_history_checked':True,'_history_sha':'old'};both=threading.Barrier(2);calls=[]
  def api(c,m,p,data=None):
   calls.append((m,p))
   if '/git/ref/' in p:return {'object':{'sha':'head'}}
   if '/git/commits/head' in p:return {'tree':{'sha':'tree'}}
   if p.endswith('/git/blobs'):
    both.wait(timeout=3)
    if 'protected-payload' in data['content']:raise core.PublishError(503,'Synthetic HTML upload failure')
    return {'sha':'new-history'}
   raise AssertionError('No tree/commit/ref may follow a failed upload')
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'index.html';path.write_text('<script id="protected-payload">{}</script>')
   with patch.object(core,'github_request',side_effect=api),patch.object(core,'github_history_record',return_value={'sha':'old'}),patch.object(core,'encrypt_history',return_value={'fixture':True}),self.assertRaises(core.PublishError):core.publish_history_commit(config,path,s,'main')
  self.assertFalse(any(m=='PATCH' for m,p in calls))
 def test_distribution_assets_match_maintained_core(self):
  for name in ('HTML_TEMPLATE','SODIUM_JS','UPGRADE_CATALOG','TOWN_HALL_IMAGES','CLEANUP_JS'):self.assertEqual(getattr(core,name),getattr(portable,name))
