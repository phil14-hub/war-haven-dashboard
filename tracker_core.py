#!/usr/bin/env python3
"""Clash War Tracker 1.21: leadership reports, war lineups and a protected shared website.

Run this file in Pyto. No extra packages are required. Optional arguments:
  --watch 300       Check every 5 minutes while Python is running.
  --apply FILE      Apply notes, exceptions, and final results exported by the page.
  --skip-profiles   Skip player profiles, including Capital donation updates.
  --clan TAG       Track another clan in its own folder.
"""
import argparse
import base64
import hashlib
import hmac
import copy
import json
import html as html_module
import os
import re
import secrets
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

VERSION = '1.22'
DEFAULT_CLAN_TAG = '#2PQQJ0GR0'
RECRUITER_DIR = Path.home() / 'Documents' / 'Clash_Recruitment'
DEFAULT_TOKEN_FILE = RECRUITER_DIR / 'coc_token.txt'
DEFAULT_OUTPUT = RECRUITER_DIR
API_ROOT = 'https://api.clashofclans.com/v1'

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')

def normalize_tag(value):
    value = str(value or '').strip().upper()
    return ('#' + value.lstrip('#')) if value else ''

def api_time(value):
    if not value:
        return None
    try:
        value = str(value)
        if re.match(r'^\d{8}T\d{6}', value):
            fmt = '%Y%m%dT%H%M%S.%fZ' if '.' in value else '%Y%m%dT%H%M%SZ'
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
    except (ValueError, TypeError):
        return None

def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)

def token_file_candidates(path=None):
    # Explicit command-line choices stay authoritative. Automatic discovery is
    # relative to the script, never Pyto's changing working directory.
    if path is not None:
        return [Path(path).expanduser()]
    candidates = []
    script_file = globals().get('__file__')
    if script_file:
        candidates.append(Path(script_file).resolve().parent / 'coc_token.txt')
    candidates.append(DEFAULT_TOKEN_FILE)
    return list(dict.fromkeys(candidates))

def load_tokens(path=None):
    raw = re.split(r'[\s,;]+', os.getenv('COC_API_TOKENS', ''))
    raw.append(os.getenv('COC_API_TOKEN', ''))
    unreadable = []
    for candidate in token_file_candidates(path):
        try:
            text = candidate.read_text(encoding='utf-8-sig')
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError):
            unreadable.append(candidate)
            continue
        raw.extend(line for line in text.splitlines()
                   if line.strip() and not line.strip().startswith('#'))
    tokens = []
    for value in raw:
        value = value.strip().strip('"\'').strip()
        if value.lower().startswith('bearer '):
            value = value[7:].strip()
        if value and value not in tokens:
            tokens.append(value)
    if not tokens:
        hint = (' A token file could not be read. In Pyto, use Open directory to grant access to its containing folder; download the file from iCloud if needed.'
                if unreadable else '')
        raise ValueError('No API key found. Put coc_token.txt beside this script, or keep it in Documents/Clash_Recruitment. You can also specify --token-file.' + hint + ' Do not paste the key into HTML.')
    return tokens

class APIError(Exception):
    def __init__(self, status, reason=''):
        self.status, self.reason = status, str(reason)
        messages = {403:'Access denied. Check the key/network; for war endpoints also check that the clan war log is public.',
                    404:'This API resource is not available.',429:'The API rate limit was reached.',
                    503:'The API is under maintenance.',520:'The API returned an unexpected server response.',0:'The API could not be reached.'}
        super().__init__(messages.get(status, 'The API request failed.') + ' (HTTP ' + str(status) + ')')

class OfficialAPI:
    def __init__(self, tokens):
        self.tokens, self.preferred = tokens, 0
        self.lock = threading.Lock()
        self.validated = False

    def get(self, path):
        with self.lock:
            order = [self.preferred] + [i for i in range(len(self.tokens)) if i != self.preferred]
        last = APIError(403)
        for index in order:
            for attempt in range(3):
                request = Request(API_ROOT + path, headers={'Authorization':'Bearer ' + self.tokens[index],
                                  'Accept':'application/json','User-Agent':'Clash-War-Tracker/' + VERSION})
                try:
                    with urlopen(request, timeout=15) as response:
                        payload = json.load(response)
                    with self.lock:
                        self.preferred = index
                        self.validated = True
                    return payload
                except HTTPError as error:
                    try:
                        reason = json.loads(error.read().decode('utf-8')).get('reason', '')
                    except (ValueError, UnicodeError):
                        reason = ''
                    last = APIError(error.code, reason)
                    if (error.code == 429 or 500 <= error.code <= 599) and attempt < 2:
                        time.sleep(1 << attempt)
                        continue
                    if error.code in (401,403):
                        # A previously accepted key cannot bypass a private clan war log.
                        if error.code == 403 and self.validated and ('war' in path.lower()) and 'ip' not in str(reason).lower():
                            raise last
                        break
                    raise last
                except (URLError, TimeoutError, OSError, ValueError):
                    last = APIError(0)
                    if attempt < 2:
                        time.sleep(1 << attempt)
                        continue
                    raise last
        raise last

# Town Hall caps derived from clashy.py 26.9.1 static game data.
# Maintained source. scripts/sync_embedded_assets.py emits the standalone Pyto file.
def _load_asset(name):
    root=Path(__file__).resolve().parent
    files=_SOURCE_ASSETS[name]
    text='\n'.join((root/file).read_text() for file in files)
    return json.loads(text) if len(files)==1 and files[0].endswith('.json') else text

_SOURCE_ASSETS = {'HTML_TEMPLATE': ('templates/dashboard.html',), 'LOCK_TEMPLATE': ('templates/lock.html',), 'TRACKER_JS': ('shared/dashboard-model.js',), 'EXTRA_JS': ('shared/dashboard-workspace.js',), 'DASHBOARD_UI_JS': ('shared/dashboard-render.js',), 'PASSWORD_JS': ('shared/password-tools.js',), 'COMMON_UI_JS': ('shared/dashboard-ui.js',), 'CLEANUP_JS': ('shared/leadership-features.js', 'shared/leadership-workspace.js', 'shared/leader-session.js', 'shared/war-history.js', 'shared/war-history-start.js'), 'CLEANUP_CSS': ('shared/dashboard-ui.css',), 'LEADER_CACHE_JS': ('shared/leader-cache.js',), 'LIVE_DASHBOARD_JS': ('live_dashboard.js',), 'SHARED_DASHBOARD_JS': ('shared_dashboard.js',), 'MEMBER_ACCOUNTS_JS': ('member_accounts.js',), 'RECRUITMENT_JS': ('recruitment_contacts.js', 'recruitment_dashboard.js'), 'RECRUITMENT_CSS': ('recruitment_dashboard.css',), 'SODIUM_JS': ('shared/password-sodium.js',), 'PROGRESSION_CAPS': ('shared/progression-caps.json',), 'LEAGUE_POINT_SCALE': ('shared/league-point-scale.json',), 'VENDORED_AES': ('shared/vendor-aes.py',), 'TOWN_HALL_IMAGES': ('shared/town-hall-images.json',), 'UPGRADE_CATALOG': ('upgrade_catalog.json',), 'UPGRADE_MODEL_PY': ('shared/upgrade-model.py',)}

PROGRESSION_CAPS = _load_asset('PROGRESSION_CAPS')

# Cumulative clan XP thresholds for levels 1 through 51.
# https://clashofclans.fandom.com/wiki/Clan_Perks#Clan_XP_Chart
CLAN_XP_CUMULATIVE = [0, 500, 1700, 3600, 6700, 10500, 15000, 20200, 26100, 34000, 42600, 51900, 61900, 72600, 88300, 104700, 121800, 139600, 158100, 181600, 205800, 230700, 256300, 282600, 313900, 345900, 378600, 412000, 446100, 485200, 525000, 565500, 606700, 648600, 695500, 743100, 791400, 840400, 890100, 944800, 1000200, 1056300, 1113100, 1170600, 1233100, 1296300, 1360200, 1424800, 1490100, 1560400, 1631400]

def merge_observations(first, second, daily=False):
    """Merge dated observations; importing an older backup never drops new data."""
    records = {}
    for value in list(first or []) + list(second or []):
        if not isinstance(value, dict) or not api_time(value.get('at')):
            continue
        key = (api_time(value['at'])[:10] + ':' + str(value.get('clanLevel'))) if daily else api_time(value['at'])
        old = records.get(key)
        if not old or api_time(value['at']) >= api_time(old['at']):
            records[key] = copy.deepcopy(value)
    return sorted(records.values(), key=lambda v: api_time(v['at']))


_upgrade_model_cache = None

def upgrade_model():
    # The Pyto download remains self-contained; the repository uses the source module.
    global _upgrade_model_cache
    if _upgrade_model_cache is None:
        if Path(__file__).with_name('upgrade_progress.py').is_file():
            import upgrade_progress
            _upgrade_model_cache = vars(upgrade_progress)
        else:
            scope = {'_BUNDLED_CATALOG': UPGRADE_CATALOG}
            exec(UPGRADE_MODEL_PY, scope)
            _upgrade_model_cache = scope
    return _upgrade_model_cache

def army_progress(profile):
    return upgrade_model()['army_progress'](profile)


def capture_progression(state):
    state.setdefault('clanHistory', [])
    state.setdefault('memberProgressHistory', {})
    model = upgrade_model()
    CATALOG, METHOD = model['CATALOG'], model['METHOD']
    state['progressionInfo'] = {k: CATALOG[k] for k in ('source', 'sourceUrl', 'catalogVersion')}
    state['progressionInfo']['method'] = METHOD
    state['memberProgress'] = {}
    for tag, profile in state.get('profiles', {}).items():
        if not isinstance(profile, dict):
            continue
        progress = army_progress(profile)
        state['memberProgress'][tag] = progress
        if not progress.get('at') or progress.get('percent') is None:
            continue
        sample = {'method': METHOD, 'at': progress['at'], 'townHall': progress['townHall'], 'percent': progress['percent'],
                  'current': progress['current'], 'maximum': progress['maximum'], 'completionPercent': progress.get('completionPercent'),
                  'groups': {k: {f: v.get(f) for f in ('current', 'maximum', 'percent', 'completionPercent')} for k, v in progress['groups'].items()}}
        history = state['memberProgressHistory'].setdefault(tag, [])
        signature = lambda s: (s.get('method'), s.get('townHall'), s.get('groups'))
        if not history or signature(history[-1]) != signature(sample):
            state['memberProgressHistory'][tag] = merge_observations(history, [sample])
    observed = api_time(state.get('lastSuccessfulSync'))
    clan = state.get('clanProfile') or {}
    roster = state.get('roster', [])
    if not observed or not clan:
        return
    def total(field):
        return sum(p[field] for p in roster) if all(integer(p.get(field)) for p in roster) else None
    halls = [(p.get('townHallLevel') or (state.get('profiles', {}).get(p.get('tag')) or {}).get('townHallLevel')) for p in roster]
    sample = {'at': observed, 'clanLevel': clan.get('clanLevel'), 'members': len(roster),
              'totalTrophies': total('trophies'), 'seasonDonations': total('donations'),
              'averageTownHall': round(sum(halls) / len(halls), 2) if halls and all(integer(v) for v in halls) else None}
    for field in ('clanPoints', 'clanBuilderBasePoints', 'clanCapitalPoints', 'warWins', 'warWinStreak'):
        sample[field] = clan.get(field) if integer(clan.get(field)) else None
    signature = lambda p: {k: p.get(k) for k in sample if k != 'at'}
    if not state['clanHistory'] or signature(state['clanHistory'][-1]) != signature(sample):
        state['clanHistory'] = merge_observations(state['clanHistory'], [sample])


def validate_progress_edits(edits):
    for key, record in edits.get('xpCheckpoints', {}).items():
        if record.get('deleted'):
            continue
        level, xp = record.get('level'), record.get('xp')
        if not api_time(record.get('at')) or not integer(level) or not 1 <= level < len(CLAN_XP_CUMULATIVE):
            raise ValueError('Invalid clan XP checkpoint date or level.')
        limit = CLAN_XP_CUMULATIVE[level] - CLAN_XP_CUMULATIVE[level - 1]
        if not integer(xp) or not 0 <= xp < limit:
            raise ValueError('Clan XP must be the XP within that level, below its next-level requirement.')
    for record in edits.get('villageProgress', {}).values():
        if record.get('deleted'):
            continue
        if not integer(record.get('townHall')) or not 1 <= record['townHall'] <= 99:
            raise ValueError('Invalid manually recorded village Town Hall.')
        for field in ('overall', 'buildings', 'walls'):
            value = record.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100):
                raise ValueError('Manually recorded village percentages must be from 0 to 100.')



