# War Haven leadership dashboard

The redesigned dashboard keeps the existing navy/gold cards and typography, with **Home, Members, Wars, Capital and Manage** navigation. It includes weekly league-point reports, clan and player progression, clan XP milestones, a war lineup planner, recruiting, and a single player report with war information first.

The website and complete clan history are password encrypted. Source code is public; **the dashboard passphrase and publishing/API credentials are not stored in this repository**.

## First run with your existing clan history

1. Download **Clash_War_Tracker.py** from this repository and replace the older script in Pyto. Keep your existing `Documents/Clash_Recruitment` folder, `war_tracker_state.json`, exported changes and `coc_token.txt`.
2. Run the new script normally. Enter the dashboard passphrase supplied privately with the published website. Press Return at the repository prompt to use `phil14-hub/war-haven-dashboard`.
3. Enter a fine-grained GitHub publishing token for **only this repository**, with **Contents: Read and write** and **Pages: Read**. GitHub’s connected ChatGPT plugin handles edits in ChatGPT; the collector running on your device needs its own token. Enter it in Pyto, never in an issue, commit, HTML file or chat message.
4. The collector merges the encrypted GitHub archive with your device’s existing records, refreshes Clash data, and uploads matching encrypted history and dashboard files in one commit. The website then opens in your browser.

The initial publication contains an **empty baseline** because actual collected clan records remain on your device. Your first collector run uploads those records. A published empty dashboard does not mean the clan has zero members or no war history.

## Files in this repository

| File | Purpose |
| --- | --- |
| `Clash_War_Tracker.py` | Single-file collector and dashboard generator; Python standard library is sufficient |
| `index.html` | Password-encrypted website |
| `data/war_tracker_state.enc.json` | Compressed, password-encrypted complete clan archive |
| `SETUP.md` | Setup, recovery and password-change instructions |

GitHub commits retain previous encrypted revisions. The collector refuses to overwrite history it could not read and refuses a conflicting update from another collector. A failed cloud sync keeps local records intact. Local files remain available as an offline safety copy.

## Daily use

Run the script when you want fresh data. It saves history on GitHub and updates the same website URL. Capture regular-war results after a war ends and before starting the next war. The website itself displays the last published snapshot.

All authorized viewers can unlock the site with the shared passphrase. Viewing does not grant repository write access. Notes and lineup edits made in a browser still need **Manage → Save changes / backup**, followed by import on the collector device, before they appear in the next shared publication. GitHub Pages is a snapshot host, not a shared-editing backend.

Useful arguments:

```text
--setup-website     Change the passphrase or publishing settings.
--no-publish        Work locally without reading/writing GitHub history.
--offline          Regenerate saved data without Clash API calls.
--no-open          Save/update without opening a browser.
--apply FILE       Merge a downloaded changes/backup file.
--watch 300        Collect and publish while Python stays running.
```

This version does not add AI or unattended cloud collection. iOS may suspend Pyto in the background, and the Clash API still requires an allowed outgoing IP for the collector.

## Data coverage

League points use 100 points per ranked division, with Unranked = 0 and unknown leagues left unknown. Weekly reports separate progress of continuing members from joins, departures and changes in coverage. Army percentages use permanent troop, spell, hero, pet and siege levels at each Town Hall. Buildings and walls require verified manual records. Exact clan XP checkpoints are entered from the in-game XP bar; the API provides clan levels.

Never commit `coc_token.txt`, `dashboard_website.json`, plaintext state files, backups or the private access file. The ignore file helps with accidental local Git additions; only the explicit encrypted files are uploaded by the collector.

The bundled AES fallback is pyaes 1.6.1, copyright 2014 Richard Moore, MIT licensed. Its original license is retained in the single-file source.

Validation completed locally: 36 Python tests plus JavaScript calculations and desktop/mobile browser flows. Tests cover encryption/decryption, wrong passwords, tampering, old/new history merges, conflict handling, password rotation, navigation, reports, profiles, lineups, exports and backup imports. Test fixture files are kept out of the published repository.
