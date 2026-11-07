"""Provision encrypted server-side refresh dispatch using the existing repository token."""
import argparse
import os
import shared_actions


def configure(env=None):
    env = os.environ if env is None else env
    if env.get('GITHUB_REPOSITORY') != 'phil14-hub/war-haven-dashboard':
        raise ValueError('Dispatch setup is restricted to War Haven.')
    token = env.get('DASHBOARD_PUBLISH_TOKEN', '').strip()
    if not token:
        raise ValueError('The configured repository publishing credential is required.')
    result = shared_actions.Client('').request('/members/api/refresh-dispatch', {'token': token})
    if not result.get('configured'):
        raise ValueError('Dispatch configuration was not confirmed.')
    print('Encrypted immediate refresh dispatch configured. Provider credentials remain server-side.')
    return result


def verify():
    result = shared_actions.Client('').request('/v1/refresh/request', {'kind':'clan', 'dispatch':True})
    request = result.get('request') or {}
    if request.get('dispatch', {}).get('status') != 'accepted':
        raise ValueError('Immediate dispatch was not confirmed. The saved request still has the scheduled fallback.')
    print('Immediate refresh accepted: request ' + request['id'] + '; requested at ' + request['requestedAt'])
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args=parser.parse_args()
    try:
        verify() if args.verify else configure()
    except Exception:
        # No provider response, token or request body is written to logs.
        print('::warning::Immediate refresh '+('verification' if args.verify else 'setup')+' unavailable. The scheduled fallback is retained.')
        if args.verify:
            raise SystemExit(1)