LEAGUE_POINT_SCALE = _load_asset('LEAGUE_POINT_SCALE')

def league_placement(member, profile=None, observed_at=None, clan_tag=None):
    """Only modern ranked leagues qualify; unknown never becomes unranked."""
    observed = api_time(observed_at)
    sources = [(member.get('leagueTier'), observed)]
    profile = profile or {}
    checked = api_time(profile.get('profileCheckedAt'))
    matched = not clan_tag or normalize_tag((profile.get('clan') or {}).get('tag')) == clan_tag
    fresh = observed and checked and 0 <= (datetime.fromisoformat(observed.replace('Z','+00:00')) - datetime.fromisoformat(checked.replace('Z','+00:00'))).total_seconds() <= 3600
    if matched and fresh:
        sources.append((profile.get('leagueTier'), checked))
    for raw, checked in sources:
        if not isinstance(raw, dict):
            continue
        tier = next((v for v in LEAGUE_POINT_SCALE if raw.get('id') == v['id']), None)
        if not tier:
            name = re.sub(r'[^a-z0-9]', '', str(raw.get('name') or '').lower())
            tier = next((v for v in LEAGUE_POINT_SCALE if re.sub(r'[^a-z0-9]', '', v['name'].lower()) == name), None)
        if tier:
            return {**tier, 'checkedAt': checked, 'known': True}
    return {'id': None, 'name': 'League not captured', 'tier': None, 'points': None, 'checkedAt': None, 'known': False}


def league_week(stamp):
    """Ranked report weeks start Monday at 05:00 UTC, not phone local time."""
    value = datetime.fromisoformat(api_time(stamp).replace('Z','+00:00')) - timedelta(hours=5)
    value = (value - timedelta(days=value.weekday())).replace(hour=5, minute=0, second=0, microsecond=0)
    return value.isoformat(timespec='milliseconds').replace('+00:00','Z')


def merge_league_history(first, second):
    records = {}
    for sample in list(first or []) + list(second or []):
        if not isinstance(sample, dict) or not api_time(sample.get('at')) or not isinstance(sample.get('members'), list):
            continue
        at = api_time(sample['at'])
        key = at
        old = records.get(key)
        if not old or at >= api_time(old['at']):
            records[key] = copy.deepcopy(sample)
    return sorted(records.values(), key=lambda v: api_time(v['at']))


def capture_leadership(state):
    capture_progression(state)
    state.setdefault('leagueHistory', [])
    state['leaguePointScale'] = copy.deepcopy(LEAGUE_POINT_SCALE)
    at = api_time(state.get('lastSuccessfulSync'))
    if not at or not state.get('clanProfile'):
        return
    members = []
    for player in state.get('roster', []):
        tag = normalize_tag(player.get('tag'))
        profile = state.get('profiles', {}).get(tag) or {}
        progress = state.get('memberProgress', {}).get(tag) or {}
        members.append({'tag': tag, 'name': player.get('name') or tag,
                        'townHallLevel': player.get('townHallLevel') or profile.get('townHallLevel'),
                        'trophies': player.get('trophies') if integer(player.get('trophies')) else None,
                        'league': league_placement(player, profile, at, state.get('clanTag')),
                        'armyPercent': progress.get('percent'), 'profileAt': progress.get('at')})
    known = [p for p in members if p['league']['known']]
    sample = {'at': at, 'week': league_week(at), 'members': members,
              'points': sum(p['league']['points'] for p in known), 'known': len(known), 'count': len(members)}
    def signature(value):
        return (value.get('week'), [(p.get('tag'), p.get('name'), p.get('townHallLevel'), p.get('trophies'),
                (p.get('league') or {}).get('id'), (p.get('league') or {}).get('known'), p.get('armyPercent')) for p in value.get('members', [])])
    if not state['leagueHistory'] or signature(state['leagueHistory'][-1]) != signature(sample):
        state['leagueHistory'] = merge_league_history(state['leagueHistory'], [sample])
    league_fields = {'leaguePoints': sample['points'], 'leagueKnown': sample['known'], 'leagueMembers': sample['count']}
    latest = (state.get('clanHistory') or [None])[-1]
    if latest and api_time(latest.get('at')) == at:
        latest.update(league_fields)
    elif latest and any(latest.get(k) != v for k, v in league_fields.items()):
        state['clanHistory'] = merge_observations(state['clanHistory'], [{**latest, **league_fields, 'at': at}])


def normalize_lineup_edits(edits):
    plans=edits.setdefault('lineupPlans',{});drafts=edits.setdefault('lineupDrafts',{})
    for mode,plan in list(plans.items()):
        if not isinstance(plan,dict) or plan.get('deleted') or not isinstance(plan.get('tags'),list):
            continue
        allowed=(15,30) if mode=='CWL' else (5,10,15,20,25,30,40,50)
        options=plan.get('options') or {};size=len(plan['tags'])
        complete=size in allowed and (options.get('size')=='max' or str(options.get('size'))==str(size))
        if not complete and plan.get('committed') is not True:
            if not drafts.get(mode) or str(plan.get('updatedAt',''))>str(drafts[mode].get('updatedAt','')):
                drafts[mode]={**plan,'legacyDraft':True,'baseCommitId':None}
            plans[mode]={'deleted':True,'updatedAt':plan.get('updatedAt')}
        elif complete:
            plan['options']={**options,'size':str(size)};plan['committed']=True
            plan.setdefault('commitId',plan.get('updatedAt') or 'legacy')
    return edits


def validate_lineup_edits(edits):
    normalize_lineup_edits(edits)
    for category in ('lineupPlans','lineupDrafts'):
        for mode,plan in edits.get(category,{}).items():
            if mode not in ('Regular','CWL') or not isinstance(plan,dict):
                raise ValueError('Invalid saved war lineup.')
            if plan.get('deleted') is True:
                continue
            tags,options=plan.get('tags'),plan.get('options')
            if not isinstance(tags,list) or len(tags)>50 or any(not isinstance(t,str) or not re.fullmatch(r'#[0289PYLQGRJCUV]+',t) for t in tags) or len(set(tags))!=len(tags):
                raise ValueError('Invalid saved lineup participants.')
            if not isinstance(options,dict) or options.get('mode')!=mode or options.get('balance') not in ('representative','strength') or not isinstance(options.get('includeUnknown'),bool) or str(options.get('size')) not in ('max','5','10','15','20','25','30','40','50'):
                raise ValueError('Invalid saved lineup options.')
            if category=='lineupPlans' and (len(tags) not in ((15,30) if mode=='CWL' else (5,10,15,20,25,30,40,50)) or str(options.get('size'))!=str(len(tags))):
                raise ValueError('A committed lineup must match a supported team size.')


def new_state(clan_tag):
    return {'schemaVersion':1, 'clanTag':clan_tag, 'clanName':'Your clan', 'policyStart':now_iso(),
            'trackingStarted':False, 'roster':[], 'wars':[], 'leagueLookups':{},
            'edits':{'exceptions':{},'notes':{},'manualWars':{},'xpCheckpoints':{},'villageProgress':{},'lineupPlans':{},'lineupDrafts':{},'flagResolutions':{}}, 'warnings':[], 'lastSuccessfulSync':None,
            'clanProfile':{},'profiles':{},'raids':[],'activity':[],'leagueGroups':{},'leagueWarSummaries':{},'memberHistory':{},'honors':{},'leagueBadgeImages':{},'leagueHistory':[],'clanHistory':[],'memberProgressHistory':{},'memberProgress':{}}

def load_state(path, clan_tag):
    if not path.exists():
        return new_state(clan_tag)
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as error:
        raise ValueError('The saved tracker data cannot be read. Restore war_tracker_state.json.bak or your exported backup. The file has not been reset.') from error
    if state.get('schemaVersion') != 1 or normalize_tag(state.get('clanTag')) != clan_tag:
        raise ValueError('This state file belongs to another clan or an unsupported tracker version.')
    for key,value in {'clanProfile':{},'profiles':{},'raids':[],'activity':[],'leagueGroups':{},'leagueWarSummaries':{},'memberHistory':{},'honors':{},'leagueBadgeImages':{},'leagueHistory':[],'clanHistory':[],'memberProgressHistory':{},'memberProgress':{}}.items():
        state.setdefault(key,value)
    return state

def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    if path.exists():
        path.with_suffix(path.suffix + '.bak').write_bytes(path.read_bytes())
    temporary.replace(path)

def normalize_war(raw, clan_tag, kind='Regular', war_tag=None):
    home, enemy = raw.get('clan') or {}, raw.get('opponent') or {}
    if normalize_tag(home.get('tag')) != clan_tag:
        if normalize_tag(enemy.get('tag')) != clan_tag:
            return None
        home, enemy = enemy, home
    ended = api_time(raw.get('endTime'))
    observed = now_iso()
    if not ended or raw.get('state') == 'notInWar':
        return None
    attacks_allowed = raw.get('attacksPerMember', 1 if kind == 'CWL' else 2)
    if kind == 'Regular' and (attacks_allowed != 2 or raw.get('type') == 'friendly'):
        kind = 'Friendly'
    members, size = home.get('members'), raw.get('teamSize')
    complete = isinstance(members, list) and integer(size) and size > 0 and len(members) == size
    participants, seen, attack_orders, capture_issues = [], set(), set(), []
    for member in members or []:
        if not isinstance(member, dict):
            complete = False
            capture_issues.append('A participant record is invalid.')
            continue
        member_tag = normalize_tag(member.get('tag'))
        attacks = member.get('attacks', [])
        valid_attacks = isinstance(attacks, list) and integer(attacks_allowed) and len(attacks) <= attacks_allowed
        if valid_attacks:
            for attack in attacks:
                if not isinstance(attack, dict) or not integer(attack.get('stars')) or not 0 <= attack['stars'] <= 3:
                    valid_attacks = False
                    break
                destruction = attack.get('destructionPercentage')
                if destruction is not None and (isinstance(destruction, bool) or not isinstance(destruction, (int, float)) or not 0 <= destruction <= 100):
                    valid_attacks = False
                    break
                order = attack.get('order')
                if order is not None:
                    if not integer(order) or order in attack_orders:
                        valid_attacks = False
                        break
                    attack_orders.add(order)
        if not member_tag or member_tag in seen or not valid_attacks:
            complete = False
        seen.add(member_tag)
        participants.append({'tag':member_tag,'name':str(member.get('name') or member_tag),
            'townHallLevel':member.get('townhallLevel',member.get('townHallLevel')),
            'mapPosition':member.get('mapPosition'), 'attacksUsed':len(attacks) if valid_attacks else None,
            'starsEarned':sum(a.get('stars',0) for a in attacks if isinstance(a,dict)) if valid_attacks else None,
            'attacks':attacks if valid_attacks else [],'defenseCount':member.get('defenseCount'),
            'bestOpponentAttack':member.get('bestOpponentAttack')})
    reported_attacks = home.get('attacks')
    if reported_attacks is not None and (not integer(reported_attacks) or
            any(p['attacksUsed'] is None for p in participants) or
            reported_attacks != sum(p['attacksUsed'] for p in participants)):
        complete = False
        capture_issues.append('Clan attack total does not match the captured participant attacks. Refresh final details before reviewing attendance.')
    identity = ('cwl:' + normalize_tag(war_tag)) if kind == 'CWL' and war_tag else kind.lower() + ':' + clan_tag + ':' + ended
    return {'id':identity,'kind':kind,'warTag':war_tag,'state':raw.get('state'),
        'endTime':ended,'startTime':api_time(raw.get('startTime')),'preparationStartTime':api_time(raw.get('preparationStartTime')),
        'opponent':{'tag':normalize_tag(enemy.get('tag')),'name':str(enemy.get('name') or 'Unknown opponent')},
        'teamSize':size,'attacksPerMember':attacks_allowed,'stars':home.get('stars'),
        'expEarned':home.get('expEarned') if integer(home.get('expEarned')) and home['expEarned'] >= 0 else None,
        'opponentStars':enemy.get('stars'),'destruction':home.get('destructionPercentage'),
        'opponentDestruction':enemy.get('destructionPercentage'),
        'opponentMembers':[{'tag':normalize_tag(m.get('tag')),'name':m.get('name'),'townHallLevel':m.get('townhallLevel',m.get('townHallLevel')),'mapPosition':m.get('mapPosition')} for m in (enemy.get('members') or [])],
        'participants':participants,'rosterComplete':complete,'final':raw.get('state') == 'warEnded' and complete and datetime.fromisoformat(observed.replace('Z','+00:00')) >= datetime.fromisoformat(ended.replace('Z','+00:00')),
        'reportedAttacks':reported_attacks,'captureIssues':capture_issues,
        'source':'API','observedAt':observed}

