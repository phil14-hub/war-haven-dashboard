# Setup, passwords and recovery

## Personal account access

Use [Member or Leadership sign in](https://portal.warhavenclan.com/members/). **Forgot username** sends a reminder; **Forgot password** sends a single-use reset link valid for 30 minutes. New/reset passwords require at least 15 characters, up to bcrypt's 72 UTF-8 bytes; existing passwords remain valid. Verification links last 24 hours. Check spam, then retry after the displayed delay if no email arrives.

An account password reset signs out existing sessions and retains authenticator protection. Use an authenticator recovery code if needed. Recovery codes are shown once; keep them privately. Contact an authorized owner if both the authenticator and its recovery codes are unavailable. Do not create duplicate accounts to work around lost access.

The owner must retain `RESEND_API_KEY`, a verified `MAIL_FROM` sender and the Site-managed MFA encryption key. Missing email configuration closes registration rather than bypassing verification. Ordinary Sign out affects this device; Sign out all devices is a separate Settings action.

## Change the shared dashboard password

This is separate from your personal account password. Open **Settings → Leader settings → Change shared password**, also linked from **Management → Operations**.

1. Keep a matching encrypted dashboard/archive backup and the current password.
2. Enter the current shared password and the replacement twice (at least 12 characters).
3. Supply a temporary fine-grained GitHub owner token restricted to `phil14-hub/war-haven-dashboard`, with repository Contents and Actions Secrets read/write. The repository owner's identity is checked. The token is not saved.
4. The browser verifies the current password locally, reads matching website/history revisions, re-encrypts both, updates the `DASHBOARD_PASSWORD` Actions secret and publishes the encrypted pair. A concurrent publication stops the change; a confirmed failure restores the previous secret.
5. Wait for publication and portal synchronization. Test the new password, then update each Pyto collector's saved password and share it privately with authorized users. Check Operations for failures or partial delivery. SMS alerts are disabled.

If the response is lost, test the new password against the latest publication before retrying. If the interface reports an uncertain secret rollback, check the latest encrypted pair and set `DASHBOARD_PASSWORD` to the password that unlocks it before resuming collection. Never replace the archive with an empty file to fix access.

## Website owner recovery

An approved owner can manage lower roles and assign leadership permissions in the audited account list. If a restored older database has **no approved website owner**, a verified, signed-in current in-game clan leader may see **Recover website owner access** on the pending page. This requires the account password, fresh GitHub repository-owner authorization and authenticator/recovery-code confirmation when enabled. Recovery records an audit entry and invalidates existing sessions. Normal login never promotes or approves an account automatically.

The emergency route refuses recovery when an approved owner already exists, the leader is no longer present in the captured clan roster, or the village belongs to another active account. Resolve those cases through the existing owner or a controlled deployment/database repair with a backup. Preserve the MFA key, account hashes and village links. Applied migrations remain part of recovery compatibility.

## Pyto setup and archive recovery

Keep `Documents/Clash_Recruitment` and existing local state/backups. Replace the collector script and run it. Use the same repository and shared password. A publishing token needs Contents read/write and Pages read for this repository. Keep API keys and `dashboard_website.json` on the device; they are excluded from publication.

On another device, the collector downloads and merges `data/war_tracker_state.enc.json` before collection. If the archive cannot be authenticated, publishing stops and local history remains intact. Resolve the password, connectivity or permissions, then rerun. A concurrent publication requires another merge, never a force overwrite.

To recover an older version, restore **both** encrypted `index.html` and `data/war_tracker_state.enc.json` from the same successful revision using a password you still know. Keep the latest originals as well. Retain shared encrypted records and war evidence. Previous Git revisions and downloaded copies keep their original password; changing today's password cannot revoke them.

For a collector-side password change, run `--setup-website` on the configured device. It retains the old password in memory while restoring the current archive, then publishes the re-encrypted pair. Set the Actions `DASHBOARD_PASSWORD` secret to the new password before unattended collection resumes. Prefer the website's coordinated owner procedure when automation is active.
