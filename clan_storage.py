"""Read, verify and advance the isolated R2 clan release used by staging jobs."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.parse import urlencode

from shared_actions import CLAN_STORAGE_PATH, CLAN_STORAGE_STAGING_PATH, Client, SharedActionsError
from war_end_updates import iso, next_update


OBJECT_TYPES = {'archive': 'application/json', 'page': 'application/octet-stream'}
MAX_OBJECT_BYTES = 70 * 1024 * 1024


def staging_enabled(env):
    return env.get('WAR_HAVEN_CLAN_STORAGE_STAGE') == 'true'


def production_enabled(env):
    return env.get('WAR_HAVEN_CLAN_STORAGE_R2') == 'true' and not staging_enabled(env)


def sha(value, length):
    return isinstance(value, str) and len(value) == length and re.fullmatch('[a-f0-9]+', value) is not None


def reference(body):
    return {'sha256': hashlib.sha256(body).hexdigest(), 'size': len(body)}


def git_blob(tracker, config, digest):
    if not sha(digest, 40):
        raise ValueError('Invalid Git blob revision.')
    record = tracker.github_request(config, 'GET', '/repos/' + config['repository'] + '/git/blobs/' + digest)
    if record.get('encoding') != 'base64' or record.get('sha') != digest or not isinstance(record.get('content'), str):
        raise ValueError('Git did not return the pinned file.')
    body = base64.b64decode(''.join(record['content'].split()), validate=True)
    if hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() != digest:
        raise ValueError('The file did not match its saved Git revision.')
    return body


def verified_state(archive, tracker, password):
    state = tracker.decrypt_history(json.loads(archive), password)
    if tracker.normalize_tag(state.get('clanTag')) != tracker.DEFAULT_CLAN_TAG:
        raise ValueError('The archive belongs to a different clan.')
    return state


def validated_index(value):
    if not isinstance(value, dict) or value.get('version') != 1 or not sha(value.get('source'), 40):
        raise ValueError('The staged clan release index is invalid.')
    previous = value.get('previousRevision')
    if previous is not None and not sha(previous, 64):
        raise ValueError('The previous storage revision is invalid.')
    target = value['nextWarUpdateAt']
    if target is not None and (not isinstance(target, str) or iso(datetime.fromisoformat(target)) != target):
        raise ValueError('The staged war timing record is invalid.')
    canonical = dict(version=1, previousRevision=previous, source=value['source'], nextWarUpdateAt=target)
    for kind in OBJECT_TYPES:
        entry = value.get(kind)
        if not isinstance(entry, dict) or not sha(entry.get('sha256'), 64) or type(entry.get('size')) is not int or not 0 < entry['size'] <= MAX_OBJECT_BYTES:
            raise ValueError('The staged release object reference is invalid.')
        canonical[kind] = {'sha256': entry['sha256'], 'size': entry['size']}
    if 'collectorCredential' in value:
        credential = value['collectorCredential']
        if (not isinstance(credential, dict) or not sha(credential.get('rotationOf'), 64) or
                not isinstance(credential.get('sealed'), str) or not re.fullmatch(r'[A-Za-z0-9+/=]{40,1500}', credential['sealed'])):
            raise ValueError('The staged collector credential reference is invalid.')
        canonical['collectorCredential'] = {'rotationOf': credential['rotationOf'], 'sealed': credential['sealed']}
    revision = hashlib.sha256(json.dumps(canonical, separators=(',', ':')).encode()).hexdigest()
    if revision != value.get('revision'):
        raise ValueError('The staged release index checksum does not match.')
    return {**canonical, 'revision': revision}


class StagedClanStorage:
    def __init__(self, client=None, *, production=False):
        self.client = client if client is not None else Client('')
        self.path = CLAN_STORAGE_PATH if production else CLAN_STORAGE_STAGING_PATH

    def current(self, *, allow_empty=False):
        try:
            return validated_index(self.client.request(self.path, method='GET')['index'])
        except SharedActionsError as error:
            if allow_empty and error.status == 404:
                return None
            raise

    def release(self, revision):
        if not sha(revision, 64):
            raise ValueError('Expected a 64-character R2 release revision.')
        response = self.client.request(self.path + '?revision=' + revision, method='GET')
        index = validated_index(response['index'])
        if index['revision'] != revision:
            raise ValueError('R2 returned a different release revision.')
        return index

    def release_password(self, index, fallback):
        if 'collectorCredential' not in index:
            return fallback
        reply = self.client.request(self.path + '?credential=' + index['revision'], method='GET')
        if reply.get('revision') != index['revision'] or not isinstance(reply.get('password'), str) or not reply['password']:
            raise ValueError('The collector credential does not match the staged release.')
        return reply['password']

    def object_path(self, kind, entry):
        return self.path + '?' + urlencode({'kind': kind, 'sha256': entry['sha256']})

    def read(self, kind, index):
        entry = index[kind]
        result = self.client.request(self.object_path(kind, entry), method='GET')
        if result.get('sha256') != entry['sha256'] or reference(result['body']) != entry:
            raise ValueError('The staged release object failed verification.')
        return result['body']

    def ensure_object(self, kind, body, entry):
        path = self.object_path(kind, entry)
        if not self.client.request(path, method='HEAD'):
            try:
                saved = self.client.request(path, method='PUT', body=body, extra_headers={'Content-Type': OBJECT_TYPES[kind]})
                if any(saved.get(key) != value for key, value in entry.items()):
                    raise ValueError('R2 did not confirm the staged release object.')
            except SharedActionsError as error:
                if error.status not in (None, 503) or not self.client.request(path, method='HEAD'):
                    raise

    def store(self, previous, source, target, archive, page):
        entries = {'archive': reference(archive), 'page': reference(page)}
        candidate = {'source': source, 'nextWarUpdateAt': iso(target) if target else None, **entries}
        if previous and all(previous[key] == value for key, value in candidate.items()):
            current = self.current()
            if current['revision'] != previous['revision']:
                raise ValueError('The staged release advanced. Retry with the latest saved version.')
            return current
        payload = {'expectedRevision': previous['revision'] if previous else None, **candidate}
        for kind, body in (('archive', archive), ('page', page)):
            self.ensure_object(kind, body, entries[kind])
        try:
            saved = validated_index(self.client.request(self.path, payload)['index'])
        except SharedActionsError as error:
            if error.status not in (None, 409, 503):
                raise
            saved = self.current(allow_empty=True)
            if saved is None:
                raise
        if saved['previousRevision'] != payload['expectedRevision'] or any(saved[key] != value for key, value in candidate.items()):
            raise ValueError('The staged release advanced. Retry with the latest saved version.')
        return saved

    def restore(self, tracker, password):
        index = self.current()
        archive = self.read('archive', index)
        return index, archive, verified_state(archive, tracker, self.release_password(index, password))


class StagedUpdate:
    """Use the production collector and renderer with an isolated storage and publication sink."""
    def __init__(self, storage, tracker, config):
        self.storage = storage
        self.index = storage.current()
        self.password = storage.release_password(self.index, config['password'])
        self.archive = storage.read('archive', self.index)
        self.state = verified_state(self.archive, tracker, self.password)
        self.fingerprint = tracker.archive_fingerprint(self.state)
        self.tracker = tracker
        self.client = storage.client

    def progress(self, phase, percent):
        print(f'Staged update: {phase} ({percent}%).')

    def save(self, state, dashboard, source=None, view=None):
        index = self.commit_release(state, dashboard, source, view)
        print('Verified staged clan release and both dashboard projections: ' + index['revision'])
        return {'stagedRevision': index['revision']}

    def commit_release(self, state, dashboard, source=None, view=None):
        from member_exports import verify_staged_projection

        verify_staged_projection(state, dashboard, self.password, self.tracker, view)
        archive = self.archive
        if self.tracker.archive_fingerprint(state) != self.fingerprint:
            envelope = self.tracker.encrypt_history(state, self.password)
            archive = json.dumps(envelope, separators=(',', ':')).encode()
        target = next_update(state, datetime.now(timezone.utc))
        return self.storage.store(self.index, source or self.index['source'], target, archive, dashboard.read_bytes())
