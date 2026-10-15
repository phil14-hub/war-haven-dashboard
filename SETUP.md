# Setup and recovery

The repository and GitHub Pages source are already configured. Use `Clash_War_Tracker.py` version 1.13 for encrypted history synchronization.

## Publishing from Pyto

Keep your current clan state files in `Documents/Clash_Recruitment`. Replace the Python script and run it. The first setup asks for:

- **Dashboard passphrase:** use the passphrase delivered privately with the website. It unlocks both the dashboard and the initial encrypted archive.
- **Repository:** press Return for `phil14-hub/war-haven-dashboard`.
- **Publishing token:** a fine-grained GitHub token restricted to this repository, with Contents read/write and Pages read. Create it in your GitHub personal settings under Developer settings → Personal access tokens → Fine-grained tokens. Choose an expiration you can maintain.

You can open the local dashboard without publishing by entering `local` at the repository prompt. On subsequent runs, settings load from the device-local `dashboard_website.json`. That file is excluded from published data and backups.

## Recover on another device

Download the current collector, configure the same repository and passphrase, and supply a token with access to it. The collector reads and merges `data/war_tracker_state.enc.json` before its first refresh. Existing notes, war results, contributions, league history, progress history, manual XP checkpoints and saved lineups are preserved. Your Clash API key must permit the new device/network’s outgoing IP.

If the GitHub archive cannot be unlocked or downloaded, publishing pauses and local history is retained. Resolve the passphrase, connectivity or permissions before retrying. If another collector updates the archive during a run, the collector stops that upload instead of overwriting it; rerun to merge.

## Change the dashboard passphrase

On the existing configured collector device, run with `--setup-website` and enter the new passphrase. The previous local passphrase is retained in memory for that run so the existing archive can be read and re-encrypted. After the combined publication succeeds, share the new passphrase with your chosen leaders.

Changing a passphrase protects future publications. Prior Git revisions and downloaded copies remain protected by the passphrase used at the time. Keep the private access details in a password manager; they cannot be recovered from encrypted data.

## Website access and editing

The repository source is public. The website and clan archive are encrypted using PBKDF2-SHA256, AES-256-CBC and encrypt-then-HMAC-SHA256 with fresh salt/IV on every publication. The passphrase is never sent to the website host. The archive is compressed before encryption.

Reload the website or use **Manage → Lock dashboard** to lock it again. Anyone with the passphrase can view the dashboard; in-game roles are not automatically authenticated. Do not give clan members repository write access just to let them view the site.

Browser changes remain local until exported and merged on the collector device. This update centralizes published history and code on GitHub; it does not turn GitHub Pages into a live database or start an automatic collector.
