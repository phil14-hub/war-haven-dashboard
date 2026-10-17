"""Encrypted shared edits and dashboard refresh queue; provider tokens stay in Actions."""
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BACKEND_URL = 'https://portal.warhavenclan.com'
# The service requires current dashboard-passphrase proof on every data/action request.
ENABLED = True
CONTEXT = b'WarHavenSharedEdit:v1'


class SharedActionsError(Exception):
    pass


class Client:
    def __init__(self, password):
        self.password = password
        self.proof = None

    def request(self, path, payload=None, retry=True):
        try:
            if path != '/v1/challenge' and not self.proof:
                challenge = self.request('/v1/challenge')
                salt = base64.b64decode(challenge['salt'], validate=True)
                rounds = challenge['rounds']
                if len(salt) != 16 or not isinstance(rounds, int) or not 100000 <= rounds <= 2000000:
                    raise SharedActionsError('Invalid shared service challenge.')
                raw = hashlib.pbkdf2_hmac('sha256', self.password.encode(), salt, rounds, dklen=64)
                self.proof = base64.b64encode(raw[32:]).decode()
            headers = {'Content-Type': 'application/json',
                       'User-Agent': 'WarHavenDashboard/1.19 (+https://github.com/phil14-hub/war-haven-dashboard)'}
            if self.proof:
                headers['X-War-Haven-Proof'] = self.proof
            request = Request(BACKEND_URL + path,
                              data=json.dumps(payload or {}).encode(),
                              headers=headers, method='POST')
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as error:
            status = error.code
            error.close()
            if status == 401 and retry:
                self.proof = None
                return self.request(path, payload, retry=False)
            raise SharedActionsError('Shared service request failed (HTTP ' + str(status) + ').') from None
        except (ValueError, OSError, KeyError, TypeError):
            raise SharedActionsError('Shared service is temporarily unavailable.') from None


def decrypt_record(envelope, key, tracker):
    try:
        raw = base64.b64decode(key, validate=True)
        iv, ciphertext, tag = (base64.b64decode(envelope[n], validate=True)
                               for n in ('iv', 'ciphertext', 'tag'))
        if envelope.get('version') != 1 or len(raw) != 64 or len(iv) != 16 or len(tag) != 32 or not ciphertext or len(ciphertext) % 16 or len(ciphertext) > 24000:
            raise ValueError()
        expected = hmac.new(raw[32:], CONTEXT + iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, tag):
            raise ValueError()
        padded = tracker.aes_cbc_decrypt(raw[:32], iv, ciphertext)
        count = padded[-1]
        if not 1 <= count <= 16 or padded[-count:] != bytes([count]) * count:
            raise ValueError()
        value = json.loads(padded[:-count])
        if not isinstance(value, dict) or value.get('category') not in ('notes', 'lineupPlans'):
            raise ValueError()
        return value
    except (ValueError, KeyError, TypeError, IndexError):
        raise SharedActionsError('A shared record failed verification. Existing edits were retained.') from None


def prepare(state):
    if not ENABLED:
        return False
    current = state.get('sharedActions') or {}
    key = current.get('encryptionKey')
    if key is not None and len(base64.b64decode(key, validate=True)) != 64:
        raise SharedActionsError('The shared editing key is invalid.')
    state['sharedActions'] = {'version': 1, 'url': BACKEND_URL, 'enabled': True,
                              'encryptionKey': key or base64.b64encode(secrets.token_bytes(64)).decode()}
    return True


def pull(state, client, tracker):
    if not prepare(state):
        return
    result = client.request('/v1/records')
    edits = tracker.empty_edits() if hasattr(tracker, 'empty_edits') else {'notes': {}, 'lineupPlans': {}}
    for record in result.get('records', []):
        clear = decrypt_record(record['envelope'], state['sharedActions']['encryptionKey'], tracker)
        category, key, value = clear['category'], clear.get('key'), clear.get('value')
        if not isinstance(key, str) or not isinstance(value, dict) or category != record.get('kind'):
            raise SharedActionsError('Invalid shared record.')
        expected_id = hmac.new(base64.b64decode(state['sharedActions']['encryptionKey'])[32:], (category + ':' + key).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(record['id'], expected_id):
            raise SharedActionsError('A shared record failed identity verification.')
        if category == 'notes' and (tracker.normalize_tag(key) != key or not isinstance(value.get('text'), str) or len(value['text']) > 6000):
            raise SharedActionsError('Invalid shared note.')
        if category == 'lineupPlans':
            tracker.validate_lineup_edits({'lineupPlans': {key: value}})
        # The service timestamp resolves updates independently of device clocks.
        edits[category][key] = {**value, 'updatedAt': record['updatedAt']}
    merged = tracker.merge_edits(state.get('edits'), {})
    for category in ('notes', 'lineupPlans'):
        merged[category].update(edits[category])
    state['edits'] = merged


def pending(client, kind='clan'):
    if not ENABLED:
        return None
    request = client.request('/v1/refresh/status', {'kind': kind}).get('request')
    if not request:
        return None
    if request.get('status') == 'pending':
        return request
    if request.get('status') == 'running':
        deadline = datetime.fromisoformat(request['leaseUntil'].replace('Z', '+00:00'))
        if deadline <= datetime.now(timezone.utc):
            return request
    return None


class UpdateRequest:
    """A leased, independent update request. Status failure cannot undo a publication."""
    def __init__(self, client, kind, request=None):
        self.client, self.kind, self.request = client, kind, request
        self.lease = None
        if ENABLED and self.request is None:
            try:
                # A scheduled or owner-triggered run gets the same visible progress
                # as a browser request, without starting another collector.
                self.request = client.request('/v1/refresh/request', {'kind': kind})['request']
            except SharedActionsError:
                print('::warning::This run could not create a new progress entry; collection will continue.')

    def claim(self):
        if self.request:
            result = self.client.request('/v1/refresh/claim', {'kind': self.kind, 'id': self.request['id']})
            self.lease = result['request']['lease']

    def progress(self, phase, percent):
        if self.lease:
            try:
                self.client.request('/v1/refresh/progress', {'kind': self.kind, 'id': self.request['id'],
                                    'lease': self.lease, 'phase': phase, 'progress': percent})
            except SharedActionsError:
                print('::warning::Update progress could not be synchronized; collection continues.')

    def finish(self, result=None):
        if self.lease:
            try:
                self.client.request('/v1/refresh/finish', {'kind': self.kind, 'id': self.request['id'],
                                    'lease': self.lease, 'ok': bool(result and result.get('published')),
                                    'commit': result.get('commit') if result else None})
                print('Independent ' + self.kind + ' update status synchronized.')
            except SharedActionsError:
                print('::warning::Update status could not be synchronized. Check the latest dashboard before retrying.')