def same_api_war(a, b):
    """A revised deadline must not create a second copy of one API war."""
    if a.get('source') != 'API' or b.get('source') != 'API' or a.get('kind') != b.get('kind'):
        return False
    if a.get('warTag') or b.get('warTag'):
        return bool(a.get('warTag') and a.get('warTag') == b.get('warTag'))
    opponent = normalize_tag((a.get('opponent') or {}).get('tag'))
    if not opponent or opponent != normalize_tag((b.get('opponent') or {}).get('tag')):
        return False
    prepared = api_time(a.get('preparationStartTime') or a.get('startTime'))
    return bool(prepared and prepared == api_time(b.get('preparationStartTime') or b.get('startTime')))


def store_war(state, war):
    if not war:
        return
    if not state.get('trackingStarted') and war['kind'] == 'Regular':
        state['policyStart'], state['trackingStarted'] = war['endTime'], True
    matches = [w for w in state['wars'] if w['id'] == war['id'] or same_api_war(w, war)]
    if any(w.get('final') for w in matches) and not war.get('final'):
        # A fresh API deadline revision can re-arm a prematurely finalized war.
        revised = any(same_api_war(old, war) and war.get('endTime') != old.get('endTime')
                      and str(war.get('observedAt', '')) >= str(old.get('observedAt', '')) for old in matches)
        invalid_prior = all(old.get('source') == 'API' and (str(old.get('observedAt', '')) < str(old.get('endTime', ''))) for old in matches if old.get('final'))
        if not revised and not invalid_prior:
            return
    if matches:
        # Retain the original key so saved exceptions and other references still apply.
        war = {**war, 'id': matches[0]['id']}
        state['wars'] = [w for w in state['wars'] if w not in matches]
    state['wars'].append(war)

def add_summaries(state, payload):
    known = {w['id'] for w in state['wars']}
    for raw in payload.get('items', []):
        enemy = raw.get('opponent') or {}
        ended = api_time(raw.get('endTime'))
        # League-season summaries have no enemy clan. Single-attack friendly wars are not regular wars.
        if not ended or not enemy.get('tag') or raw.get('attacksPerMember') != 2:
            continue
        identity = 'regular:' + state['clanTag'] + ':' + ended
        existing = next((w for w in state['wars'] if w['id'] == identity or (w.get('kind') == 'Regular'
            and w.get('source') == 'API' and api_time(w.get('endTime')) == ended
            and normalize_tag((w.get('opponent') or {}).get('tag')) == normalize_tag(enemy.get('tag')))), None)
        if existing is not None:
            xp = (raw.get('clan') or {}).get('expEarned')
            if integer(xp) and xp >= 0: existing['expEarned'] = xp
            continue
        state['wars'].append({'id':identity,'kind':'Regular','state':'warEnded','endTime':ended,
            'opponent':{'tag':normalize_tag(enemy.get('tag')),'name':enemy.get('name','Unknown opponent')},
            'teamSize':raw.get('teamSize'),'attacksPerMember':2,'stars':(raw.get('clan') or {}).get('stars'),
            'opponentStars':enemy.get('stars'),'result':raw.get('result'),'expEarned':(raw.get('clan') or {}).get('expEarned'),'participants':[],
            'rosterComplete':False,'final':False,'source':'War-log summary','observedAt':now_iso()})
        known.add(identity)

def event(state, player_tag, player_name, message, kind):
    state['activity'].append({'tag':player_tag,'name':player_name,'message':message,'kind':kind,'detectedAt':now_iso()})
    state['activity'] = state['activity'][-300:]

def compare_profile(state, old, current):
    if not old:
        return
    ptag,pname=normalize_tag(current.get('tag')),str(current.get('name') or current.get('tag'))
    for field,label in [('warStars','lifetime war stars'),('attackWins','season attack wins'),
                        ('clanCapitalContributions','lifetime Capital contributions'),('townHallLevel','Town Hall level')]:
        before,after=old.get(field),current.get(field)
        if integer(before) and integer(after) and after>before:
            event(state,ptag,pname,'+'+str(after-before)+' '+label+' observed.','Progress')
    for field,label in [('heroes','Hero'),('heroEquipment','Equipment'),('troops','Troop / pet'),('spells','Spell')]:
        previous={(v.get('name'),v.get('village')):v.get('level') for v in (old.get(field) or []) if isinstance(v,dict)}
        for item in (current.get(field) or []):
            if not isinstance(item,dict):
                continue
            before,after=previous.get((item.get('name'),item.get('village'))),item.get('level')
            if integer(before) and integer(after) and after>before:
                event(state,ptag,pname,label+' '+str(item.get('name'))+': level '+str(before)+' to '+str(after)+' detected.','Upgrade')

def store_raids(state, payload):
    if not isinstance(payload.get('items'),list):
        raise ValueError('The raid response is incomplete.')
    raids={r['id']:r for r in state['raids']}
    for raw in payload['items']:
        start,end=api_time(raw.get('startTime')),api_time(raw.get('endTime'))
        if not start or not end:
            continue
        raid=copy.deepcopy(raw)
        raid.update(id='raid:'+state['clanTag']+':'+start,startTime=start,endTime=end,observedAt=now_iso())
        saved=raids.get(raid['id'],{})
        if saved.get('members') and not raid.get('members') and api_time(saved.get('startTime'))==start:
            raid['members']=copy.deepcopy(saved['members'])
            if saved.get('membersRecoveredFrom'):
                raid['membersRecoveredFrom']=saved['membersRecoveredFrom']
        raids[raid['id']]=raid
    state['raids']=sorted(raids.values(),key=lambda r:r['startTime'])
    state['lastRaidSync']=now_iso()

def league_summary(raw,war_tag):
    if not api_time(raw.get('endTime')) or not (raw.get('clan') or {}).get('tag'):
        return None
    def side(value):
        return {k:value.get(k) for k in ('tag','name','stars','attacks','destructionPercentage')}
    return {'warTag':war_tag,'state':raw.get('state'),'endTime':api_time(raw.get('endTime')),
            'clan':side(raw.get('clan') or {}),'opponent':side(raw.get('opponent') or {})}

def merge_edits(first, second):
    result = copy.deepcopy(first or {})
    for field in ('exceptions','notes','manualWars','xpCheckpoints','villageProgress','lineupPlans','lineupDrafts','flagResolutions'):
        result.setdefault(field,{})
        for key, value in (second or {}).get(field,{}).items():
            if not isinstance(value,dict):
                raise ValueError('Invalid tracker edit.')
            if not result[field].get(key) or str(value.get('updatedAt','')) >= str(result[field][key].get('updatedAt','')):
                result[field][key] = value
    return normalize_lineup_edits(result)

def apply_edits(state, path):
    return apply_snapshot(state,json.loads(path.read_text(encoding='utf-8')))

def apply_snapshot(state,payload):
    if normalize_tag(payload.get('clanTag')) != state['clanTag']:
        raise ValueError('The imported edits belong to another clan.')
    edits = payload.get('edits')
    if not isinstance(edits,dict):
        raise ValueError('This file does not contain tracker edits.')
    for field in ('exceptions','notes','manualWars','xpCheckpoints','villageProgress','lineupPlans','lineupDrafts','flagResolutions'):
        if not isinstance(edits.get(field,{}),dict):
            raise ValueError('Invalid tracker edit collection.')
    validate_progress_edits(edits)
    validate_lineup_edits(edits)
    for key,w in edits.get('manualWars',{}).items():
        if w.get('deleted'):
            continue
        allowed = 1 if w.get('kind') == 'CWL' else 2
        members = w.get('participants')
        if w.get('kind') not in ('Regular','CWL') or not api_time(w.get('endTime')) or not isinstance(members,list) or not members:
            raise ValueError('Invalid manually entered war.')
        seen = set()
        for member in members:
            ptag = normalize_tag(member.get('tag'))
            if not ptag or ptag in seen or not integer(member.get('attacksUsed')) or not 0 <= member['attacksUsed'] <= allowed:
                raise ValueError('Invalid manual attack count or duplicate player.')
            seen.add(ptag)
        w.update(id=key,final=True,rosterComplete=True,state='warEnded',source='Manual',attacksPerMember=allowed)
    if payload.get('schemaVersion') == 1:
        recruiter=payload.get('recruiter')
        if recruiter is not None:
            if not isinstance(recruiter,dict) or recruiter.get('format')!=1 or not isinstance(recruiter.get('files'),dict) or not isinstance(recruiter.get('report'),dict) or not api_time(recruiter.get('updatedAt')):
                raise ValueError('Invalid recruiter archive. Saved recruiting history was not reset.')
            prior_recruiter=state.get('recruiter') or {}
            if (api_time(recruiter.get('updatedAt')) or '') >= (api_time(prior_recruiter.get('updatedAt')) or ''):
                state['recruiter']=copy.deepcopy(recruiter)
                state['recruiterSummary']=copy.deepcopy(recruiter.get('summary',{}))
        recruiter_status=payload.get('recruiterStatus')
        if isinstance(recruiter_status,dict) and (api_time(recruiter_status.get('lastAttemptAt')) or '') >= (api_time((state.get('recruiterStatus') or {}).get('lastAttemptAt')) or ''):
            state['recruiterStatus']=copy.deepcopy(recruiter_status)
        newer=(api_time(payload.get('lastSuccessfulSync')) or '')>(api_time(state.get('lastSuccessfulSync')) or '')
        if newer:
            for field in ('roster','clanName','clanProfile','lastSuccessfulSync','lastRaidSync','keyInfo','automaticUpdates','sharedActions'):
                if field in payload:
                    state[field]=copy.deepcopy(payload[field])
        for field in ('wars','raids'):
            stored={v['id']:v for v in state.get(field,[])}
            for value in payload.get(field,[]):
                if not isinstance(value,dict) or not value.get('id'):
                    raise ValueError('Invalid archived data in the backup.')
                old=stored.get(value['id'])
                if not old or (not old.get('final') and value.get('final')) or (old.get('final')==value.get('final') and (api_time(value.get('observedAt')) or '')>(api_time(old.get('observedAt')) or '')):
                    merged=copy.deepcopy(value)
                    if field=='raids' and old and old.get('members') and not merged.get('members') and api_time(old.get('startTime'))==api_time(merged.get('startTime')):
                        merged['members']=copy.deepcopy(old['members'])
                        if old.get('membersRecoveredFrom'):merged['membersRecoveredFrom']=old['membersRecoveredFrom']
                    stored[value['id']]=merged
            state[field]=list(stored.values())
        for ptag,profile in payload.get('profiles',{}).items():
            old=state['profiles'].get(ptag)
            if not old or (api_time(profile.get('profileCheckedAt')) or '')>(api_time(old.get('profileCheckedAt')) or ''):
                state['profiles'][ptag]=copy.deepcopy(profile)
        starts=[api_time(v) for v in (state.get('policyStart'),payload.get('policyStart')) if api_time(v)]
        if starts:state['policyStart']=min(starts)
        state['trackingStarted']=bool(state.get('trackingStarted') or payload.get('trackingStarted'))
        for key,record in payload.get('honors',{}).items():
            if isinstance(record,dict):
                old=state.setdefault('honors',{}).get(key)
                if not old or (api_time(record.get('observedAt')) or '')<(api_time(old.get('observedAt')) or ''):
                    state['honors'][key]=copy.deepcopy(record)
        state['leagueBadgeImages']={**payload.get('leagueBadgeImages',{}),**state.get('leagueBadgeImages',{})}
        # Preserve completed negative lookups across authenticated archive restores.
        recovery=state.setdefault('raidMemberRecovery',{})
        for raid_id,marker in payload.get('raidMemberRecovery',{}).items():
            if isinstance(marker,(str,dict)):
                old=recovery.get(raid_id)
                if old is None or isinstance(marker,dict) and (not isinstance(old,dict) or marker.get('at','')>old.get('at','')):
                    recovery[raid_id]=copy.deepcopy(marker)
        state['memberHistory']=merge_member_history(state.get('memberHistory'),payload.get('memberHistory'))
        state['leagueHistory']=merge_league_history(state.get('leagueHistory'),payload.get('leagueHistory'))
        state['clanHistory']=merge_observations(state.get('clanHistory'),payload.get('clanHistory'))
        for tag, records in payload.get('memberProgressHistory',{}).items():
            state.setdefault('memberProgressHistory',{})[tag]=merge_observations(state.get('memberProgressHistory',{}).get(tag),records)
        for field in ('leagueGroups','leagueWarSummaries','leagueLookups'):
            state[field]={**payload.get(field,{}),**state.get(field,{})}
    state['edits'] = merge_edits(state.get('edits'),edits)
    if payload.get('schemaVersion') == 1:
        # Progress is derived from the merged profiles, not archive metadata.
        # Recruiter-only and code-only publications restore here without a
        # clan refresh; they must retain the same army results and timestamps.
        capture_progression(state)

