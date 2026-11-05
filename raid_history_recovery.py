"""Restore only missing raid members from authenticated, same-clan archive revisions."""
import copy
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode


def same_time(a,b):
    try:
        return datetime.fromisoformat(a.replace('Z','+00:00')) == datetime.fromisoformat(b.replace('Z','+00:00'))
    except (ValueError,TypeError,AttributeError):
        return False

def preserve(previous, current):
    """A later metadata-only API report must not erase individual raid evidence."""
    old = {r.get('id'): r for r in previous.get('raids', [])}
    for raid in current.get('raids', []):
        saved = old.get(raid.get('id'), {})
        if saved.get('members') and not raid.get('members') and same_time(saved.get('startTime'),raid.get('startTime')):
            raid['members'] = copy.deepcopy(saved['members'])


def recover(state, config, tracker):
    attempted = state.setdefault('raidMemberRecovery', {})
    restored = 0
    missing = [r for r in state.get('raids', []) if r.get('state') == 'ended' and not r.get('members') and r.get('endTime') and r.get('id') not in attempted]
    for raid in sorted(missing, key=lambda r: r['endTime'], reverse=True)[:8]:
        try:
            # Use the last archive before the next Friday raid begins.
            until = datetime.fromisoformat(raid['endTime'].replace('Z', '+00:00')) + timedelta(days=3, hours=23)
            path = '/repos/' + config['repository'] + '/commits?' + urlencode({'path': tracker.GITHUB_HISTORY_PATH, 'until': until.astimezone(timezone.utc).isoformat(), 'per_page': 1})
            commits = tracker.github_request(config, 'GET', path)
            if not isinstance(commits, list):
                raise ValueError('Invalid archive revision list')
            if not commits:
                attempted[raid['id']] = 'no-archive'
                continue
            sha = commits[0].get('sha', '')
            if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('Invalid archive revision')
            record = tracker.github_history_record(config, ref=sha, include_content=True)
            if not record:
                continue
            historic = tracker.decrypt_history(record['envelope'], config['password'])
            if historic.get('clanTag') != state.get('clanTag'):
                raise ValueError('Archive clan mismatch')
            source = next((r for r in historic.get('raids', []) if r.get('id') == raid['id'] and same_time(r.get('startTime'),raid.get('startTime')) and r.get('state') == 'ended'), None)
            if source and isinstance(source.get('members'), list) and source['members']:
                raid['members'] = copy.deepcopy(source['members'])
                raid['membersRecoveredFrom'] = sha
                restored += 1
                attempted[raid['id']] = 'restored'
            else:
                attempted[raid['id']] = 'no-member-details'
        except Exception:
            # A transient lookup or incompatible passphrase never changes live evidence.
            print('Raid member recovery deferred for one archive; existing records retained.')
    print('Recovered individual raid reports:', restored)
    return restored
