# Automatic updates from GitHub

The **Update clan dashboard** workflow runs the existing collector on GitHub,
restores the encrypted archive, collects fresh Clash data, and publishes matching
encrypted website/history files. Pyto does not need to stay open.

**Status on installation: inactive.** Both scheduled and manual collection are
gated by `CLAN_AUTO_UPDATES_ENABLED=true`. No credentials are embedded in code.

## One-time setup

1. Import your old `war_tracker_state.json` once to preserve past records. The
   published baseline does not contain your device's existing history.
2. Decide how GitHub will reach the Clash API. The standard GitHub runner has
   changing outbound IPs. For the RoyaleAPI route, create a separate Clash of
   Clans developer API key allowing **45.79.218.79**. This route sends that key
   and API requests/responses through **https://cocproxy.royaleapi.dev**. Use it
   only after you approve this third-party connection. Documentation:
   https://docs.royaleapi.com/proxy
3. In this repository, open **Settings > Secrets and variables > Actions**.
   Under **Secrets**, add:

   | Name | Value |
   | --- | --- |
   | `COC_API_TOKEN` | The separate Clash API key for your chosen route |
   | `DASHBOARD_PASSWORD` | The existing website/archive passphrase |
   | `DASHBOARD_PUBLISH_TOKEN` | Your existing GitHub publishing token, restricted to this repository, Contents read/write and Pages read |

4. Under **Variables**, add `CLAN_API_ROUTE` with value `royaleapi` for that
   approved route, or `official` for a runner/network whose IP your key permits.
5. Add variable `CLAN_AUTO_UPDATES_ENABLED` with value `true` when ready.
6. Open **Actions > Update clan dashboard > Run workflow**. Confirm a successful
   run and the dashboard's latest refresh time. The schedule then targets minute
   23 of every hour (UTC). Scheduled runs can be delayed; they are not exact timers.

The publishing token is used rather than the workflow's built-in token so the
existing branch-based GitHub Pages deployment is triggered by the publication.
Replace secrets when tokens expire. A passphrase must match the current archive;
use the configured collector's password-change procedure before changing this
secret. Incorrect credentials stop collection/publication rather than resetting
history. The collector also rejects a concurrent archive update without force.

## Everyday use

Open the same website. Use **Actions > Update clan dashboard > Run workflow**
for an extra refresh. Set `CLAN_AUTO_UPDATES_ENABLED=false` to pause all collection.
The source code stays public; records are encrypted before publication.

Browser edits still require export/import before a later shared publication.
The workflow captures current/future observations; it cannot recreate missed
historical wars. Local verification covers configuration, archive-first restore,
API failures and publication conflicts. Live collection requires configured keys.
