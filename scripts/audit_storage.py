"""Measure an authenticated archive without logging any player values or editing it."""
import gzip
import json
from collections import Counter
from datetime import datetime, timezone


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def describe(value):
    body = encoded(value)
    return {'bytes': len(body), 'gzipBytes': len(gzip.compress(body, mtime=0)),
            'items': len(value) if isinstance(value, (dict, list)) else None}


def field_totals(rows):
    totals = Counter()
    for row in rows:
        if isinstance(row, dict):
            for key, value in row.items():
                totals[key] += len(encoded(value)) + len(encoded(key)) + 1
    return dict(totals.most_common())


def summarize(state):
    sections = {key: describe(value) for key, value in state.items()}
    recruiter = state.get('recruiter') or {}
    files = recruiter.get('files') or {}
    players = (files.get('detected_leavers.json') or {}).get('players') or {}
    lifecycle = Counter(row.get('lifecycle', 'unknown') for row in players.values())
    rosters = (files.get('us_clan_rosters.json') or {}).get('clans') or {}
    roster_fields = field_totals(member for clan in rosters.values() for member in (clan.get('members') or {}).values())
    now = datetime.now(timezone.utc)
    old = {}
    for days in (7, 30, 90):
        selected = []
        for row in players.values():
            stamp = row.get('lastVerifiedAt') or row.get('lastDepartureDetectedAt') or row.get('detectedAt')
            try:
                age = (now - datetime.fromisoformat(stamp.replace('Z', '+00:00'))).total_seconds() / 86400
            except (AttributeError, TypeError, ValueError):
                continue
            if age > days and not row.get('joinedMyClanAt'):
                selected.append(row)
        old[str(days)] = {'neverJoinedRecords': len(selected), 'bytes': sum(len(encoded(row)) for row in selected)}
    roster_tags = {row.get('tag') for row in state.get('roster', [])}
    profiles = state.get('profiles') or {}
    inactive = {tag: profile for tag, profile in profiles.items() if tag not in roster_tags}
    from tracker_core import archive_document
    return {'total': describe(state), 'storageDocument': describe(archive_document(state)), 'sections': sections,
            'recruiterFiles': {key: describe(value) for key, value in files.items()},
            'recruiterReport': {key: describe(value) for key, value in (recruiter.get('report') or {}).items()},
            'candidateRecordFields': field_totals(players.values()), 'candidateLifecycleCounts': dict(lifecycle),
            'oldNeverJoinedCandidates': old, 'recruiterRosterMemberFields': roster_fields,
            'inactiveProfiles': describe(inactive), 'profileFields': field_totals(profiles.values()),
            'warFields': field_totals(state.get('wars', [])), 'raidFields': field_totals(state.get('raids', [])),
            'memberHistoryFields': field_totals((state.get('memberHistory') or {}).values()),
            'edits': {key: describe(value) for key, value in (state.get('edits') or {}).items()}}
