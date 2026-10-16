# Automated War Haven recruiter

The recruiter now runs on GitHub as part of **Update clan dashboard**, using the
same approved Clash API route and the same three existing repository secrets.
There are no additional credentials to enter. The daily scan targets **7:23 AM
Mountain time**; manual dashboard updates also run the recruiter. Code changes to
the collector/recruiter start a scan so the hosted version can be verified.

Open **Manage > Recruiter** for the latest results. The report uses the same navy
backgrounds, gold actions, cards, typography, and mobile layouts as the dashboard.
Use **Refresh recruiting candidates** for the manual update controls. You can use
the GitHub route or a private owner token with Actions read/write from the website.
Your phone and Pyto can remain closed during scheduled scans.

## Search behavior

- Target up to 50 active candidates with Town Hall 11 or higher.
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
