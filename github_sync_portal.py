"""Retry member and leadership portal publication without collecting Clash data."""
import base64
import hashlib
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
import github_collector
import member_exports
import shared_actions
import snapshot_audit
import argparse
from publication_sync import phase,publish_r2,record as record_publication
from clan_storage import StagedClanStorage, git_blob, production_enabled, reference, sha, staging_enabled, verified_state
from war_end_updates import next_update


def read_clan_archive_backup(config, tracker, client, day=None, *, staged=False, production=False):
    """Verify a stored archive in memory without replacing any live data."""
    endpoint = shared_actions.CLAN_STORAGE_BACKUP_PATH if production else (
        shared_actions.CLAN_STORAGE_STAGING_BACKUP_PATH if staged else shared_actions.CLAN_ARCHIVE_BACKUP_PATH)
    if day:
        endpoint += '?' + urlencode({'day': day})
    saved = client.request(endpoint, method='GET')
    body = saved['body']
    if hashlib.sha256(body).hexdigest() != saved.get('sha256') or not re.fullmatch('[a-f0-9]{40}', saved.get('source') or ''):
        raise ValueError('The private backup did not match its saved checksum and revision.')
    if (staged or production) and not sha(saved.get('revision'), 64):
        raise ValueError('The backup is missing its R2 archive revision.')
    password = config['password']
    if staged or production:
        storage = StagedClanStorage(client, production=True) if production else StagedClanStorage(client)
        index = storage.release(saved['revision'])
        if index['archive']['sha256'] != saved['sha256'] or index['source'] != saved['source']:
            raise ValueError('The staging backup does not match the referenced release.')
        password = storage.release_password(index, password)
    state = tracker.decrypt_history(json.loads(body), password)
    if tracker.normalize_tag(state.get('clanTag')) != tracker.DEFAULT_CLAN_TAG:
        raise ValueError('The private backup belongs to a different clan.')
    print('Private clan archive restored and verified in memory (' + str(len(body)) + ' bytes).')
    return body


def backup_clan_archive(config, tracker, client, commit, archive_sha, *, verify_restore=False):
    """Copy a verified Git archive to the private daily backup, keeping Git authoritative."""
    with phase('clan-archive-backup'):
        endpoint = shared_actions.CLAN_ARCHIVE_BACKUP_PATH
        if client.request(endpoint, method='HEAD'):
            print('A verified encrypted clan archive backup already exists for today.')
            if verify_restore:
                read_clan_archive_backup(config, tracker, client)
            return
        body = git_blob(tracker, config, archive_sha)
        verified_state(body, tracker, config['password'])
        saved = save_daily_backup(client, endpoint, body, commit)
        if verify_restore:
            restored = read_clan_archive_backup(config, tracker, client, saved['day'])
            if saved.get('reused') is not True and restored != body:
                raise ValueError('The private backup did not match the uploaded bytes.')


def save_daily_backup(client, endpoint, body, source, *, revision=None):
    checksum = hashlib.sha256(body).hexdigest()
    headers = {'X-Archive-SHA256': checksum, 'X-Archive-Source': source}
    if revision is not None:
        headers['X-Archive-Revision'] = revision
    saved = client.request(endpoint, body=body, extra_headers=headers)
    if saved.get('status') != 'saved' or not re.fullmatch('[a-f0-9]{64}', saved.get('sha256') or ''):
        raise ValueError('The private daily clan archive backup was not confirmed.')
    if saved.get('reused') is not True and (saved['sha256'] != checksum or saved.get('source') != source or
                                           saved.get('bytes') != len(body) or saved.get('revision') != revision):
        raise ValueError('The private daily clan archive backup did not match the verified archive.')
    print('Encrypted clan archive backup confirmed for ' + saved['day'] + ' (' + str(saved['bytes']) + ' bytes).')
    return saved


def release_backup(config, tracker, storage, *, verify=False, production=False):
    endpoint = shared_actions.CLAN_STORAGE_BACKUP_PATH if production else shared_actions.CLAN_STORAGE_STAGING_BACKUP_PATH
    if storage.client.request(endpoint, method='HEAD'):
        if verify:
            read_clan_archive_backup(config, tracker, storage.client, staged=not production, production=production)
        print('A verified R2 backup already exists for today.')
        return
    index, archive, _ = storage.restore(tracker, config['password'])
    saved = save_daily_backup(storage.client, endpoint, archive, index['source'], revision=index['revision'])
    if verify:
        restored = read_clan_archive_backup(config, tracker, storage.client, saved['day'],
                                            staged=not production, production=production)
        if not saved['reused'] and restored != archive:
            raise ValueError('The daily backup differs from the saved release.')


