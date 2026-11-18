"""Apply lossless storage changes only after verifying complete recovery coverage."""
import hashlib
import json
import os
from clan_storage import StagedClanStorage, verified_state
from github_collector import load_tracker
from github_sync_portal import read_clan_archive_backup
from shared_actions import CLAN_STORAGE_PATH, Client
from war_end_updates import timestamp


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def main():
    client = Client('')
    storage = StagedClanStorage(client, production=True)
    tracker = load_tracker()
    password = os.environ['DASHBOARD_PASSWORD']
    before = client.request(CLAN_STORAGE_PATH + '?inventory=2', method='GET')
    plan = client.request(CLAN_STORAGE_PATH + '?retention=1', method='GET')
    index, archive, state = storage.restore(tracker, password)
    if index['revision'] != plan['revision']:
        raise ValueError('Storage advanced before verification. Retry on current main.')
    page = storage.read('page', index)
    if index.get('previousRevision'):
        previous = storage.release(index['previousRevision'])
        verified_state(storage.read('archive', previous), tracker, storage.release_password(previous, password))
        storage.read('page', previous)
    config = {'password': password}
    def days():
        return {day: hashlib.sha256(read_clan_archive_backup(config, tracker, client, day, production=True)).hexdigest()
                for day in plan['dailyDays']}
    recovery_before = days()
    # Store and decrypt a completely self-contained v2 archive. No state fields
    # are dropped. Old daily points and the prior release remain restorable.
    release_password = storage.release_password(index, password)
    packed = tracker.archive_document(state)
    if tracker.restore_archive_document(packed) != state:
        raise ValueError('Packed archive did not preserve the complete logical state.')
    if json.loads(archive).get('version') == 1:
        replacement = json.dumps(tracker.encrypt_history(state, release_password), separators=(',', ':')).encode()
        if fingerprint(verified_state(replacement, tracker, release_password)) != fingerprint(state):
            raise ValueError('Archive migration changed saved data.')
        index = storage.store(index, os.environ['GITHUB_SHA'], timestamp(index['nextWarUpdateAt']), replacement, page)
        archive = replacement
    result = client.request(CLAN_STORAGE_PATH + '?optimize=1', method='POST')
    restored_index, restored_archive, restored = storage.restore(tracker, password)
    if restored_index != index or restored_archive != archive or storage.read('page', index) != page or fingerprint(restored) != fingerprint(state):
        raise ValueError('Storage verification failed after optimization.')
    if recovery_before != days():
        raise ValueError('A retained recovery point changed.')
    # Re-run to prove that compression migration does not create another copy.
    retry = client.request(CLAN_STORAGE_PATH + '?optimize=1', method='POST')
    if retry['compressedObjects'] or retry['savedBytes']:
        raise ValueError('Publication compression did not converge.')
    after = client.request(CLAN_STORAGE_PATH + '?inventory=2', method='GET')
    print(json.dumps({'before': before, 'after': after, 'optimization': result,
                      'logicalStateSHA256': fingerprint(state), 'allLogicalFieldsPreserved': True,
                      'verifiedDailyDates': sorted(recovery_before), 'retry': retry,
                      'archiveLogicalBytes': len(json.dumps(state, ensure_ascii=False, separators=(',', ':')).encode()),
                      'archiveStoredDocumentBytes': len(json.dumps(packed, ensure_ascii=False, separators=(',', ':')).encode()),
                      'revision': index['revision']}))


if __name__ == '__main__':
    main()
