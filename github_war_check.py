"""Inspect encrypted saved war times without calling Clash or publishing data."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time

from github_collector import load_tracker
from war_end_updates import next_update


def check(env=None, *, wait=False, now=None, sleep=time.sleep):
    env = os.environ if env is None else env
    password = env.get('DASHBOARD_PASSWORD')
    if not password:
        raise ValueError('The existing dashboard password secret is required.')
    tracker = load_tracker()
    path = Path(__file__).resolve().parent / 'data' / 'war_tracker_state.enc.json'
    state = tracker.decrypt_history(json.loads(path.read_text(encoding='utf-8')), password)
    if state.get('clanTag') != tracker.DEFAULT_CLAN_TAG:
        raise ValueError('The saved archive belongs to a different clan.')
    clock = now or (lambda: datetime.now(timezone.utc))
    target = next_update(state, clock())
    if target is None or target > clock() + timedelta(minutes=5):
        print('No recorded war needs its final-results update yet.')
        return False
    if wait:
        # GitHub starts the watcher near the target. Wait only for the remaining
        # part of the five-minute grace period; never refresh before it.
        while target > clock():
            sleep(max(0, min(30, (target - clock()).total_seconds())))
    print('A recorded war is ready for its automatic final-results update.'
          if wait else 'A recorded war final-results update is due shortly.')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait', action='store_true')
    args = parser.parse_args()
    try:
        should_run = check(wait=args.wait)
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            with open(output, 'a', encoding='utf-8') as stream:
                stream.write('due=' + str(should_run).lower() + '\n')
    except (ValueError, OSError, TypeError):
        print('Could not verify the encrypted war schedule. Existing history was not changed.')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
