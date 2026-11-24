import unittest
from urllib.parse import parse_qs, urlparse
from html.parser import HTMLParser
import Clash_War_Tracker as tracker

class IconParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'link':
            self.icon = dict(attrs)

class ClanFaviconTests(unittest.TestCase):
    def test_current_badge_uses_public_png_and_badge_changes_change_url(self):
        icons = []
        for name in ('first', 'changed'):
            badge = 'https://api-assets.clashofclans.com/badges/512/' + name + '.png'
            parser = IconParser()
            parser.feed(tracker.clan_favicon_link(badge))
            icon = parser.icon
            self.assertEqual(icon['type'], 'image/png')
            url = urlparse(icon['href'])
            self.assertEqual(url.netloc, 'portal.warhavenclan.com')
            self.assertEqual(url.path, '/members/favicon.png')
            self.assertEqual(parse_qs(url.query)['v'], [badge])
            icons.append(icon['href'])
        self.assertNotEqual(*icons)

    def test_missing_or_untrusted_badge_keeps_safe_fallback(self):
        for badge in (None, 'https://untrusted.example/badge.png'):
            parser = IconParser()
            parser.feed(tracker.clan_favicon_link(badge))
            self.assertEqual(parser.icon['type'], 'image/svg+xml')
            self.assertTrue(parser.icon['href'].startswith('data:image/svg+xml,'))
