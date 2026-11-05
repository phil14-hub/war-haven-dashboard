"""Small, authenticated source associations. No archive contents or credentials are logged."""
import re
import time
from contextlib import contextmanager
import shared_actions

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
