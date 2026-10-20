# Account and village access

## Join once, add villages in one place

1. Open [Member sign in](https://portal.warhavenclan.com/members/?portal=member), choose Create account, and enter your primary player tag, username, private email and password. Usernames contain 3–24 letters, numbers or underscores and ignore case. New passwords require at least 15 characters and pass a breached-password check; password managers are supported.
2. Verify your email. Sign in to see the pending status. New arrivals may need the next successful clan update before their tag appears.
3. Ask an authorized leader to verify your ownership in Clash. A public tag, screenshot or exported village JSON alone is not ownership proof.
4. After approval, use **Add village** in the sidebar or Settings. Both open the same dialog. Enter the additional village tag and confirm that you own it. The request remains pending until an independent authorized reviewer checks it; approval notifications link to the shared action list.
5. Select an approved village from the village switcher. Pending or declined villages never appear as accessible dashboards. Settings lets you choose a primary approved village, unlink an additional one, or request it again when eligible.

Failed/incomplete roster collection keeps the last successful membership snapshot. A confirmed departure removes eligibility; an approved secondary village still in the clan can retain access. Rejoining requires review. An open pending screen detects approval automatically.

## What members see

Each village has captured wars, contributions, league/army progress, heroes, milestones, goals, announcements and approved comparison metrics. **My wars** shows the clan's final Victory, Defeat or Tie separately from your individual attack results. Incomplete results remain awaiting confirmation. Times use your device time zone.

Private leadership notes, recruitment records, management flags, encryption keys and password hashes are excluded. Graphs retain a recent projection; the complete history remains in the encrypted archive. Upgrade coverage follows [UPGRADE_PROGRESS.md](UPGRADE_PROGRESS.md).

## Leadership approvals

**Management → Approval action list** combines pending accounts and additional-village requests. Notifications open the exact action there. Match the tag and village name against the current roster, then verify ownership through an in-game chat challenge or another independent check. Record the verification method before approving.

Reviewers cannot approve their own village requests. Co-leaders manage member accounts; leaders manage members/co-leaders; owners manage other accounts. Website roles are separate from in-game roles. Role assignment requires the existing owner or fresh GitHub owner authorization and invalidates the target's sessions. Stale decisions return a conflict instead of overwriting another leader's work. Review history retains the decision and reviewer.

Attendance flags link to saved player war evidence and the corresponding war card. Review incomplete capture warnings and approved excuses before acting. Clearing a historical flag preserves actual war records and attack totals.

## Passwords and email

See [SETUP.md](SETUP.md) for account recovery, authenticator recovery, owner recovery and shared-password changes. Password reset does not disable MFA. The member portal uses Secure, HttpOnly, SameSite=Lax cookies and hashed tokens. Remember me lasts up to 30 days; ordinary sessions last eight hours. Sensitive account changes revoke sessions.

The owner configures a verified Resend sender and keeps the Site MFA encryption key across deployments. Registration remains closed when delivery is unavailable. Password-screening outages leave accounts and reset tokens intact; retry later. No SMS alerts are used.
