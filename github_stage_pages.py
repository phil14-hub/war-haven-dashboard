"""Build a GitHub Pages artifact from one verified R2 release."""
import argparse
from pathlib import Path

from clan_storage import StagedClanStorage, reference, sha
from shared_actions import CLAN_STORAGE_PAGES_PATH, Client


def stage_pages(output, revision=None, storage=None):
    storage = StagedClanStorage() if storage is None else storage
    index = storage.current() if revision is None else storage.release(revision)
    page = storage.read('page', index)
    write_pages(output, page, index['revision'], index['page']['sha256'])
    return index['revision']


def stage_production_pages(output, revision, client=None):
    if not sha(revision, 64):
        raise ValueError('Production Pages requires an exact R2 release revision.')
    client = Client('') if client is None else client
    result = client.request(CLAN_STORAGE_PAGES_PATH + '?revision=' + revision, method='GET')
    page = result['body']
    digest = reference(page)['sha256']
    if result.get('revision') != revision or result.get('sha256') != digest:
        raise ValueError('The production Pages release did not verify.')
    write_pages(output, page, revision, digest)
    return revision


def check_production_revision(revision):
    if not sha(revision, 64):
        raise ValueError('Production Pages requires an exact R2 release revision.')
    if not Client('').request(CLAN_STORAGE_PAGES_PATH + '?revision=' + revision, method='HEAD'):
        raise ValueError('The requested production Pages release is unavailable.')


def write_pages(output, page, revision, digest):
    if not page.lower().startswith(b'<!doctype html>') or b'id="protected-payload"' not in page:
        raise ValueError('The staged page is missing its encrypted dashboard payload.')
    output.mkdir(parents=True)
    (output / 'index.html').write_bytes(page)
    (output / '.nojekyll').touch()
    print(f'Pages artifact staged from R2 release {revision} ({len(page)} uncompressed bytes, SHA-256 {digest}).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, help='New artifact directory')
    parser.add_argument('--revision', help='Rebuild the artifact from a saved immutable release')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--production', action='store_true', help='Read the current production release with Pages-only authorization')
    mode.add_argument('--check-current', action='store_true', help='Verify the production revision without downloading the page')
    args = parser.parse_args()
    if args.output is None and not args.check_current:
        parser.error('An output directory is required to build a Pages artifact.')
    try:
        if args.check_current:
            check_production_revision(args.revision)
        elif args.production:
            stage_production_pages(args.output, args.revision)
        else:
            stage_pages(args.output, args.revision)
    except Exception as error:
        parser.exit(1, 'Pages staging failed (' + type(error).__name__ + '). Live deployment was not requested.\n')
