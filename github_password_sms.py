"""Notify the leader of a published password change; credentials stay in Actions."""
import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CHANGE_MESSAGE = 'Change dashboard password and re-encrypt saved clan history'
REPOSITORY = 'phil14-hub/war-haven-dashboard'


def notification(env, event):
    if env.get('PASSWORD_SMS_ENABLED') != 'true':
        return None
    if env.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('The alert is restricted to the War Haven repository.')
    commit = event.get('head_commit') or {}
    if (commit.get('message') or '').split('\n', 1)[0] != CHANGE_MESSAGE:
        return None
    names = ('TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER', 'PASSWORD_ALERT_TO')
    values = {name: env.get(name, '').strip() for name in names}
    missing = [name for name in names if not values[name]]
    if missing:
        raise ValueError('Add these Actions secrets: ' + ', '.join(missing))
    if not re.fullmatch(r'AC[0-9a-fA-F]{32}', values['TWILIO_ACCOUNT_SID']):
        raise ValueError('TWILIO_ACCOUNT_SID is not a valid account SID.')
    for name in ('TWILIO_FROM_NUMBER', 'PASSWORD_ALERT_TO'):
        if not re.fullmatch(r'\+[1-9][0-9]{7,14}', values[name]):
            raise ValueError(name + ' must use international format, such as +1 followed by the number.')
    try:
        changed = datetime.fromisoformat(commit['timestamp'].replace('Z', '+00:00'))
        stamp = changed.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except (KeyError, ValueError, TypeError):
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    body = ('War Haven: shared dashboard password changed at ' + stamp +
            '. If this was not you, review your GitHub account.')
    return values, body


def send(env, event, opener=urlopen):
    prepared = notification(env, event)
    if prepared is None:
        return {'skipped': True}
    values, body = prepared
    sid = values['TWILIO_ACCOUNT_SID']
    credentials = base64.b64encode((sid + ':' + values['TWILIO_AUTH_TOKEN']).encode()).decode('ascii')
    payload = urlencode({'From': values['TWILIO_FROM_NUMBER'], 'To': values['PASSWORD_ALERT_TO'], 'Body': body})
    request = Request('https://api.twilio.com/2010-04-01/Accounts/' + sid + '/Messages.json',
                      method='POST', data=payload.encode('utf-8'), headers={
                          'Authorization': 'Basic ' + credentials,
                          'Content-Type': 'application/x-www-form-urlencoded',
                          'User-Agent': 'War-Haven-Password-Alert/1.0',
                      })
    # Do not retry an ambiguous POST: Twilio may already have accepted it.
    # Repeated blind POSTs could send duplicate texts and incur duplicate charges.
    with opener(request, timeout=20) as response:
        result = json.loads(response.read(65536))
    status = result.get('status')
    if not result.get('sid') or status not in ('accepted', 'queued', 'sending', 'sent', 'delivered'):
        raise ValueError('The SMS provider did not accept this alert. Check the Twilio console.')
    return {'submitted': True, 'status': status}


def main():
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        raise ValueError('Run this notifier through its GitHub Actions workflow.')
    event = json.loads(Path(event_path).read_text())
    result = send(os.environ, event)
    if result.get('skipped'):
        print('Text alert skipped: disabled or this commit did not change the shared password.')
    else:
        print('Password change alert accepted by Twilio. Delivery status: ' + result['status'] + '.')
        print('Carrier delivery is asynchronous. Check Twilio for final delivery status.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, HTTPError, URLError) as error:
        # Never print provider responses, phone numbers, tokens or the event payload.
        print('Text alert stopped (' + type(error).__name__ + '). Check the configured Actions secrets and Twilio delivery permissions.')
        raise SystemExit(1)