def stage_release(config, tracker, storage, *, seed=False, backup=False, verify_backup=False):
    """Seed from one authenticated Git commit, or retry from an immutable R2 release."""
    if backup or verify_backup:
        return release_backup(config, tracker, storage, verify=verify_backup)

    password = config['password']
    current = storage.current(allow_empty=seed)
    if seed and current is None:
        root = '/repos/' + config['repository']
        source = tracker.github_request(config, 'GET', root + '/git/ref/heads/main')['object']['sha']
        if not re.fullmatch('[a-f0-9]{40}', source):
            raise ValueError('Git did not return a valid source revision.')
        archive_meta = tracker.github_history_record(config, ref=source)
        if not archive_meta:
            raise ValueError('The saved Git clan archive is missing.')
        page_meta = tracker.github_request(config, 'GET', root + '/contents/index.html?ref=' + source)
        archive = git_blob(tracker, config, archive_meta['sha'])
        page = git_blob(tracker, config, page_meta['sha'])
        state = verified_state(archive, tracker, password)
    else:
        password = storage.release_password(current, password)
        state = verified_state(storage.read('archive', current), tracker, password)
        page = storage.read('page', current)
    view = member_exports.build_snapshot(state, tracker)
    snapshot_audit.verify(state, tracker, view=view)
    with tempfile.TemporaryDirectory(prefix='war-haven-staged-portal-') as folder:
        dashboard = Path(folder) / 'index.html'
        dashboard.write_bytes(page)
        member_exports.verify_staged_projection(state, dashboard, password, tracker, view)
    if seed and current is None:
        current = storage.store(None, source, next_update(state), archive, page)
        if storage.read('archive', current) != archive or storage.read('page', current) != page:
            raise ValueError('The staged files differ from the pinned Git revision.')
    print('Staged portal inputs verified against archive revision ' + current['revision'] + '.')
    return {'stagedRevision': current['revision'], 'members': len(view['members'])}


def seed_production(config, tracker, storage, source):
    if not sha(source, 40):
        raise ValueError('Expected the full pinned main commit for the R2 seed.')
    root = '/repos/' + config['repository']
    ref = root + '/git/ref/heads/main'
    if tracker.github_request(config, 'GET', ref)['object']['sha'] != source:
        raise ValueError('Main advanced. Pin and verify a new checkpoint before seeding.')
    metadata = tracker.github_history_record(config, ref=source)
    if not metadata:
        raise ValueError('The pinned Git archive is unavailable.')
    page_meta = tracker.github_request(config, 'GET', root + '/contents/index.html?ref=' + source)
    archive, page = (git_blob(tracker, config, digest) for digest in (metadata['sha'], page_meta['sha']))
    state = verified_state(archive, tracker, config['password'])
    view = member_exports.build_snapshot(state, tracker)
    snapshot_audit.verify(state, tracker, view=view)
    with tempfile.TemporaryDirectory(prefix='war-haven-r2-seed-') as directory:
        dashboard = Path(directory) / 'index.html'
        dashboard.write_bytes(page)
        member_exports.verify_staged_projection(state, dashboard, config['password'], tracker, view)
    current = storage.current(allow_empty=True)
    if current is None:
        if tracker.github_request(config, 'GET', ref)['object']['sha'] != source:
            raise ValueError('Main advanced while verifying the checkpoint. Production was not seeded.')
        current = storage.store(None, source, next_update(state), archive, page)
    if (current['source'] != source or current['archive'] != reference(archive) or current['page'] != reference(page) or
            storage.read('archive', current) != archive or storage.read('page', current) != page):
        raise ValueError('Existing production R2 release differs from the checkpoint. It was retained.')
    print('Verified production R2 seed revision ' + current['revision'] + '.')
    return current


