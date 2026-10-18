# War Haven audit corrections · October 17, 2026

The correction pass implements all 28 reported issues and the 20 improvement areas from the full audit. Existing accounts, clan history, audience, domains and ownership rules are retained. Optional authenticator enrollment and explicit historical-flag/role-review controls avoid silently changing clan policy.

The portal release uses additive migrations 0005–0006. It requires the Site-managed `MEMBER_MFA_KEY` secret; keep that key stable across deployments. Existing mail settings are preserved. GitHub collectors use signed main-branch OIDC identities for machine actions. The independent portal sync workflow covers cloud and Pyto publications.

| Audit item | Result |
| --- | --- |
| F01 | Password/access changes revoke pending email confirmations; password reset mutations are atomic. |
| F02 | Attendance edits merge into the captured war; unchanged players retain attack detail, XP and metadata. Contradicted attack detail is invalidated. |
| F03 | Current roster TH must match a timestamped profile before member army completion is shown. |
| F04 | Settings submit the version with which the form was rendered; stale saves reject and retain the draft. |
| F05 | Automatic refresh retains unfinished village import text. |
| F06 | Shared leader preferences preserve XP and other drafts and do not overwrite a dirty settings form. |
| F07 | Boolean preferences cannot replace string enum/time-zone fields. |
| F08 | Any approved in-clan village can keep its approved account eligible; previews/restoration handle secondary villages. |
| F09 | Account creation reports delayed verification delivery explicitly with a sign-in/resend path. |
| F10 | Expiry/account changes clear selected-village and preview state. |
| F11 | Cross-device goal changes participate in refresh comparison and rendering. |
| F12 | Newly approved villages reconcile into the active switcher. |
| F13 | Pending-account polling leaves active verification/resend forms intact. |
| F14 | Unverified departures retain their observation window for later retry. |
| F15 | Failed profile checks update attempt time, preserving the last successful verification time. |
| F16 | GitHub/portal publication outcomes are separate; partial status remains below 100% until portal reconciliation. |
| F17 | Independent `sync-portal.yml` synchronizes matched encrypted revisions after local/Pyto pushes and retries without a new collection. |
| F18 | Initial individual leader pages supply the complete authenticated envelope required by owner password tools. |
| F19 | Private local leader edits/pending drafts are encrypted; legacy plaintext caches migrate and clear on sign-out. |
| F20 | Leader/member participation denominators exclude excused opportunities consistently. |
| F21 | Performance/trends deduplicate recorded orders and validate integral stars and bounded destruction. |
| F22 | Player Dashboard and Approval History headings use proper title pairs. |
| F23 | Lower-bound chart captions say “At least.” |
| F24 | Recorded values/tooltips preserve numeric precision separately from compact captions. |
| F25 | Touch inspection supports second-tap and outside-tap dismissal with one active chart point. |
| F26 | Date-entry controls explicitly identify device time. |
| F27 | Explicit member/leader URLs open the matching sign-in form. |
| F28 | Declined village requests no longer consume the active village limit. |
| S01 | Timeouts, offline/update errors, registration partial success, busy forms, startup guidance and request-safe error logs are added. |
| S02 | Device sign-out and all-device sign-out are separate; individual leader reload behavior is labeled accurately. |
| S03 | Shared encrypted revision checks cover attendance, war corrections, XP, imports and reviewed flags, with actor/action metadata. |
| S04 | New/reset passwords use 15-character minimums and padded breached-password screening. Optional TOTP has encrypted secrets, replay checks and hashed one-use recovery codes. |
| S05 | Website and game roles are explicit; the owner can acknowledge differences in the audit history. |
| S06 | Individual leaders can review historical attendance flags while retaining the actual war facts. New wars still follow the existing policy. |
| S07 | Small labels are larger, touch targets/focus styling improve, dialogs are named and charts retain keyboard inspection. |
| S08 | Portal refresh uses authenticated conditional data projections, reuses projections only within a request and defers heavy hidden-panel rendering. |
| S09 | Portal assets have content hashes; leader/member code versions prompt safe reloads with draft guidance. |
| S10 | Drizzle is upgraded to 0.45.4; the production dependency audit reports zero known advisories. |
| S11 | Canonical catalog/model generation, digest checks and duplicate-name checks prevent portal drift. |
| S12 | Current account, upgrade, domain, collector and recovery documentation is updated; historical reviews are labeled. |
| S13 | Members can unlink/reapply/change primary village; leadership can revoke additional links. Clan statistics remain intact. |
| S14 | Signed GitHub Actions identities scope ingest/claim/progress/finish/reconcile to approved main-branch workflows. Browser proof cannot perform machine actions. |
| S15 | Unreadable recruiter data fails closed. A completed generation manifest provides an atomic commit point and recoverable prior files. |
| S16 | Recruiter and roster CSV fields escape formula prefixes, including leading whitespace/control characters. |
| S17 | Goals explain captured stars, season resets and baselines. Comparisons show samples/windows, minimum samples and tied ranks. |
| S18 | Announcements include author/edit time, preview, CAS edits, archive/restore, audit entries and updated unread state. |
| S19 | The genuine current crest renders identically with one embedded PNG, about half the SVG payload. XP OCR has loading/progress/cancel/retry and requires manual confirmation. |
| S20 | New regressions cover these failure cases using the real server/helpers/rendered pages; CI requires the generated leadership fixture and includes shared/catalog/model triggers. |

## Verification and practical limits

Automated checks cover 66 Python tests, all portal JavaScript test files, the populated leadership fixture across all navigation surfaces, security/MFA replay/concurrency, publication failures and worker packaging. Tests use synthetic accounts, in-memory databases, stub mail and isolated DOM environments. No real clan records, accounts, notices or emails were changed for testing.

Real desktop/phone browser visual QA, actual verification/recovery email delivery, genuine XP screenshot recognition, and mobile load timing were unavailable in this environment. The real current crest was rendered and pixel-compared; other badge geometries remain to be checked if the clan changes its badge. OCR continues to use the pinned reader CDN with manual entry as fallback; self-hosting was optional in the audit and is not required by this release.

A new leader code version requires reloading after shared saving finishes. Member and leader data synchronization is verified through the independent workflow; retained encrypted history is never replaced with a fixture or an empty archive.

`rebuild-dashboard.yml` republishes current code over the verified encrypted archive on source changes. It does not depend on a fresh Clash API lookup and does not erase or replace saved history.

Publication verification also handles unavailable Pages status checks after a successful commit and accepts a later source-only Pages build containing the identical encrypted page/archive blobs.
