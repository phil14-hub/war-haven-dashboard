from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import Clash_War_Tracker as tracker

class PagesUrlTests(unittest.TestCase):
 def test_https_metadata_keeps_existing_url(self):
  with patch.object(tracker,'urlopen') as open_url:
   self.assertEqual(tracker.pages_https_url({'html_url':'https://warhavenclan.com/'}),'https://warhavenclan.com/')
   open_url.assert_not_called()

 def test_http_metadata_requires_successful_tls_on_same_domain(self):
  response=MagicMock();response.__enter__.return_value=SimpleNamespace(status=200,geturl=lambda:'https://warhavenclan.com/')
  with patch.object(tracker,'urlopen',return_value=response) as open_url:
   self.assertEqual(tracker.pages_https_url({'html_url':'http://warhavenclan.com/'}),'https://warhavenclan.com/')
   self.assertEqual(open_url.call_args.args[0].full_url,'https://warhavenclan.com/')

 def test_unavailable_tls_does_not_allow_plaintext_publication(self):
  with patch.object(tracker,'urlopen',side_effect=URLError('certificate not ready')):
   with self.assertRaises(tracker.PublishError):tracker.pages_https_url({'html_url':'http://warhavenclan.com/'})

 def test_redirect_cannot_change_domain_or_downgrade_to_http(self):
  for target in ['http://warhavenclan.com/','https://another.example/']:
   response=MagicMock();response.__enter__.return_value=SimpleNamespace(status=200,geturl=lambda:target)
   with patch.object(tracker,'urlopen',return_value=response):
    with self.assertRaises(tracker.PublishError):tracker.pages_https_url({'html_url':'http://warhavenclan.com/'})

 def test_missing_or_invalid_metadata_fails_before_publication(self):
  for url in [None,'','file:///tmp/page','https://user:password@warhavenclan.com/']:
   with self.assertRaises(tracker.PublishError):tracker.pages_https_url({'html_url':url})
