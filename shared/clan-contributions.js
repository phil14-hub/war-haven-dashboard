(function(root, factory) {
  const value = factory(root.WarTracker);
  if (typeof module === 'object' && module.exports) module.exports = value;
  else root.ClanContributions = value;
})(typeof globalThis === 'object' ? globalThis : this, function(T) {
  'use strict';
  const count = value => Number.isSafeInteger(value) && value >= 0;
  const time = value => Number.isFinite(Date.parse(value)) ? Date.parse(value) : 0;

  function history(data) {
    const asOf = time(data.lastSuccessfulSync), events = new Map(), departures = [];
    if (!asOf) return [];
    const event = at => {
      const key = time(at);
      if (!key || key > asOf) return null;
      if (!events.has(key)) events.set(key, {at: new Date(key).toISOString(), donated: 0, received: 0, capital: 0});
      return events.get(key);
    };
    const histories = T.mergeMemberHistory({}, data.memberHistory || {});
    let modernSince = Infinity;
    for (const h of Object.values(histories)) for (const stint of [...h.pastStints || [], h]) {
      if (time(stint.leftAt)) departures.push(time(stint.leftAt));
      const donations = T.donationEvidence(stint, asOf);
      if (time(donations.since) && time(donations.since) <= asOf) {
        const point = event(donations.since);
        if (point) point.donationKnown = true;
      }
      for (const interval of donations.intervals) {
        const point = event(interval.end);
        if (point) {
          point.donated += interval.count;
          (point.donationWindows ||= []).push(interval);
          point.donationKnown = true;
        }
      }
      for (const sample of stint.donationCounterSamples || []) if (count(sample.donationsReceived)) {
        const point = event(sample.at);
        if (point) point.receivedKnown = true;
      }
      for (const sample of stint.donationCounterSamples || []) if (time(sample.at) && count(sample.donations)) modernSince = Math.min(modernSince, time(sample.at));
      for (const interval of T.donationEvidence({...stint, donationIntervals: stint.receivedIntervals || []}, asOf).intervals) {
        const point = event(interval.end);
        if (point) { point.received += interval.count; point.receivedKnown = true; }
      }
      const capital = T.capitalEvidence(stint, asOf);
      for (const sample of capital.series) {
        const point = event(sample.at);
        if (point) { point.capital += sample.delta; point.capitalKnown = true; }
      }
    }
    // Keep the original roster readings intact. They remain available separately
    // and provide a starting baseline for archives predating counter samples.
    const raw = new Map();
    for (const sample of data.clanHistory || []) {
      const point = event(sample.at);
      if (point && count(sample.seasonDonations)) raw.set(time(sample.at), sample);
    }
    const roster = data.roster || [], known = roster.filter(p => count(p.donations));
    if (known.length) raw.set(asOf, {at: data.lastSuccessfulSync, members: roster.length,
      seasonDonations: known.reduce((total, p) => total + p.donations, 0)});
    const readings = [...raw.values()].sort((a, b) => time(a.at) - time(b.at));
    const resets = new Map((data.donationSeasonResets || []).filter(v => time(v.at) && time(v.at) <= asOf).map(v => [time(v.at), v]));
    // Older archives contain aggregate readings and membership evidence. A fall
    // explained by a departure is never a season reset. Preserve their existing
    // reset boundaries only when no saved membership loss explains the fall.
    for (let i = 1; i < readings.length; i++) {
      const before = readings[i - 1], after = readings[i], start = time(before.at), end = time(after.at);
      const hasModernCounters = end >= modernSince;
      if (!hasModernCounters && after.seasonDonations < before.seasonDonations && after.members >= before.members &&
          !departures.some(at => start < at && at <= end)) resets.set(end, {at: after.at, legacy: true});
    }
    for (const reset of resets.values()) event(reset.at);
    event(data.lastSuccessfulSync);
    let donated = 0, received = 0, capital = 0, season = null, seasonStartedAt = null;
    let donationKnown = false, receivedKnown = false, capitalKnown = false;
    const baseline = readings[0], baselineAt = time(baseline?.at), points = [];
    for (const [at, e] of [...events].sort(([a], [b]) => a - b)) {
      donated += e.donated;
      received += e.received;
      capital += e.capital;
      donationKnown ||= e.donationKnown;
      receivedKnown ||= e.receivedKnown;
      capitalKnown ||= e.capitalKnown;
      const reset = resets.get(at);
      if (reset || at === baselineAt) {
        season = reset && !reset.legacy ? e.donated : raw.get(at)?.seasonDonations ?? e.donated;
        seasonStartedAt = e.at;
      } else if (season !== null) season += (e.donationWindows || []).filter(v => time(v.start) >= time(seasonStartedAt)).reduce((total, v) => total + v.count, 0);
      // Legacy intervals may have gaps. A saved current-roster reading remains
      // a valid floor, without subtracting departed players or inventing deltas.
      if (season !== null && at < modernSince && raw.has(at)) season = Math.max(season, raw.get(at).seasonDonations);
      points.push({at: e.at, seasonDonations: season, observedDonations: donationKnown ? donated : null,
        observedReceived: receivedKnown ? received : null, capitalDonations: capitalKnown ? capital : null,
        seasonStartedAt, seasonReset: Boolean(reset), legacyReset: Boolean(reset?.legacy)});
    }
    return points;
  }

  function growth(data) {
    const contributions = history(data), result = new Map(), raw = [...data.clanHistory || []].sort((a, b) => time(a.at) - time(b.at));
    let index = 0, context = {};
    for (const point of contributions) {
      while (index < raw.length && time(raw[index].at) <= time(point.at)) context = raw[index++];
      result.set(time(point.at), {...context, ...point, rosterSeasonDonations: context.seasonDonations ?? null});
    }
    return [...result.values()];
  }
  function summary(data) {
    return history(data).at(-1) || {};
  }
  return {history, growth, summary};
});
