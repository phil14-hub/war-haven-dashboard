# Troop chase: portal integration checklist

This branch adds a **tested timing foundation**, not a replacement for the already-published animation. The visual scene is maintained in the War Haven Sites member-portal source, not in this GitHub repository. The live portal requires a separate renderer integration and deployment before this change has any user-visible effect.

## Goal

- Show the same Barbarian / randomized troops / Miner chase on both **Leadership → Overview** and each **individual player's dashboard**.
- The Miner chases visibly for **3 seconds**, then digs, tunnels ahead, emerges, and reverses every troop's direction.
- Moving to another dashboard section, scrolling off-screen, refreshing, or returning to the overview must **not reset or pause elapsed chase time**.
- When an inactive browser tab throttles frames, its next drawn frame should jump to the correct point on the same timeline. Browser throttling cannot be disabled.

## Source of truth

The canonical source is \`shared/troop-chase-timeline.js\`, published to the Sites source as \`public/troop-chase-timeline.js\` by \`scripts/sync_assets.py\`. It exposes:

\`\`\`js
const clock = WarHavenTroopChaseTimeline.createClock();
const stopDrawing = clock.run(frame => {
  // Drive the existing chase sprite renderer from this snapshot:
  // frame.phase, frame.phaseElapsedMs, frame.phaseProgress,
  // frame.direction (+1 or -1), frame.reversals, frame.turnProgress,
  // frame.cycle.
});
// On route unmount: stopDrawing(). Keep the browser sessionStorage record.
\`\`\`

Use the default storage key on **both** pages so a route change continues the same animation timeline. Do **not** call \`clock.restart()\` on routine render, page, scroll, visibility, resize, or route events. Restart is reserved for an explicit user reset.

For each chase cycle, call \`clock.shuffleTroops(troopNames, timestamp)\` to derive a stable randomized troop order. Use the same frame time when choosing the cycle and rendering positions. Avoid re-randomizing on every animation frame.

The previous standalone animation used \`elapsed += Math.min(75, dt)\` in its \`requestAnimationFrame\` tick, which silently paused logical time whenever frames stopped. Replace this accumulation with \`clock.at()\` and render based on the returned phase and elapsed time. Reversal position tweens should derive from \`frame.turnProgress\`, not from a separate cumulative delta. If the scene is remounted, its sprites should be immediately placed at the returned positions.

The original animation's HTML/CSS/sprites, motion, and other interactions should remain unchanged. Avoid mounting an additional clone on top of an already-existing scene. The Sites app should install the existing chase once per visible scene, clean up listeners and animation frames at unmount, and recreate it with the same clock on return.

## Validation before publication

1. Leadership overview and individual dashboard both show the chase.
2. Leave either page's chase offscreen for 30 seconds, return, and verify it has advanced rather than restarted.
3. Navigate Overview → other section → Overview and personal Dashboard → other page → Dashboard, in each direction, without restarting.
4. Leave the browser tab inactive for a minute and verify the cycle/number of reversals reflects elapsed wall time.
5. Confirm the Miner digs **3 seconds** after a cycle starts, then emerges ahead and reverses all troop motion.
6. Verify random troop waves do not re-randomize mid-cycle, responsiveness remains intact, and only one chase scene is visible on each page.
7. Run \`node tests/troop-chase-timeline.test.mjs\` and the normal repository/Sites build and UI suites.

**Do not merge/deploy this draft until the Sites renderer uses the timeline; simply copying the new asset to \`public/\` does not activate it.**
