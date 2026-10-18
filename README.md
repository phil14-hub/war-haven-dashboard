# War Haven leadership dashboard

Individual member accounts and dashboards are described in [MEMBER_ACCOUNTS.md](MEMBER_ACCOUNTS.md). The approval system makes a member view available immediately after email verification, membership validation and leadership approval. Email delivery must be activated before public registration opens.

The redesigned dashboard keeps the existing navy/gold cards and typography, with **Home, Members, Wars, Capital and Manage** navigation. It includes weekly league-point reports, clan and player progression, clan XP milestones, a war lineup planner, recruiting, and a single player report with war information first.

The website and complete clan history are password encrypted. Source code is public; **the dashboard passphrase and publishing/API credentials are not stored in this repository**.

## First run with your existing clan history

1. Download **Clash_War_Tracker.py** from this repository and replace the older script in Pyto. Keep your existing `Documents/Clash_Recruitment` folder, `war_tracker_state.json`, exported changes and `coc_token.txt`.
2. Run the new script normally. Enter the dashboard passphrase supplied privately with the published website. Press Return at the repository prompt to use `phil14-hub/war-haven-dashboard`.
3. Enter a fine-grained GitHub publishing token for **only this repository**, with **Contents: Read and write** and **Pages: Read**. GitHub’s connected ChatGPT plugin handles edits in ChatGPT; the collector running on your device needs its own token. Enter it in Pyto, never in an issue, commit, HTML file or chat message.
4. The collector merges the encrypted GitHub archive with your device’s existing records, refreshes Clash data, and uploads matching encrypted history and dashboard files in one commit. The website then opens in your browser.

The published encrypted archive already contains War Haven's collected clan records. Future collectors restore and merge those records before publishing. Keep the archive when updating code.

## Files in this repository

| File | Purpose |
| --- | --- |
| `Clash_War_Tracker.py` | Single-file collector and dashboard generator; Python standard library is sufficient |
| `index.html` | Password-encrypted website |
| `data/war_tracker_state.enc.json` | Compressed, password-encrypted complete clan archive |
| `SETUP.md` | Setup, recovery and password-change instructions |

GitHub commits retain previous encrypted revisions. The collector refuses to overwrite history it could not read and refuses a conflicting update from another collector. A failed cloud sync keeps local records intact. Local files remain available as an offline safety copy.

## Automatic updates on GitHub

Clan and recruitment collection run independently. **Update clan dashboard** collects clan, war, member and Capital data at about **7:23 AM Mountain time**. **Update recruitment** scans tracked clans at about **7:35 AM Mountain time**. Each also has its own manual workflow. Their shared publication lock protects the encrypted archive; it does not cause one collector to run when the other does.

**Management → Recruiter** is part of the dashboard, with native cards, search and filters, candidate history and clan turnover. Cards reveal gently as they scroll into view and respect reduced-motion settings. Town Hall 1–18 images appear beside player names across roster, lineup, contribution and recruiting cards. **Management → How to Use** explains the dashboard for first-time leaders.

The encrypted shared-saving and token-free update service uses dashboard passphrase access to authorize encrypted shared notes/plans and separate clan/recruitment requests. The supporting API is reachable from the dashboard and accepts individual leadership sessions or dashboard proof for reading/requesting, and requires a signed main-branch GitHub Actions token for ingesting or claiming/completing updates. Each request has an estimated duration, a progress bar and confirmed publication at 100%. Provider credentials remain in GitHub Actions. Password changes still require owner authorization. See [shared actions](SHARED_ACTIONS.md).

After either update request is accepted, leaders can close the dialog, leave the page or exit the browser; collection and publication continue in the cloud. The Home refresh icon spins while clan collection is queued or running, independently of recruitment. Open dashboards load newly published data automatically without a page reload or another unlock. The current page, filters, open player report, scroll position and pending notes/plans are retained. Hidden tabs check when they become visible again. A failed download or authentication check keeps the current dashboard available and retries later. A changed passphrase requires a new unlock.