HARD_ACHIEVEMENTS = {'war hero','league master','friend in need','sharing is caring','games champion',
                     'aggressive capitalism','most valuable clanmate','unbreakable','conqueror','heroic heist',
                     'gold grab','elixir escapade'}

def record_profile_honors(state, old, profile):
    """Honor a lifetime threshold only when it is crossed during a clan stint."""
    ptag=normalize_tag(profile.get('tag'))
    if not ptag:
        return
    observed=api_time(profile.get('profileCheckedAt')) or now_iso()
    previous=api_time((old or {}).get('profileCheckedAt'))
    history=state.get('memberHistory',{}).get(ptag) or {}
    since=api_time(history.get('since'))
    clan_tag=normalize_tag(state.get('clanTag'))
    # The first profile is a baseline, including on a return to the clan. A
    # profile observed outside this clan also breaks the comparison window.
    if (not previous or previous>=observed or not since or previous<since
            or history.get('inClan') is False
            or not any(normalize_tag(p.get('tag'))==ptag for p in state.get('roster',[]))
            or normalize_tag((old or {}).get('tag'))!=ptag
            or normalize_tag(((old or {}).get('clan') or {}).get('tag'))!=clan_tag
            or normalize_tag((profile.get('clan') or {}).get('tag'))!=clan_tag):
        return
    ledger=state.setdefault('honors',{})
    def add(key,title,detail,category,priority,already):
        if already:
            return
        identity=ptag+'::'+key
        if identity in ledger and ledger[identity].get('alreadyReached') is False:
            ledger[identity]['name']=str(profile.get('name') or ptag)
            return
        ledger[identity]={'id':identity,'tag':ptag,'name':str(profile.get('name') or ptag),'title':title,
                         'detail':detail,'category':category,'priority':priority,'observedAt':observed,
                         'alreadyReached':False,'previousObservedAt':previous,
                         'earnedInClan':True,'clanTag':clan_tag,'membershipSince':since,
                         'source':'Saved API profile'}
    for field,levels,title,category in [
        ('warStars',[1000,2500,5000,10000,20000],'Lifetime war stars','War'),
        ('clanCapitalContributions',[1000000,5000000,10000000,25000000],'Lifetime Capital Gold contributed','Capital')]:
        value=profile.get(field);before=(old or {}).get(field)
        if not integer(value) or value<0:
            continue
        for index,level in enumerate(levels):
            if value>=level:
                add(field+':'+str(level),format(level,',')+' '+title.lower(),format(value,',')+' verified in the saved lifetime profile.','War' if field=='warStars' else category,80+index*5,not integer(before) or before>=level)
    old_achievements={(a.get('name','').casefold(),a.get('village','home')):a for a in (old or {}).get('achievements',[]) if isinstance(a,dict)}
    for achievement in profile.get('achievements',[]):
        if not isinstance(achievement,dict):
            continue
        name=str(achievement.get('name',''));stars=achievement.get('stars');value=achievement.get('value');target=achievement.get('target')
        key=(name.casefold(),achievement.get('village','home'));prior=old_achievements.get(key,{})
        if name.casefold() in HARD_ACHIEVEMENTS and integer(stars) and stars>=3 and integer(value) and integer(target) and target>0 and value>=target:
            add('achievement:'+key[1]+':'+name.casefold(),name+' • three stars',
                str(achievement.get('completionInfo') or achievement.get('info') or 'All three stars recorded.')+' · '+format(value,',')+' / '+format(target,','),'Game achievement',90,not integer(prior.get('stars')) or prior.get('stars',0)>=3)
        for index,level in enumerate([100000,250000,1000000] if name.casefold()=='friend in need' else [1000000,5000000,10000000,25000000,100000000,500000000,1000000000,5000000000] if name.casefold() in ('gold grab','elixir escapade') else []):
            if integer(value) and value>=level:
                before=prior.get('value')
                label='lifetime troops donated' if name.casefold()=='friend in need' else 'lifetime gold looted' if name.casefold()=='gold grab' else 'lifetime elixir looted'
                add('counter:'+name.casefold()+':'+str(level),format(level,',')+' '+label,format(value,',')+' verified in '+name+'.','Donations' if name.casefold()=='friend in need' else 'Game achievement',100+index*5,not integer(before) or before>=level)
    tier=profile.get('leagueTier') or profile.get('league') or {};previous=(old or {}).get('leagueTier') or (old or {}).get('league') or {}
    league=str(tier.get('name',''));old_league=str(previous.get('name',''))
    if re.match(r'^Legend\b',league,re.I):
        add('ranked:legend','Legend League reached',league+' recorded in the profile.','Ranked',110,not old_league or bool(re.match(r'^Legend\b',old_league,re.I)))
    for field,category,minimum in [('heroes','Heroes & equipment',50),('heroEquipment','Heroes & equipment',27)]:
        before={(v.get('name'),v.get('village','home')):v for v in (old or {}).get(field,[]) if isinstance(v,dict)}
        for item in profile.get(field,[]):
            if not isinstance(item,dict) or item.get('village','home')!='home':
                continue
            level,maximum=item.get('level'),item.get('maxLevel');name=str(item.get('name') or '')
            if name and integer(level) and integer(maximum) and maximum>=minimum and level==maximum:
                prior=before.get((name,'home'),{})
                already=not integer(prior.get('level')) or prior.get('level',0)>=maximum
                add(field+':'+name+':'+str(maximum),name+' • level '+str(maximum),
                    'Reached the API-reported maximum of '+str(maximum)+' at this snapshot. Future updates may raise the cap.',category,95,already)

def safe_league_icon(value):
    if not isinstance(value,str):
        return False
    parsed=urlparse(value)
    return not parsed.fragment and parsed.scheme=='https' and parsed.netloc=='api-assets.clashofclans.com' and parsed.path.startswith(('/leaguetiers/','/leagues/')) and parsed.path.endswith('.png') and not parsed.query

def cache_league_badges(state):
    cache=state.setdefault('leagueBadgeImages',{})
    urls=set();active_urls=set()
    active_tags={p.get('tag') for p in state.get('roster',[])}
    for source in state.get('roster',[])+list(state.get('profiles',{}).values()):
        league=source.get('leagueTier') or source.get('league') or {}
        icons=league.get('iconUrls') or {}
        url=icons.get('small') or icons.get('medium') or icons.get('large')
        if safe_league_icon(url):
            urls.add(url)
            if source.get('tag') in active_tags:
                active_urls.add(url)
    failures=state.setdefault('leagueBadgeFailures',{})
    def fetch(url):
        # Public images never receive the clan API token. Validate redirects too.
        with urlopen(Request(url,headers={'Accept':'image/png','User-Agent':'Clash-War-Tracker/'+VERSION}),timeout=8) as response:
            if not safe_league_icon(response.geturl()):
                raise ValueError('Unexpected icon redirect.')
            raw=response.read(262145)
            if len(raw)>262144 or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('Invalid league image.')
        return 'data:image/png;base64,'+base64.b64encode(raw).decode('ascii')
    pending_urls=[url for url in sorted(urls) if url not in cache and time.time()-failures.get(url,0)>=3600]
    if pending_urls:
        with ThreadPoolExecutor(max_workers=4) as pool:
            pending={pool.submit(fetch,url):url for url in pending_urls}
            for future in as_completed(pending):
                url=pending[future]
                try:
                    cache[url]={'dataUrl':future.result(),'fetchedAt':now_iso()};failures.pop(url,None)
                except (OSError,ValueError):
                    failures[url]=time.time()
    # Retain current badges first, with a bounded cache for saved history.
    keep=sorted(cache,key=lambda url:(url in active_urls,str(cache[url].get('fetchedAt',''))),reverse=True)[:48]
    state['leagueBadgeImages']={url:cache[url] for url in keep}
    state['leagueBadgeFailures']={url:stamp for url,stamp in failures.items() if url in urls}

def merge_member_history(first, second):
    result=copy.deepcopy(first or {})
    latest=lambda record:max(api_time(record.get('lastSeen')) or '',api_time(record.get('leftAt')) or '')
    for ptag,entry in (second or {}).items():
        if not isinstance(entry,dict):
            continue
        old=result.get(ptag)
        if not old:
            result[ptag]=copy.deepcopy(entry)
            continue
        # Combine individual stints, rather than adding running totals on import.
        stints={}
        for record in [*old.get('pastStints',[]),old,*entry.get('pastStints',[]),entry]:
            if not isinstance(record,dict) or not api_time(record.get('since')):
                continue
            key=api_time(record['since']);prior=stints.get(key)
            combined=copy.deepcopy(record if not prior or latest(record)>latest(prior) else prior)
            combined.pop('pastStints',None)
            if prior:
                for field in ('donationIntervals','capitalSamples'):
                    values={json.dumps(v,sort_keys=True):v for v in prior.get(field,[])+record.get(field,[]) if isinstance(v,dict)}
                    combined[field]=sorted(values.values(),key=lambda v:v.get('at',v.get('end','')))
            stints[key]=combined
        current=entry if latest(entry)>latest(old) else old
        key=api_time(current.get('since'))
        combined=copy.deepcopy(stints.pop(key, current))
        combined['pastStints']=sorted(stints.values(),key=lambda v:v['since'])
        result[ptag]=combined
    return result

def record_capital_sample(entry, profile, clan_tag):
    """A matched profile is a baseline; only later matched increases earn credit."""
    if not isinstance(profile,dict):
        return
    checked=api_time(profile.get('profileCheckedAt'))
    since=api_time(entry.get('since'));last_seen=api_time(entry.get('lastSeen'))
    if not checked or not since or checked<since or (last_seen and checked>last_seen):
        return
    samples=entry.setdefault('capitalSamples',[])
    if samples and checked<=max(v.get('at','') for v in samples):
        return
    total=profile.get('clanCapitalContributions')
    eligible=normalize_tag((profile.get('clan') or {}).get('tag'))==clan_tag and integer(total) and total>=0
    # A fresh profile outside this clan breaks continuity. Rejoining gets a new
    # baseline even if the brief departure was missed by the roster scan.
    samples.append({'at':checked,'total':total if eligible else None})

def update_member_history(state, prior, roster, observed_at, previous_profiles=None, roster_observed_at=None):
    """Track evidence from successful scans; never claim exact join/donation times."""
    stamp=api_time(observed_at)
    history=state.setdefault('memberHistory',{})
    previous=api_time(state.get('lastSuccessfulSync'))
    current={p['tag'] for p in roster}
    for player in roster:
        ptag=player['tag'];old=prior.get(ptag);entry=history.get(ptag)
        continuous=bool(old and (not entry or entry.get('inClan') is not False))
        # A observed departure and return starts a new stint and donation baseline.
        if not entry or not old or entry.get('inClan') is False:
            past=copy.deepcopy((entry or {}).get('pastStints',[]))
            if entry:
                archived=copy.deepcopy(entry);archived.pop('pastStints',None)
                past.append(archived)
            since=previous if old and previous and not (entry or {}).get('leftAt') else (api_time(roster_observed_at) or stamp)
            role_since=since if old and old.get('role')==player.get('role') else stamp
            entry={'since':since,'firstEverObserved':(entry or {}).get('firstEverObserved',since),
                   'roleSince':role_since,'role':player.get('role'),'donationIntervals':[],
                   'capitalSamples':[],'pastStints':past,'donationTrackingSince':since}
            history[ptag]=entry
        if entry.get('role')!=player.get('role'):
            entry['roleSince']=stamp
        entry.update(inClan=True,lastSeen=stamp,role=player.get('role'),name=player.get('name'))
        entry.pop('leftAt',None)
        # Older releases kept only 90 days of troop donation windows. Preserve
        # all future windows, and label the earliest evidence that still exists.
        retained=[api_time(v.get('start')) for v in entry.get('donationIntervals',[]) if api_time(v.get('start'))]
        entry.setdefault('donationTrackingSince',min(retained) if retained else (previous if old and previous else stamp))
        record_capital_sample(entry,(previous_profiles or {}).get(ptag),state['clanTag'])
        record_capital_sample(entry,state.get('profiles',{}).get(ptag),state['clanTag'])
        before=(old or {}).get('donations');after=player.get('donations')
        if continuous and previous and previous<stamp and integer(before) and integer(after) and before>=0 and after>=0:
            # A decreased counter establishes a new-season floor; never add the old total again.
            delta=after-before if after>=before else after
            if delta>0:
                entry['donationIntervals'].append({'start':previous,'end':stamp,'count':delta})
    for ptag in prior:
        if ptag not in current:
            entry=history.setdefault(ptag,{'since':previous or stamp,'roleSince':previous or stamp,'donationIntervals':[]})
            entry.update(inClan=False,leftAt=stamp,lastSeen=entry.get('lastSeen') or previous)

