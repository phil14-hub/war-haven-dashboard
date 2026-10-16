"""Run the existing tracker in GitHub Actions without interactive Pyto setup."""
import argparse
import copy
import importlib.util
import os
import tempfile
from pathlib import Path

from war_end_updates import next_update, record_update
import shared_actions
from datetime import datetime, timezone


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


def run(env=None, tracker=None, *, post_war=False):
    env = os.environ if env is None else env
    config, route = settings(env)
    tracker = load_tracker() if tracker is None else tracker
    tracker.API_ROOT = API_ROUTES[route]
    state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
    # Verify and restore the latest archive before asking Clash for new data.
    # Any decryption/download failure aborts without a publication.
    tracker.pull_github_history(state, config)
    client = shared_actions.Client(config['password'])
    shared_request = None
    if shared_actions.ENABLED:
        shared_request = shared_actions.pending(client, 'clan')
        if post_war and shared_request is None and (next_update(state) is None or next_update(state) > datetime.now(timezone.utc)) and shared_actions.pending(client, 'recruitment'):
            import github_recruitment_collector
            return github_recruitment_collector.run(env, tracker)
    if post_war and shared_request is None:
        due = next_update(state)
        if due is None or due > datetime.now(timezone.utc):
            print('The latest archive has no pending final-war update. No duplicate collection needed.')
            return {'published': False, 'skipped': True}
    request = shared_actions.UpdateRequest(client, 'clan', shared_request)
    request.claim()
    try:
        return collect(env, tracker, config, route, state, post_war=post_war and shared_request is None, request=request)
    except Exception:
        request.finish()
        raise


def collect(env, tracker, config, route, state, *, post_war, request):
    candidate = copy.deepcopy(state)
    if shared_actions.ENABLED:
        shared_actions.pull(candidate, request.client, tracker)
    request.progress('collecting', 20)
    print('Collecting clan data independently; the saved recruitment scan is retained.')
    tracker.refresh(candidate, tracker.OfficialAPI([env['COC_API_TOKEN'].strip()]))
    candidate['website'] = {'protected': True, 'configured': True, 'historyStored': True}
    candidate['automaticUpdates'] = {**candidate.get('automaticUpdates', {}),
        'lastRunAt': tracker.now_iso(),
        'schedule': '23 7 * * *',
        'timezone': 'America/Denver',
        'lastRunKind': 'after-war' if post_war else 'daily-or-manual',
    }
    final_schedule = record_update(candidate)
    print('Automatic final-war follow-up armed from a recorded end time.'
          if final_schedule['nextUpdateAt'] else 'No pending final-war follow-up in the saved data.')
    request.progress('publishing', 75)
    # Only an encrypted HTML file is written; state stays in memory.
    with tempfile.TemporaryDirectory(prefix='war-haven-') as directory:
        dashboard = Path(directory) / 'index.html'
        tracker.write_dashboard(candidate, dashboard, password=config['password'])
        request.progress('deploying', 90)
        result = tracker.publish_dashboard(config, dashboard, state=candidate, **({'wait_seconds': 180} if request.lease else {}))
        try:
            import member_exports
            member_exports.publish(candidate, dashboard, request.client, config['password'], tracker)
        except Exception:
            print('::warning::Member dashboards retained their previous snapshot; member synchronization will retry on the next clan update.')
    print('Encrypted dashboard and history updated.' if result['published']
          else 'Encrypted update uploaded; GitHub Pages is still deploying.')
    request.finish(result)
    return result


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--post-war', action='store_true',
                            help='Collect due final war results and retain the existing recruiter scan.')
        run(post_war=parser.parse_args().post_war)
    except ValueError as error:
        print('Setup needed:', str(error))
        raise SystemExit(1)
    except Exception as error:
        # Never dump an API response, credential value or state into public logs.
        print('Update stopped safely (' + type(error).__name__ + ').')
        print('Check the configured secrets, API route/IP and Pages permissions. Existing published history was not deliberately replaced with an empty archive.')
        raise SystemExit(1)
