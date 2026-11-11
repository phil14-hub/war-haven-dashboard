# War Haven troop chase

The live member portal is the **War Haven shared actions** Sites project. Its
`worker/header-runner.js` renders the existing sprite sheets and grass scene
for Leadership and each personal dashboard. The signed-out portal keeps the
personal scene in an inert template until the dashboard opens.

The shared clock lives in `shared/troop-chase-timeline.mjs`. The Sites copy is
`public/troop-chase-timeline.js`, tracked in `canonical-assets.json` and
bundled into the versioned renderer by the portal build. When updating the
clock, synchronize the copy and its manifest hash using
`scripts/sync_assets.py` as the source of the mapping. Review other asset
drift independently so a chase release changes only the chase.

The renderer samples elapsed wall time from the origin saved in the browser
tab's session storage. The saved lane width schedules full passes and keeps
their order and phase aligned when the two dashboards have different widths.
The renderer fits the current pass to the available space. Each round
contains all six pursuers in a seeded random order. When the Miner is fully
in view, it runs for 3,000 ms, digs, tunnels, and emerges ahead. Both sprites
reverse 120 ms into the emergence and later pursuers keep that direction
until the next Miner. Offscreen and background views skip drawing and
sample the current time on return.

## Verification

- Run `node tests/troop-chase-timeline.test.mjs` and the dashboard release checks.
- Build and test the Sites checkout with the synthetic leadership fixture.
  The header tests cover the sprite poses, three-second chase, reversal,
  responsive sizing, skipped frames, randomized rounds, and renderer cleanup.
- In both dashboard views, check desktop and mobile layouts, scroll offscreen
  and back, change sections and return, and switch browser tabs. Confirm one
  scene draws and elapsed time advances through each transition.
- Publish the existing Sites project with the matching renderer. Verify the
  deployed build and the signed-in member and leadership dashboards.
