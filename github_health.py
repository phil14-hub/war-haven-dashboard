"""Report workflow health without passwords, private logs or archive access."""
import argparse
import os
import shared_actions


def report(kind,status,env=None):
    env=os.environ if env is None else env
    if env.get('GITHUB_REPOSITORY')!='phil14-hub/war-haven-dashboard':
        raise ValueError('Health reports are restricted to War Haven.')
    return shared_actions.Client('').request('/members/api/collector-health',{
        'kind':kind,'status':status,'runId':env['GITHUB_RUN_ID'],
        'runNumber':int(env['GITHUB_RUN_NUMBER'])})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=['clan','recruitment','portal','code','war-watch','war-capture'],required=True)
    parser.add_argument('--status',choices=['running','success','failure','cancelled'],required=True)
    args=parser.parse_args()
    try:
        report(args.kind,args.status)
        print('Workflow health recorded.')
    except (ValueError,KeyError,shared_actions.SharedActionsError):
        print('::warning::Workflow health could not be recorded; collection and existing data are unaffected.')
