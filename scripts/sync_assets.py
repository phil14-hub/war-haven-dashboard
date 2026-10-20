"""Generate portal upgrade assets from this repository's canonical game catalog."""
from pathlib import Path
import argparse, ast, hashlib, json
root=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('portal',type=Path);args=parser.parse_args()
    catalog=(root/'upgrade_catalog.json').read_bytes();model=(root/'shared/upgrade-model.js').read_bytes()
    names=[u['name'] for u in json.loads(catalog)['units']]
    if len(names)!=len(set(names)):raise SystemExit('Duplicate named army upgrades')
    (args.portal/'worker/upgrade-catalog.json').write_bytes(catalog);(args.portal/'public/upgrade-model.js').write_bytes(model)
    module=ast.parse((root/'Clash_War_Tracker.py').read_text())
    sodium=next(ast.literal_eval(node.value) for node in module.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='SODIUM_JS').encode()
    (args.portal/'public/password-sodium.js').write_bytes(sodium)
    (args.portal/'canonical-assets.json').write_text(json.dumps({'catalogSha256':hashlib.sha256(catalog).hexdigest(),'modelSha256':hashlib.sha256(model).hexdigest(),'sodiumSha256':hashlib.sha256(sodium).hexdigest(),'source':'phil14-hub/war-haven-dashboard'},indent=2)+'\n')
