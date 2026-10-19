import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class VillageExportTests(unittest.TestCase):
    def test_sparse_and_new_game_entries_do_not_reject_valid_buildings(self):
        program=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
vm.runInThisContext(fs.readFileSync('shared/upgrade-model.js','utf8'));
const parser=WarHavenUpgrades.create(JSON.parse(fs.readFileSync('upgrade_catalog.json','utf8')));
const source={tag:'#P0Q',timestamp:1792440000,buildings:[{data:1000001,lvl:13},{data:1000021,lvl:7,cnt:2},{data:1000021,timer:120},{data:1000008,cnt:0},{data:19999999,cnt:1},{data:1000097,types:[]}],traps:[]};
const result=parser.parseVillage(source,'#P0Q',Date.parse('2026-10-20T00:00:00Z'));
assert.equal(result.rows.filter(r=>r.id===1000021&&!r.missing).reduce((n,r)=>n+r.count,0),3);
assert.equal(result.rows.find(r=>r.id===1000021&&r.level===null).remaining,null);
assert.equal(result.categories.Defenses.known,false);
assert.ok(result.issues.some(s=>s.includes('19999999')));
assert.ok(result.issues.some(s=>s.includes('Crafting Station')));
assert.equal(result.active[0].level,null);assert.equal(result.active[0].target,null);
assert.throws(()=>parser.parseVillage({...source,tag:'#P0Y'},'#P0Q'),/tag must match/);
assert.throws(()=>parser.parseVillage({...source,buildings:[...source.buildings,{data:1000008,lvl:1,cnt:-1}]},'#P0Q',Date.parse('2026-10-20')),/Cannon.*invalid count/);
'''
        result=subprocess.run(['node','-e',program],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
