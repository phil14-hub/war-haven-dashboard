import copy
import unittest
from upgrade_progress import CATALOG, army_progress, compact_series
import Clash_War_Tracker as tracker


def profile(th, baseline=None):
    p={'townHallLevel':th,'profileCheckedAt':'2026-10-17T12:00:00Z','troops':[],'spells':[],'heroes':[],'heroEquipment':[]}
    for u in CATALOG['units']:
        level=u['caps'][(baseline or th)-1]
        if not level or u['group']=='equipment':continue
        field={'troops':'troops','siege':'troops','pets':'troops','spells':'spells','heroes':'heroes'}[u['group']]
        p[field].append({'name':u['name'],'level':level,'village':'home','maxLevel':max(u['caps'])})
    return p

class UpgradeProgressTests(unittest.TestCase):
    def test_previous_max_zero_and_current_max_one_hundred(self):
        for th in range(3,19):
            with self.subTest(th=th):
                p=army_progress(profile(th,th-1))
                self.assertEqual(p['percent'],0)
                self.assertEqual(army_progress(profile(th))['percent'],100)
                self.assertEqual(p['method'],'th-work-v2')
    def test_rush_negative_and_short_explanation(self):
        p=profile(14,12);result=army_progress(p)
        self.assertLess(result['percent'],0)
        self.assertIn('earlier',result['explanation'])
        self.assertGreater(result['earlierLevelsRemaining'],0)
        self.assertTrue(any(i['earlierLevelsRemaining'] for i in result['groups']['heroes']['items']))
    def test_unknown_never_invents_a_zero_or_max(self):
        p=profile(14);del p['heroes']
        self.assertIsNone(army_progress(p)['percent'])
        p=profile(14);p['troops'][0]['level']=999
        self.assertIsNone(army_progress(p)['percent'])
        p=profile(14);p['troops'].append({'name':'Unknown future troop','level':1})
        self.assertIsNone(army_progress(p)['percent'])
    def test_hero_caps_and_no_new_work(self):
        r=army_progress(profile(14,13))
        for h in r['groups']['heroes']['items']:
            u=next(u for u in CATALOG['units'] if u['id']==h['id'])
            self.assertEqual(h['maximum'],u['caps'][13])
        self.assertEqual(r['groups']['heroes']['percent'],0)
    def test_changed_only_history_and_legacy_history_preserved(self):
        s=tracker.new_state('#P0Y');s['profiles']={'#P0Y':profile(14,13)}
        tracker.capture_progression(s);self.assertEqual(len(s['memberProgressHistory']['#P0Y']),1)
        s['profiles']['#P0Y']['profileCheckedAt']='2026-10-17T13:00:00Z';tracker.capture_progression(s)
        self.assertEqual(len(s['memberProgressHistory']['#P0Y']),1)
        s['profiles']['#P0Y']['heroes'][0]['level']+=1;tracker.capture_progression(s)
        self.assertEqual(len(s['memberProgressHistory']['#P0Y']),2)
    def test_only_consecutive_duplicates_collapse(self):
        points=[{'value':v} for v in (0,0,1,1,0,0)]
        self.assertEqual([p['value'] for p in compact_series(points)],[0,1,0])

if __name__=='__main__':unittest.main()
