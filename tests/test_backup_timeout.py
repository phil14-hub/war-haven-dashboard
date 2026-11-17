import io
import time
import unittest
from unittest.mock import patch

import shared_actions


class BackupTimeoutTests(unittest.TestCase):
    def test_only_backup_maintenance_receives_the_longer_timeout(self):
        for path, expected in [('/members/api/maintenance', 120),
                               ('/members/api/publication-source', 15),
                               ('/members/api/ingest', 15)]:
            client = shared_actions.Client('')
            client.machine_token = 'synthetic-collector-token'
            client.machine_until = time.time() + 240
            client.machine_audience = 'war-haven-collector'
            with patch.object(shared_actions, 'urlopen', return_value=io.BytesIO(b'{"ok":true}')) as request:
                self.assertEqual(client.request(path), {'ok': True})
                self.assertEqual(request.call_args.kwargs['timeout'], expected)
                self.assertEqual(request.call_args.args[0].get_header('Authorization'),
                                 'Bearer synthetic-collector-token')

    def test_staging_and_production_requests_never_reuse_the_other_audience(self):
        client = shared_actions.Client('')
        environment = {'ACTIONS_ID_TOKEN_REQUEST_URL': 'https://issuer.example/token',
                       'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'synthetic-auth-request'}
        responses = [io.BytesIO(b'{"value":"stage"}'), io.BytesIO(b'{}'),
                     io.BytesIO(b'{"value":"production"}'), io.BytesIO(b'{}')]
        with patch.dict(shared_actions.os.environ, environment), patch.object(shared_actions, 'urlopen', side_effect=responses) as send:
            client.request(shared_actions.CLAN_STORAGE_STAGING_PATH)
            client.request('/members/api/maintenance')
        id_stage, get_stage, id_prod, get_prod = (call.args[0] for call in send.call_args_list)
        self.assertTrue(id_stage.full_url.endswith('audience=war-haven-storage-staging'))
        self.assertEqual(get_stage.get_header('Authorization'), 'Bearer stage')
        self.assertTrue(id_prod.full_url.endswith('audience=war-haven-collector'))
        self.assertEqual(get_prod.get_header('Authorization'), 'Bearer production')
