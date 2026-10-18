# Individual War Haven dashboards

The public website offers Leader / Co-Leader Sign In and Member Sign In. Personal accounts use the member portal at https://portal.warhavenclan.com/members/. Existing leadership passphrase access remains available during account setup.

## Registration and approval

1. Choose a player tag, unique username, private email and password. Usernames use 3–24 letters, numbers or underscores and are case insensitive. Passwords require at least six characters; common passwords are rejected. Longer passwords and password managers are supported. A show/hide control is provided.
2. Verify the email using a single-use, expiring link. The email is also used for password recovery.
3. Sign in to the pending-review page. New arrivals can wait here until a successful clan update captures their tag.
4. Leadership opens Management → Account approvals. The review shows the saved player name, tag, Town Hall, in-game role, username, email verification status and application date. Leaders can approve, decline, suspend access or request ownership confirmation.
5. Approval requires a verified email and the tag in the latest successful clan roster. Leadership confirms ownership separately; a public player tag alone does not prove ownership.
6. Approval makes the personalized dashboard available immediately. It does not create a separate website or duplicate the complete clan archive. An open pending page notices approval automatically.

Daily and manual clan updates refresh membership. Failed or incomplete roster collection does not replace the last successful roster. A confirmed departure suspends access and invalidates current sessions. Rejoining requires another approval.

## Member views

Members receive only their own detailed member projection plus the approved comparison metrics for the current roster. The views include overview, captured Regular/CWL wars, recorded contributions, league/army progress graphs, hero levels, milestones, clan comparisons, personal goals, leadership announcements and account details. Times use the viewer's device time zone. War availability is read from saved in-game observations and must be changed inside Clash.

Capital Gold and donation increases are confirmed lower bounds within the observed clan stint. Unknown data is labeled rather than attributed to War Haven. Recent graph projections retain up to 730 observations; the complete history remains in the encrypted archive. Private leadership notes, recruiting records, internal management flags, shared-edit keys and password hashes are excluded from member responses.

## Leadership and recovery

Approval grants member access. Assigning website leadership permissions is a separate action requiring GitHub owner authorization, or an already authorized owner account. Changing permissions invalidates that account's existing sessions. Individual leadership accounts can open the complete leadership dashboard after approval and role assignment. The legacy passphrase route provides owner recovery during migration.

Passwords are stored as salted bcrypt hashes with cost 12. Session cookies are Secure, HttpOnly and SameSite=Lax; only hashed session/reset/verification tokens are stored in the database. Remember me lasts up to 30 days; ordinary sessions last eight hours. Reset links expire after 30 minutes and verification links after 24 hours. Password reset invalidates existing sessions. Registration and login requests are throttled. No owner token is retained by the website.

## Required email activation

Registration stays closed until a verified transactional email sender is configured. There is no bypass or simulated email verification in production.

The prepared delivery adapter uses Resend. In the existing shared-actions Site's environment settings, configure:

| Name | Value |
| --- | --- |
| `RESEND_API_KEY` | A sending key from the owner's Resend account; store as a secret |
| `MAIL_FROM` | A sender on a domain verified in that account, such as `War Haven <accounts@your-domain.example>` |

Deploy the saved Site version after changing runtime environment values. The member portal then enables account creation. Confirm a real verification and password recovery email before inviting the clan. A public provider's default test sender is not suitable for arbitrary clan-member addresses.

## Storage and collection

The existing service retains its R2 bucket. A D1 database stores the small account records, password hashes, review decisions, goals, announcements and expiring sessions/tokens. R2 stores one current member projection and one authenticated leadership publication bridge. The collectors upload only after archive-first restoration and successful collection/publication. Both collectors remain independent.

Collection logs record member-projection size, complete uncompressed history size and leadership-publication size. This feature does not yet move the original GitHub archive/index out of Git history; the planned R2 migration remains separate. Existing history has not been deleted or rewritten.

## Verification

Python tests cover privacy filtering, complete roster validation, contribution baselines and final-war calculations. Account tests use real SQLite migrations and cover pending access restrictions, verification and token replay, owner-only role assignment, secure cookies, immediate approval access, confirmed departure/rejoin handling, goals, announcements, recovery and unavailable-email gating. Browser visual QA was unavailable in the build environment; live email delivery requires owner email activation.

## October 17 audit corrections

Use https://portal.warhavenclan.com/members/?portal=member or `?portal=leader` for the corresponding sign-in form. The public portal has private, individually scoped account data. Website roles and in-game roles are distinct; the owner can acknowledge differences in the audited account list. A primary village departure does not block an approved in-clan secondary village. Accounts can change their primary approved village, unlink additional villages, or request a declined/unlinked village again. Leaders can revoke additional village links without deleting clan statistics.

New and reset passwords require at least 15 characters (bcrypt's 72 UTF-8 byte limit still applies) and a maintained breached-password check using a padded five-character hash-prefix request. Existing passwords continue to work. Password-screening outages preserve accounts and reset links. Settings & accounts offers optional authenticator sign-in, encrypted server-side TOTP secrets and ten single-use recovery codes. Password resets retain enabled MFA. Keep recovery codes somewhere private; they are shown once. The Site-managed MFA key must be retained across deployments.

Ordinary Sign out affects this device; Sign out all devices is a separate account control. Recovery/access changes invalidate pending email-change links. If initial verification email delivery fails, the created account is reported explicitly with a sign-in/resend path. No real email was sent during automated regression testing.

Announcement authors and edit times are visible. The author or owner can preview/edit/archive announcements; edits become unread and changes appear in Approval History. Routine collector synchronization creates no announcements.