def refresh(state, api, profiles=True):
    warnings, clan_tag = [], state['clanTag']
    clan_path = '/clans/' + quote(clan_tag, safe='')
    print('Loading clan roster and war data...')
    clan = api.get(clan_path)
    if normalize_tag(clan.get('tag')) != clan_tag or not isinstance(clan.get('memberList'),list):
        raise ValueError('The clan roster response is incomplete. Saved members were not changed.')
    members = clan['memberList']
    if not 1 <= len(members) <= 50 or ('members' in clan and (not integer(clan['members']) or clan['members'] != len(members))):
        raise ValueError('The clan roster count is incomplete. Saved members were not changed.')
    roster_tags = [normalize_tag(p.get('tag')) if isinstance(p, dict) else '' for p in members]
    if any(not re.fullmatch(r'#[0289PYLQGRJCUV]{3,20}', tag) for tag in roster_tags) or len(set(roster_tags)) != len(roster_tags):
        raise ValueError('The clan roster has invalid or duplicate player tags. Saved members were not changed.')
    roster_observed_at=now_iso()
    prior = {p['tag']:p for p in state['roster']}
    previous_profiles=copy.deepcopy(state.get('profiles',{}))
    roster = []
    for item in clan['memberList']:
        member = dict(item)
        member['tag'] = normalize_tag(member.get('tag'))
        if not member['tag']:
            raise ValueError('The roster contains a player without a tag. Saved members were not changed.')
        old = prior.get(member['tag'],{})
        for field in ('warPreference','warPreferenceCheckedAt'):
            if field in old:
                member[field] = old[field]
        member['name'] = str(member.get('name') or member['tag'])
        roster.append(member)
    if prior:
        current_tags={p['tag'] for p in roster}
        for p in roster:
            old=prior.get(p['tag'])
            if not old:
                event(state,p['tag'],p['name'],'First observed in the clan roster.','Joined')
            elif old.get('name') != p.get('name'):
                event(state,p['tag'],p['name'],'Name changed from '+str(old.get('name'))+'.','Name')
            if old and old.get('role') != p.get('role'):
                event(state,p['tag'],p['name'],'Role changed to '+str(p.get('role'))+'.','Role')
            if old and integer(p.get('donations')) and integer(old.get('donations')) and p['donations']>old['donations']:
                event(state,p['tag'],p['name'],'+'+str(p['donations']-old['donations'])+' donations observed.','Donations')
        for ptag,old in prior.items():
            if ptag not in current_tags:
                event(state,ptag,old.get('name',ptag),'No longer in the clan roster at this scan.','Left')
    if profiles and roster:
        print('Loading player profiles, preferences, and progression...')
        failures = []
        def profile(player):
            checked = api_time(player.get('warPreferenceCheckedAt'))
            saved_profile = state['profiles'].get(player['tag']) or {}
            compatible = saved_profile.get('townHallLevel') == player.get('townHallLevel') and isinstance(saved_profile.get('troops'), list) and isinstance(saved_profile.get('heroes'), list)
            if compatible and checked and (datetime.now(timezone.utc) - datetime.fromisoformat(checked.replace('Z','+00:00'))).total_seconds() < 900:
                return None
            return api.get('/players/' + quote(player['tag'],safe=''))
        with ThreadPoolExecutor(max_workers=5) as pool:
            pending = {pool.submit(profile,p):p for p in roster}
            for future in as_completed(pending):
                player = pending[future]
                try:
                    result = future.result()
                    if result:
                        compare_profile(state,state['profiles'].get(player['tag']),result)
                        result['profileCheckedAt']=now_iso()
                        record_profile_honors(state,state['profiles'].get(player['tag']),result)
                        state['profiles'][player['tag']]=result
                        player['warPreferenceCheckedAt']=now_iso()
                        if result.get('warPreference') in ('in','out'):
                            player['warPreference'] = result['warPreference']
                except APIError as error:
                    failures.append((player['tag'],player['name'],str(error)))
        if failures:
            details='; '.join(name+' ('+tag+'): '+error for tag,name,error in sorted(failures))
            warnings.append(str(len(failures)) + ' player profile lookups failed after available retries. Saved profiles were retained. Failed players: ' + details)
    for player in roster:
        saved=state['profiles'].get(player['tag'])
        if saved:
            record_profile_honors(state,saved,saved)
    update_member_history(state,prior,roster,now_iso(),previous_profiles,roster_observed_at)
    state['roster'], state['clanName'] = roster, str(clan.get('name') or clan_tag)
    state['clanProfile']=clan
    if clan.get('isWarLogPublic') is False:
        warnings.append('The clan war log is private. Make it public in Clash to allow regular-war data access.')
    try:
        raw = api.get(clan_path + '/currentwar')
        store_war(state,normalize_war(raw,clan_tag))
    except APIError as error:
        warnings.append('Current regular war: ' + str(error))
    try:
        add_summaries(state,api.get(clan_path + '/warlog?limit=50'))
    except APIError as error:
        warnings.append('Regular war history: ' + str(error))
    try:
        store_raids(state,api.get(clan_path + '/capitalraidseasons?limit=10'))
    except (APIError,ValueError) as error:
        warnings.append('Clan Capital raids: ' + str(error))
    try:
        group = api.get(clan_path + '/currentwar/leaguegroup')
        if group.get('season'):
            state['leagueGroups'][group['season']]=group
        for round_data in group.get('rounds',[]):
            for war_tag in round_data.get('warTags',[]):
                if not war_tag or war_tag == '#0':
                    continue
                lookup = state['leagueLookups'].get(war_tag)
                group_summary=state['leagueWarSummaries'].get(war_tag)
                if group_summary and group_summary.get('state') == 'warEnded' and lookup == 'other':
                    continue
                saved = next((w for w in state['wars'] if w.get('warTag') == war_tag),None)
                if saved and saved.get('final') and saved.get('observedAt') and datetime.fromisoformat(saved['observedAt'].replace('Z','+00:00')) >= datetime.fromisoformat(saved['endTime'].replace('Z','+00:00')) + timedelta(minutes=5) and datetime.fromisoformat(saved['endTime'].replace('Z','+00:00')) < datetime.now(timezone.utc) - timedelta(days=1):
                    continue
                try:
                    raw = api.get('/clanwarleagues/wars/' + quote(war_tag,safe=''))
                    summary=league_summary(raw,war_tag)
                    if summary:
                        state['leagueWarSummaries'][war_tag]=summary
                    war = normalize_war(raw,clan_tag,'CWL',war_tag)
                    if war:
                        state['leagueLookups'][war_tag] = 'ours'
                        store_war(state,war)
                    elif (raw.get('clan') or {}).get('tag') and (raw.get('opponent') or {}).get('tag'):
                        state['leagueLookups'][war_tag] = 'other'
                except APIError as error:
                    warnings.append('A CWL round could not be refreshed: ' + str(error))
                    continue
    except APIError as error:
        if error.status != 404:
            warnings.append('CWL group: ' + str(error))
    state['wars'].sort(key=lambda w:w.get('endTime',''))
    state['lastSuccessfulSync'],state['warnings'] = now_iso(),warnings
    capture_leadership(state)
    cache_league_badges(state)
    state['keyInfo']={'configured':len(api.tokens),'activeNumber':api.preferred+1} if hasattr(api,'tokens') else {}

