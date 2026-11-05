import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import Clash_War_Tracker as t
from raid_history_recovery import recover, preserve

class RaidRecovery(unittest.TestCase):
    def fixture(self):
        s=t.new_state(t.DEFAULT_CLAN_TAG)
        s['raids']=[{'id':'raid:fixture','state':'ended','startTime':'2026-10-23T07:00:00Z','endTime':'2026-10-26T07:00:00Z','capitalTotalLoot':103034,'members':[]}]
        return s
    def test_refresh_keeps_members_when_api_omits_them(self):
        s=self.fixture();s['raids'][0]['id']='raid:'+s['clanTag']+':2026-10-23T07:00:00.000Z';s['raids'][0]['members']=[{'tag':'#L88YRVJJV','capitalResourcesLooted':1234,'attacks':6}]
        old=copy.deepcopy(s['raids'][0]['members'])
        before=copy.deepcopy(s)
        t.store_raids(s,{'items':[{'startTime':'20261023T070000.000Z','endTime':'20261026T070000.000Z','state':'ended','members':[]}]})
        preserve(before,s)
        self.assertEqual(s['raids'][0]['members'],old)
        t.store_raids(s,{'items':[{'startTime':'20261023T070000.000Z','endTime':'20261026T070000.000Z','state':'ended','members':[{'tag':'#L88YRVJJV','capitalResourcesLooted':1500}]}]})
        self.assertEqual(s['raids'][0]['members'][0]['capitalResourcesLooted'],1500)
    def test_verified_revision_restores_only_members_and_is_idempotent(self):
        s=self.fixture();archive=copy.deepcopy(s);archive['raids'][0]['members']=[{'tag':'#L88YRVJJV','attacks':6,'capitalResourcesLooted':1234}];archive['raids'][0]['capitalTotalLoot']=1
        fake=SimpleNamespace(GITHUB_HISTORY_PATH=t.GITHUB_HISTORY_PATH,github_request=lambda *a:[{'sha':'a'*40}],github_history_record=lambda *a,**kw:{'envelope':{}},decrypt_history=lambda *a:archive)
        self.assertEqual(recover(s,{'repository':'phil14-hub/war-haven-dashboard','password':'fixture'},fake),1)
        self.assertEqual(s['raids'][0]['capitalTotalLoot'],103034)
        self.assertEqual(s['raids'][0]['members'][0]['capitalResourcesLooted'],1234)
        self.assertEqual(recover(s,{'repository':'fixture','password':'fixture'},fake),0)
    def test_foreign_or_unreadable_archive_cannot_change_data(self):
        for fail in (False,True):
            s=self.fixture();before=copy.deepcopy(s['raids'])
            def decrypt(*a):
                if fail:raise ValueError('bad signature')
                return {'clanTag':'OTHER','raids':[]}
            fake=SimpleNamespace(GITHUB_HISTORY_PATH=t.GITHUB_HISTORY_PATH,github_request=lambda *a:[{'sha':'b'*40}],github_history_record=lambda *a,**kw:{'envelope':{}},decrypt_history=decrypt)
            self.assertEqual(recover(s,{'repository':'fixture','password':'fixture'},fake),0);self.assertEqual(s['raids'],before);self.assertEqual(s['raidMemberRecovery'],{})
