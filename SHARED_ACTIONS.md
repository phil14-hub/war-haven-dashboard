# Encrypted shared actions

The supporting service at https://portal.warhavenclan.com is reachable from the dashboard. `shared_actions.ENABLED` is true. Individual leadership sessions or the dashboard proof authorize reading and requesting updates; scoped GitHub Actions identity tokens authorize collector writes; the service stores encrypted notes/plans and independent refresh queues.

## Behavior when enabled

- The existing dashboard passphrase authorizes shared actions. A password-derived archive MAC proof is sent; the raw passphrase and provider tokens are not sent to the service. The browser retains only a non-extractable derivation key in memory after unlock.
- Notes and Regular/CWL lineup drafts save after a short typing pause and sync across devices. Each record is encrypted and authenticated in the browser with a separate random key retained inside the encrypted archive. The service stores encrypted files, opaque identifiers and revisions in R2.
- Revisions prevent silent simultaneous overwrites. A conflict retains the draft and offers Load their change or Save my draft. Pending drafts are retained locally and retry after reconnection. Attendance exceptions, war corrections, XP checkpoints, village imports and reviewed flags use the same encrypted revision checks. Complete history can still be exported as a backup.
- Clan and recruitment requests have separate queues, status, estimates and progress. Their actual collectors are independent. A shared publication lock protects the encrypted archive.
- Both update dialogs explain that accepted jobs continue in the cloud after the dialog, page or browser closes. Each refresh button tracks its own queue; the Home icon spins while clan collection is queued or running. Status polling continues with the update dialog closed.
- An unlocked dashboard checks for new publications and loads their authenticated JSON data in place. It uses the existing in-memory derivation key with each publication's fresh salt, without retaining or requesting the raw passphrase. It preserves the current page, filters, player report, focus, scroll and pending edits. New publication scripts are not executed. Download, authentication or render failures keep the previous snapshot and retry automatically. A passphrase or shared-key change requires reopening with current access.
- The five-minute GitHub watcher claims requests and uses only existing Actions secrets. Queue delays can exceed five minutes when GitHub scheduling is delayed. Each running estimate starts from 120 seconds for clan collection or 180 seconds for recruitment and adapts to previous duration. The bar is an estimate between real collection/publication milestones and remains below 100% until Pages publication is confirmed.
- Password changes retain their separate owner authorization. Changing the dashboard password revokes old shared-action proofs after the service’s short archive cache expires.

## Files

`shared_dashboard.js` supplies client synchronization and update status; `live_dashboard.js` applies newly published snapshots. Both are embedded in the portable Python tracker. `shared_actions.py` supplies the Actions client and encrypted-record import. Backend source is maintained in the registered War Haven shared actions Site. It contains no GitHub token, password or plaintext notes.

## Verification

The same registered Site remains deployed. Both independent collectors restore the archive and preserve the shared encryption key before regeneration. The dashboard never requests a provider token for clan or recruitment refresh. Password changes retain separate owner authorization. Tests cover actual tracker record import, the first activation with existing notes, concurrent saves, retry behavior and hover cleanup.

## October 17 audit corrections

The canonical service is https://portal.warhavenclan.com. Legacy addresses redirect browser navigation. Pending edits and private leader caches use purpose-separated AES-GCM encryption in local storage; the key is available only after authorized unlock. Sign-out removes old plaintext cache keys. Concurrent edits require a revision match and record an actor/action entry in Approval History. Historical flag review requires an individual leadership account and retains actual attendance history.

Collectors use GitHub Actions OIDC (`war-haven-collector` audience), validated issuer/signature, repository, main branch, event and workflow claims. Browser proof cannot ingest, claim, advance or finish jobs. The dedicated `sync-portal.yml` workflow republishes a matched encrypted dashboard/archive revision after local/Pyto pushes and retries independently. A portal failure appears as partial synchronization. Immutable generation objects and one conditional publication pointer keep member and leader data together.

Open portal dashboards fetch authenticated data projections and conditional versions, rather than HTML on every refresh. Current privileges are checked on every request. A code change displays a new-version notice; encrypted drafts remain recoverable after reload.
