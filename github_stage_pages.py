"""Build a GitHub Pages artifact from one verified R2 staging release."""
import argparse
from pathlib import Path

from clan_storage import StagedClanStorage, sha, validated_index
from shared_actions import CLAN_STORAGE_STAGING_PATH


def stage_pages(output, revision=None, storage=None):
    storage = StagedClanStorage() if storage is None else storage
    if revision is None:
        index = storage.current()
    else:
        if not sha(revision, 64):
            raise ValueError('Expected a 64-character R2 release revision.')
        response = storage.client.request(CLAN_STORAGE_STAGING_PATH + '?revision=' + revision, method='GET')
        index = validated_index(response['index'])
        if index['revision'] != revision:
            raise ValueError('R2 returned a different release revision.')
    page = storage.read('page', index)
    if not page.lower().startswith(b'<!doctype html>') or b'id="protected-payload"' not in page:
        raise ValueError('The staged page is missing its encrypted dashboard payload.')
    output.mkdir(parents=True)
    (output / 'index.html').write_bytes(page)
    (output / '.nojekyll').touch()
    print(f"Pages artifact staged from R2 release {index['revision']} ({len(page)} uncompressed bytes, SHA-256 {index['page']['sha256']}).")
    return index['revision']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New artifact directory')
    parser.add_argument('--revision', help='Rebuild the artifact from a saved immutable release')
    args = parser.parse_args()
    try:
        stage_pages(args.output, args.revision)
    except Exception as error:
        parser.exit(1, 'Pages staging failed (' + type(error).__name__ + '). Live deployment was not requested.\n')
