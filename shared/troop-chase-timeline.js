/**
 * War Haven chase timeline shared by leadership and individual dashboards.
 * Elapsed time comes from a persisted absolute timestamp, not rendered frames:
 * scrolling, route changes, or throttled background tabs do not pause it.
 * The portal's existing chase renderer must call clock.at() on every render.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.WarHavenTroopChaseTimeline = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const DEFAULT_DURATIONS = Object.freeze({
    chase: 3000, dig: 400, tunnel: 640, emerge: 430, turn: 140
  });
  const PHASE_ORDER = Object.freeze(['chase', 'dig', 'tunnel', 'emerge', 'turn']);
  const DEFAULT_KEY = 'warhaven:troop-chase:timeline:v1';
  const TURN_TWEEN_MS = 720;

  function safeStorage() {
    try { return typeof sessionStorage !== 'undefined' ? sessionStorage : null; }
    catch { return null; }
  }
  function positive(n) { return Number.isFinite(n) && n > 0; }
  function normalizeDurations(source) {
    const values = { ...DEFAULT_DURATIONS, ...(source || {}) };
    for (const name of PHASE_ORDER) {
      if (!positive(values[name])) throw new TypeError('Invalid chase duration: ' + name);
    }
    return values;
  }
  function storedOrigin(storage, key, now) {
    try {
      const raw = storage?.getItem(key);
      if (!raw) return null;
      const record = JSON.parse(raw);
      if (record?.version !== 1 || !Number.isFinite(record.startedAt) ||
          record.startedAt > now + 1000 || !Number.isInteger(record.seed)) return null;
      return record;
    } catch { return null; }
  }
  function storeOrigin(storage, key, record) {
    try { storage?.setItem(key, JSON.stringify(record)); }
    catch { /* Browsers that block storage can still run the chase. */ }
  }
  function hash32(value) {
    let x = value >>> 0;
    x ^= x >>> 16; x = Math.imul(x, 0x7feb352d);
    x ^= x >>> 15; x = Math.imul(x, 0x846ca68b);
    return (x ^ (x >>> 16)) >>> 0;
  }

  function createClock(options = {}) {
    const now = options.now || Date.now;
    const storage = options.storage === undefined ? safeStorage() : options.storage;
    const key = options.key || DEFAULT_KEY;
    const durations = normalizeDurations(options.durations);
    const cycleDuration = PHASE_ORDER.reduce((n, phase) => n + durations[phase], 0);
    const beforeTurn = cycleDuration - durations.turn;
    const initialNow = now();
    if (!Number.isFinite(initialNow)) throw new TypeError('Invalid chase clock');
    let origin = storedOrigin(storage, key, initialNow);
    if (!origin) {
      origin = {
        version: 1,
        startedAt: initialNow,
        seed: (Math.random() * 0x100000000) >>> 0
      };
      storeOrigin(storage, key, origin);
    }

    function at(timestamp = now()) {
      if (!Number.isFinite(timestamp)) throw new TypeError('Invalid timestamp');
      const elapsedMs = Math.max(0, timestamp - origin.startedAt);
      const cycle = Math.floor(elapsedMs / cycleDuration);
      const cycleElapsedMs = elapsedMs - cycle * cycleDuration;
      let cutoff = 0, phase = 'chase', phaseElapsedMs = 0;
      for (const name of PHASE_ORDER) {
        if (cycleElapsedMs < cutoff + durations[name]) {
          phase = name;
          phaseElapsedMs = cycleElapsedMs - cutoff;
          break;
        }
        cutoff += durations[name];
      }
      // Turn reverses the Barbarian and every pursuer in the same frame.
      const reversing = cycleElapsedMs >= beforeTurn;
      const reversals = cycle + (reversing ? 1 : 0);
      const lastTurnStarted = (cycle - (reversing ? 0 : 1)) * cycleDuration + beforeTurn;
      const turnElapsedMs = Math.max(0, elapsedMs - lastTurnStarted);
      return {
        elapsedMs, cycle, cycleDuration, phase, phaseElapsedMs,
        phaseDurationMs: durations[phase],
        phaseProgress: phaseElapsedMs / durations[phase],
        direction: reversals % 2 ? -1 : 1, reversals,
        turnProgress: Math.min(1, turnElapsedMs / TURN_TWEEN_MS)
      };
    }

    function shuffleTroops(names, timestamp = now()) {
      const troops = [...names];
      if (troops.length < 2) return troops;
      const cycle = at(timestamp).cycle;
      let random = hash32(origin.seed ^ hash32(cycle + 1));
      for (let i = troops.length - 1; i > 0; i--) {
        random = hash32(random + 0x9e3779b9);
        const j = random % (i + 1);
        [troops[i], troops[j]] = [troops[j], troops[i]];
      }
      // Prevent a repeated troop at the transition between two waves.
      if (cycle) {
        let previous = hash32(origin.seed ^ hash32(cycle));
        const prior = [...names];
        for (let i = prior.length - 1; i > 0; i--) {
          previous = hash32(previous + 0x9e3779b9);
          const j = previous % (i + 1);
          [prior[i], prior[j]] = [prior[j], prior[i]];
        }
        if (troops[0] === prior[prior.length - 1]) [troops[0], troops[1]] = [troops[1], troops[0]];
      }
      return troops;
    }

    function restart(timestamp = now()) {
      if (!Number.isFinite(timestamp)) throw new TypeError('Invalid timestamp');
      origin = { ...origin, startedAt: timestamp };
      storeOrigin(storage, key, origin);
      return at(timestamp);
    }

    function run(render, requestFrame = fn => requestAnimationFrame(fn), cancelFrame = id => cancelAnimationFrame(id)) {
      if (typeof render !== 'function') throw new TypeError('Chase render callback is required');
      let stopped = false, frameId;
      function tick() {
        if (stopped) return;
        render(at());
        frameId = requestFrame(tick);
      }
      tick();
      return () => { stopped = true; if (frameId !== undefined) cancelFrame(frameId); };
    }

    return {
      at, shuffleTroops, restart, run,
      get startedAt() { return origin.startedAt; },
      durations: { ...durations }
    };
  }

  return Object.freeze({ createClock, DEFAULT_DURATIONS, DEFAULT_KEY });
});
