"""Signed, duration-weighted upgrade work relative to the previous TH maximum.

Catalog durations are standard (unboosted), not elapsed account age. Instant
unlocks receive one reporting unit so an unavailable unlock cannot count as maxed.
"""
import json
import math
import re
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name('upgrade_catalog.json').read_text())
METHOD = 'th-work-v2'

def canonical(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())

def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)

def compact_series(values, signature=None):
    """Consecutive equal observations collapse; a return to an old value remains."""
    out = []
    signature = signature or (lambda p: (p.get('value'), p.get('townHall')))
    for item in values:
        if not out or signature(out[-1]) != signature(item):
            out.append(item)
    return out

def _work(unit, level):
    if unit['group'] == 'equipment':
        return level
    seconds = unit.get('levelSeconds') or []
    return sum(max(1, seconds[i]) for i in range(1, level + 1))

def _group(items, available=True, equipment=False):
    known = available and all(i['level'] is not None for i in items)
    cur = sum(i['level'] or 0 for i in items) if known else None
    maximum = sum(i['maximum'] for i in items)
    previous = sum(i['previousMaximum'] for i in items)
    new_work = sum(i['newWork'] for i in items)
    done = sum(i['newWorkDone'] for i in items) if known else None
    backlog = sum(i['earlierWorkRemaining'] for i in items) if known else None
    remaining = sum(i['remainingLevels'] or 0 for i in items) if known else None
    percent = 100 * (done - backlog) / new_work if known and new_work else None
    if equipment:
        percent = 100 * cur / maximum if known and maximum else None
    if percent is not None:
        percent = round(percent, 1) if remaining == 0 else min(99.9, math.floor(percent * 10) / 10)
    return {'current': cur, 'maximum': maximum, 'previousMaximum': previous,
            'percent': percent, 'newWork': new_work, 'newWorkDone': done,
            'earlierWorkRemaining': backlog, 'remainingLevels': remaining,
            'earlierLevelsRemaining': sum(i['earlierLevelsRemaining'] or 0 for i in items) if known else None,
            'maxed': sum(i['level'] == i['maximum'] for i in items) if known else None,
            'count': len(items), 'available': known, 'items': items,
            'method': 'owned-equipment-levels' if equipment else METHOD,
            'noNewUpgrades': not bool(maximum if equipment else new_work), 'isMaxed': bool(items) and known and remaining == 0}

def army_progress(profile, ignored=()):
    th = profile.get('townHallLevel')
    result = {'townHall': th, 'at': profile.get('profileCheckedAt'), 'method': METHOD,
              'percent': None, 'groups': {}, 'issues': []}
    if not integer(th) or not 1 <= th <= CATALOG['maxTownHall']:
        result['issues'].append('This Town Hall is outside the current upgrade catalog.')
        return result
    raw = {field: [v for v in profile.get(field, []) if isinstance(v, dict) and v.get('village', 'home') == 'home']
           if isinstance(profile.get(field), list) else []
           for field in ('troops', 'spells', 'heroes', 'pets', 'heroEquipment')}
    lookup = {canonical(v.get('name')): v for collection in raw.values() for v in collection}
    known = {canonical(v['name']) for v in CATALOG['units']}
    ignored = {canonical(v) for v in (*ignored, *CATALOG.get('ignored', []))}
    unknown = {str(v.get('name')) for field in ('troops', 'spells', 'heroes', 'pets') for v in raw[field]
               if canonical(v.get('name')) not in known | ignored}
    if unknown:
        result['issues'].append('Upgrade catalog needs an update for: ' + ', '.join(sorted(unknown)))
    sources = {g: [] for g in ('troops', 'spells', 'siege', 'heroes', 'pets', 'equipment')}
    fields = {'troops': 'troops', 'siege': 'troops', 'spells': 'spells', 'heroes': 'heroes', 'pets': 'troops', 'equipment': 'heroEquipment'}
    for unit in CATALOG['units']:
        maximum = unit['caps'][th - 1]
        if not maximum:
            continue
        group, item = unit['group'], lookup.get(canonical(unit['name']))
        if group == 'equipment' and item is None:
            continue
        previous = unit['caps'][th - 2] if th > 1 else 0
        level = item.get('level') if item else 0
        valid = integer(level) and 0 <= level <= maximum
        if item and integer(item.get('maxLevel')) and item['maxLevel'] < maximum:
            valid = False
        if not valid:
            level = None
        row = {'name': unit['name'], 'id': unit['id'], 'level': level, 'maximum': maximum,
               'previousMaximum': previous, 'unlocked': bool(item),
               'remainingLevels': maximum - level if level is not None else None,
               'earlierLevelsRemaining': max(0, previous - level) if level is not None else None,
               'newWork': _work(unit, maximum) - _work(unit, previous),
               'newWorkDone': max(0, _work(unit, level) - _work(unit, previous)) if level is not None else 0,
               'earlierWorkRemaining': max(0, _work(unit, previous) - _work(unit, level)) if level is not None else 0}
        if group == 'equipment':
            ore = {'shiny_ore': 0, 'glowy_ore': 0, 'starry_ore': 0}
            if level is not None:
                for costs in unit.get('oreToLevel', [])[level + 1:maximum + 1]:
                    for resource in ore:
                        ore[resource] += costs.get(resource, 0)
            row['oreRemaining'] = ore if level is not None else None
        sources[group].append(row)
    for group, items in sources.items():
        available = isinstance(profile.get(fields[group]), list) or group == 'pets' and isinstance(profile.get('pets'), list)
        result['groups'][group] = _group(items, available, group == 'equipment')
        if items and not result['groups'][group]['available']:
            result['issues'].append('Missing or incompatible ' + group + ' levels; progress is unknown.')
    lab_items = sources['troops'] + sources['spells'] + sources['siege']
    result['groups']['laboratory'] = _group(lab_items, all(result['groups'][g]['available'] for g in ('troops', 'spells', 'siege') if sources[g]))
    combined = _group([i for g, items in sources.items() if g != 'equipment' for i in items],
                      not unknown and all(v['available'] for k, v in result['groups'].items() if k != 'equipment' and v['count']))
    for key in ('percent', 'current', 'maximum', 'newWork', 'newWorkDone', 'earlierWorkRemaining', 'remainingLevels', 'earlierLevelsRemaining', 'isMaxed'):
        result[key] = combined[key]
    if result.get('percent') is not None and result['percent'] < 0:
        result['explanation'] = f"Behind TH{th - 1} maximum: {combined['earlierLevelsRemaining']} earlier upgrade levels remain unfinished."
    elif combined['earlierLevelsRemaining']:
        result['explanation'] = f"{combined['earlierLevelsRemaining']} earlier upgrade levels still need attention."
    else:
        result['explanation'] = '0% starts at the previous Town Hall maximum; 100% completes this Town Hall.'
    return result
