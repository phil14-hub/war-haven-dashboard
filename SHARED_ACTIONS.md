# Encrypted shared actions

The supporting service at https://war-haven-actions.readydrake18.chatgpt.site is reachable from the dashboard. `shared_actions.ENABLED` is true. The dashboard passphrase authorizes every shared-data and update operation; the service stores encrypted notes/plans and independent refresh queues.

## Behavior when enabled

- The existing dashboard passphrase authorizes shared actions. A password-derived archive MAC proof is sent; the raw passphrase and provider tokens are not sent to the service. The browser retains only a non-extractable derivation key in memory after unlock.
- Notes and Regular/CWL lineup drafts save after a short typing pause and sync across devices. Each record is encrypted and authenticated in the browser with a separate random key retained inside the encrypted archive. The service stores encrypted files, opaque identifiers and revisions in R2.
- Revisions prevent silent simultaneous overwrites. A conflict retains the draft and offers Load their change or Save my draft. Pending drafts are retained locally and retry after reconnection. Other edit categories still use backups.
- Clan and recruitment requests have separate queues, status, estimates and progress. Their actual collectors are independent. A shared publication lock protects the encrypted archive.
- Both update dialogs explain that accepted jobs continue in the cloud after the dialog, page or browser closes. Each refresh button tracks its own queue; the Home icon spins while clan collection is queued or running. Status polling continues with the update dialog closed.
- An unlocked dashboard checks for new publications and loads their authenticated JSON data in place. It uses the existing in-memory derivation key with each publication's fresh salt, without retaining or requesting the raw passphrase. It preserves the current page, filters, player report, focus, scroll and pending edits. New publication scripts are not executed. Download, authentication or render failures keep the previous snapshot and retry automatically. A passphrase or shared-key change requires reopening with current access.
- The five-minute GitHub watcher claims requests and uses only existing Actions secrets. Queue delays can exceed five minutes when GitHub scheduling is delayed. Each running estimate starts from 120 seconds for clan collection or 180 seconds for recruitment and adapts to previous duration. The bar is an estimate between real collection/publication milestones and remains below 100% until Pages publication is confirmed.
- Password changes retain their separate owner authorization. Changing the dashboard password revokes old shared-action proofs after the service’s short archive cache expires.

## Files

`shared_dashboard.js` supplies client synchronization and update status; `live_dashboard.js` applies newly published snapshots. Both are embedded in the portable Python tracker. `shared_actions.py` supplies the Actions client and encrypted-record import. Backend source is maintained in the registered War Haven shared actions Site. It contains no GitHub token, password or plaintext notes.

## Verification

The same registered Site remains deployed. Both independent collectors restore the archive and preserve the shared encryption key before regeneration. The dashboard never requests a provider token for clan or recruitment refresh. Password changes retain separate owner authorization. Tests cover actual tracker record import, the first activation with existing notes, concurrent saves, retry behavior and hover cleanup.
