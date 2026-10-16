"""Plan a final-results update from each war's already recorded end time."""
import copy
from datetime import datetime, timedelta, timezone


DELAY = timedelta(minutes=5)
RETRY = timedelta(minutes=10)
RETRY_WINDOW = timedelta(hours=6)


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def plan(state, now=None):
    """Preserve completed checks and arm recently observed API wars only.

    Old war-log summaries and manually entered wars cannot trigger collection.
    A failed lookup never counts as a captured final result.
    """
    now = now or datetime.now(timezone.utc)
    previous = (state.get('automaticUpdates') or {}).get('postWar') or {}
    watches = copy.deepcopy(previous.get('watches') or {})
    watches = {key: value for key, value in watches.items()
               if isinstance(value, dict) and timestamp(value.get('endTime'))
               and timestamp(value['endTime']) >= now - timedelta(days=14)}
    for war in state.get('wars', []):
        if not isinstance(war, dict) or war.get('source') != 'API' or not war.get('id'):
            continue
        ended = timestamp(war.get('endTime'))
        if not ended or ended < now - RETRY_WINDOW or ended > now + timedelta(days=3):
            continue
        if war.get('state') not in ('preparation', 'inWar', 'warEnded'):
            continue
        due = ended + DELAY
        watch = watches.setdefault(war['id'], {'endTime': iso(ended), 'dueAt': iso(due)})
        # A manual/daily scan after the target already satisfies the final check.
        observed = timestamp(war.get('observedAt'))
        if war.get('final') and observed and observed >= due:
            watch['completedAt'] = watch.get('completedAt') or iso(observed)
    for watch in watches.values():
        ended = timestamp(watch['endTime'])
        if not watch.get('completedAt') and now > ended + RETRY_WINDOW:
            watch['expiredAt'] = watch.get('expiredAt') or iso(now)
    pending = []
    for key, watch in watches.items():
        if watch.get('completedAt') or watch.get('expiredAt'):
            continue
        due = timestamp(watch.get('dueAt'))
        last_attempt = timestamp(watch.get('lastAttemptAt'))
        if due:
            pending.append((max(due, last_attempt + RETRY) if last_attempt else due, key))
    pending.sort()
    return {'version': 1, 'delayMinutes': 5, 'watches': watches,
            'nextUpdateAt': iso(pending[0][0]) if pending else None}


def next_update(state, now=None):
    return timestamp(plan(state, now)['nextUpdateAt'])


def record_update(state, now=None):
    """Re-arm from fresh wars and acknowledge only final, complete player data."""
    now = now or datetime.now(timezone.utc)
    schedule = plan(state, now)
    wars = {war.get('id'): war for war in state.get('wars', []) if isinstance(war, dict)}
    for key, watch in schedule['watches'].items():
        due = timestamp(watch.get('dueAt'))
        if watch.get('completedAt') or watch.get('expiredAt') or not due or due > now:
            continue
        watch['lastAttemptAt'] = iso(now)
        war = wars.get(key, {})
        if war.get('final') and war.get('rosterComplete'):
            watch['completedAt'] = iso(now)
    state.setdefault('automaticUpdates', {})['postWar'] = schedule
    state['automaticUpdates']['postWar'] = plan(state, now)
    return state['automaticUpdates']['postWar']
