"""Small, authenticated source associations. No archive contents or credentials are logged."""
import re
import time
from contextlib import contextmanager
import shared_actions
import member_exports

@contextmanager
def phase(name):
    started=time.monotonic()
    try:yield
    finally:print('Phase '+name+': '+format(time.monotonic()-started,'.2f')+' seconds')

def record(client,result,config,pages_confirmed=False):
    pair=config.get('_publication_pair')
    if not pair or not result.get('publication'):return
    try:
        client.request('/members/api/publication-source',{'publication':result['publication'],'source':{**pair,'pagesConfirmed':bool(pages_confirmed)}})
    except shared_actions.SharedActionsError:
        print('Publication is saved; source association will be retried independently.')


def publish_r2(state, dashboard, client, config, tracker, index, view=None):
    """Publish the portal from a verified release independently of Pages."""
    with phase('portal-publication'):
        publication = member_exports.publish(state, dashboard, client, config['password'], tracker, view=view)
    config['_publication_pair'] = {
        'r2Revision': index['revision'], 'commit': index['source'],
        'pageSha': index['page']['sha256'], 'historySha': index['archive']['sha256'],
    }
    record(client, publication, config)
    return publication


def save_r2(release, state, dashboard, client, config, tracker, source=None, view=None):
    with phase('save-r2-release'):
        index = release.commit_release(state, dashboard, source, view)
    result = {'r2Revision': index['revision'], 'partial': True,
              'components': {'backup': True, 'github': False, 'portal': False}}
    try:
        publish_r2(state, dashboard, client, config, tracker, index, view)
    except Exception:
        print('::warning::The verified R2 release is saved. Independent portal sync will retry it.')
    else:
        result['partial'] = False
        result['components']['portal'] = True
    return result
