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
            with patch.object(shared_actions, 'urlopen', return_value=io.BytesIO(b'{"ok":true}')) as request:
                self.assertEqual(client.request(path), {'ok': True})
                self.assertEqual(request.call_args.kwargs['timeout'], expected)
                self.assertEqual(request.call_args.args[0].get_header('Authorization'),
                                 'Bearer synthetic-collector-token')
