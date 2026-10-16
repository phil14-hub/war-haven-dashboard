from pathlib import Path
import unittest
import Clash_War_Tracker as tracker

class AccountManagementIntegrationTests(unittest.TestCase):
 def test_canonical_management_client_and_styles_are_embedded(self):
  root=Path(__file__).resolve().parents[1]
  self.assertEqual(tracker.MEMBER_ACCOUNTS_JS,(root/'member_accounts.js').read_text())
  self.assertIn((root/'account_management.css').read_text(),tracker.HTML_TEMPLATE)
  for name in ['account-approvals','player-dashboards','approval-history','playerdashboards','approvalhistory']:
   self.assertIn(name,tracker.HTML_TEMPLATE)
  self.assertIn("MemberAccounts.open('dashboards')",tracker.HTML_TEMPLATE)
  self.assertIn("MemberAccounts.open('history')",tracker.HTML_TEMPLATE)
