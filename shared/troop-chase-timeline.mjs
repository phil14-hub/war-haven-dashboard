/** The shared clock and choreography for War Haven's dashboard chase. */
const STORAGE_KEY = 'warhaven:troop-chase:timeline:v2';

export const MINER_TIMING = Object.freeze({
  chase: 3000, dig: 400, tunnel: 640, emerge: 430, turn: 120
});

function sessionStore() {
  try {
    return globalThis.sessionStorage;
  } catch {
    return null;
  }
}

function readOrigin(storage, key, timestamp) {
  try {
    const origin = JSON.parse(storage?.getItem(key) ?? 'null');
    if (origin && Number.isFinite(origin.startedAt) && origin.startedAt <= timestamp &&
        Number.isFinite(origin.laneWidth) && origin.laneWidth > 0 &&
        Number.isInteger(origin.seed) && origin.seed >= 0 && origin.seed <= 0xffffffff) {
      return origin;
    }
  } catch {
    // The document can still keep its own clock when session storage is unavailable.
  }
  return null;
}

function hash32(value) {
  let x = value >>> 0;
  x = Math.imul(x ^ (x >>> 16), 0x7feb352d);
  x = Math.imul(x ^ (x >>> 15), 0x846ca68b);
  return (x ^ (x >>> 16)) >>> 0;
}

export function createClock({ laneWidth, now = Date.now, storage = sessionStore(), key = STORAGE_KEY } = {}) {
  const timestamp = now();
  let origin = readOrigin(storage, key, timestamp);
  if (!origin) {
    origin = { startedAt: timestamp, laneWidth, seed: (Math.random() * 0x100000000) >>> 0 };
    try {
      storage?.setItem(key, JSON.stringify(origin));
    } catch {
      // Keep using this clock for the lifetime of the document.
    }
  }

  function shuffle(names, wave) {
    const order = [...names];
    let random = hash32(origin.seed ^ hash32(wave + 1));
    for (let i = order.length - 1; i > 0; i--) {
      random = hash32(random + 0x9e3779b9);
      const j = random % (i + 1);
      [order[i], order[j]] = [order[j], order[i]];
    }
    return order;
  }

  return {
    laneWidth: origin.laneWidth,
    elapsedAt(time = now()) {
      return Math.max(0, time - origin.startedAt);
    },
    shuffleTroops(names, wave) {
      // With two troops the initial random order must repeat to avoid duplicate neighbors.
      if (names.length <= 2) return shuffle(names, 0);
      const order = shuffle(names, wave);
      // This adjustment never changes the last troop, so the prior raw order suffices.
      if (wave > 0 && order[0] === shuffle(names, wave - 1).at(-1)) {
        [order[0], order[1]] = [order[1], order[0]];
      }
      return order;
    }
  };
}

export function minerAt(chaseElapsed) {
  const { chase, dig, tunnel, emerge, turn } = MINER_TIMING;
  if (chaseElapsed < 0) return { phase: 'approach', phaseElapsed: 0, turned: false };
  if (chaseElapsed < chase) return { phase: 'chase', phaseElapsed: chaseElapsed, turned: false };
  let phaseElapsed = chaseElapsed - chase;
  if (phaseElapsed < dig) return { phase: 'dig', phaseElapsed, turned: false };
  phaseElapsed -= dig;
  if (phaseElapsed < tunnel) return { phase: 'tunnel', phaseElapsed, turned: false };
  phaseElapsed -= tunnel;
  if (phaseElapsed < emerge) return { phase: 'emerge', phaseElapsed, turned: phaseElapsed >= turn };
  return { phase: 'done', phaseElapsed: 0, turned: true };
}
