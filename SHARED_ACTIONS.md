# Encrypted shared actions

The supporting service is deployed at https://war-haven-actions.readydrake18.chatgpt.site with owner-only hosting access. `shared_actions.ENABLED` is false until the owner explicitly authorizes the service to be reachable by co-leaders at the existing GitHub Pages dashboard. This keeps existing controls functional while the new access decision is pending.

## Behavior when enabled

- The existing dashboard passphrase authorizes shared actions. A password-derived archive MAC proof is sent; the raw passphrase and provider tokens are not sent to the service. The browser retains only a non-extractable derivation key in memory after unlock.
- Notes and Regular/CWL lineup drafts save after a short typing pause and sync across devices. Each record is encrypted and authenticated in the browser with a separate random key retained inside the encrypted archive. The service stores encrypted files, opaque identifiers and revisions in R2.
- Revisions prevent silent simultaneous overwrites. A conflict retains the draft and offers Load their change or Save my draft. Pending drafts are retained locally and retry after reconnection. Other edit categories still use backups.
- Clan and recruitment requests have separate queues, status, estimates and progress. Their actual collectors are independent. A shared publication lock protects the encrypted archive.
- The five-minute GitHub watcher claims requests and uses only existing Actions secrets. Queue delays can exceed five minutes when GitHub scheduling is delayed. Each running estimate starts from 120 seconds for clan collection or 180 seconds for recruitment and adapts to previous duration. The bar is an estimate between real collection/publication milestones and remains below 100% until Pages publication is confirmed.
- Password changes retain their separate owner authorization. Changing the dashboard password revokes old shared-action proofs after the service’s short archive cache expires.

## Files

`shared_dashboard.js` supplies client synchronization; its source is embedded in the portable Python tracker. `shared_actions.py` supplies the Actions client and encrypted-record import. Backend source is maintained in the registered War Haven shared actions Site. It contains no GitHub token, password or plaintext notes.

## Activation after the audience decision

Keep the existing Site ID and deployment. With explicit owner authorization, use Sites access controls to make the password-protected API reachable, then set `ENABLED = True` in `shared_actions.py`. Publishing that change triggers independent cloud jobs that restore the archive, create/preserve the shared editing key and regenerate the encrypted dashboard. Verify both queues, shared saves and Pages publication. No new provider credential should be pasted into the dashboard.
