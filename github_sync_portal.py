"""Retry member and leadership portal publication without collecting Clash data."""
import base64
import os
import tempfile
from pathlib import Path
import github_collector
import member_exports
import shared_actions
import snapshot_audit
import argparse


def pages_contains_publication(config, tracker, page_sha, history_sha):
    """A later source-only commit can deploy the same encrypted publication."""
    try:
        runs=tracker.github_request(config,'GET','/repos/'+config['repository']+'/actions/runs?status=success&per_page=50')
        for run in runs.get('workflow_runs',[]):
            if run.get('name')!='pages build and deployment' or not run.get('head_sha'):
                continue
            ref=run['head_sha']
            page=tracker.github_request(config,'GET','/repos/'+config['repository']+'/contents/index.html?ref='+ref)
            if page.get('sha')!=page_sha:
                continue
            history=tracker.github_history_record(config,ref=ref)
            if history and history.get('sha')==history_sha:
                return True
    except tracker.PublishError:
        return False
    return False


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
    snapshot_audit.verify(state, tracker)
    record = tracker.github_request(config, 'GET', '/repos/'+repository+'/contents/index.html?ref='+head)
    if not record.get('content'):
        record = tracker.github_request(config, 'GET', '/repos/'+repository+'/git/blobs/'+record['sha'])
    page_sha=record['sha']
    document = base64.b64decode(record['content'], validate=False).decode('utf-8')
    read_config={**config,'token':env.get('GITHUB_TOKEN') or config['token']}
    github_published=pages_contains_publication(read_config,tracker,page_sha,archive['sha'])
    with tempfile.TemporaryDirectory(prefix='war-haven-portal-sync-') as folder:
        path = Path(folder)/'index.html'
        path.write_text(document, encoding='utf-8')
        client = shared_actions.Client(config['password'])
        result = member_exports.publish(state, path, client, config['password'], tracker)
        for kind in ('clan','recruitment'):
            try:
                client.request('/v1/refresh/reconcile', {'kind': kind, 'publication': result['publication'], 'githubPublished':github_published})
            except shared_actions.SharedActionsError:
                print('Portal data is current; an older progress entry will be reconciled on the next retry.')
    print('Member and leadership portal synchronized from the same saved revision.')
    return result


def maintenance(env=None):
    env = os.environ if env is None else env
    if env.get('GITHUB_REPOSITORY') != 'phil14-hub/war-haven-dashboard':
        raise ValueError('Maintenance is restricted to War Haven.')
    # Machine authorization does not depend on archive decryption or email delivery.
    result = shared_actions.Client('').request('/members/api/maintenance')
    print('Temporary account data and generated-publication retention checked. Archives and clan evidence are unchanged.')
    return result


if __name__ == '__main__':
    try:
        parser=argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--maintenance-only',action='store_true')
        if parser.parse_args().maintenance_only:
            maintenance()
        else:
            run()
    except Exception as error:
        print('Portal synchronization retained the previous complete publication ('+type(error).__name__+').')
        raise SystemExit(1)
