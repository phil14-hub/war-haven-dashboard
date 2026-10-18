# Upgrade progress and dashboard preferences

Army work uses the `th-work-v2` method. The zero reference is the previous Town Hall maximum. The score is:

`100 × (new-TH work completed − unfinished earlier-TH work) / all new-TH work`

Work uses standard, unboosted upgrade durations. Laboratory, hero and pet work have separate breakdowns; the combined work score excludes equipment. The primary completion percentage separately credits every completed army upgrade available at the current TH, divided by all available army work. It is not the signed current-TH work score. For example, nine of twelve maxed pets can have high completion while the signed backlog score is negative. Instant unlocks receive one reporting unit so a missing unlock cannot count as complete. A score can be below −100%. Missing or incompatible data stays unknown. A category with no new upgrades shows remaining levels instead of dividing by zero. Equipment shows owned-piece level completion and separate ore balances.

The normalized game catalog comes from clashy.py 26.9.1, backed by the ClashKing static data. Source URL, version and SHA-256 are embedded in `upgrade_catalog.json`. Recheck the catalog after game releases. Historical scores are versioned; charts do not mix old level-count percentages with the new work score.

Village imports accept the in-game JSON export from Settings → More Settings → Data Export → Copy. The server matches the tag to an individually approved linked village, validates levels and counts, and stores a sanitized summary. Grouped idle structures and individual active structures count separately. Merged structures credit consumed predecessors. Countdown estimates use the exported timestamp; passing the estimated finish never confirms a new level. A newer import is required. Public API data cannot supply building queues.

Graph histories keep the first observation and changes to their own metric. Consecutive display duplicates collapse; a return to an earlier value remains visible. Source war, raid and contribution evidence is retained. A marker-free flat tail reaches the latest successful sync. Exact dates and values remain available with pointer, keyboard or tap and in a table.

Player preferences and goals belong to the website account and selected village. The leadership display preferences are shared and use version checks to prevent one device overwriting a newer save. Remembering the last open section stays local. Username, verified email changes, notification reads, and linked villages always belong to the individual login.

Additional villages require a separate leadership ownership confirmation. An imported export is not ownership evidence. Announcements are the notification source, so ordinary data syncs cannot duplicate them.

## Completion, freshness and goals

The primary army completion metric counts standard-time-weighted completed work across all available laboratory, hero and pet upgrades. Equipment/buildings remain separate. The signed current-TH work metric remains available in its own explanation. An old Town Hall profile is never displayed as current completion; the member view includes its captured time and waits for a matching successful profile. `upgrade_catalog.json` is canonical; `scripts/sync_assets.py PORTAL_PATH` generates the portal copy and digest manifest. Builds reject drift and duplicate named army units.

Member goals identify captured war stars and explain season resets/current-counter behavior. Comparison rankings show attack sample counts and captured periods, allow a minimum sample threshold, and assign equal values the same rank. Estimated attendance remains distinct from recorded destruction and actual attack-use rates. Excused opportunities are excluded from participation denominators in both leader and member views.
