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
   run and the dashboard's latest refresh time. The schedule then targets
   **7:23 AM America/Denver once a day**, following daylight saving time.
   Scheduled runs can be delayed; they are not exact timers.

The publishing token is used rather than the workflow's built-in token so the
existing branch-based GitHub Pages deployment is triggered by the publication.
Replace secrets when tokens expire. A passphrase must match the current archive;
use the configured collector's password-change procedure before changing this
secret. Incorrect credentials stop collection/publication rather than resetting
history. The collector also rejects a concurrent archive update without force.

## Everyday use

Open the same website and choose **Refresh data > Open GitHub updater**. On GitHub,
choose **Run workflow**, then the green **Run workflow** button. After collection
and publication finish, use **Load latest dashboard** to see the result. GitHub
requires an account authorized to run workflows; the shared dashboard password
does not grant that access. Set `CLAN_AUTO_UPDATES_ENABLED=false` to pause all collection.
The source code stays public; records are encrypted before publication.

Browser edits still require export/import before a later shared publication.
The workflow captures current/future observations; it cannot recreate missed
historical wars. Local verification covers configuration, archive-first restore,
API failures and publication conflicts. Live collection requires configured keys.

## Saved settings and live war timing

The top-right gear opens Settings. Home summaries, compact roster cards, 24-hour
times, countdown seconds, last-section navigation, and update checks save in this
browser. They persist across reloads and later publications. Clearing website data
or using a different browser/device starts with its own preferences.

Preparation wars display **Preparation day**, with a countdown calculated from
the captured start time every second. At that time the label becomes **In progress**,
and the timer counts down to the captured end time. It then shows **War ended**
and requests a final refresh. Scores and attacks stay labeled as saved data until
collection runs. The timer uses the device clock; it cannot discover an uncaptured war.

## Leader-only password changes

Use **Settings > Leader settings > Change shared password**. Enter the current
dashboard password, the new password twice (at least 12 characters), and a
fine-grained GitHub token restricted to this repository with **Contents** and
**Secrets: read/write**. Your ordinary publishing token may need the additional
Secrets permission. The form requires repository owner authorization; knowing the
shared co-leader password alone does not permit a password change.

The browser verifies the current password locally, reads the latest encrypted
website and history at the same revision, re-encrypts both without changing clan
records, updates the Actions `DASHBOARD_PASSWORD` secret, and publishes the two
encrypted files in one commit. The token is used only for the operation and is not
saved in browser storage or published. Passwords are encrypted before sending to
GitHub. A conflicting publication is refused; the collector secret is restored
when the update is confirmed not to have published.

Wait for GitHub Pages to finish before loading the updated dashboard. Update any
Pyto collector's saved password before using it again. Keep your GitHub account
and tokens private; co-leaders need only the website URL and shared password.
GitHub ownership remains the recovery route: restore a matching older encrypted
website and archive together using a password you still know. Password changes
protect future publications; copies or Git revisions already unlocked with an
older password cannot be revoked.

The bundled libsodium.js 0.8.4 encrypts the Actions secret using GitHub's public
key. Its ISC license is included in the collector and encrypted dashboard. It
loads locally for a password change; no external script host receives credentials.
