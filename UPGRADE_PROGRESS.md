# Upgrade progress and dashboard preferences

Army work uses the `th-work-v2` method. The zero reference is the previous Town Hall maximum. The score is:

`100 × (new-TH work completed − unfinished earlier-TH work) / all new-TH work`

Work uses standard, unboosted upgrade durations. Laboratory, hero and pet work have separate breakdowns; the combined score excludes equipment. Instant unlocks receive one reporting unit so a missing unlock cannot count as complete. A score can be below −100%. Missing or incompatible data stays unknown. A category with no new upgrades shows remaining levels instead of dividing by zero. Equipment shows owned-piece level completion and separate ore balances.

The normalized game catalog comes from clashy.py 26.9.1, backed by the ClashKing static data. Source URL, version and SHA-256 are embedded in `upgrade_catalog.json`. Recheck the catalog after game releases. Historical scores are versioned; charts do not mix old level-count percentages with the new work score.

Village imports accept the in-game JSON export from Settings → More Settings → Data Export → Copy. The server matches the tag to an individually approved linked village, validates levels and counts, and stores a sanitized summary. Grouped idle structures and individual active structures count separately. Merged structures credit consumed predecessors. Countdown estimates use the exported timestamp; passing the estimated finish never confirms a new level. A newer import is required. Public API data cannot supply building queues.

Graph histories keep the first observation and changes to their own metric. Consecutive display duplicates collapse; a return to an earlier value remains visible. Source war, raid and contribution evidence is retained. A marker-free flat tail reaches the latest successful sync. Exact dates and values remain available with pointer, keyboard or tap and in a table.

Player preferences and goals belong to the website account and selected village. The leadership display preferences are shared and use version checks to prevent one device overwriting a newer save. Remembering the last open section stays local. Username, verified email changes, notification reads, and linked villages always belong to the individual login.

Additional villages require a separate leadership ownership confirmation. An imported export is not ownership evidence. Announcements are the notification source, so ordinary data syncs cannot duplicate them.
