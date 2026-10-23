"""Generate and verify portal copies from the dashboard's maintained assets."""
from pathlib import Path
import argparse, ast, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
COPIES={
 'upgrade_catalog.json':'worker/upgrade-catalog.json',
 'shared/upgrade-model.js':'public/upgrade-model.js',
 'shared/dashboard-ui.js':'public/dashboard-ui.js',
 'shared/dashboard-ui.css':'public/dashboard-ui.css',
 'member_accounts.js':'public/account-management.js',
 'recruitment_contacts.js':'public/recruitment-contacts.js',
 'recruitment_dashboard.js':'public/recruitment-dashboard.js',
 'recruitment_dashboard.css':'public/recruitment-dashboard.css',
 'shared/leader-cache.js':'public/leader-cache.js',
 'shared_dashboard.js':'public/shared-dashboard.js',
 'shared/password-tools.js':'public/password-tools.js',
}
def synchronize(portal,check=False):
 assets={target:(ROOT/source).read_bytes() for source,target in COPIES.items()}
 names=[u['name'] for u in json.loads(assets['worker/upgrade-catalog.json'])['units']]
 if len(names)!=len(set(names)):raise ValueError('Duplicate named army upgrades')
 module=ast.parse((ROOT/'Clash_War_Tracker.py').read_text())
 assets['public/password-sodium.js']=next(ast.literal_eval(n.value).encode() for n in module.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='SODIUM_JS')
 assets['worker/war-history-core.js']=b'export '+(ROOT/'shared/war-history.js').read_bytes()
 hashes={name:hashlib.sha256(value).hexdigest() for name,value in assets.items()}
 manifest={'source':'phil14-hub/war-haven-dashboard','version':2,'files':hashes,'catalogSha256':hashes['worker/upgrade-catalog.json'],'modelSha256':hashes['public/upgrade-model.js'],'sodiumSha256':hashes['public/password-sodium.js']}
 assets['canonical-assets.json']=(json.dumps(manifest,indent=2)+'\n').encode()
 drift=[name for name,value in assets.items() if not (portal/name).exists() or (portal/name).read_bytes()!=value]
 if check and drift:raise ValueError('Regenerate canonical portal assets: '+', '.join(drift))
 if not check:
  for name,value in assets.items():
   path=portal/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
 return drift
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('portal',type=Path);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 try:synchronize(args.portal,args.check)
 except ValueError as error:parser.exit(1,str(error)+'\n')
 print('Canonical portal assets verified.' if args.check else 'Canonical portal assets generated.')
