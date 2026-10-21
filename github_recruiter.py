"""Restore the recruiter, scan in a temporary directory, and retain encrypted state."""
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


STATE_FILES = (
    'tracked_us_clans.json', 'us_clan_rosters.json', 'detected_leavers.json',
    'clan_metrics.json', 'last_run_stats.json',
)


def load_recruiter():
    path = Path(__file__).resolve().parent / 'Clash_Recruitment.py'
    spec = importlib.util.spec_from_file_location('war_haven_recruiter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rebuild_report(state, *, module=None):
    """Recover all recent cards from retained records without another API scan."""
    saved = state.get('recruiter') or {}
    files = saved.get('files') or {}
    store = files.get('detected_leavers.json') or {}
    stats = files.get('last_run_stats.json') or {}
    report = saved.get('report') or {}
    filters = stats.get('filters') or report.get('filters')
    if not isinstance(store.get('players'), dict) or not isinstance(filters, dict):
        return
    module = module or load_recruiter()
    groups = module.build_result_groups(store, filters, 7, 7, 50, stats.get('runId'))
    counts = {'newCandidatesShown': len(groups['new']), 'stillAvailableShown': len(groups['still']),
              'joinedMyClanCurrent': len(groups['joined_my'])}
    saved['report'] = {**report, 'groups': {key: [module.clean_row(row) for row in groups[key]]
                      for key in ('new', 'still', 'joined_my', 'no_longer')},
                       'stats': {**stats, **counts}}
    # Preserve the actual scan timestamp and every full archived player record.
    saved['summary'] = {**saved.get('summary', {}), 'newCandidates': counts['newCandidatesShown'],
                        'availableCandidates': counts['newCandidatesShown'] + counts['stillAvailableShown'],
                        'joinedClan': counts['joinedMyClanCurrent']}
    state['recruiterSummary'] = copy.deepcopy(saved['summary'])


def scan(previous, token, api_root, clan_tag, *, module=None, max_clans=1000):
    """Do not alter the caller's saved state unless a complete scan succeeds."""
    if not token or api_root not in ('https://api.clashofclans.com/v1', 'https://cocproxy.royaleapi.dev/v1'):
        raise ValueError('A configured Clash API key and approved API route are required.')
    if not 1 <= max_clans <= 1000:
        raise ValueError('The recruiter clan limit must be between 1 and 1000.')
    previous = {} if previous is None else previous
    if not isinstance(previous, dict):
        raise ValueError('The saved recruiter archive is invalid. It was not reset.')
    if previous and (previous.get('format') != 1 or not isinstance(previous.get('files'), dict)):
        raise ValueError('The saved recruiter archive is invalid. It was not reset.')
    files = previous.get('files', {})
    if previous and set(files) != set(STATE_FILES):
        raise ValueError('The saved recruiter archive is incomplete. It was not reset.')
    if any(name not in STATE_FILES or not isinstance(value, dict) for name, value in files.items()):
        raise ValueError('The saved recruiter files are invalid. They were not reset.')
    module = load_recruiter() if module is None else module
    with tempfile.TemporaryDirectory(prefix='war-haven-recruiter-') as folder:
        directory = Path(folder)
        module.configure_paths(directory)
        module.STATE_DIR.mkdir(parents=True, exist_ok=True)
        for name, value in files.items():
            (module.STATE_DIR / name).write_text(json.dumps(value), encoding='utf-8')
        module.API_ROOT = api_root
        # The API key is supplied in memory, never a generated token file.
        module.get_tokens = lambda: [token]
        # Public workflow logs contain only aggregates, never player names/tags,
        # profile responses, the HTML report, or exception bodies.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            module.main([
                '--my-clan-tag', clan_tag, '--min-th', '11', '--target', '50',
                '--max-clans', str(max_clans), '--workers', '10', '--profile-workers', '10',
            ])
        retained = {}
        for name in STATE_FILES:
            value = json.loads((module.STATE_DIR / name).read_text(encoding='utf-8'))
            if not isinstance(value, dict):
                raise ValueError('The recruiter produced an invalid state file.')
            retained[name] = value
        stats = retained['last_run_stats.json']
        if not stats.get('successfulClanScans') or not stats.get('myClanLookupOk'):
            raise ValueError('The recruiter could not verify the required rosters. Retaining the last saved report.')
        document = module.DEFAULT_HTML.read_text(encoding='utf-8')
        if not document.startswith('<!doctype html>') or 'War Haven Recruiter' not in document:
            raise ValueError('The recruiter did not produce a valid report.')
        native = json.loads(module.DEFAULT_HTML.with_suffix('.json').read_text(encoding='utf-8'))
        if native.get('version') != 1 or not isinstance(native.get('groups'), dict):
            raise ValueError('The recruiter did not produce valid dashboard data.')
        updated = stats.get('runFinishedAt')
        if not updated:
            raise ValueError('The recruiter scan did not finish.')
        return {
            'format': 1, 'updatedAt': updated, 'files': retained,
            'report': {**native, 'html': document, 'updatedAt': updated, 'source': 'Independent cloud recruitment scan'},
            'summary': {
                'updatedAt': updated, 'baselineCreated': bool(stats.get('baselineCreated')),
                'trackedClans': stats.get('trackedClanCount', 0),
                'scannedClans': stats.get('successfulClanScans', 0),
                'newCandidates': stats.get('newCandidatesShown', 0),
                'availableCandidates': stats.get('newCandidatesShown', 0) + stats.get('stillAvailableShown', 0),
                'joinedClan': stats.get('joinedMyClanCurrent', 0),
                'rosterErrors': stats.get('rosterErrors', 0),
            },
        }


def refresh(state, env, api_root, *, module=None):
    """A recruiting outage keeps the last good report and the clan refresh."""
    if (env.get('RECRUITER_ENABLED') or 'true').lower() == 'false':
        return
    attempted = datetime.now(timezone.utc).isoformat()
    try:
        maximum = int(env.get('RECRUITER_MAX_CLANS') or '1000')
        result = scan(copy.deepcopy(state.get('recruiter')), env['COC_API_TOKEN'].strip(),
                      api_root, state['clanTag'], module=module, max_clans=maximum)
    except (Exception, SystemExit) as error:
        state['recruiterStatus'] = {'lastAttemptAt': attempted, 'ok': False, 'errorType': type(error).__name__}
        print('::warning::Recruiter scan did not finish. The last saved recruiting report and history were retained.')
        return
    state['recruiter'] = result
    state['recruiterSummary'] = copy.deepcopy(result['summary'])
    state['recruiterStatus'] = {'lastAttemptAt': attempted, 'ok': True}
    summary = result['summary']
    print('Recruiter: ' + str(summary['scannedClans']) + ' clans scanned; '
          + str(summary['availableCandidates']) + ' verified available candidates shown; '
          + ('cloud baseline created.' if summary['baselineCreated'] else 'saved baseline compared.'))
