# War Haven Account Management — review release

Prepared October 16, 2026. Unpublished. Existing Site identity, URL, environment variables, Resend configuration, database and storage bindings are retained. No live account actions, database migrations, collector runs or archive rewrites were performed for this release.

## Behavior

Management contains Account Approvals (pending only), Player Dashboards (active and suspended, searchable and filterable), and Approval History. Approve, deny, suspend and restore require a Yes/No confirmation. Approval and restoration also require explicit confirmation of village ownership and verified email/current saved roster membership. A successful decision immediately leaves the pending list. Approval immediately unlocks the member dashboard using saved data.

Deletion has a distinct permanent-deletion dialog requiring the exact player tag. It removes website credentials, email/username associations, private goals, sessions and recovery tokens; it retains all clan projections, war/raid/donation/Capital Gold/progression records and encrypted archives. Clan announcements remain with their account author association removed. A new registration requires email verification and leadership approval again.

Mutations require an approved individual leadership session. Co-leaders can manage member accounts but cannot permanently delete them. Leaders can delete member/co-leader accounts; owners can manage other accounts. Self-lockout and last-owner checks apply. Shared passphrase access remains available for viewing and the existing owner-token permission bootstrap; it cannot perform lifecycle decisions. This restriction is intentional. The leadership sign-in link opens the individual-account portal where these management controls are also built in.

Server-side version checks, transactional updates and idempotency prevent competing decisions or duplicate audit effects. Read-only player previews exclude private account settings and goals. History retains minimal actor/tag/action/time/outcome metadata for 180 days, with retention cleanup during successful collector ingest.

## Acceptance results

All automated checks passed:

| Required behavior | Result |
| --- | --- |
| Approval Yes/No, No/Esc cancellation and ownership confirmation | Passed API + DOM |
| Denial Yes/No and explicit reapplication | Passed API + DOM |
| Pending rows/counts update immediately after confirmed save | Passed API + DOM |
| Approved/suspended dashboards separated; search and status filters | Passed DOM |
| Suspension blocks access and revokes sessions/recovery links | Passed API + DOM |
| Restoration requires current roster and ownership confirmation | Passed API + DOM |
| Permanent deletion authorization, strong confirmation and revocation | Passed API + DOM |
| Deletion preserves clan history and subsequent collector updates | Passed isolated API/storage fixtures |
| Audit history and duplicate-request idempotency | Passed API + DOM |
| Permissions, self/last-owner safeguards and stale-device decisions | Passed API + DOM |
| Failed writes roll back without partial deletion or false success | Passed SQLite failure injection + DOM error checks |
| Existing data survives upgrade; existing dashboard functions regressions | Passed migration test + all 41 Python tests |

Commands: `node tests/backend.test.mjs`, `node tests/accounts.test.mjs`, `node tests/management.test.mjs`, `node tests/management-ui.test.mjs`, `node tests/management-migration.test.mjs`, `bash scripts/build.sh`, `node scripts/validate-artifact.mjs`; connected frontend: `python -m unittest discover -s tests -v` (41 passed).

UI tests use jsdom and actual isolated backend handlers/SQLite. Responsive and focus CSS is checked structurally. Actual browser/phone visual testing and production end-to-end testing remain pending; no real members were altered to test destructive actions. `review/management-preview.html` is a synthetic interactive review, never a live account console.

## Release sequence after review approval

1. Deploy the saved version of the existing War Haven shared actions Site. This applies additive migration `0002_foamy_vermin.sql` to the retained database; it does not recreate tables or reset accounts. The isolated migration test checks pre-existing data and audit-tag backfill.
2. Merge the connected leadership frontend review branch and publish through the existing collector workflow. Existing encrypted archives, CNAME, workflows and collected index are unchanged in the proposed source changes.
3. Perform browser/mobile and a non-destructive real leadership sign-in smoke check. Keep the previous Site version available for rollback; the additive schema remains backward compatible.

No additional runtime dependency is added. jsdom is a development-only test dependency. Audit retention bounds account-action storage growth. Existing R2 and encrypted archive handling are preserved.
