"""Refresh recruitment independently, preserving every clan snapshot and shared edit."""
import copy
import os
from pathlib import Path
import tempfile

import github_collector
import github_recruiter
import shared_actions


def run(env=None, tracker=None):
    env = os.environ if env is None else env
    config, route = github_collector.settings(env)
    tracker = github_collector.load_tracker() if tracker is None else tracker
    state = tracker.new_state(tracker.DEFAULT_CLAN_TAG)
    tracker.pull_github_history(state, config)
    client = shared_actions.Client(config['password'])
    request = shared_actions.UpdateRequest(client, 'recruitment', shared_actions.pending(client, 'recruitment'))
    request.claim()
    try:
        return collect(env, tracker, config, route, state, request)
    except Exception:
        request.finish()
        raise


def collect(env, tracker, config, route, state, request):
    candidate = copy.deepcopy(state)
    if shared_actions.ENABLED:
        shared_actions.pull(candidate, request.client, tracker)
    request.progress('collecting', 20)
    github_recruiter.refresh(candidate, env, github_collector.API_ROUTES[route])
    if candidate.get('recruiterStatus', {}).get('ok') is not True:
        raise ValueError('Recruitment scan did not finish. Existing report was retained.')
    candidate['website'] = {'protected': True, 'configured': True, 'historyStored': True}
    request.progress('publishing', 75)
    with tempfile.TemporaryDirectory(prefix='war-haven-recruitment-') as folder:
        dashboard = Path(folder) / 'index.html'
        tracker.write_dashboard(candidate, dashboard, password=config['password'])
        request.progress('deploying', 90)
        result = tracker.publish_dashboard(config, dashboard, state=candidate, **({'wait_seconds': 180} if request.lease else {}))
        try:
            import member_exports
            member_exports.publish(candidate, dashboard, request.client, config['password'], tracker)
            result['components']={'github':bool(result.get('published')),'portal':True}
        except Exception:
            result['partial']=True
            result['components']={'github':bool(result.get('published')),'portal':False}
            print('::warning::Member dashboards retained their previous snapshot; the independent portal sync workflow will retry.')
    print('Recruitment updated independently. Clan collection was not run.')
    request.finish(result)
    return result


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        print('Recruitment update stopped safely (' + type(error).__name__ + '). Existing encrypted history was retained.')
        raise SystemExit(1)
