# War Haven

The member portal is [portal.warhavenclan.com/members/](https://portal.warhavenclan.com/members/). Individual accounts provide private member dashboards and role-based leadership tools. The encrypted GitHub Pages dashboard remains available for shared access and recovery. Website permissions and Clash roles are separate.

## Start here

- **Member:** follow [Account and village access](MEMBER_ACCOUNTS.md). Create one account, verify your email, and wait for ownership review. Use **Add village** for additional villages. **My wars** labels confirmed clan results Victory, Defeat or Tie; your attacks appear separately.
- **Co-leader:** open **Management → Approval action list**. Account and village requests share one list. Notifications link to the exact request. Verify ownership in Clash before approval. Attendance flags open the underlying saved wars; incomplete captures are not confirmed misses.
- **Leader/owner:** use **Management → Operations** for data capture times, update progress, successful and failed workflows, stuck jobs and maintenance status. Follow [Setup and recovery](SETUP.md) for password changes, lost access and archive recovery. SMS alerts are disabled.

## Data and operations

The collector restores and merges the encrypted archive before changing published data. Roster validation and snapshot consistency checks run before publication. Incomplete final-war captures remain labeled incomplete and retain their evidence. Clan and recruitment collection run independently, with a shared publication queue to prevent concurrent archive writes.

[Automatic updates](AUTOMATIC_UPDATES.md) covers scheduling and workflow setup. [Shared actions](SHARED_ACTIONS.md) covers encrypted collaboration. [Recruitment](RECRUITER.md) covers candidate collection. [Upgrade coverage](UPGRADE_PROGRESS.md) documents the existing upgrade model; this maintenance release does not change it.

| Source | Purpose |
| --- | --- |
| `Clash_War_Tracker.py` | Portable Pyto/desktop collector and embedded dashboard |
| `shared/`, `member_accounts.js`, other browser sources | Canonical dashboard UI and shared features |
| `scripts/sync_embedded_assets.py` | Regenerates portable fallbacks; `--check` detects drift |
| `index.html` | Published encrypted dashboard |
| `data/war_tracker_state.enc.json` | Complete encrypted archive |
| `.github/workflows/` | Collection, final capture, source verification and portal delivery |

The separate Sites source owns member authentication, permissions, notifications and database migrations. Its immutable publication generations use one atomic pointer. Repeated delivery of the same publication reuses that generation. Maintenance removes only old generated delivery copies after seven days, retaining the current and previous generations. Encrypted archives, shared records, war evidence and applied migrations are preserved.

## Development checks

Use Python 3.12+ and Node 22+. Install `requests==2.34.2` and `npm ci --ignore-scripts`, then run:

```bash
python scripts/sync_embedded_assets.py --check
python -m unittest discover -s tests -v
python tests/create_leadership_fixture.py
WAR_HAVEN_DASHBOARD_FIXTURE=tests/fixtures/leadership.html npm run test:ui
```

The UI runner discovers every `tests/*.test.mjs` suite. Backend changes also require the Sites project's full test runner, build and artifact validation. Source rebuilds use the same release checks before publishing. Synthetic DOM tests complement, but do not replace, real-device visual checks.

Never commit provider tokens, passwords, plaintext state, private access files or local backups. Town Hall images are bundled from [ClashKingAssets](https://github.com/ClashKingInc/ClashKingAssets/tree/main/assets/buildings/home-village/town_hall). Supercell owns the game assets. Embedded pyaes and libsodium retain their original licenses.

See [CHANGELOG.md](CHANGELOG.md) for the consolidated maintenance record.
