"""Retry member and leadership portal publication without collecting Clash data."""
import base64
import os
import tempfile
from pathlib import Path
import github_collector
import member_exports
import shared_actions


def run(env=None, tracker=None):
    env = os.environ if env is None else env
    repository = env.get('GITHUB_REPOSITORY')
    if repository != 'phil14-hub/war-haven-dashboard':
        raise ValueError('Portal synchronization is restricted to War Haven.')
    config = {'repository': repository, 'password': env['DASHBOARD_PASSWORD'], 'token': env.get('DASHBOARD_PUBLISH_TOKEN') or env['GITHUB_TOKEN']}
    tracker = tracker or github_collector.load_tracker()
    # Pin both encrypted objects to the same main-branch commit.
    head = tracker.github_request(config, 'GET', '/repos/'+repository+'/git/ref/heads/main')['object']['sha']
    archive = tracker.github_history_record(config, ref=head, include_content=True)
    if not archive:
        raise ValueError('The saved clan archive is missing. No publication was made.')
    state = tracker.decrypt_history(archive['envelope'], config['password'])
    record = tracker.github_request(config, 'GET', '/repos/'+repository+'/contents/index.html?ref='+head)
    if not record.get('content'):
        record = tracker.github_request(config, 'GET', '/repos/'+repository+'/git/blobs/'+record['sha'])
    document = base64.b64decode(record['content'], validate=False).decode('utf-8')
    with tempfile.TemporaryDirectory(prefix='war-haven-portal-sync-') as folder:
        path = Path(folder)/'index.html'
        path.write_text(document, encoding='utf-8')
        client = shared_actions.Client(config['password'])
        result = member_exports.publish(state, path, client, config['password'], tracker)
        for kind in ('clan','recruitment'):
            try:
                client.request('/v1/refresh/reconcile', {'kind': kind, 'publication': result['publication']})
            except shared_actions.SharedActionsError:
                print('Portal data is current; an older progress entry will be reconciled on the next retry.')
    print('Member and leadership portal synchronized from the same saved revision.')
    return result


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        print('Portal synchronization retained the previous complete publication ('+type(error).__name__+').')
        raise SystemExit(1)
