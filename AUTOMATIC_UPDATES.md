# Automatic updates from GitHub

The **Update clan dashboard** workflow runs the existing collector on GitHub,
restores the encrypted archive, collects fresh Clash data, and publishes matching
encrypted website/history files. Pyto does not need to stay open.

The [recruiter](RECRUITER.md) also runs in this workflow. Its report and persistent
scan history share the encrypted archive, using the existing credentials. Both
daily and manual updates refresh recruiting candidates as well as clan data.

**Status on installation: inactive.** Both scheduled and manual collection are
gated by `CLAN_AUTO_UPDATES_ENABLED=true`. No credentials are embedded in code.

## One-time setup

1. Keep the existing encrypted archive in `data/war_tracker_state.enc.json`.
   War Haven's earlier device history has already been uploaded. The automatic
   collector restores that archive before collecting new observations.
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

Open the same website and choose **Refresh data**. The leader can enter a private
fine-grained GitHub token restricted to this repository with **Actions: read and
write**, then choose **Start update here**. The website verifies repository owner
authorization, starts the cloud workflow, and follows its progress. It follows an
already queued/running update instead of starting a duplicate. The token is never
embedded in a publication or saved in browser storage; enter it again for a later
request. This token does not need Contents or Secrets permission.

The existing GitHub option is under **Update through GitHub instead > Open GitHub
updater**. Choose **Run workflow**, then the green **Run workflow** button. After
collection and publication finish, use **Load latest dashboard** to see the result.
Both manual routes work from any internet-connected device, on Wi-Fi or cellular.
GitHub runs the collector, so the triggering device does not need a fixed IP and
can be closed or turned off after GitHub accepts the request. Daily collection
also runs with the phone and website closed, around 7:23 AM Mountain time.

The shared dashboard password alone does not authorize data collection. Keep
leader tokens private. Set `CLAN_AUTO_UPDATES_ENABLED=false` to pause all collection.
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

War-performance, clan-growth, XP, member-upgrade and contribution graphs display
the saved value, date and context when you hover or focus a point. Click or tap a
point to keep its label open; tap it again, tap elsewhere, or press Escape to close
the label. Exact-value tables remain available below each graph.

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
