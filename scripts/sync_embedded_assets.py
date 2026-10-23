"""Generate the portable tracker's embedded assets from maintained source files."""
import argparse
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    'HTML_TEMPLATE': ('templates/dashboard.html',),
    'LOCK_TEMPLATE': ('templates/lock.html',),
    'TRACKER_JS': ('shared/dashboard-model.js',),
    'EXTRA_JS': ('shared/dashboard-workspace.js',),
    'DASHBOARD_UI_JS': ('shared/dashboard-render.js',),
    'PASSWORD_JS': ('shared/password-tools.js',),
    'COMMON_UI_JS': ('shared/dashboard-ui.js',),
    'CLEANUP_JS': ('shared/leadership-features.js', 'shared/leadership-workspace.js', 'shared/leader-session.js', 'shared/war-history.js', 'shared/war-history-start.js'),
    'CLEANUP_CSS': ('shared/dashboard-ui.css',),
    'LEADER_CACHE_JS': ('shared/leader-cache.js',),
    'LIVE_DASHBOARD_JS': ('live_dashboard.js',),
    'SHARED_DASHBOARD_JS': ('shared_dashboard.js',),
    'MEMBER_ACCOUNTS_JS': ('member_accounts.js',),
    'RECRUITMENT_JS': ('recruitment_contacts.js', 'recruitment_dashboard.js'),
    'RECRUITMENT_CSS': ('recruitment_dashboard.css',),
}


def synchronize(check=False):
    path = ROOT / 'Clash_War_Tracker.py'
    template_path = ROOT / 'templates/dashboard.html'
    if template_path.exists():
        import re
        html = template_path.read_text()
        css = '/*ACCOUNT_MANAGEMENT_START*/'+(ROOT/'account_management.css').read_text()+'/*ACCOUNT_MANAGEMENT_END*/'
        html = html.replace('__ACCOUNT_MANAGEMENT_CSS__', css)
        html = re.sub(r'/\*ACCOUNT_MANAGEMENT_START\*/[\s\S]*?/\*ACCOUNT_MANAGEMENT_END\*/', lambda match: css, html)
        if html != template_path.read_text():
            if check: raise ValueError('Regenerate maintained account-management CSS')
            template_path.write_text(html)
    source = path.read_text()
    lines = source.splitlines(keepends=True)
    changes = []
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if name not in ASSETS:
            continue
        expected = '\n'.join((ROOT / file).read_text() for file in ASSETS[name])
        if ast.literal_eval(node.value) != expected:
            changes.append((node.lineno - 1, node.end_lineno, name, expected))
    changes.sort()
    if check and changes:
        raise ValueError('Regenerate embedded assets: ' + ', '.join(c[2] for c in changes))
    for first, last, name, value in reversed(changes):
        lines[first:last] = [name + ' = ' + repr(value) + '\n']
    if changes:
        path.write_text(''.join(lines))
    return len(changes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        count = synchronize(args.check)
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    print('Embedded assets verified.' if args.check else f'Generated {count} embedded assets.')
