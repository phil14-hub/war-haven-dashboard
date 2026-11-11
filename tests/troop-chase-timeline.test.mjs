import assert from 'node:assert/strict';
import { createClock, minerAt, MINER_TIMING } from '../shared/troop-chase-timeline.mjs';

const state = new Map();
const storage = {
  getItem: key => state.get(key) ?? null,
  setItem: (key, value) => state.set(key, value)
};
let now = 10_000;
const options = { laneWidth: 390, storage, now: () => now };
const clock = createClock(options);
assert.equal(clock.elapsedAt(), 0);
now += 60_000;
const remounted = createClock({ ...options, laneWidth: 1200 });
assert.equal(remounted.elapsedAt(), 60_000);
assert.equal(remounted.laneWidth, 390, 'Both views use the original lane for scheduling');
assert.equal(remounted.elapsedAt(now + 86_400_000), 86_460_000);
assert.equal(createClock({ ...options, storage: null }).elapsedAt(), 0);

assert.equal(MINER_TIMING.chase, 3000);
for (const [time, phase, turned, phaseElapsed] of [
  [-1, 'approach', false, 0], [0, 'chase', false, 0], [2999, 'chase', false, 2999],
  [3000, 'dig', false, 0], [3399, 'dig', false, 399], [3400, 'tunnel', false, 0],
  [4039, 'tunnel', false, 639], [4040, 'emerge', false, 0], [4159, 'emerge', false, 119],
  [4160, 'emerge', true, 120], [4469, 'emerge', true, 429], [4470, 'done', true, 0]
]) {
  assert.deepEqual(minerAt(time), { phase, phaseElapsed, turned });
}

for (const names of [[], ['miner'], ['dragon', 'miner'], ['dragon', 'yeti', 'miner'],
  ['dragon', 'yeti', 'pekka', 'giant', 'hog-rider', 'miner']]) {
  let previous;
  const orders = new Set();
  for (let wave = 0; wave < 512; wave++) {
    const order = clock.shuffleTroops(names, wave);
    assert.deepEqual(order, remounted.shuffleTroops(names, wave));
    assert.deepEqual([...order].sort(), [...names].sort());
    if (previous && names.length > 1) assert.notEqual(previous.at(-1), order[0]);
    previous = order;
    orders.add(order.join(','));
  }
  if (names.length === 6) assert.ok(orders.size > 50);
}
console.log('Troop chase clock, Miner phases and randomized rounds passed.');
