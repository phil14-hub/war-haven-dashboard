from datetime import datetime, timezone
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo


class DailyUpdateScheduleTests(unittest.TestCase):
    def test_daily_clan_update_targets_0723_mountain_with_daylight_saving(self):
        source = (Path(__file__).resolve().parents[1] / '.github/workflows/update-clan.yml').read_text()
        self.assertRegex(source, r"schedule:\s*\n\s*- cron: ['\"]23 7 \* \* \*['\"]\s*\n\s*timezone: ['\"]?America/Denver")
        self.assertIn("if: vars.CLAN_AUTO_UPDATES_ENABLED == 'true'", source)
        self.assertIn('run: python github_collector.py', source)
        self.assertIn('cancel-in-progress: false', source)
        zone = ZoneInfo('America/Denver')
        for month, day, utc_hour in [(1, 15, 14), (3, 7, 14), (3, 9, 13), (7, 15, 13), (10, 31, 13), (11, 2, 14)]:
            target = datetime(2026, month, day, 7, 23, tzinfo=zone)
            self.assertEqual(target.astimezone(timezone.utc).hour, utc_hour)
            self.assertEqual(target.astimezone(timezone.utc).minute, 23)


if __name__ == '__main__':
    unittest.main()
