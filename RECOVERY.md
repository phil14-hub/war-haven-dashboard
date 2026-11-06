# Website recovery

There are two different backups:

- **Export clan history**: readable clan data and leadership edits. Import merges same-clan, version-1 files up to 20 MB. It does not contain website accounts or private plans.
- **Website recovery backup**: encrypted account database and active durable storage, including private plans, linked villages, imports, goals, preferences, MFA records, announcements, shared records, and the current publication generation. Source code remains in the Sites source repository and GitHub.

## Routine protection

The existing twice-hourly portal maintenance job creates a complete recovery snapshot when the last successful snapshot is at least 24 hours old. Recognized recovery objects are retained for 14 days. Status shows the last successful backup and any maintenance failure. Data changing during capture causes a retry; no incomplete snapshot becomes current. A failed backup retains the prior complete backup. Streaming serialization and compression avoid duplicate full-size memory copies. A 32 MB uncompressed safety limit bounds Worker memory; exceeding it requires an operator to partition/expand the backup implementation, rather than silently omitting records.

Database tables are read together in a D1 batch. Durable R2 object revisions and the database are rechecked before sealing. Active sessions, reset/verification tokens, rate limits, pending email changes, temporary health/update records and obsolete delivery generations and superseded legacy delivery files are excluded. Restoration invalidates old sessions. Pending users can request new verification/recovery messages.

Automatic snapshots use AES-256-GCM and a purpose-separated HKDF key derived from the existing MEMBER_MFA_KEY. Preserve that secret separately before rotating it. An owner can also download a self-contained encrypted recovery export using a separate 12–200-character backup passphrase (PBKDF2-SHA256, 600,000 rounds). That export includes the MFA encryption key inside its encrypted payload. Keep the export and its passphrase separately off the website. A server-side backup alone cannot protect against loss of the entire hosting account.

## Owner download

Open Management → Update health & recovery → Website recovery backup. Check its saved time, choose **Create recovery backup** if needed, or enter an export passphrase twice and choose **Download encrypted recovery export**. This passphrase encrypts the file; it does not change your account password. Keep it safely; it cannot be recovered from the export. No extra owner password/MFA step-up was added.

## Tested isolated restore

1. Obtain the encrypted owner export and the matching Sites source checkout (including `drizzle/` and `scripts/restore-recovery-backup.py`). Keep the original encrypted clan archive and its existing dashboard passphrase too.
2. Install the tested native dependency: `python -m pip install cryptography==50.0.2`.
3. Run `python scripts/restore-recovery-backup.py export.json /absolute/path/to/new-recovery-folder`. Enter the export passphrase at the hidden prompt. For an automatic R2 snapshot, add `--server-key` and enter the separately preserved MEMBER_MFA_KEY.
4. The tool authenticates/decrypts, bounds decompression, verifies R2 checksums and paths, applies the source migrations to a new local SQLite database, restores durable rows/objects, invalidates sessions and runs integrity/foreign-key checks. It refuses existing output directories. No production endpoint restores or overwrites accounts.
5. In an isolated deployment of the matching source, have the hosting operator import `accounts.sqlite` into its D1 binding and upload `r2/` objects with metadata from `r2-metadata.json`. Restore MEMBER_MFA_KEY from the protected recovery-secrets file. Configure mail/provider credentials separately; those credentials, domains, hosting identity and connected-app grants are not included. Sites' exposed tools do not currently provide D1/R2 bulk restore, so provider/operator assistance is required for this deployment step.
6. Check owner/member sign-in, MFA, leadership denial for members, private plans/goals/imports, shared notes and publication consistency. Reconnect collectors only after this verification. Make production cutover/rollback a separate deliberate operator action.
7. Securely remove plaintext recovery output after the test. Keep the encrypted export and recovery record.

The automated regression creates synthetic accounts, plans, links and R2 objects, encrypts an export in the Worker implementation, restores it using the Python tool into a new SQLite/R2 folder and compares records. It also checks wrong passphrase, tampering, role denial and failure retention. This is an isolated restore test, not a production disaster cutover or verification of provider-managed backup settings.
