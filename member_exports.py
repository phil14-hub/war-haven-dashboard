"""Build the member-only projection; never publish leadership notes or raw edits."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.request import Request, urlopen


def stamp(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError):
        return 0


def count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def capital_evidence(history, as_of):
    samples = {}
    since, end = stamp(history.get('since')), min(as_of, stamp(history.get('leftAt')) or as_of)
    for sample in history.get('capitalSamples', []):
        at = stamp(sample.get('at'))
        if not since <= at <= end or not at:
            continue
        value = sample.get('total') if count(sample.get('total')) else None
        if at in samples:
            old = samples[at]['total']
            value = max(old, value) if old is not None and value is not None else None
        samples[at] = {'at': sample['at'], 'total': value}
    high = previous = None
    total, series = 0, []
    for sample in sorted(samples.values(), key=lambda item: stamp(item['at'])):
        value = sample['total']
        if value is None:
            previous = None
            continue
        if previous is not None and high is not None:
            total += max(0, value - high)
        series.append({'at': sample['at'], 'value': total})
        high, previous = max(high if high is not None else value, value), sample['at']
    return (total if series else None), series


def donation_evidence(history, as_of):
    previous = stamp(history.get('since'))
    end = min(as_of, stamp(history.get('leftAt')) or as_of)
    total, series = 0, []
    for sample in sorted(history.get('donationIntervals', []), key=lambda v: (stamp(v.get('end')), v.get('count', 0))):
        start, stop, value = stamp(sample.get('start')), stamp(sample.get('end')), sample.get('count')
        if not count(value) or not value or not start or start < previous or stop <= start or stop > end:
            continue
        total += value
        previous = stop
        series.append({'at': sample['end'], 'value': total})
    return series


def build_snapshot(state, tracker):
    at = state.get('lastSuccessfulSync')
    roster = state.get('roster')
    if not stamp(at) or not isinstance(roster, list) or not 1 <= len(roster) <= 50:
        raise ValueError('Member publication requires a complete successful clan snapshot.')
    clan = state.get('clanProfile') or {}
    if isinstance(clan.get('members'), int) and clan['members'] != len(roster):
        raise ValueError('Member roster count does not match the clan snapshot.')
    wars = {v['id']: v for v in state.get('wars', []) if v.get('id')}
    wars.update({key:value for key,value in (state.get('edits') or {}).get('manualWars', {}).items() if not value.get('deleted')})
    members, comparisons = {}, []
    for player in roster:
        tag = tracker.normalize_tag(player.get('tag'))
        if not tag or tag in members:
            raise ValueError('Invalid or duplicate member tag.')
        profile = state.get('profiles', {}).get(tag) or {}
        history = state.get('memberHistory', {}).get(tag) or {}
        capital, capital_series = capital_evidence(history, stamp(at))
        donations = donation_evidence(history, stamp(at))
        own_wars = []
        stats = {'used': 0, 'allowed': 0, 'appearances': 0, 'stars': 0, 'attacks': 0, 'triples': 0, 'destruction': 0, 'destructionAttacks': 0}
        for war in sorted(wars.values(), key=lambda w: stamp(w.get('endTime'))):
            if war.get('kind') not in ('Regular', 'CWL'):
                continue
            participant = next((p for p in war.get('participants', []) if tracker.normalize_tag(p.get('tag')) == tag), None)
            if not participant:
                continue
            final = bool(war.get('final') and war.get('rosterComplete'))
            used, allowed = participant.get('attacksUsed'), war.get('attacksPerMember')
            own_wars.append({'id': war.get('id'), 'kind': war.get('kind'), 'opponent': (war.get('opponent') or {}).get('name', 'Opponent'),
                             'startTime': war.get('startTime'), 'endTime': war.get('endTime'), 'state': war.get('state'), 'final': final,
                             'used': used if count(used) else None, 'allowed': allowed if count(allowed) else None,
                             'stars': participant.get('starsEarned') if count(participant.get('starsEarned')) else (0 if used == 0 else None)})
            if not final:
                continue
            stats['appearances'] += 1
            excused = bool((state.get('edits') or {}).get('exceptions', {}).get(war['id'] + '::' + tag, {}).get('value'))
            if count(used) and count(allowed) and used <= allowed and not excused:
                stats['used'] += used
                stats['allowed'] += allowed
            seen_attacks = set()
            for index, attack in enumerate(participant.get('attacks', [])):
                if not isinstance(attack, dict):
                    continue
                attack_id = attack.get('order') if attack.get('order') is not None else 'index:'+str(index)
                if not isinstance(attack_id, (str,int)):
                    continue
                if attack_id in seen_attacks:
                    continue
                seen_attacks.add(attack_id)
                destruction = attack.get('destructionPercentage')
                if isinstance(destruction, (int, float)) and not isinstance(destruction, bool) and 0 <= destruction <= 100:
                    stats['destruction'] += destruction
                    stats['destructionAttacks'] += 1
                if count(attack.get('stars')) and attack['stars'] <= 3:
                    stats['attacks'] += 1
                    stats['stars'] += attack['stars']
                    stats['triples'] += attack['stars'] == 3
        raids = []
        for raid in {r.get('id') or r.get('startTime'): r for r in state.get('raids', [])}.values():
            entry = next((p for p in raid.get('members', []) if tracker.normalize_tag(p.get('tag')) == tag), None)
            if entry:
                raids.append({'id': raid.get('id'), 'endTime': raid.get('endTime'), 'state': raid.get('state'), 'loot': entry.get('capitalResourcesLooted'), 'attacks': entry.get('attacks')})
        completed_loot = [r['loot'] for r in raids if r['state'] == 'ended' and count(r['loot'])]
        league = tracker.league_placement(player, profile, at, state.get('clanTag'))
        league_series = []
        for sample in state.get('leagueHistory', []):
            entry = next((p for p in sample.get('members', []) if tracker.normalize_tag(p.get('tag')) == tag), None)
            if entry and entry.get('league', {}).get('points') is not None:
                league_series.append({'at': sample['at'], 'value': entry['league']['points'], 'detail': entry['league'].get('name', '')})
        roster_th = player.get('townHallLevel')
        profile_at = profile.get('profileCheckedAt')
        profile_matches = bool(profile and profile.get('townHallLevel') == roster_th and profile_at)
        army = tracker.army_progress(profile) if profile_matches else {}
        profile_status = {'capturedAt': profile_at, 'townHallMatches': bool(profile and profile.get('townHallLevel') == roster_th), 'available': profile_matches,
                          'message': None if profile_matches else 'Army progress is waiting for a successful player profile matching the current Town Hall.'}
        army_series = [{'at': p['at'], 'value': p['completionPercent'], 'townHall': p.get('townHall'), 'detail': 'TH ' + str(p.get('townHall'))} for p in state.get('memberProgressHistory', {}).get(tag, []) if p.get('method') == 'th-work-v2' and p.get('at') and p.get('completionPercent') is not None]
        badges = []
        for condition, label in [(stats['used'] >= 10, '10 confirmed war attacks'), (stats['stars'] >= 30, '30 recorded war stars'),
                                 (capital is not None and capital >= 10000, '10,000 confirmed Capital Gold'),
                                 (bool(donations) and donations[-1]['value'] >= 1000, '1,000 observed donations')]:
            if condition:
                badges.append(label)
        view = {'tag': tag, 'name': str(player.get('name') or tag), 'townHallLevel': player.get('townHallLevel') or profile.get('townHallLevel'),
                'role': player.get('role'), 'since': history.get('since'), 'warPreference': player.get('warPreference'),
                'league': {'points': league.get('points'), 'name': league.get('name') or league.get('tier')},
                'seasonDonations': player.get('donations'), 'donationsReceived': player.get('donationsReceived'),
                'capitalGold': capital, 'capitalSeries': capital_series, 'donationSeries': donations,
                'raidLoot': sum(completed_loot) if completed_loot else None, 'raids': raids, 'wars': own_wars,
                'warStats': stats, 'leagueSeries': league_series, 'armySeries': army_series, 'armyPercent': army.get('completionPercent'), 'army': army,
                'heroes': [{'name': h['name'], 'level': h['level'], 'maximum': h['maximum']} for h in army.get('groups', {}).get('heroes', {}).get('items', [])],
                'achievements': badges, 'profileStatus': profile_status, 'season': str(at)[:7]}
        members[tag] = view
        comparisons.append({'tag': tag, 'name': view['name'], 'townHallLevel': view['townHallLevel'], 'leaguePoints': league.get('points'),
                            'seasonDonations': view['seasonDonations'], 'capitalGold': capital, 'warStars': stats['stars'] if stats['attacks'] else None,
                            'raidLoot': view['raidLoot'], 'averageDestruction': stats['destruction'] / stats['destructionAttacks'] if stats['destructionAttacks'] else None,
                            'windowStart': next((w['endTime'] for w in own_wars if w['final']), None), 'windowEnd': next((w['endTime'] for w in reversed(own_wars) if w['final']), None), 'destructionAttacks': stats['destructionAttacks'], 'attackUse': stats['used'] / stats['allowed'] if stats['allowed'] else None})
    from upgrade_progress import compact_series
    for player in members.values():
        for field in ('capitalSeries', 'donationSeries', 'leagueSeries', 'armySeries'):
            player[field] = compact_series(player[field])[-730:]
    return {'version': 1, 'updatedAt': at, 'clan': {'tag': state['clanTag'], 'name': state.get('clanName') or 'War Haven', 'level': clan.get('clanLevel'), 'badgeUrl': tracker.clan_badge_url(clan)},
            'members': members, 'comparisons': comparisons}


def fetch_clan_badge(state, tracker):
    """Keep only the current public badge in R2, outside GitHub history."""
    url=tracker.clan_badge_url(state.get('clanProfile'))
    if not url:
        return None
    try:
        request=Request(url,headers={'User-Agent':'WarHavenDashboard/1.22 (+https://github.com/phil14-hub/war-haven-dashboard)'})
        with urlopen(request,timeout=15) as response:
            raw=response.read(262145)
            if response.geturl()!=url or len(raw)>262144 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('Invalid clan badge.')
        return {'url':url,'png':base64.b64encode(raw).decode('ascii')}
    except (OSError,ValueError):
        print('Clan crest download unavailable; the previous saved icon is retained.')
        return None


def publish(state, dashboard, client, password, tracker):
    """Publish a small member projection and authenticated leadership bridge to R2."""
    view = build_snapshot(state, tracker)
    html = dashboard.read_text()
    match = re.search(r'id="protected-payload">(.*?)</script>', html, re.S)
    if not match:
        raise ValueError('Protected dashboard payload not found.')
    envelope = json.loads(match.group(1))
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(envelope['salt'], validate=True), envelope['rounds'], dklen=64)
    publication={'view': view, 'leadership': {'payload': envelope, 'key': base64.b64encode(key).decode()}}
    badge=fetch_clan_badge(state,tracker)
    if badge:
        publication['clanBadge']=badge
    result = client.request('/members/api/ingest', publication)
    print('Member projection synchronized (' + str(result.get('members', 0)) + ' members; ' + str(result.get('bytes', 0)) + ' bytes).')
    raw_bytes = len(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode())
    print('Storage check: complete uncompressed history ' + str(raw_bytes) + ' bytes of the 52428800-byte safeguard; leadership publication ' + str(dashboard.stat().st_size) + ' bytes.')
    return result

