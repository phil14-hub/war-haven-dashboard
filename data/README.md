# Encrypted clan history

`war_tracker_state.enc.json` holds the complete compressed and encrypted clan archive. The collector merges it with device-local history before refreshing and updates it in the same commit as `index.html`.

The first published revision is an empty baseline. Actual clan records are uploaded when the updated collector runs on the device where those records are saved. No synthetic player or war data is published as real clan history.

Do not replace this file with plaintext JSON. Credentials and the shared passphrase are excluded. Previous encrypted revisions are available in Git history.
