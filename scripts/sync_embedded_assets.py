"""Build the standalone Pyto distribution from tracker_core.py and maintained assets."""
import argparse
import ast
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
ASSETS={
 'HTML_TEMPLATE':('templates/dashboard.html',),
 'LOCK_TEMPLATE':('templates/lock.html',),
 'TRACKER_JS':('shared/dashboard-model.js',),
 'EXTRA_JS':('shared/dashboard-workspace.js',),
 'DASHBOARD_UI_JS':('shared/dashboard-render.js',),
 'PASSWORD_JS':('shared/password-tools.js',),
 'COMMON_UI_JS':('shared/dashboard-ui.js',),
 'CLEANUP_JS':('shared/leadership-features.js','shared/leadership-workspace.js','shared/leader-session.js','shared/war-history.js','shared/war-history-start.js'),
 'CLEANUP_CSS':('shared/dashboard-ui.css',),
 'LEADER_CACHE_JS':('shared/leader-cache.js',),
 'LIVE_DASHBOARD_JS':('live_dashboard.js',),
 'SHARED_DASHBOARD_JS':('shared_dashboard.js',),
 'MEMBER_ACCOUNTS_JS':('member_accounts.js',),
 'RECRUITMENT_JS':('recruitment_contacts.js','recruitment_dashboard.js'),
 'RECRUITMENT_CSS':('recruitment_dashboard.css',),
 'SODIUM_JS':('shared/password-sodium.js',),
}

ASSETS.update({'PROGRESSION_CAPS': ('shared/progression-caps.json',), 'LEAGUE_POINT_SCALE': ('shared/league-point-scale.json',), 'VENDORED_AES': ('shared/vendor-aes.py',), 'TOWN_HALL_IMAGES': ('shared/town-hall-images.json',), 'UPGRADE_CATALOG': ('upgrade_catalog.json',), 'UPGRADE_MODEL_PY': ('shared/upgrade-model.py',)})

def synchronize(check=False):
    template=ROOT/'templates/dashboard.html'
    html=template.read_text()
    css='/*ACCOUNT_MANAGEMENT_START*/'+(ROOT/'account_management.css').read_text()+'/*ACCOUNT_MANAGEMENT_END*/'
    updated=html.replace('__ACCOUNT_MANAGEMENT_CSS__',css)
    updated=re.sub(r'/\*ACCOUNT_MANAGEMENT_START\*/[\s\S]*?/\*ACCOUNT_MANAGEMENT_END\*/',lambda m:css,updated)
    if updated!=html:
        if check:raise ValueError('Regenerate maintained account-management CSS')
        template.write_text(updated)
    source=(ROOT/'tracker_core.py').read_text();lines=source.splitlines(keepends=True);found=set();changes=[]
    for node in ast.parse(source).body:
        if not isinstance(node,ast.Assign) or not isinstance(node.targets[0],ast.Name):continue
        name=node.targets[0].id
        if name not in ASSETS:continue
        if not isinstance(node.value,ast.Call) or not isinstance(node.value.func,ast.Name) or node.value.func.id!='_load_asset':raise ValueError('Assets must load from maintained source: '+name)
        found.add(name);files=ASSETS[name];value='\n'.join((ROOT/file).read_text() for file in files)
        if len(files)==1 and files[0].endswith('.json'):value=__import__('json').loads(value)
        changes.append((node.lineno-1,node.end_lineno,name,value))
    if found!=set(ASSETS):raise ValueError('Missing maintained asset declarations')
    for first,last,name,value in reversed(changes):lines[first:last]=[name+' = '+repr(value)+'\n']
    generated=''.join(lines);path=ROOT/'Clash_War_Tracker.py'
    changed=not path.exists() or path.read_text()!=generated
    if check and changed:raise ValueError('Regenerate portable tracker from tracker_core.py and maintained assets')
    if changed:path.write_text(generated)
    return int(changed)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    try:count=synchronize(args.check)
    except ValueError as error:parser.exit(1,str(error)+'\n')
    print('Portable source and assets verified.' if args.check else 'Generated '+str(count)+' portable distribution.')