def preview_html(state):
    """Read-only saved data remains visible when a file preview blocks JavaScript."""
    esc = lambda value: html_module.escape(str(value if value is not None else '—'))
    def number(value):
        return format(value, ',') if isinstance(value, (int,float)) else '—'
    def table(headers, values):
        return '<div class="table-scroll"><table><thead><tr>' + ''.join('<th>'+esc(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in values) + '</tbody></table></div>'
    def panel(title, contents, identity):
        return '<section class="panel" id="preview-'+identity+'"><h2>'+esc(title)+'</h2>'+contents+'</section>'
    roster, clan = state.get('roster',[]), state.get('clanProfile',{})
    sync = state.get('lastSuccessfulSync')
    out = '<div class="panel"><div class="eyebrow" style="color:#946010">Clash of Clans · saved preview</div><h1>'+esc(state.get('clanName') or 'Clan Dashboard')+'</h1><p>'+esc(state.get('clanTag'))+' · '+('Updated '+esc(sync) if sync else 'No successful API refresh yet')+'</p><p>This viewer has not started the interactive dashboard. Run Clash_War_Tracker.py in Pyto to open its browser view. The saved data below is read-only.</p><nav class="toolbar"><a class="link" href="#preview-roster">Roster</a><a class="link" href="#preview-current">Current wars</a><a class="link" href="#preview-capital">Clan Capital</a><a class="link" href="#preview-history">War history</a></nav></div>'
    out += ''.join('<div class="warning">'+esc(w)+'</div>' for w in state.get('warnings',[]))
    if not sync and not roster:
        out += '<div class="warning">No clan data has been collected in this copy. Run the script on a network accepted by a key in Clash_Recruitment/coc_token.txt, then open the generated dashboard.</div>'
    out += panel('Roster · '+str(len(roster))+' members', table(['Player','Tag','TH','Donated','Received'],[(p.get('name'),p.get('tag'),p.get('townHallLevel'),number(p.get('donations')),number(p.get('donationsReceived'))) for p in roster]) if roster else '<p>No saved roster yet.</p>','roster')
    current = []
    for war in state.get('wars',[]):
        if war.get('state') not in ('preparation','inWar'):
            continue
        title=esc(war.get('kind'))+' war vs '+esc((war.get('opponent') or {}).get('name'))
        current.append('<h3>'+title+'</h3><p>'+esc(war.get('state'))+' · ends '+esc(war.get('endTime'))+' · '+esc(war.get('stars'))+' stars</p>' + table(['Player','Attacks used','Allowed','Attack stars'],[(p.get('name'),p.get('attacksUsed'),war.get('attacksPerMember'),p.get('starsEarned')) for p in war.get('participants',[])]))
    out += panel('Current wars',''.join(current) or '<p>No active war in the saved data. Refresh the collector to check.</p>','current')
    districts=(clan.get('clanCapital') or {}).get('districts',[])
    capital='<p>Capital Hall '+esc((clan.get('clanCapital') or {}).get('capitalHallLevel'))+'</p>'
    if districts:
        capital+=table(['District','Hall'],[(d.get('name'),d.get('districtHallLevel')) for d in districts])
    raids=sorted(state.get('raids',[]),key=lambda r:r.get('startTime',''),reverse=True)
    if raids:
        raid=raids[0]
        capital+='<h3>Latest saved raid</h3><p>'+esc(raid.get('startTime'))+' · Capital Gold '+number(raid.get('capitalTotalLoot'))+'</p>'
        capital+=table(['Player','Attacks','Capital Gold'],[(p.get('name'),p.get('attacks'),number(p.get('capitalResourcesLooted'))) for p in raid.get('members',[])])
    else:
        capital+='<p>No saved raid report yet.</p>'
    out += panel('Clan Capital',capital,'capital')
    wars=sorted(state.get('wars',[]),key=lambda w:w.get('endTime',''),reverse=True)
    out += panel('War history',table(['Type','Opponent','Ended','Stars','Player results'],[(w.get('kind'),(w.get('opponent') or {}).get('name'),w.get('endTime'),w.get('stars'),'Final counts saved' if w.get('final') and w.get('rosterComplete') else 'Incomplete / in progress') for w in wars]) if wars else '<p>No saved wars yet.</p>','history')
    return out

def recruiter_report(path):
    """Embed the latest recruiter output, independently of saved war history."""
    try:
        contents=Path(path).read_text(encoding='utf-8')
        if not contents.strip():
            return {'error':'The recruiter report is empty. Run the recruiter again.'}
        modified=datetime.fromtimestamp(Path(path).stat().st_mtime,timezone.utc).isoformat()
        return {'html':contents,'updatedAt':modified}
    except FileNotFoundError:
        return {}
    except (OSError,UnicodeError):
        return {'error':'Could not read the recruiter report. Check Pyto folder access, then run the tracker again.'}

def clan_badge_url(clan=None):
    """Only official clan badge artwork from the latest successful snapshot."""
    badges = (clan or {}).get('badgeUrls') or {}
    if not isinstance(badges, dict):
        return ''
    for size in ('large', 'medium', 'small'):
        value = badges.get(size)
        if not isinstance(value, str) or len(value) > 2048:
            continue
        try:
            url = urlparse(value)
            if url.scheme == 'https' and url.netloc == 'api-assets.clashofclans.com' and url.path.startswith('/badges/') and not url.query and not url.fragment:
                return value
        except ValueError:
            pass
    return ''


def clan_favicon_link(url=None):
    # A small gold shield is used until the first successful clan snapshot.
    url = clan_badge_url({'badgeUrls': {'large': url}})
    fallback = 'data:image/svg+xml,' + quote('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><path d="M8 9 32 2 56 9v21c0 14-12 25-24 32C20 55 8 44 8 30Z" fill="#d4a64e" stroke="#f5d58a" stroke-width="3"/></svg>', safe='')
    href='https://portal.warhavenclan.com/members/favicon.svg?v='+quote(url,safe='') if url else fallback
    return '<link id="clan-favicon" rel="icon" type="image/svg+xml" href="' + html_module.escape(href, quote=True) + '">'


def dashboard_assets():
    shared = Path(__file__).with_name('shared')
    asset = lambda name, fallback: (shared / name).read_text() if (shared / name).is_file() else fallback
    return {'common': asset('dashboard-ui.js', COMMON_UI_JS),
            'cleanup': '\n'.join((shared / name).read_text() for name in ('leadership-features.js','leadership-workspace.js','leader-session.js')) if all((shared / name).is_file() for name in ('leadership-features.js','leadership-workspace.js','leader-session.js')) else CLEANUP_JS,
            'css': asset('dashboard-ui.css', CLEANUP_CSS)}


def write_dashboard(state, path, recruiter_html=None, password=None):
    # Also repair older saved states when rendering offline or after an import.
    capture_progression(state)
    # Escape '<' so clan/player names cannot close the JSON script element.
    # The cloud scan baseline stays in the encrypted archive, not the browser.
    browser_state={key:value for key,value in state.items() if key!='recruiter'}
    assets = dashboard_assets()
    browser_state['sourceBuildVersion']=hashlib.sha256((HTML_TEMPLATE+TRACKER_JS+EXTRA_JS+assets['common']+assets['cleanup']+assets['css']+DASHBOARD_UI_JS+PASSWORD_JS+SODIUM_JS+LEADER_CACHE_JS+LIVE_DASHBOARD_JS+MEMBER_ACCOUNTS_JS+SHARED_DASHBOARD_JS+RECRUITMENT_JS+RECRUITMENT_CSS+UPGRADE_MODEL_PY+json.dumps(UPGRADE_CATALOG,sort_keys=True)+json.dumps(TOWN_HALL_IMAGES,sort_keys=True)).encode()).hexdigest()[:16]
    data = json.dumps(browser_state,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    path=Path(path)
    report=recruiter_report(recruiter_html or RECRUITER_DIR/'recruiting_candidates.html')
    cloud_report=(state.get('recruiter') or {}).get('report')
    if isinstance(cloud_report,dict) and isinstance(cloud_report.get('html'),str):
        if not report.get('html') or (api_time(cloud_report.get('updatedAt')) or '') >= (api_time(report.get('updatedAt')) or ''):
            report=copy.deepcopy(cloud_report)
    if isinstance(report.get('groups'),dict):
        # Native cards use structured rows. The legacy standalone report stays
        # in the encrypted archive; duplicating its HTML inflates every login
        # and collector publication as the weekly list accumulates.
        report.pop('html',None)
    report_json=json.dumps(report,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    html = HTML_TEMPLATE.replace('__TRACKER_JS__',TRACKER_JS).replace('__EXTRA_JS__',EXTRA_JS).replace('__DASHBOARD_UI_JS__',DASHBOARD_UI_JS).replace('__PASSWORD_JS__',PASSWORD_JS).replace('__SODIUM_JS__',SODIUM_JS).replace('__RECRUITMENT_JS__',RECRUITMENT_JS).replace('__RECRUITMENT_CSS__',RECRUITMENT_CSS).replace('__TOWN_HALL_IMAGES__',json.dumps(TOWN_HALL_IMAGES)).replace('__SHARED_DASHBOARD_JS__',SHARED_DASHBOARD_JS).replace('__LIVE_DASHBOARD_JS__',LIVE_DASHBOARD_JS).replace('__LEADER_CACHE_JS__',LEADER_CACHE_JS).replace('__MEMBER_ACCOUNTS_JS__',MEMBER_ACCOUNTS_JS).replace('__WAR_DATA__',data).replace('__PREVIEW_HTML__',preview_html(state)).replace('__RECRUITER_DATA__',report_json)
    html = html.replace('__CLEANUP_CSS__', assets['css']).replace('__COMMON_UI_JS__', assets['common']).replace('__CLEANUP_JS__', assets['cleanup'])
    favicon_url=clan_badge_url(state.get('clanProfile'))
    html=html.replace('__CLAN_FAVICON__',clan_favicon_link(favicon_url))
    path.write_text(protected_dashboard(html,password,favicon_url=favicon_url) if password else html,encoding='utf-8')

def mirror_dashboard(html_file, shared_output=None, script_path=None):
    """Keep a viewable HTML copy beside a script stored in iCloud Drive."""
    html_file=Path(html_file)
    if shared_output is not None:
        folder=Path(shared_output).expanduser()
    else:
        folder=Path(script_path or __file__).resolve().parent
        if 'com~apple~CloudDocs' not in folder.parts:
            return None
    destination=folder/'war_tracker.html'
    if destination.resolve()==html_file.resolve():
        return destination
    folder.mkdir(parents=True,exist_ok=True)
    temporary=folder/'war_tracker.html.sync.tmp'
    try:
        temporary.write_bytes(html_file.read_bytes())
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination

def dashboard_server(html_file, port=0):
    """Serve only this dashboard and its explicit exports, never the token folder."""
    route = '/clan-dashboard/' + secrets.token_urlsafe(24) + '/'
    html_file = Path(html_file)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def reply(self, status, body, content_type='text/plain; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path.split('?',1)[0] != route:
                self.reply(404,b'Not found')
                return
            try:
                self.reply(200,html_file.read_bytes(),'text/html; charset=utf-8')
            except OSError:
                self.reply(503,b'Dashboard could not be read. Run the collector again.')
        def do_POST(self):
            if self.path != route + 'export':
                self.reply(404,b'Not found')
                return
            # Browser exports are same-origin. Reject requests from other sites.
            if self.headers.get('Origin') != 'http://127.0.0.1:' + str(self.server.server_port):
                self.reply(403,b'Invalid origin')
                return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 25*1024*1024:
                    raise ValueError('Invalid export size')
                value=json.loads(self.rfile.read(length).decode('utf-8'))
                name,text=value.get('name'),value.get('text')
                if (name not in ('war_tracker_changes.json','clan_war_roster.csv','war_lineup_regular.txt','war_lineup_cwl.txt') and not re.fullmatch(r'weekly_clan_report_\d{4}-\d{2}-\d{2}\.txt',str(name))) or not isinstance(text,str):
                    raise ValueError('Invalid export')
                if name.endswith('.json'):
                    payload=json.loads(text)
                    if not isinstance(payload,dict) or not isinstance(payload.get('edits'),dict):
                        raise ValueError('Invalid backup')
                    save_json(html_file.parent/name,payload)
                else:
                    (html_file.parent/name).write_text(text,encoding='utf-8')
                self.reply(200,json.dumps({'saved':name}).encode('utf-8'),'application/json')
            except (ValueError,UnicodeError,AttributeError,TypeError):
                self.reply(400,b'Invalid export')
            except OSError:
                self.reply(500,b'Could not save the export')
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server, 'http://127.0.0.1:' + str(server.server_port) + route

def open_pyto_dashboard(html_file):
    """Use a real WKWebView in Pyto instead of iOS's static file preview."""
    try:
        import pyto_ui as ui
    except ImportError:
        return False
    server, url = dashboard_server(html_file)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        from Foundation import NSURL, NSURLRequest
        from WebKit import WKWebView, WKWebViewConfiguration
        from rubicon.objc.types import CGRect
        class DashboardView(ui.UIKitView):
            def make_view(self):
                configuration=WKWebViewConfiguration.alloc().init()
                web=WKWebView.alloc().initWithFrame(CGRect((0,0),(390,750)),configuration=configuration)
                web.loadRequest(NSURLRequest.requestWithURL(NSURL.URLWithString(url)))
                return web
        view=DashboardView()
        view.title='Clan Dashboard'
        view.size=(390,750)
        view.background_color=ui.COLOR_SYSTEM_BACKGROUND
        print('Opening the interactive dashboard in Pyto. Close its view to return to the script.')
        ui.show_view(view,ui.PRESENTATION_MODE_SHEET)
        return True
    except Exception as error:
        # Keep a browser route available even if a Pyto build lacks the UIKit bridge.
        import webbrowser
        print('The in-app viewer could not open:',type(error).__name__)
        print('Open this address in Safari while this script is running:',url)
        print('Return to Pyto and tap Stop when finished.')
        webbrowser.open(url)
        while True:
            time.sleep(1)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def aes_cbc_encrypt(key, iv, plaintext):
    """Use an installed native AES implementation, otherwise bundled pyaes MIT."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        engine = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        return engine.update(plaintext) + engine.finalize()
    except ImportError:
        import types
        module = types.ModuleType('_clash_vendored_pyaes')
        exec(compile(VENDORED_AES, '<bundled pyaes 1.6.1 MIT>', 'exec'), module.__dict__)
        cipher = module.AESModeOfOperationCBC(key, iv=iv)
        return b''.join(cipher.encrypt(plaintext[i:i+16]) for i in range(0, len(plaintext), 16))


def protected_dashboard(document, password, rounds=600000, favicon_url=None):
    """PBKDF2-SHA256, AES-256-CBC and encrypt-then-HMAC-SHA256.

    The encrypted publication contains no API or GitHub credentials. Authenticate
    the complete envelope before decryption. Salt and IV are fresh per update.
    """
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError('Use a dashboard passphrase of at least 12 characters.')
    if not integer(rounds) or not 100000 <= rounds <= 2000000:
        raise ValueError('Password derivation rounds must be between 100,000 and 2,000,000.')
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, rounds, dklen=64)
    import gzip
    plaintext = gzip.compress(document.encode('utf-8'), compresslevel=9, mtime=0)
    padding = 16 - len(plaintext) % 16
    ciphertext = aes_cbc_encrypt(key[:32], iv, plaintext + bytes([padding]) * padding)
    context = b'WarHavenDashboard:v1'
    tag = hmac.new(key[32:], context + salt + iv + ciphertext, hashlib.sha256).digest()
    encode = lambda value: base64.b64encode(value).decode('ascii')
    payload = {'version': 1, 'rounds': rounds, 'salt': encode(salt), 'iv': encode(iv), 'ciphertext': encode(ciphertext), 'tag': encode(tag)}
    return LOCK_TEMPLATE.replace('__CLAN_FAVICON__', clan_favicon_link(favicon_url)).replace('__ENCRYPTED_PAYLOAD__', json.dumps(payload, separators=(',', ':')))


GITHUB_HISTORY_PATH = 'data/war_tracker_state.enc.json'
DEFAULT_WEBSITE_REPOSITORY = 'phil14-hub/war-haven-dashboard'
STATE_ENCRYPTION_CONTEXT = b'WarHavenState:v1'
MAX_STATE_BYTES = 50 * 1024 * 1024


def save_website_secrets(path, value):
    """Atomic device-local settings write, deliberately without a backup copy."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    descriptor=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(descriptor,'w',encoding='utf-8') as handle:
        json.dump(value,handle)
    temporary.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def aes_cbc_decrypt(key, iv, ciphertext):
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        engine = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        return engine.update(ciphertext) + engine.finalize()
    except ImportError:
        import types
        module = types.ModuleType('_clash_vendored_pyaes')
        exec(compile(VENDORED_AES, '<bundled pyaes 1.6.1 MIT>', 'exec'), module.__dict__)
        cipher = module.AESModeOfOperationCBC(key, iv=iv)
        return b''.join(cipher.decrypt(ciphertext[i:i+16]) for i in range(0, len(ciphertext), 16))


def encrypt_history(state, password, rounds=600000):
    """Compress then encrypt the complete archive, with a separate MAC context."""
    import gzip
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError('Use a dashboard passphrase of at least 12 characters.')
    if not integer(rounds) or not 100000 <= rounds <= 2000000:
        raise ValueError('Invalid password derivation rounds.')
    raw = json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_STATE_BYTES:
        raise ValueError('The clan archive exceeds the supported 50 MiB size.')
    raw = gzip.compress(raw, compresslevel=9, mtime=0)
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, rounds, dklen=64)
    padding = 16-len(raw)%16
    ciphertext = aes_cbc_encrypt(key[:32], iv, raw+bytes([padding])*padding)
    signature = hmac.new(key[32:], STATE_ENCRYPTION_CONTEXT+salt+iv+ciphertext, hashlib.sha256).digest()
    encode = lambda b: base64.b64encode(b).decode('ascii')
    return {'format': 'war-haven-state', 'version': 1, 'compression': 'gzip', 'rounds': rounds,
            'salt': encode(salt), 'iv': encode(iv), 'ciphertext': encode(ciphertext), 'tag': encode(signature)}


def decrypt_history(envelope, password):
    import gzip
    import io
    try:
        if not isinstance(envelope, dict) or envelope.get('format') != 'war-haven-state' or envelope.get('version') != 1 or envelope.get('compression') != 'gzip':
            raise ValueError('Unsupported archive format.')
        rounds = envelope['rounds']
        if not integer(rounds) or not 100000 <= rounds <= 2000000:
            raise ValueError('Unsupported archive settings.')
        decode = lambda k: base64.b64decode(envelope[k], validate=True)
        salt, iv, ciphertext, signature = (decode(k) for k in ('salt','iv','ciphertext','tag'))
        if len(salt)!=16 or len(iv)!=16 or len(signature)!=32 or not ciphertext or len(ciphertext)%16 or len(ciphertext)>MAX_STATE_BYTES:
            raise ValueError('Invalid encrypted archive.')
        key=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,rounds,dklen=64)
        actual=hmac.new(key[32:],STATE_ENCRYPTION_CONTEXT+salt+iv+ciphertext,hashlib.sha256).digest()
        if not hmac.compare_digest(actual,signature):
            raise ValueError('The passphrase does not unlock the GitHub history. The archive was not changed.')
        padded=aes_cbc_decrypt(key[:32],iv,ciphertext)
        count=padded[-1]
        if not 1<=count<=16 or padded[-count:]!=bytes([count])*count:
            raise ValueError('Invalid encrypted archive padding.')
        with gzip.GzipFile(fileobj=io.BytesIO(padded[:-count])) as stream:
            raw=stream.read(MAX_STATE_BYTES+1)
        if len(raw)>MAX_STATE_BYTES:
            raise ValueError('The archive exceeds the supported size.')
        state=json.loads(raw.decode('utf-8'))
        if not isinstance(state,dict) or state.get('schemaVersion')!=1 or not isinstance(state.get('edits'),dict):
            raise ValueError('Invalid clan history snapshot.')
        return state
    except (KeyError,TypeError,UnicodeError,EOFError,OSError) as error:
        raise ValueError('The encrypted GitHub history cannot be read. The archive was not changed.') from error


def github_history_record(config, ref=None, include_content=False):
    root='/repos/'+config['repository']
    path=root+'/contents/'+GITHUB_HISTORY_PATH
    if ref:
        path+='?ref='+quote(ref,safe='')
    try:
        record=github_request(config,'GET',path)
    except PublishError as error:
        if error.status==404:
            return None
        raise
    if not isinstance(record,dict) or not record.get('sha'):
        raise PublishError(0,'GitHub did not return a valid history-file revision.')
    if include_content:
        value=record
        if value.get('encoding')!='base64' or not value.get('content'):
            value=github_request(config,'GET',root+'/git/blobs/'+quote(record['sha'],safe=''))
        if value.get('encoding')!='base64' or not value.get('content'):
            raise PublishError(0,'GitHub could not return the encrypted history contents.')
        try:
            record={**record,'envelope':json.loads(base64.b64decode(value['content']).decode('utf-8'))}
        except (ValueError,UnicodeError,TypeError):
            raise PublishError(0,'The stored encrypted history file is invalid. It was not replaced.') from None
    return record


def archive_fingerprint(state):
    return hashlib.sha256(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def pull_github_history(state, config):
    """Merge remote history before collecting; never replace a local archive blindly."""
    config['_history_checked']=False
    try:
        record=github_history_record(config,include_content=True)
        if record:
            try:
                archive=decrypt_history(record['envelope'],config['password'])
            except ValueError:
                previous=config.get('_history_password')
                if not previous or previous==config['password']:
                    raise
                archive=decrypt_history(record['envelope'],previous)
            if normalize_tag(archive.get('clanTag'))!=state['clanTag']:
                raise ValueError('The GitHub history belongs to another clan. It was not replaced.')
            config['_history_fingerprint']=archive_fingerprint(archive)
            candidate=copy.deepcopy(state)
            apply_snapshot(candidate,archive)
            events={json.dumps(v,sort_keys=True):v for v in state.get('activity',[])+archive.get('activity',[]) if isinstance(v,dict)}
            candidate['activity']=sorted(events.values(),key=lambda v:api_time(v.get('detectedAt')) or '')[-300:]
            state.clear()
            state.update(candidate)
            print('Encrypted GitHub history merged with this device’s saved history.')
        config['_history_sha']=record['sha'] if record else None
        config['_history_checked']=True
        return bool(record)
    except (ValueError,TypeError,AttributeError) as error:
        raise PublishError(0,str(error)) from None


def publish_history_commit(config, protected_file, state, branch):
    """Publish matching website+archive in one fast-forward-only commit."""
    if not config.get('_history_checked'):
        raise PublishError(0,'Saved GitHub history was not verified. Run again before publishing; the remote archive is unchanged.')
    root='/repos/'+config['repository']
    head=github_request(config,'GET',root+'/git/ref/heads/'+quote(branch,safe=''))
    parent=(head.get('object') or {}).get('sha')
    if not parent:
        raise PublishError(0,'GitHub did not return the current branch revision.')
    remote=github_history_record(config,ref=parent)
    if (remote['sha'] if remote else None)!=config.get('_history_sha'):
        raise PublishError(409,'Another update changed the GitHub history. Run again to merge it; no remote data was overwritten.')
    commit=github_request(config,'GET',root+'/git/commits/'+parent)
    tree_sha=(commit.get('tree') or {}).get('sha')
    if not tree_sha:
        raise PublishError(0,'GitHub did not return the current file tree.')
    document=Path(protected_file).read_text(encoding='utf-8')
    if 'id="protected-payload"' not in document:
        raise PublishError(0,'Only a password-encrypted dashboard can be published with clan history.')
    fingerprint=archive_fingerprint(state)
    rotating=bool(config.get('_history_password') and config['_history_password'] != config['password'])
    def upload_html():
        return github_request(config,'POST',root+'/git/blobs',{'content':document,'encoding':'utf-8'})
    def upload_state():
        envelope=encrypt_history(state,config['password'])
        return github_request(config,'POST',root+'/git/blobs',{'content':json.dumps(envelope,separators=(',',':')),'encoding':'utf-8'})
    if remote and not rotating and config.get('_history_fingerprint') == fingerprint:
        state_blob={'sha':remote['sha']}
        html_blob=upload_html()
        print('Storage check: verified unchanged encrypted archive reused.')
    else:
        # No tree/ref is created until both independent uploads succeed.
        with ThreadPoolExecutor(max_workers=2) as pool:
            state_future=pool.submit(upload_state)
            html_future=pool.submit(upload_html)
            state_blob,html_blob=state_future.result(),html_future.result()
    if not state_blob.get('sha') or not html_blob.get('sha'):
        raise PublishError(0,'GitHub did not confirm the encrypted file uploads.')
    tree=github_request(config,'POST',root+'/git/trees',{'base_tree':tree_sha,'tree':[
        {'path':GITHUB_HISTORY_PATH,'mode':'100644','type':'blob','sha':state_blob['sha']},
        {'path':'index.html','mode':'100644','type':'blob','sha':html_blob['sha']}]})
    if not tree.get('sha'):
        raise PublishError(0,'GitHub did not confirm the new file tree.')
    written=github_request(config,'POST',root+'/git/commits',{'message':('Change dashboard password and re-encrypt saved clan history' if config.get('_history_password') and config['_history_password'] != config['password'] else 'Update encrypted clan dashboard and history'),'tree':tree['sha'],'parents':[parent]})
    sha=written.get('sha')
    if not sha:
        raise PublishError(0,'GitHub did not confirm the combined update.')
    try:
        updated=github_request(config,'PATCH',root+'/git/refs/heads/'+quote(branch,safe=''),{'sha':sha,'force':False})
    except PublishError as error:
        if error.status in (409,422):
            raise PublishError(error.status,'The repository changed while saving. Run again to merge; no remote history was overwritten.') from None
        raise
    if (updated.get('object') or {}).get('sha')!=sha:
        raise PublishError(0,'GitHub did not confirm the branch update. Check its current revision before retrying.')
    config['_publication_pair']={'pageSha':html_blob['sha'],'historySha':state_blob['sha'],'commit':sha}
    config['_history_sha']=state_blob['sha']
    config['_history_fingerprint']=fingerprint
    if config.get('_history_password') and config.get('_settings_file'):
        try:
            settings=Path(config['_settings_file'])
            value=json.loads(settings.read_text(encoding='utf-8'))
            if value.get('password')==config['password']:
                value.pop('archivePassword',None)
                save_website_secrets(settings,value)
        except (OSError,ValueError,AttributeError):
            print('The update is saved; local password-rotation settings could not be cleaned up.')
    config.pop('_history_password',None)
    return sha


def website_config(path, setup=False):
    """Configuration remains on the user's own device, never inside backups."""
    previous_password=None
    if setup and path.exists():
        try:
            saved_settings=json.loads(path.read_text(encoding='utf-8'))
            previous_password=saved_settings.get('archivePassword') or saved_settings.get('password')
        except (ValueError,OSError,AttributeError):
            pass
    if setup:
        import getpass
        print('Set up your password-protected leadership dashboard.')
        print('Choose a shared passphrase for the leaders and co-leaders you invite.')
        password = getpass.getpass('Dashboard passphrase (at least 12 characters): ')
        confirmation = getpass.getpass('Repeat dashboard passphrase: ')
        if password != confirmation:
            raise ValueError('The passphrases did not match. Website settings were not changed.')
        if len(password) < 12:
            raise ValueError('Use a shared passphrase of at least 12 characters.')
        print('For a shared website, use a dedicated GitHub repository with Pages enabled from the default branch / root folder.')
        repository = input('GitHub repository [phil14-hub/war-haven-dashboard], or type local: ').strip()
        repository = '' if repository.lower()=='local' else repository or DEFAULT_WEBSITE_REPOSITORY
        token = getpass.getpass('GitHub publishing token (Contents: write, Pages: read): ').strip() if repository else ''
        if repository and (not re.fullmatch(r'[A-Za-z0-9-]+/[A-Za-z0-9_.-]+', repository) or not token):
            raise ValueError('Enter owner/repository and a publishing token for that repository.')
        value = {'repository':repository,'token':token,'password':password}
        if isinstance(previous_password,str) and previous_password!=password:
            value['archivePassword']=previous_password
        path.parent.mkdir(parents=True, exist_ok=True)
        save_website_secrets(path,value)
        print('Website settings saved on this device. Do not upload this settings file.')
    if not path.exists():
        return None
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as error:
        raise ValueError('Website settings could not be read; run --setup-website again.') from error
    if not isinstance(config, dict) or (config.get('repository') and not re.fullmatch(r'[A-Za-z0-9-]+/[A-Za-z0-9_.-]+', str(config['repository']))):
        raise ValueError('Invalid website repository settings.')
    password = os.getenv('CLASH_DASHBOARD_PASSWORD') or config.get('password')
    token = os.getenv('CLASH_DASHBOARD_GITHUB_TOKEN') or config.get('token')
    if not isinstance(password, str) or len(password) < 12 or (config.get('repository') and (not isinstance(token, str) or not token)):
        raise ValueError('Website settings need a publishing token and a passphrase of at least 12 characters.')
    result={**config,'password':password,'token':token,'_settings_file':str(path)}
    archive_password=config.get('archivePassword') or previous_password
    if isinstance(archive_password,str) and archive_password!=password:
        result['_history_password']=archive_password
    return result


class PublishError(Exception):
    def __init__(self, status, message=None):
        self.status = status
        super().__init__(message or 'GitHub publishing failed (HTTP ' + str(status) + '). Check repository access and publishing-token permissions.')


def github_request(config, method, path, payload=None):
    if not path.startswith('/repos/' + config['repository'] + '/') and path != '/repos/' + config['repository']:
        raise PublishError(0, 'Publishing is restricted to the configured dashboard repository.')
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    accept = 'application/vnd.github.object+json' if method == 'GET' and '/contents/' in path else 'application/vnd.github+json'
    request = Request('https://api.github.com' + path, data=body, method=method,
                      headers={'Authorization': 'Bearer ' + config['token'], 'Accept': accept,
                               'X-GitHub-Api-Version': '2026-03-10', 'Content-Type': 'application/json', 'User-Agent': 'Clash-War-Tracker/' + VERSION})
    try:
        with urlopen(request, timeout=25) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        raise PublishError(error.code) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise PublishError(0, 'GitHub could not be reached. Local history was saved; the website was not replaced.') from None


def pages_https_url(pages):
    """Keep the configured Pages domain, verifying TLS if its metadata still says HTTP."""
    url = pages.get('html_url')
    parsed = urlparse(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise PublishError(0, 'GitHub Pages has not supplied a ready website URL yet.')
    if parsed.scheme == 'https':
        return url
    secure_url = parsed._replace(scheme='https').geturl()
    request = Request(secure_url, headers={'User-Agent': 'Clash-War-Tracker/' + VERSION})
    try:
        with urlopen(request, timeout=20) as response:
            final = urlparse(response.geturl())
            if response.status != 200 or final.scheme != 'https' or final.hostname != parsed.hostname:
                raise PublishError(0, 'The configured Pages domain must serve HTTPS before publishing.')
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        raise PublishError(0, 'HTTPS is not ready on the configured Pages domain. The saved dashboard was not replaced.') from None
    return secure_url


def publish_dashboard(config, protected_file, wait_seconds=60, state=None):
    root = '/repos/' + config['repository']
    repository = github_request(config, 'GET', root)
    branch = repository.get('default_branch') or 'main'
    try:
        pages = github_request(config, 'GET', root + '/pages')
    except PublishError as error:
        if error.status == 404:
            raise PublishError(404, 'Enable GitHub Pages for this repository from its default branch and root folder, then run again.') from None
        raise
    source = pages.get('source') or {}
    if pages.get('build_type') == 'workflow' or source.get('branch') != branch or source.get('path', '/') != '/':
        raise PublishError(0, 'Use a dedicated dashboard repository with Pages publishing from the default branch and root folder.')
    url = pages_https_url(pages)
    if state is not None:
        sha=publish_history_commit(config,protected_file,state,branch)
    else:
        content = base64.b64encode(protected_file.read_bytes()).decode('ascii')
        committed = None
        for attempt in range(2):
            try:
                old = github_request(config, 'GET', root + '/contents/index.html?ref=' + quote(branch, safe=''))
            except PublishError as error:
                if error.status != 404:
                    raise
                old = {}
            payload = {'message': 'Update password-protected clan dashboard', 'content': content, 'branch': branch}
            if old.get('sha'):
                payload['sha'] = old['sha']
            try:
                committed = github_request(config, 'PUT', root + '/contents/index.html', payload)
                break
            except PublishError as error:
                if error.status != 409 or attempt:
                    raise
        sha = (committed.get('commit') or {}).get('sha') if committed else None
        if not sha:
            raise PublishError(0, 'GitHub did not confirm the dashboard update.')
    deadline = time.monotonic() + max(0, wait_seconds)
    print('Encrypted dashboard uploaded. Waiting for GitHub Pages to publish...')
    while time.monotonic() < deadline:
        try:
            build = github_request(config, 'GET', root + '/pages/builds/latest')
            if build.get('commit') == sha:
                if build.get('status') == 'built':
                    return {'url': url, 'published': True, 'commit': sha}
                if build.get('status') == 'errored':
                    return {'url':url,'published':False,'commit':sha,'publicationError':'GitHub Pages reported a build error; the saved publication will be checked independently.'}
        except PublishError as error:
            if error.status != 404:
                return {'url':url,'published':False,'commit':sha,'publicationError':'Pages confirmation is unavailable; the committed dashboard and history were retained.'}
        time.sleep(min(3, max(0, deadline - time.monotonic())))
    return {'url': url, 'published': False, 'commit': sha}



def main(argv=None):
    parser = argparse.ArgumentParser(prog='Clash_War_Tracker.py', description=__doc__)
    parser.add_argument('--clan',default=DEFAULT_CLAN_TAG)
    parser.add_argument('--token-file',type=Path,help='Use only this token file; otherwise find coc_token.txt beside the script and in the existing recruiter folder.')
    parser.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--apply',type=Path)
    parser.add_argument('--watch',type=int,default=0)
    parser.add_argument('--skip-profiles',action='store_true',help='Skip player profiles; Capital donation baselines will not refresh.')
    parser.add_argument('--offline',action='store_true',help='Open the saved data without API calls.')
    parser.add_argument('--no-open',action='store_true',help='Save files without opening the Pyto dashboard.')
    parser.add_argument('--recruiter-html',type=Path,default=RECRUITER_DIR/'recruiting_candidates.html',help='Recruiter report to include in the dashboard.')
    parser.add_argument('--shared-output',type=Path,help='Also save the HTML in this shared folder. Automatic when the script is in iCloud Drive.')
    parser.add_argument('--setup-website',action='store_true',help='Choose a passphrase and configure GitHub Pages publishing.')
    parser.add_argument('--no-publish',action='store_true',help='Generate the dashboard without updating the shared website.')
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    clan_tag = normalize_tag(args.clan)
    if not re.fullmatch(r'#[0289PYLQGRJCUV]+',clan_tag):
        parser.error('Enter a valid Clash clan tag.')
    if args.watch and args.watch < 30:
        parser.error('--watch must be at least 30 seconds.')
    output_dir = args.output if clan_tag == DEFAULT_CLAN_TAG else args.output / clan_tag.lstrip('#')
    output_dir.mkdir(parents=True,exist_ok=True)
    state_file, html_file = output_dir / 'war_tracker_state.json', output_dir / 'war_tracker.html'
    config_file=output_dir/'dashboard_website.json'
    setup=args.setup_website or (not config_file.exists() and not args.no_open and not args.offline)
    config=website_config(config_file,setup=setup)
    website=None
    opened_website=False
    state_source = state_file
    legacy_state = Path.home() / 'Documents' / 'Clash_War_Tracker' / 'tracker_state.json'
    if not state_file.exists() and output_dir == DEFAULT_OUTPUT and legacy_state.exists():
        state_source = legacy_state
    state = load_state(state_source,clan_tag)
    edits_file = args.apply or (output_dir / 'war_tracker_changes.json')
    if not args.apply and not edits_file.exists() and state_source == legacy_state:
        edits_file = legacy_state.parent / 'war_tracker_changes.json'
    if edits_file.exists():
        apply_edits(state,edits_file)
    elif args.apply:
        raise ValueError('The requested edits file was not found.')
    capture_leadership(state)
    api = None if args.offline else OfficialAPI(load_tokens(args.token_file))
    while True:
        history_ready=True
        if config and config.get('repository') and not args.no_publish:
            try:
                pull_github_history(state,config)
                capture_leadership(state)
            except PublishError as error:
                history_ready=False
                print('GitHub history:',str(error))
                print('Collecting locally; remote publishing is paused until history can be verified.')
        # Backfill verified saved profiles even when regenerating offline or a refresh fails.
        for player in state.get('roster',[]):
            saved=state.get('profiles',{}).get(player['tag'])
            if saved:
                record_profile_honors(state,saved,saved)
                history=state.get('memberHistory',{}).get(player['tag'])
                if history and history.get('inClan') is not False:
                    record_capital_sample(history,saved,state['clanTag'])
        if api:
            # Sync a copy so a failed roster lookup never empties or overwrites saved membership.
            candidate = copy.deepcopy(state)
            try:
                refresh(candidate,api,profiles=not args.skip_profiles)
                state = candidate
            except (APIError,ValueError) as error:
                state['warnings'] = ['Sync failed. Saved roster and wars were retained. ' + str(error)]
                print(state['warnings'][0])
        state['website']={'protected':bool(config),'configured':bool(config and config.get('repository')),'historyStored':bool(config and config.get('_history_sha'))}
        save_json(state_file,state)
        write_dashboard(state,html_file,args.recruiter_html,password=config['password'] if config else None)
        if config and config.get('repository') and not args.no_publish and history_ready:
            try:
                website=publish_dashboard(config,html_file,state=state)
                if website['published']:
                    print('Website and encrypted history updated:',website['url'])
                else:
                    print('Update uploaded; GitHub Pages is still publishing:',website['url'])
                if not args.no_open and not opened_website:
                    import webbrowser
                    webbrowser.open(website['url']+'?update='+website['commit'][:12])
                    opened_website=True
            except PublishError as error:
                print('Website update:',str(error))
                print('Local dashboard and history are saved. The shared website may still show an older snapshot.')
        try:
            shared_html=mirror_dashboard(html_file,args.shared_output)
            if shared_html:
                print('Shared dashboard saved:',shared_html)
                print('On your Mac, open that iCloud Drive file in Chrome and refresh after iCloud syncs.')
        except OSError as error:
            print('The shared dashboard copy could not be updated. Local data and history are saved.')
            print('In Pyto, use the folder-access/lock button to select the iCloud folder, then run again.')
            print('Shared copy error:',str(error))
        print('Dashboard saved:',html_file)
        print('History saved:',state_file)
        print('Saved data:',len(state.get('roster',[])),'members,',len(state.get('wars',[])),'wars,',len(state.get('raids',[])),'raid reports.')
        print('Last successful refresh:',state.get('lastSuccessfulSync') or 'none yet')
        print('Run after each regular war ends, before starting the next one. API keys stay in coc_token.txt.')
        if not args.watch or args.offline:
            break
        print('Watching every',args.watch,'seconds. Keep Python running; iOS may suspend it in the background.')
        time.sleep(args.watch)
    if not args.no_open and not args.watch and not opened_website:
        if not open_pyto_dashboard(html_file):
            import webbrowser
            webbrowser.open(html_file.resolve().as_uri())

VENDORED_AES = _load_asset('VENDORED_AES')

LOCK_TEMPLATE = _load_asset('LOCK_TEMPLATE')

HTML_TEMPLATE = _load_asset('HTML_TEMPLATE')

TRACKER_JS = _load_asset('TRACKER_JS')

EXTRA_JS = _load_asset('EXTRA_JS')


DASHBOARD_UI_JS = _load_asset('DASHBOARD_UI_JS')


PASSWORD_JS = _load_asset('PASSWORD_JS')
SODIUM_JS = _load_asset('SODIUM_JS')

RECRUITMENT_JS = _load_asset('RECRUITMENT_JS')
RECRUITMENT_CSS = _load_asset('RECRUITMENT_CSS')
TOWN_HALL_IMAGES = _load_asset('TOWN_HALL_IMAGES')

SHARED_DASHBOARD_JS = _load_asset('SHARED_DASHBOARD_JS')

LEADER_CACHE_JS = _load_asset('LEADER_CACHE_JS')

LIVE_DASHBOARD_JS = _load_asset('LIVE_DASHBOARD_JS')

MEMBER_ACCOUNTS_JS = _load_asset('MEMBER_ACCOUNTS_JS')

UPGRADE_CATALOG = _load_asset('UPGRADE_CATALOG')
UPGRADE_MODEL_PY = _load_asset('UPGRADE_MODEL_PY')
COMMON_UI_JS = _load_asset('COMMON_UI_JS')
CLEANUP_JS = _load_asset('CLEANUP_JS')
CLEANUP_CSS = _load_asset('CLEANUP_CSS')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Stopped. Saved war history is kept.')
    except (ValueError,OSError,EOFError) as error:
        print('Tracker stopped:',error)


