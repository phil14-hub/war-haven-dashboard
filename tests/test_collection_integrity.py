"""Reject contradictory observations before replacing evidence or publications."""
import ast
import contextlib
import copy
import io
import base64
import hashlib
import hmac
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import Clash_War_Tracker as tracker
import github_collector
import member_exports
import shared_actions


class CollectionIntegrityTests(unittest.TestCase):
    def state(self):
        state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        state['roster']=[{'tag':'#P0Y','name':'One'},{'tag':'#P0Q','name':'Two'}]
        return state

    def test_invalid_roster_does_not_record_departures_or_success(self):
        for payload in [
            {'members':2,'memberList':[{'tag':'#P0Y'}]},
            {'members':2,'memberList':[{'tag':'#P0Y'},{'tag':'#P0Y'}]},
            {'members':1,'memberList':[{'tag':'invalid tag'}]},
            {'members':0,'memberList':[]},
        ]:
            with self.subTest(payload=payload):
                state=self.state();before=copy.deepcopy(state)
                api=SimpleNamespace(get=lambda path:{'tag':tracker.DEFAULT_CLAN_TAG,**payload})
                with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(ValueError):
                    tracker.refresh(state,api,profiles=False)
                self.assertEqual(state,before)

    def war(self):
        return {'state':'warEnded','endTime':'20200101T120000.000Z','teamSize':2,'attacksPerMember':2,
                'clan':{'tag':tracker.DEFAULT_CLAN_TAG,'attacks':2,'stars':6,'members':[{'tag':'#P0Y'},{'tag':'#P0Q'}]},
                'opponent':{'tag':'#P0R','name':'Synthetic opponent'}}

    def test_contradictory_totals_never_confirm_zero_attendance(self):
        war=tracker.normalize_war(self.war(),tracker.DEFAULT_CLAN_TAG)
        self.assertFalse(war['final']);self.assertFalse(war['rosterComplete'])
        self.assertTrue(war['captureIssues']);self.assertEqual(war['reportedAttacks'],2)
        # Evidence is retained for repair, but it is explicitly incomplete.
        self.assertEqual(len(war['participants']),2)

    def test_valid_zero_and_valid_attack_counts_still_finish(self):
        raw=self.war();raw['clan']['attacks']=0
        self.assertTrue(tracker.normalize_war(raw,tracker.DEFAULT_CLAN_TAG)['final'])
        raw=self.war()
        raw['clan']['members'][0]['attacks']=[{'order':1,'stars':3,'destructionPercentage':100},{'order':2,'stars':2,'destructionPercentage':80}]
        self.assertTrue(tracker.normalize_war(raw,tracker.DEFAULT_CLAN_TAG)['final'])
        raw['clan']['members'][0]['attacks'][1]['order']=1
        self.assertFalse(tracker.normalize_war(raw,tracker.DEFAULT_CLAN_TAG)['final'])

    def test_member_results_use_final_scores_and_destruction_ties(self):
        base={'state':'warEnded','stars':30,'opponentStars':29}
        self.assertEqual(member_exports.war_outcome(base),'Victory')
        self.assertEqual(member_exports.war_outcome({**base,'stars':28}),'Defeat')
        self.assertEqual(member_exports.war_outcome({**base,'opponentStars':30,'destruction':90,'opponentDestruction':90}),'Tie')
        self.assertEqual(member_exports.war_outcome({**base,'opponentStars':30,'destruction':89,'opponentDestruction':90}),'Defeat')
        self.assertIsNone(member_exports.war_outcome({**base,'state':'inWar'}))
        self.assertIsNone(member_exports.war_outcome({**base,'opponentStars':30}))

    def test_bad_projection_stops_before_any_github_or_portal_publication(self):
        calls=[]
        state=self.state()
        fake=SimpleNamespace(refresh=lambda candidate,api:None,OfficialAPI=lambda tokens:None,now_iso=tracker.now_iso,
                             write_dashboard=lambda *a,**k:calls.append('render'),publish_dashboard=lambda *a,**k:calls.append('github'))
        request=SimpleNamespace(client=None,progress=lambda *a:None,lease=None)
        with patch.object(shared_actions,'ENABLED',False),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(ValueError):
            github_collector.collect({'COC_API_TOKEN':'synthetic'},fake,{'password':'synthetic passphrase'},'official',state,post_war=False,request=request)
        self.assertEqual(calls,[])

    def test_embedded_asset_parity_is_enforced_for_all_generated_sources(self):
        from scripts.sync_embedded_assets import ASSETS,synchronize
        self.assertEqual(synchronize(check=True),0)
        self.assertGreaterEqual(len(ASSETS),9)

    def test_shared_import_reads_every_page_and_rejects_repeated_cursors(self):
        state=self.state();shared_actions.prepare(state);key=state['sharedActions']['encryptionKey']
        def record(tag,text):
            identity=hmac.new(base64.b64decode(key)[32:],('notes:'+tag).encode(),hashlib.sha256).hexdigest()
            return {'id':identity,'kind':'notes','updatedAt':'2030-01-01T00:00:00Z',
                    'envelope':{'category':'notes','key':tag,'value':{'text':text}}}
        pages=[{'records':[record('#P0Y','First page')],'nextCursor':'second'},
               {'records':[record('#P0Q','Second page')],'nextCursor':None}]
        calls=[]
        def request(path,data=None):
            calls.append(data);return pages[len(calls)-1]
        with patch.object(shared_actions,'decrypt_record',side_effect=lambda envelope,*a:envelope):
            shared_actions.pull(state,SimpleNamespace(request=request),tracker)
        self.assertEqual(calls,[None,{'cursor':'second'}])
        self.assertEqual(state['edits']['notes']['#P0Q']['text'],'Second page')
        before=copy.deepcopy(state);calls.clear();pages[1]['nextCursor']='second'
        with patch.object(shared_actions,'decrypt_record',side_effect=lambda envelope,*a:envelope),self.assertRaises(shared_actions.SharedActionsError):
            shared_actions.pull(state,SimpleNamespace(request=request),tracker)
        self.assertEqual(state,before)

    def test_fingerprint_hashes_the_resolved_shared_javascript(self):
        state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        import tempfile,re
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'index.html'
            tracker.write_dashboard(state,target)
            first=json.loads(re.search(r'id="war-data"[^>]*>(.*?)</script>',target.read_text(),re.S)[1])['sourceBuildVersion']
            assets=tracker.dashboard_assets();assets['common']+='\n/* synthetic change */'
            with patch.object(tracker,'dashboard_assets',return_value=assets):tracker.write_dashboard(state,target)
            second=json.loads(re.search(r'id="war-data"[^>]*>(.*?)</script>',target.read_text(),re.S)[1])['sourceBuildVersion']
            self.assertNotEqual(first,second)


if __name__=='__main__':unittest.main()
