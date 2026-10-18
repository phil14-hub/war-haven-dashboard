# Navigation, account flows and follow-up corrections

October 18, 2026

This release implements the approved second-audit areas: final-list **3 (navigation), 8 (account flows), 10 (chart keyboard controls)**, plus **B01–B11**. Other design suggestions remain future work.

- Member and leadership pages use safe hash routes. Back/Forward restores pages and player reports; roster/performance filters and profile sections are addressable. Role checks remain on the server.
- Management groups account access, communications, operations and help. Announcements have a direct destination. Mobile users get a labeled section selector or More menu.
- Settings separates village display choices, website credentials, linked villages and account security. Primary-village changes preserve legacy goals on their original village.
- Account creation and review show setup steps. Declined and paused accounts have accurate next actions. Recovery has persistent confirmation and cooldown; forgotten usernames are sent only to the registered address with a generic public response and address/IP throttles.
- Optional authenticator enrollment generates its QR locally using pinned `qrcode-generator` 2.0.4, with a manual-key fallback, setup expiry, copy/download recovery codes and save acknowledgement. Disable and replacement have distinct result screens. Secrets and codes are not retained in page drafts.
- Charts use one keyboard entry, arrows and Home/End to move through observations, and Escape to dismiss. Exact-value tables remain available. Document/host listeners stay bounded as charts are replaced.

| Follow-up | Result |
| --- | --- |
| B01 | Reopened settings drafts retain their original version. Explicit reload/review reconciles edits with the newest saved values. |
| B02 | Only the latest village-switch response can change the active view. |
| B03 | Goal-type visibility and required fields are recomputed after draft restoration. |
| B04 | `lineupDrafts` stores collaborative exploration; `lineupPlans` stores validated committed teams. Legacy incomplete plans migrate to drafts. Committed size is fixed, changed commits require review, and exports use the committed team. |
| B05 | Home availability uses the same confirmed-opt-in regular-war rule as the planner. |
| B06 | Declined, paused, verification, roster and review states have distinct guidance. |
| B07 | An intentional Choose dashboard action overrides the direct-entry portal hint. |
| B08 | Disabling MFA shows a disabled result, with no empty recovery-code screen. |
| B09 | Session expiry transitions to sign-in and retains only safe in-memory drafts for the same account/village. No action is automatically replayed. |
| B10 | Saving instructions distinguish shared status, working drafts, committed lineups and optional private exports. |
| B11 | Shared charts use one document dismissal handler and one set of host handlers per chart. |

No destructive migration or reset is required. Existing accounts, clan history, domains, audience and MFA encryption key are retained. Additive draft record support must be deployed to the portal before publishing the new leadership client.

Verification covers the Python suite, portal account/security/data/UI suites, actual populated leadership DOM across both navigation layouts, route/profile/history behavior, draft/commit validation, stale-device recovery, village response ordering, QR generation and chart listener counts. Tests use synthetic accounts, isolated databases and stub mail. Real-device visuals, screen-reader behavior and real email delivery remain to be checked in a browser; automated tests do not certify those experiences.