The gear opens real Settings with persistent browser preferences. Preparation wars have a live start countdown and switch to **In progress** without a new scan. Password changes are under **Leader settings** and require both the current dashboard password and GitHub owner authorization; the co-leader password alone cannot change shared access.

Hover, tap, click or keyboard-focus a graph point to inspect its saved value and date. This works for war performance, clan growth and XP, member upgrades and player contributions. Moving the mouse away clears the label and detail text. On touchscreens, tap a point to keep it visible; tap again, tap elsewhere or press Escape to dismiss it.

## Final results after a war

The cloud updater records each known war's end time and targets another update
five minutes afterward. It works with the phone closed and keeps the daily
schedule. GitHub scheduling may delay the start. Wait for the final capture to
finish before searching for the next regular war. See
[automatic final-war updates](AUTOMATIC_UPDATES.md#automatic-final-war-update).

## Daily use

Run the script when you want fresh data. It saves history on GitHub and updates the same website URL. Capture regular-war results after a war ends and before starting the next war. The website itself displays the last published snapshot.

All authorized viewers can unlock the site with the shared passphrase. Viewing does not grant repository write access. Leadership edits save automatically to encrypted shared records across leaders. Attendance exceptions, war corrections, XP checkpoints, village imports and reviewed flags also share automatically. Backups retain the complete captured history. GitHub Pages serves the encrypted snapshots and the separate service handles shared actions.

Useful arguments:

```text
--setup-website     Change the passphrase or publishing settings.
--no-publish        Work locally without reading/writing GitHub history.
--offline          Regenerate saved data without Clash API calls.
--no-open          Save/update without opening a browser.
--apply FILE       Merge a downloaded changes/backup file.
--watch 300        Collect and publish while Python stays running.
```

This version does not add AI. For unattended collection on GitHub, see [AUTOMATIC_UPDATES.md](AUTOMATIC_UPDATES.md). The prepared workflow remains inactive until its secrets, API route, and enable variable are configured. Pyto collection still requires an allowed outgoing IP, and iOS may suspend it in the background.

## Data coverage

League points use 100 points per ranked division, with Unranked = 0 and unknown leagues left unknown. Weekly reports separate progress of continuing members from joins, departures and changes in coverage. Army percentages use permanent troop, spell, hero, pet and siege levels at each Town Hall. Buildings and walls require verified manual records. Exact clan XP checkpoints are entered from the in-game XP bar; the API provides clan levels.

Never commit `coc_token.txt`, `dashboard_website.json`, plaintext state files, backups or the private access file. The ignore file helps with accidental local Git additions; only the explicit encrypted files are uploaded by the collector.

The bundled AES fallback is pyaes 1.6.1, copyright 2014 Richard Moore, MIT licensed. Its original license is retained in the single-file source.

Current checks: 40 Python tests, including actual generated JavaScript syntax, independent collector behavior, viewer-local times, hover dismissal, archive continuity and browser/cloud encryption interoperability. JavaScript checks cover concurrent shared edits, retained drafts, idempotent retry, progress completion, password proofs, CORS, separate update queues and automatic data-only updates that preserve the unlocked view. Browser visual QA was unavailable in this environment.

Town Hall images are bundled from [ClashKingAssets](https://github.com/ClashKingInc/ClashKingAssets/tree/main/assets/buildings/home-village/town_hall), so the dashboard does not fetch them from a third-party host at view time. Clash of Clans assets belong to Supercell.

## Audit corrections and checks

See [AUDIT_FIXES.md](AUDIT_FIXES.md) for the October 17 corrections and verification limits. Run `python -m pip install requests==2.34.2`, `npm ci --ignore-scripts`, and `python -m unittest discover -s tests -v`. Generate the synthetic UI fixture with `python tests/create_leadership_fixture.py`, then run `WAR_HAVEN_DASHBOARD_FIXTURE=tests/fixtures/leadership.html npm run test:ui`. The regression workflow requires the rendered fixture test for source changes. It is isolated DOM testing; real phone/browser and genuine screenshot QA remain separate.
