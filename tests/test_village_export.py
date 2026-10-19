import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class VillageExportTests(unittest.TestCase):
    def test_helper_hut_does_not_hide_known_building_progress(self):
        program=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
vm.runInThisContext(fs.readFileSync('shared/upgrade-model.js','utf8'));
const parser=WarHavenUpgrades.create(JSON.parse(fs.readFileSync('upgrade_catalog.json','utf8')));
const source=JSON.parse(fs.readFileSync('tests/fixtures/th13-helper-hut-export.json','utf8'));
const current=parser.parseVillage(source,source.tag,Date.parse('2030-01-01'));
const withoutHut=JSON.parse(JSON.stringify(source));withoutHut.buildings=withoutHut.buildings.filter(r=>r.data!==1000093);
const baseline=parser.parseVillage(withoutHut,source.tag,Date.parse('2030-01-01'));
assert.deepEqual(current.categories,baseline.categories);assert.equal(current.categories.Buildings.known,true);
assert.equal(current.categories.Buildings.knownCount,current.categories.Buildings.count);assert.equal(current.categories.Buildings.unknownCount,0);
assert.equal(current.active.length,4);assert.ok(!current.rows.some(r=>r.id===1000093));
const legacy=JSON.parse(JSON.stringify(current));
legacy.rows.push({id:1000093,name:'Helper Hut',category:'Buildings',level:1,maximum:null,count:1,remaining:null});
legacy.categories.Buildings.known=false;legacy.issues.push('Helper Hut level exceeds the catalog cap; its progress is unknown.');
const before=JSON.stringify(legacy),fixed=parser.refreshVillage(legacy);
assert.deepEqual(fixed.categories,current.categories);assert.deepEqual(fixed.active,legacy.active);
assert.equal(fixed.exportedAt,legacy.exportedAt);assert.equal(fixed.importedAt,legacy.importedAt);assert.equal(JSON.stringify(legacy),before);
assert.ok(!fixed.issues.some(s=>s.startsWith('Helper Hut ')));assert.ok(fixed.issues.some(s=>s.includes('Crafting Station')));
const sparse=JSON.parse(JSON.stringify(source));delete sparse.buildings.find(r=>r.data===1000008).lvl;
const partial=parser.parseVillage(sparse,source.tag,Date.parse('2030-01-01')).categories.Defenses;
assert.equal(partial.known,false);assert.equal(partial.knownCount,46);assert.equal(partial.unknownCount,1);assert.equal(partial.count,47);
'''
        result=subprocess.run(['node','-e',program],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

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
