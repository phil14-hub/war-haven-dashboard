"""Publish current dashboard code over the verified saved history, without a Clash lookup."""
import os
from pathlib import Path
import tempfile
import github_collector
import member_exports
import shared_actions
import snapshot_audit


def run(env=None, tracker=None):
    env = os.environ if env is None else env
    if env.get('GITHUB_REPOSITORY') != 'phil14-hub/war-haven-dashboard':
        raise ValueError('This release is restricted to War Haven.')
    config={'repository':env['GITHUB_REPOSITORY'],'password':env['DASHBOARD_PASSWORD'],'token':env['DASHBOARD_PUBLISH_TOKEN']}
    tracker=tracker or github_collector.load_tracker()
    state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
    if not tracker.pull_github_history(state,config):
        raise ValueError('Verified existing history is required. No empty release was published.')
    client=shared_actions.Client(config['password'])
    if shared_actions.ENABLED:
        shared_actions.pull(state,client,tracker)
    snapshot_audit.verify(state, tracker)
    with tempfile.TemporaryDirectory(prefix='war-haven-code-release-') as folder:
        path=Path(folder)/'index.html'
        tracker.write_dashboard(state,path,password=config['password'])
        result=tracker.publish_dashboard(config,path,state=state,wait_seconds=180)
        try:
            member_exports.publish(state,path,client,config['password'],tracker)
        except shared_actions.SharedActionsError:
            print('::warning::Code and encrypted history are published. Independent portal sync will retry.')
    print('Current dashboard code published over retained clan history, without another Clash collection.')
    return result


if __name__=='__main__':
    try:
        run()
    except Exception as error:
        print('Dashboard code release retained prior history ('+type(error).__name__+').')
        raise SystemExit(1)
