# Corrections checkpoint — paused 2026-10-17

User requested a pause after implementing the collected corrections. Resume only when asked.

## Status

Correction code is implemented. No new live deployment or GitHub main-branch update has been made.

- Python dashboard: 58 tests passed (`python -m unittest discover -s tests -q`).
- Portal: 10 Node test files passed, including leadership startup and exact chart interaction in both themes, roster combinations, screenshot XP review, authentication and canonical navigation.
- Portal build and artifact validation passed.
- Client OCR was also exercised against a synthetic numeric screenshot using Tesseract 6.0.1.
- The updated SVG crest was rendered and visually inspected as a standalone asset.
- Real-browser page screenshots were not checked: the Sites control-browser capability is unavailable in this environment. Do not claim live visual QA.

## Implemented

1. Crest: full shield boundary and gold outline, with the game-level plaque removed using the current badge's pattern; updates with clan badge sync.
2. Canonical portal navigation: `https://portal.warhavenclan.com`; legacy browser routes redirect while legacy API support remains.
3. Refresh: same-origin cookies on snapshot GET/HEAD, descriptive warning tone and preserved view/drafts when a refresh fails.
4. Roster: sorting by average attack use, likelihood, stars per attack, Town Hall, missed-both streak and name; Town Hall and attack-use range filters alongside status/search.
5. Short chart dates omit the two-digit year; details retain complete timestamps.
6. Upgrade completion: 0–100% total standard-duration completion is primary; the prior signed current-Town-Hall work score is separately labeled. All available pets count. Removed duplicate non-upgrade Meteor Golem catalog row. Buildings/equipment remain separate.
7. Charts: visible floating exact-value tooltip and inline detail for hover, click/tap, keyboard focus and Escape, with light/dark styles.
8. Clan XP: explicit four-source explanation, captured explicit war XP, honest exact checkpoints versus level minimums, and local screenshot OCR with required review before saving. No unsupported exact current total is invented.
9. Planner: spacing between action buttons and summary cards.
10. Planner/profile reminder: “Both attacks missed X war(s) ago”; clears permanently after five consecutive confirmed participated wars with at least one attack, including CWL. Sit-outs/excuses do not advance recovery; unknown results interrupt it. Does not block selection.

The Omid-like 12-pet regression fixture (9 maxed, 3 unfinished) produces 85.8% pet completion while retaining the separately labeled -0.5% signed work score. This is synthetic verification, not a verified reading of Omid's actual current profile.

## Sources and pending publication

GitHub repository: `phil14-hub/war-haven-dashboard`.
Base main commit: `767f6b690f934440b25990ec7b51a942a9986732`.
Base tree: `c057f966be2fc822bfef7e47bcf550619de5247a`.
This checkpoint is on a separate branch. Main remains unchanged by this task.

Sites project: `appgprj_6ad1bb739c708191815503ab6330440b`.
Portal source has been committed and pushed through the Sites source workflow:
`eb15f9e302746898fc5110d1b80210e3219cd5df`.
It has NOT been saved as a new Site version or deployed.

Local portal source: `/workspace/scratch/191adb878b2e/war-haven-portal`.
Local GitHub source: `/workspace/scratch/191adb878b2e/war-haven-dashboard`.
Built portal archive: `/workspace/scratch/191adb878b2e/war-haven-corrections.tar.gz`.
Local working scripts and synthetic fixture: `/workspace/scratch/191adb878b2e/inspection/`.

## Resume

1. Review the checkpoint branch against fresh main. Preserve any newer encrypted clan/history updates and reconcile source changes if main advanced.
2. Publish the source changes to main atomically with an expected-head check. The main push triggers Update clan dashboard; watch its tests, collector and encrypted publication. Do not publish the synthetic fixture or plaintext member data.
3. Save/deploy the portal Site using the exact project ID and pushed source commit above. If the local archive is gone, reopen the stored source commit through the Sites workflow and rebuild it. Keep the existing public audience and custom domain.
4. Confirm the collector publishes updated encrypted leadership HTML and member snapshot. Check Omid's actual new completion if signed-in data is available; do not infer it from the synthetic case.
5. Verify canonical redirect/favicon/public health and, when available, real-browser light/dark appearance. Ask the user to reopen the dashboard once to load changed JavaScript.

No passphrases, tokens or private screenshots are included in this checkpoint.
