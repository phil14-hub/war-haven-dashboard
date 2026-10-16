# War Haven: Management > Account Approvals & Player Dashboards

Implementation specification (approved October 16, 2026). This is a product/engineering specification, **not** deployed site code. Implement it in the existing **War Haven shared actions** Site and its associated leadership dashboard without replacing the project.

## Goal

Account Approvals lists **only actionable pending applications**. Approving or denying requires a brief Yes/No confirmation. A successful decision removes the applicant from the pending list immediately. Approved users appear in a distinct **Management > Player Dashboards** section where authorized leadership can view, suspend, restore, or permanently delete the *website account*. A separate **Management > Approval History** section provides an audit trail.

**Deletion is limited to personal account access and account-owned private information. Never delete or rewrite clan-relevant history**, including contributions, member progression observations, wars, raids, donation records, cumulative Capital Gold, published clan snapshots, historical player profiles, or the encrypted GitHub archive.

## Navigation and presentation

Use existing War Haven navy/gold styles and navigation conventions. Group these entries under the current Management area, without disrupting unrelated tools.

- **Account Approvals**: pending application count; verified-email status; saved player name/tag, Town Hall, in-game role, username and application date; Approve and Deny actions; optional ownership-review guidance.
- **Player Dashboards**: active approved accounts and suspended accounts, clearly labeled and searchable by player name, tag, and username. Include filters for Active / Suspended / All. Each row can open that user's authorized dashboard view and account-management actions.
- **Approval History**: chronological log of approved, denied, suspended, restored, removed actions; actor, time, target player tag and decision/action. Keep private account email/password information out of public clan-facing outputs. Use minimal retention for identifiers after account deletion.

Each list uses server-authoritative results and shows loading, empty, retryable error, and permission-denied states. A successful mutation updates the list and its counts immediately, reconciles with the server, and remains correct after refresh or on another leader's device. Never silently convert failures into a successful-looking state.

## Confirmations

1. When **Approve** is clicked, show a compact dialog: "Approve [player name]'s account?" with **No** and **Yes, Approve**. No closes without changing anything. Yes sends the actual server-side decision.
2. When **Deny** is clicked, show: "Deny [player name]'s request?" with **No** and **Yes, Deny**. No closes without changing anything. Yes submits the denial.
3. While a decision is submitting, disable duplicate submissions; show clear result/error. On success, remove the item from pending immediately.
4. **Suspend** and **Restore** require concise confirmation and show the access consequence.
5. **Delete Account** uses a stronger, destructive confirmation that displays the player's identifying name/tag and clearly explains that website login and personal settings will be permanently removed, sessions revoked, and clan-history data retained. Require an explicit final confirmation; do not reuse the simple approvals dialog for deletion.

## State transitions

- Registration starts as Pending (after email verification, or an existing separate verification state if present).
- Approval: Pending -> Approved/Active, immediately visible in Player Dashboards, removed from Account Approvals, available to sign in when latest roster and ownership requirements are satisfied.
- Denial: Pending -> Denied, removed from Account Approvals, added to Approval History; never appears in Active Player Dashboards. If a denied user reapplies, require a new explicit application rather than resurrecting an approved session.
- Suspension: Active -> Suspended, shown in Player Dashboards under suspended filter; immediately revoke active sessions and refresh/reset tokens as appropriate. Preserve account record for later restoration.
- Restoration: Suspended -> Active only after checking current clan membership, email verification, ownership and leadership authorization requirements.
- Deletion: Active or Suspended -> Deleted account, permanently remove login credentials, email/username associations, personal account goals/preferences and account-specific private details as appropriate; revoke all sessions and recovery/verification tokens; remove from Player Dashboards. Keep only minimal non-sensitive audit metadata and non-account clan history. A future login requires entirely new registration and leadership approval.
- Confirmed clan departure continues to trigger existing suspension behavior; do not silently delete accounts or alter clan history.

## Security & data invariants

- All transitions must be authorized and validated **server-side** with the existing authenticated individual leadership role system. A shared browser passphrase or a hidden button is not sufficient authorization for account deletion.
- Approve/Deny: permitted to authenticated leaders and explicitly authorized co-leaders/admins with the existing approval capability. Delete: only owner/leader or explicitly granted administrators. Never allow a user to gain access by spoofing the target tag or role.
- Preserve the current safeguard that account approval requires verified email, membership in the latest *successful* roster, and separate confirmation of player-tag ownership. A failed or incomplete roster fetch must not revoke or grant accounts.
- Disallow deleting the last owner/administrator and accidental self-lockout. Do not expose another player's password hash, recovery tokens, email address, notes, or private personal data in the member-facing views.
- Treat mutations as atomic DB transactions where supported; if a request fails or is replayed, the UI and audit trail must remain consistent. Prevent double decisions and conflicting cross-device requests; return useful conflict responses.
- Keep an audit log of action, target player tag, actor ID, timestamp and outcome. Avoid retaining unnecessary personal identifiers after account deletion.
- Account deletion must **not** delete shared/roster-derived projections or any other account-independent player statistics; however no deleted user may authenticate to obtain their old projection until re-registered and newly approved.
- Preserve all existing code, member accounts, D1 database and migrations, R2 storage, encrypted GitHub archives, workflows, environment variables, Resend integration, website URL and unrelated site features.

## Integration guidance

The existing member backend is maintained in **War Haven shared actions** (Site) and uses D1 for membership/auth records and R2 for projections/publication. The GitHub repository stores the dashboard collector and encrypted archive. Implement actual authorization and account mutations in the Site; integrate its authenticated endpoints with the existing dashboard Management UI. Discover and reuse current endpoint naming and database structure; do not invent routes or run destructive schema reinitialization.

If a D1 migration is necessary, make it additive and backward-compatible, then apply it to the existing database. Preview diffs and ensure collection/publication continue unchanged. Do not regenerate production histories as a shortcut.

## Acceptance tests (required before publishing)

1. Verified pending user -> Click Approve -> Click No: remains pending, no audit action.
2. Pending user -> Click Approve -> Click Yes: removed instantly from pending, appears Active in Player Dashboards, granted authorized access, audit written.
3. Pending user -> Click Deny -> Click No: stays pending.
4. Pending user -> Click Deny -> Click Yes: disappears from pending, appears only in history, cannot log into personal dashboard.
5. Two concurrent leaders acting on one pending request: only one authoritative decision, correct UI reconciliation and single audit effect.
6. User without delete permission is rejected by backend even if API called directly.
7. Suspend -> active sessions rejected immediately; restore -> allowed only after permission and membership checks.
8. Delete -> confirmation warns of permanence; cancel leaves account intact; confirm revokes all tokens/sessions, removes login and personal account data; user cannot access old dashboard with cached session.
9. Deleted player still appears in historical war/raid/donation/Capital Gold and progression views, both now and after scheduled collector runs. Current roster statistics still update if player remains a clan member.
10. Deleted user may newly register but needs email verification and explicit approval again.
11. Existing owner access and other members stay intact; no database reset, URL change or Resend regressions.
12. UI works on mobile, is keyboard accessible and clearly distinguishes Active/Suspended/Deleted/history.

## Release procedure

Implement in existing Site and connected dashboard, run automated tests and a production-like check against a safe test account, publish/redeploy the approved existing Site version (not a fresh Site), and verify end-to-end in production. Record the new version and any migrations. Never claim live functionality until redeployed and tested.
