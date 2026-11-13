"""Retry member and leadership portal publication without collecting Clash data."""
import base64
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
import github_collector
import member_exports
import shared_actions
import snapshot_audit
import argparse
from publication_sync import phase,record as record_publication


def backup_clan_archive(config, tracker, client, commit, archive_sha):
    """Copy a verified Git archive to the private daily backup, keeping Git authoritative."""
    with phase('clan-archive-backup'):
        endpoint = '/members/api/clan-archive-backup'
        if client.request(endpoint, method='HEAD'):
            print('A verified encrypted clan archive backup already exists for today.')
            return
        root = '/repos/' + config['repository']
        record = tracker.github_request(config, 'GET', root + '/git/blobs/' + archive_sha)
        if record.get('encoding') != 'base64' or record.get('sha') != archive_sha:
            raise ValueError('The encrypted Git archive was not returned.')
        body = base64.b64decode(''.join(record['content'].split()), validate=True)
        git_sha = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        if git_sha != archive_sha:
            raise ValueError('The archive did not match its saved Git revision.')
        state = tracker.decrypt_history(json.loads(body), config['password'])
        if tracker.normalize_tag(state.get('clanTag')) != tracker.DEFAULT_CLAN_TAG:
            raise ValueError('The archive belongs to a different clan.')
        checksum = hashlib.sha256(body).hexdigest()
        saved = client.request(endpoint, body=body, extra_headers={
            'X-Archive-SHA256': checksum,
            'X-Archive-Source': commit,
        })
        if saved.get('status') != 'saved' or not re.fullmatch('[a-f0-9]{64}', saved.get('sha256') or ''):
            raise ValueError('The private daily clan archive backup was not confirmed.')
        if saved.get('reused') is not True and (saved['sha256'] != checksum or saved.get('source') != commit or
                                               saved.get('bytes') != len(body)):
            raise ValueError('The private daily clan archive backup did not match the verified archive.')
        print('Encrypted clan archive backup confirmed for ' + saved['day'] + ' (' + str(saved['bytes']) + ' bytes).')


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


def run(env=None, tracker=None, *, backup_archive=False):
    env = os.environ if env is None else env
    repository = env.get('GITHUB_REPOSITORY')
    if repository != 'phil14-hub/war-haven-dashboard':
        raise ValueError('Portal synchronization is restricted to War Haven.')
    config = {'repository': repository, 'password': env['DASHBOARD_PASSWORD'], 'token': env.get('DASHBOARD_PUBLISH_TOKEN') or env['GITHUB_TOKEN']}
    tracker = tracker or github_collector.load_tracker()
    # Pin both encrypted objects to the same main-branch commit.
    head = tracker.github_request(config, 'GET', '/repos/'+repository+'/git/ref/heads/main')['object']['sha']
    client=shared_actions.Client(config['password'])
    archive_meta=tracker.github_history_record(config,ref=head)
    if not archive_meta:raise ValueError('The saved clan archive is missing. No publication was made.')
    if backup_archive:
        backup_clan_archive(config, tracker, client, head, archive_meta['sha'])
        return
    record=tracker.github_request(config,'GET','/repos/'+repository+'/contents/index.html?ref='+head)
    pair={'pageSha':record['sha'],'historySha':archive_meta['sha'],'commit':head}
    config['_publication_pair']=pair
    try:prior=client.request('/members/api/publication-source',{'read':True}).get('source')
    except shared_actions.SharedActionsError:prior=None
    same=prior and all(prior.get(k)==pair[k] for k in ('pageSha','historySha'))
    read_config={**config,'token':env.get('GITHUB_TOKEN') or config['token']}
    with phase('pages-confirmation'):
        github_published=bool(same and prior.get('pagesConfirmed')) or pages_contains_publication(read_config,tracker,pair['pageSha'],pair['historySha'])
    if same:
        result={'publication':prior['publication'],'reused':True}
        record_publication(client,result,config,github_published)
        reconcile(client,result,github_published)
        print('Verified source pair is unchanged; archive download, decryption and portal rebuild skipped.')
        return result
    with phase('archive-download-and-verify'):
        archive=tracker.github_history_record(config,ref=head,include_content=True)
        state=tracker.decrypt_history(archive['envelope'],config['password'])
        snapshot_audit.verify(state,tracker)
    if not record.get('content'):
        record=tracker.github_request(config,'GET','/repos/'+repository+'/git/blobs/'+record['sha'])
    document=base64.b64decode(record['content'],validate=False).decode('utf-8')
    with tempfile.TemporaryDirectory(prefix='war-haven-portal-sync-') as folder:
        path = Path(folder)/'index.html'
        path.write_text(document, encoding='utf-8')
        with phase('portal-publication'):
            result=member_exports.publish(state,path,client,config['password'],tracker)
            record_publication(client,result,config,github_published)
        reconcile(client,result,github_published)
    print('Member and leadership portal synchronized from the same saved revision.')
    return result


def reconcile(client,result,github_published):
    for kind in ('clan','recruitment'):
        try:client.request('/v1/refresh/reconcile',{'kind':kind,'publication':result['publication'],'githubPublished':github_published})
        except shared_actions.SharedActionsError:print('Portal data is current; an older progress entry will be reconciled on the next retry.')


def maintenance(env=None):
    env = os.environ if env is None else env
    if env.get('GITHUB_REPOSITORY') != 'phil14-hub/war-haven-dashboard':
        raise ValueError('Maintenance is restricted to War Haven.')
    # Machine authorization does not depend on archive decryption or email delivery.
    result = shared_actions.Client('').request('/members/api/maintenance')
    backup=result.get('backup') or {}
    if backup.get('status')!='saved':
        raise ValueError('Recovery backup was not confirmed; the previous complete backup is retained.')
    print('Encrypted website recovery backup confirmed: '+str(backup.get('createdAt'))+'; '+str(backup.get('tables'))+' tables; '+str(backup.get('objects'))+' storage objects.')
    print('Temporary account data and generated-publication retention checked. Archives and clan evidence are unchanged.')
    return result


if __name__ == '__main__':
    try:
        parser=argparse.ArgumentParser(description=__doc__)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--maintenance-only',action='store_true')
        mode.add_argument('--backup-clan-archive',action='store_true')
        args = parser.parse_args()
        if args.maintenance_only:
            maintenance()
        else:
            run(backup_archive=args.backup_clan_archive)
    except Exception as error:
        print('Portal synchronization retained the previous complete publication ('+type(error).__name__+').')
        raise SystemExit(1)
