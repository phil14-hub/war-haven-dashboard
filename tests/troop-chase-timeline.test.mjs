import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { createClock } = require('../shared/troop-chase-timeline.js');

const state = new Map();
const storage = {
  getItem: key => state.get(key) ?? null,
  setItem: (key, value) => state.set(key, value)
};
let now = 10_000;
const opts = { storage, now: () => now, key: 'test:chase' };
const clock = createClock(opts);
assert.equal(clock.at().phase, 'chase');
now += 2_999;
assert.equal(clock.at().phase, 'chase');
now++;
assert.equal(clock.at().phase, 'dig', 'Miner starts digging after three seconds');
now += 400;
assert.equal(clock.at().phase, 'tunnel');
now += 640;
assert.equal(clock.at().phase, 'emerge');
now += 430;
assert.equal(clock.at().phase, 'turn');
assert.equal(clock.at().direction, -1);
assert.equal(clock.at().reversals, 1);
now += 140;
assert.equal(clock.at().phase, 'chase');
assert.equal(clock.at().direction, -1);

// Route changes / remounts must not restart the timeline.
const nextView = createClock(opts);
assert.equal(nextView.startedAt, clock.startedAt);
assert.equal(nextView.at().cycle, 1);
const before = nextView.at().elapsedMs;
now += 60_000; // No frames while scrolled away, hidden, or on another page.
assert.equal(nextView.at().elapsedMs, before + 60_000);
assert.equal(createClock(opts).at().elapsedMs, before + 60_000);

const troops = ['archer', 'giant', 'wizard', 'pekka', 'dragon', 'goblin'];
const first = nextView.shuffleTroops(troops);
assert.deepEqual(first, createClock(opts).shuffleTroops(troops));
assert.deepEqual([...first].sort(), [...troops].sort());
const nextWave = nextView.shuffleTroops(
  troops, nextView.startedAt + (nextView.at().cycle + 1) * nextView.at().cycleDuration
);
assert.notEqual(first.at(-1), nextWave[0]);

let rendered, savedCallback, cancelled = false;
const stop = nextView.run(
  s => { rendered = s; },
  callback => { savedCallback = callback; return 7; },
  id => { assert.equal(id, 7); cancelled = true; }
);
assert.equal(rendered.elapsedMs, nextView.at().elapsedMs);
now += 10_000;
savedCallback();
assert.equal(rendered.elapsedMs, nextView.at().elapsedMs);
stop();
assert.equal(cancelled, true);
assert.equal(clock.restart().elapsedMs, 0);
console.log('Troop chase timeline continuity and phase tests passed.');
