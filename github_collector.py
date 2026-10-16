"""Run the existing tracker in GitHub Actions without interactive Pyto setup."""
import copy
import importlib.util
import os
import tempfile
from pathlib import Path


REQUIRED_SECRETS = ('COC_API_TOKEN', 'DASHBOARD_PASSWORD', 'DASHBOARD_PUBLISH_TOKEN')
API_ROUTES = {
    'official': 'https://api.clashofclans.com/v1',
    'royaleapi': 'https://cocproxy.royaleapi.dev/v1',
}


def settings(env):
    missing = [name for name in REQUIRED_SECRETS if not env.get(name, '').strip()]
    if missing:
        raise ValueError('Add these repository Actions secrets: ' + ', '.join(missing))
    if len(env['DASHBOARD_PASSWORD']) < 12:
        raise ValueError('DASHBOARD_PASSWORD must be the existing dashboard passphrase (12+ characters).')
    route = env.get('CLAN_API_ROUTE', 'official') or 'official'
    if route not in API_ROUTES:
        raise ValueError('CLAN_API_ROUTE must be official or royaleapi.')
    if env.get('GITHUB_REPOSITORY') != 'phil14-hub/war-haven-dashboard':
        raise ValueError('This updater is restricted to the War Haven repository.')
    return {
        'repository': env['GITHUB_REPOSITORY'],
        'password': env['DASHBOARD_PASSWORD'],
        'token': env['DASHBOARD_PUBLISH_TOKEN'].strip(),
    }, route


def load_tracker():
    path = Path(__file__).resolve().parent / 'Clash_War_Tracker.py'
    spec = importlib.util.spec_from_file_location('war_haven_tracker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(env=None, tracker=None):
    env = os.environ if env is None else env
    config, route = settings(env)
    tracker = load_tracker() if tracker is None else tracker
    tracker.API_ROOT = API_ROUTES[route]
    state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
    # Verify and restore the latest archive before asking Clash for new data.
    # Any decryption/download failure aborts without a publication.
    tracker.pull_github_history(state, config)
    candidate = copy.deepcopy(state)
    tracker.refresh(candidate, tracker.OfficialAPI([env['COC_API_TOKEN'].strip()]))
    import github_recruiter
    github_recruiter.refresh(candidate, env, API_ROUTES[route])
    candidate['website'] = {'protected': True, 'configured': True, 'historyStored': True}
    candidate['automaticUpdates'] = {
        'lastRunAt': tracker.now_iso(),
        'schedule': '23 7 * * *',
        'timezone': 'America/Denver',
    }
    # Only an encrypted HTML file is written; state stays in memory.
    with tempfile.TemporaryDirectory(prefix='war-haven-') as directory:
        dashboard = Path(directory) / 'index.html'
        tracker.write_dashboard(candidate, dashboard, password=config['password'])
        result = tracker.publish_dashboard(config, dashboard, state=candidate)
    print('Encrypted dashboard and history updated.' if result['published']
          else 'Encrypted update uploaded; GitHub Pages is still deploying.')
    return result


if __name__ == '__main__':
    try:
        run()
    except ValueError as error:
        print('Setup needed:', str(error))
        raise SystemExit(1)
    except Exception as error:
        # Never dump an API response, credential value or state into public logs.
        print('Update stopped safely (' + type(error).__name__ + ').')
        print('Check the configured secrets, API route/IP and Pages permissions. Existing published history was not deliberately replaced with an empty archive.')
        raise SystemExit(1)