def sync_r2(config, tracker, storage):
    client = storage.client
    index = storage.current()
    try:
        prior = client.request('/members/api/publication-source', {'read': True}).get('source')
    except shared_actions.SharedActionsError:
        prior = None
    if prior and prior.get('r2Revision') == index['revision']:
        publication = {'publication': prior['publication'], 'reused': True}
    else:
        config['password'] = storage.release_password(index, config['password'])
        state = verified_state(storage.read('archive', index), tracker, config['password'])
        view = member_exports.build_snapshot(state, tracker)
        snapshot_audit.verify(state, tracker, view=view)
        with tempfile.TemporaryDirectory(prefix='war-haven-r2-sync-') as directory:
            dashboard = Path(directory) / 'index.html'
            dashboard.write_bytes(storage.read('page', index))
            member_exports.verify_staged_projection(state, dashboard, config['password'], tracker, view)
            publication = publish_r2(state, dashboard, client, config, tracker, index, view)
    reconcile(client, publication, bool(prior and prior.get('r2Revision') == index['revision'] and prior.get('pagesConfirmed')))
    return publication


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


def run(env=None, tracker=None, *, backup_archive=False, verify_backup=False, seed_staging=False, seed_revision=None):
    env = os.environ if env is None else env
    repository = env.get('GITHUB_REPOSITORY')
    if repository != 'phil14-hub/war-haven-dashboard':
        raise ValueError('Portal synchronization is restricted to War Haven.')
    config = {'repository': repository, 'password': env['DASHBOARD_PASSWORD'], 'token': env.get('DASHBOARD_PUBLISH_TOKEN') or env['GITHUB_TOKEN']}
    tracker = tracker or github_collector.load_tracker()
    if staging_enabled(env):
        return stage_release(config, tracker, StagedClanStorage(), seed=seed_staging, backup=backup_archive, verify_backup=verify_backup)
    if seed_staging:
        raise ValueError('Seeding requires the staged clan storage path.')
    if seed_revision is not None:
        if env.get('GITHUB_REF') != 'refs/heads/main' or env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
            raise ValueError('Production seeding requires the manually dispatched main workflow.')
        return seed_production(config, tracker, StagedClanStorage(production=True), seed_revision)
    if production_enabled(env):
        storage = StagedClanStorage(production=True)
        if backup_archive or verify_backup:
            return release_backup(config, tracker, storage, verify=True, production=True)
        return sync_r2(config, tracker, storage)
    # Pin both encrypted objects to the same main-branch commit.
    head = tracker.github_request(config, 'GET', '/repos/'+repository+'/git/ref/heads/main')['object']['sha']
    client=shared_actions.Client(config['password'])
    archive_meta=tracker.github_history_record(config,ref=head)
    if not archive_meta:raise ValueError('The saved clan archive is missing. No publication was made.')
    if backup_archive or verify_backup:
        backup_clan_archive(config, tracker, client, head, archive_meta['sha'], verify_restore=verify_backup)
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
    if staging_enabled(env):
        raise ValueError('Use the staging backup operation for the isolated release.')
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
        mode.add_argument('--verify-clan-archive-backup',action='store_true')
        mode.add_argument('--verify-archive-day',type=date.fromisoformat)
        mode.add_argument('--seed-r2-staging', action='store_true')
        mode.add_argument('--seed-r2-production')
        args = parser.parse_args()
        if args.maintenance_only:
            maintenance()
        elif args.verify_archive_day:
            env = os.environ
            if env.get('GITHUB_REPOSITORY') != 'phil14-hub/war-haven-dashboard':
                raise ValueError('Clan archive verification is restricted to War Haven.')
            config = {'password': env['DASHBOARD_PASSWORD']}
            tracker = github_collector.load_tracker()
            client = shared_actions.Client(config['password'])
            day = args.verify_archive_day.isoformat()
            try:
                read_clan_archive_backup(config, tracker, client, day,
                                         staged=staging_enabled(env), production=production_enabled(env))
            except shared_actions.SharedActionsError as error:
                if not production_enabled(env) or error.status != 404:
                    raise
                read_clan_archive_backup(config, tracker, client, day)
        else:
            run(backup_archive=args.backup_clan_archive, verify_backup=args.verify_clan_archive_backup,
                seed_staging=args.seed_r2_staging, seed_revision=args.seed_r2_production)
    except Exception as error:
        print('Portal synchronization retained the previous complete publication ('+type(error).__name__+').')
        raise SystemExit(1)
