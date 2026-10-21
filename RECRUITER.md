# Automated War Haven recruiter

Recruitment runs through **Update recruitment**, independently of clan collection. Its daily schedule targets **7:35 AM America/Denver**; clan collection targets **7:23 AM**. A manual clan update does not scan recruitment, and source changes rebuild the saved dashboard without starting duplicate scans. Both collectors use the configured API route and restore the same encrypted archive before publishing through a shared queue.

Open **Management → Recruiter → Refresh recruiting candidates** to request a scan using your individual leadership session. The accepted request continues with the phone/browser closed; no provider token is needed. Existing shared-passphrase access remains a compatibility route. Operations shows failures, successful updates and recruiter data freshness. GitHub scheduling may delay a queued scan.

## Search behavior

- Find candidates with Town Hall 11 or higher; the scan target does not cap the saved card list.
- Retain all detected players for seven days across daily scans, deduplicated by player tag. Daily verification does not restart that clock.
- After returning from Clash, **Yes** saves the invitation and removes the card for every leader. **No** keeps it available until expiry. Failed saves keep the card and offer a retry.
- Monitor up to 1,000 clans whose game location is United States, keeping the
  existing core/rotating pool, verification, duplicate cooldown and lifecycle.
- Verify a departed player's live profile before listing them as clanless.
- Track known candidates who join War Haven and those who join another clan.
- Keep invitations manual. No script sends invites or controls the game.

The API does not reveal player residence or language. A U.S.-listed former clan
is only an association, and saved availability can change after a scan. Open the
player's profile before inviting.

## Saved scan history

The first cloud run establishes its own roster baseline. Future scans compare
against that baseline; a newly tracked clan is not treated as a source of
historical departures. The existing recruiter state on your phone is unchanged.
It can be imported separately if its historical baseline is needed.

The complete recruiter state and report are stored inside
`data/war_tracker_state.enc.json`, alongside the existing clan archive. They are
encrypted with the existing dashboard password and published atomically with the
website. Password changes therefore cover recruiting history too. The website
receives the report and summary; the large monitored-roster baseline stays out
of its browser payload.

Expired and invited cards leave the active list; full archived player records and shared invitation responses remain saved. Invitation history is loaded before cards appear and refreshed while the recruiter is open. Saved profiles also rebuild army completion during archive restore and code-only publication, retaining their actual observation timestamps.

A failed clan request retains the last successful roster for that clan. If the
recruiter run cannot finish, its last good report/history remain intact while the
clan dashboard can still update. The recruiter panel shows the failed attempt.
No raw recruiter state, report, CSV or credentials are committed or uploaded as
a workflow artifact. Working files exist only in the runner's temporary directory.

Optional repository variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `RECRUITER_ENABLED` | `true` | Set `false` to pause recruiting scans while keeping clan updates |
| `RECRUITER_MAX_CLANS` | `1000` | Scan limit from 1 to 1000 |

The existing `CLAN_AUTO_UPDATES_ENABLED` switch pauses the combined workflow.
The existing workflow concurrency group and archive revision check protect
against overlapping publications. Source is `Clash_Recruitment.py` (version 4.5);
`github_recruiter.py` supplies encrypted restore/save and a noninteractive run.

## Integrated dashboard and independent scans

The recruitment view now renders native dashboard cards, filters, verification details and a collapsible clan-turnover table. It shares the dashboard’s scrolling and navigation. Matching Town Hall images sit beside player names. Scroll reveals respect reduced-motion preferences. New scans include structured display data; older saved HTML reports are read as data without executing their markup or scripts.

Recruitment collection runs independently through `.github/workflows/update-recruitment.yml`, daily around 7:35 AM America/Denver or manually. Clan updates, including the post-war capture, retain the last recruitment report. The recruitment button submits only a recruitment request and shows its own estimate/progress, using dashboard access without a GitHub token.

## Recovery and verification corrections

Detected departures remain pending when the first profile lookup fails, including their observation window. Failed checks update the attempt time; the last successful verification time remains unchanged. Local recruiter files fail closed on unreadable JSON. A completed generation manifest is the commit point for the related state files; the previous generation and `.previous` mirrors support recovery. CSV exports escape spreadsheet formula prefixes, including leading whitespace/control characters.
