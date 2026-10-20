# Automatic updates from GitHub

The **Update clan dashboard** workflow runs the existing collector on GitHub,
restores the encrypted archive, collects fresh Clash data, and publishes matching
encrypted website/history files. Pyto does not need to stay open.

The [recruiter](RECRUITER.md) has an independent **Update recruitment** workflow at about 7:35 AM Mountain time, with its own manual trigger. A clan update never scans recruiting candidates, and a recruitment scan never refreshes the clan snapshot. Both restore the latest encrypted archive and use the same publication lock to prevent conflicting writes.

The [shared actions service](SHARED_ACTIONS.md), enabled for dashboard-passphrase holders, accepts independent password-authorized requests without GitHub tokens in the browser. The five-minute watcher checks each queue and recorded war ends. Running progress uses collection/publication stages plus an estimate from prior duration. It reaches 100% only on confirmed publication.

Scheduled and manual collection require `CLAN_AUTO_UPDATES_ENABLED=true`. Check the repository variable and Operations panel for current status. No credentials are embedded in code.

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

Sign in with your individual leadership account and choose **Refresh data → Start clan update**. Shared-passphrase access remains a compatibility/recovery route. Recruitment
has its own **Management → Recruiter → Refresh recruiting candidates** button.
The shared service authorizes both through the existing unlocked session; no
provider token is needed. Each follows its own queue and shows estimated progress.
An already queued or running request is followed without starting a duplicate.

Once a request is accepted, you can close the dialog, leave the page or exit the
browser. Collection continues in the cloud. The Home icon spins while a clan
update is queued or running. If the dashboard stays open, new data loads
automatically without reloading the page or signing out. Filters, open reports
and pending notes/plans are retained; hidden tabs check when visible again.
Daily collection also runs with the phone and website closed, around 7:23 AM
Mountain time for clan data and 7:35 AM for recruitment.

Repository owners can still run either workflow from GitHub. Keep owner and
provider credentials private. Set `CLAN_AUTO_UPDATES_ENABLED=false` to pause all collection.
The source code stays public; records are encrypted before publication.

Notes, lineup drafts, attendance exceptions, war corrections, XP checkpoints, village imports and reviewed flags save through encrypted shared records. Export/import remains a recovery and offline option.
The workflow captures current/future observations; it cannot recreate missed
historical wars. Local verification covers configuration, archive-first restore,
API failures and publication conflicts. Live collection requires configured keys.

## Automatic final-war update

Each daily or manual update records known regular-war, friendly-war and CWL end
times. The **Capture final war results** workflow uses those saved times to target
an extra collection **five minutes after each war ends**. Your phone and website
can remain closed; no additional secret or setup is needed.

A lightweight check runs every five minutes and reads only the encrypted saved
archive. If a known war's target is within five minutes, the capture job waits
until that target before collecting. GitHub can delay scheduled jobs, so five
minutes is the target rather than an exact delivery guarantee. The daily update
continues around 7:23 AM Mountain time. The follow-up captures clan and final war data and preserves the saved recruiter snapshot. Recruitment runs only through its independent schedule or a separately queued request.

The capture job shares the existing collection lock, reads the latest archive
again, and skips a war if its final update already finished. Completed checks and
upcoming targets are retained inside `automaticUpdates.postWar` in the encrypted
archive. If final player details are unavailable, it retries after ten minutes,
for up to six hours after the end, without inventing attack counts. Old war-log
summaries and manually entered wars do not trigger automatic capture.

**Wait until the final update has finished before starting the next regular-war
search.** Starting another search before capture can make the previous war's
player details unavailable. The watcher can only schedule wars already recorded
by a successful update. `CLAN_AUTO_UPDATES_ENABLED=false` pauses both workflows.

Run `python -m unittest discover -s tests -v` for synthetic-data timing,
archive-continuity, duplicate-prevention and retry checks.

## Saved settings and live war timing

The top-right gear opens Settings. Home summaries, compact roster cards, 24-hour
times, countdown seconds, last-section navigation, and update checks save in this
browser. They persist across reloads and later publications. Clearing website data
or using a different browser/device starts with its own preferences.

War-performance, clan-growth, XP, member-upgrade and contribution graphs display
the saved value, date and context when you hover or focus a point. Mouse hover labels and their detail text disappear when the pointer leaves.
On touchscreens, tap a point to keep its label open; tap it again, tap elsewhere,
or press Escape to close the label. Exact-value tables remain available below each graph.

Preparation wars display **Preparation day**, with a countdown calculated from
the captured start time every second. At that time the label becomes **In progress**,
and the timer counts down to the captured end time. It then shows **War ended**
and requests a final refresh. Scores and attacks stay labeled as saved data until
collection runs. The timer uses the device clock; it cannot discover an uncaptured war.

## Passwords and operations

See [Setup, passwords and recovery](SETUP.md) for the coordinated shared-password change, personal account recovery and emergency owner recovery. Operations shows workflow successes/failures, pending/running requests, stuck leases, data capture times and maintenance. SMS alerts are disabled.

## Portal publication retry

`sync-portal.yml` runs after encrypted dashboard/archive pushes, on demand, and twice hourly. It restores the same main-branch revision without another Clash collection and publishes matching member/leader projections. Local/Pyto publications use this path. Collector workflows require `id-token: write` for scoped portal authorization; publishing/API secrets remain in Actions. A successful GitHub publication with a failed portal upload is reported as partial, preserving the prior complete portal snapshot until retry.

Portal retry first removes expired sessions, tokens, rate limits, MFA challenges and email-change requests independently of archive decoding. Identical publications reuse their generation. Generated delivery objects older than seven days may be removed, preserving the current and previous generations. Archives, war evidence and encrypted shared records are retained. Source changes run the release gate and rebuild saved history; they do not also start redundant clan and recruitment scans.
