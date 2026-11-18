# Lossless storage optimization

The encrypted archive is self-contained. Version 2 uses independently checksummed gzip/base64 sections for the complete recruiter and current-progress cache inside the authenticated archive. No candidate records, events, former profiles, dated progress, war/CWL evidence, donations or capital observations are removed. Packing the progress cache also preserves historical calculation outputs exactly across model changes. The 50 MiB outer-document and per-section expansion guards remain in force.

Current collectors restore both version 1 and version 2. Use the current standalone tracker when opening a new version-2 archive. Older trackers reject the version before attempting to load a partial state. Server and browser passphrase rotation retain the incoming archive version and transform authenticated clear bytes without changing the section contents. Existing version-1 daily points remain readable.

Recruiter age labels are generated in the browser from absolute detection timestamps. Rebuilt cloud reports omit those volatile words. Successful roster baselines keep tags, names, Town Halls and capture timestamps. Future scans omit unused XP and trophy fields from that departure baseline. Candidate profiles and trophy observations retain their existing fields and history.

Portal delivery JSON is stored with lossless gzip where smaller. Existing uncompressed generations remain readable. A conditional migration verifies the original and expanded SHA-256 before and after replacing an object. It keeps the original upload date in metadata so migration cannot restart retention.

Intermediate publication generations have a 48-hour rollback window. The current and previous generation remain protected regardless of age. Clan archives and daily recovery points are separate. Thirty-day clan recovery and fourteen-day website recovery remain in place. Former-player profiles, staging recovery files, older daily archives and legacy publication fallbacks remain preserved until a separately verified retirement is appropriate.

Run the main-branch Synchronize member and leadership portal workflow with `storage_optimization=true`. This job shares the collector write queue, verifies the current and previous release and every retained daily point, checks the complete logical archive, applies compression, repeats it to prove convergence, compares all saved logical fields and daily checksums, and reconciles portal/Pages publication. Its aggregate before/after inventory contains no player values or credentials.

The independently packed sections are deliberately included in each downloaded backup. Moving them into external reference-only objects would make older offline restores depend on additional files and requires a separate versioned recovery design. No external-only dependency was introduced in this optimization.
