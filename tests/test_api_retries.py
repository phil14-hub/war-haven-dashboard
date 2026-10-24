import contextlib
import copy
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

import Clash_War_Tracker as tracker


def failure(status):
    return HTTPError('https://example.invalid', status, 'Synthetic failure', {}, io.BytesIO(b'{}'))


class RetryTests(unittest.TestCase):
    def test_transient_server_errors_recover_on_next_attempt(self):
        for status in (500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 529, 599, 429):
            with self.subTest(status=status), patch.object(tracker, 'urlopen', side_effect=[failure(status), io.BytesIO(b'{"ok": true}')]) as request, patch.object(tracker.time, 'sleep') as pause:
                self.assertEqual(tracker.OfficialAPI(['fixture']).get('/test'), {'ok': True})
                self.assertEqual(request.call_count, 2)
                pause.assert_called_once_with(1)

    def test_repeated_520_is_bounded_and_does_not_switch_keys(self):
        with patch.object(tracker, 'urlopen', side_effect=[failure(520) for _ in range(3)]) as request, patch.object(tracker.time, 'sleep') as pause:
            with self.assertRaises(tracker.APIError) as error:
                tracker.OfficialAPI(['first', 'second']).get('/test')
            self.assertEqual(error.exception.status, 520)
            self.assertEqual(request.call_count, 3)
            self.assertEqual([call.args[0] for call in pause.call_args_list], [1, 2])

    def test_unavailable_resource_is_not_retried(self):
        with patch.object(tracker, 'urlopen', side_effect=failure(404)) as request, patch.object(tracker.time, 'sleep') as pause:
            with self.assertRaises(tracker.APIError):
                tracker.OfficialAPI(['fixture']).get('/test')
            self.assertEqual(request.call_count, 1)
            pause.assert_not_called()

    def test_profile_failure_names_player_and_preserves_saved_profile(self):
        state=tracker.new_state(tracker.DEFAULT_CLAN_TAG)
        old={'tag':'#P0Y', 'name':'Saved player', 'townHallLevel':12, 'troops':[], 'heroes':[]}
        state['profiles']['#P0Y']=copy.deepcopy(old)
        def get(path):
            if path.startswith('/players/'):
                raise tracker.APIError(520)
            if path.endswith('/warlog?limit=50'):
                raise tracker.APIError(520)
            if path.endswith('/currentwar'):
                return {'state':'notInWar'}
            if path.endswith('/currentwar/leaguegroup'):
                raise tracker.APIError(404)
            if path.endswith('/capitalraidseasons?limit=10'):
                return {'items':[]}
            return {'tag':tracker.DEFAULT_CLAN_TAG, 'name':'Fixture clan', 'members':1, 'memberList':[{'tag':'#P0Y', 'name':'Test player', 'townHallLevel':12}]}
        with contextlib.redirect_stdout(io.StringIO()):
            tracker.refresh(state, SimpleNamespace(get=get))
        self.assertEqual(state['profiles']['#P0Y'],old)
        warnings=' '.join(state['warnings'])
        self.assertIn('Test player (#P0Y)',warnings)
        self.assertIn('HTTP 520',warnings)
        self.assertIn('Saved profiles were retained',warnings)
        self.assertIn('Regular war history:',warnings)


if __name__ == '__main__':
    unittest.main()
