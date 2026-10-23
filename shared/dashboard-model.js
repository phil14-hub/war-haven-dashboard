(function(root, factory) {
  const value = factory();
  if (typeof module === "object" && module.exports) module.exports = value;
  else root.WarTracker = value;
})(typeof globalThis === "object" ? globalThis : this, function() {
  "use strict";
  const tag = (v) => String(v || "").trim().toUpperCase().replace(/^(?!#)(.+)/, "#$1");
  const time = (v) => Number.isFinite(Date.parse(v)) ? Date.parse(v) : 0;
  const pair = (warId, playerTag) => `${warId}::${tag(playerTag)}`;
  const number = (v) => typeof v === "number" && Number.isFinite(v);
  const emptyEdits = () => ({ exceptions: {}, notes: {}, manualWars: {}, xpCheckpoints: {}, villageProgress: {}, lineupPlans: {}, lineupDrafts: {}, flagResolutions: {} });
  function mergeEdits(a = {}, b = {}) {
    const out = emptyEdits();
    for (const field of ["exceptions", "notes", "manualWars", "xpCheckpoints", "villageProgress", "lineupPlans", "lineupDrafts", "flagResolutions"]) {
      for (const source of [a[field] || {}, b[field] || {}]) for (const [key, value] of Object.entries(source)) {
        if (!out[field][key] || time(value.updatedAt) >= time(out[field][key].updatedAt)) out[field][key] = value;
      }
    }
    return normalizeLineups(out);
  }
  function normalizeLineups(edits) {
    edits.lineupPlans ||= {};edits.lineupDrafts ||= {};
    for (const [mode,plan] of Object.entries(edits.lineupPlans)) {
      if (!plan || plan.deleted || !Array.isArray(plan.tags)) continue;
      const allowed=mode==='CWL'?[15,30]:[5,10,15,20,25,30,40,50];
      const complete=allowed.includes(plan.tags.length)&&(plan.options?.size==='max'||Number(plan.options?.size)===plan.tags.length);
      if(!complete&&plan.committed!==true){
        if(!edits.lineupDrafts[mode]||time(plan.updatedAt)>time(edits.lineupDrafts[mode].updatedAt))edits.lineupDrafts[mode]={...plan,legacyDraft:true,baseCommitId:null};
        edits.lineupPlans[mode]={deleted:true,updatedAt:plan.updatedAt};
      }else if(complete){plan.options={...plan.options,size:String(plan.tags.length)};plan.committed=true;plan.commitId ||= plan.updatedAt||'legacy';}
    }
    return edits;
  }
  function validateLineupPlans(edits) {
    normalizeLineups(edits);
    for(const category of ['lineupPlans','lineupDrafts'])for (const [mode,plan] of Object.entries(edits[category]||{})) {
      if(!['Regular','CWL'].includes(mode)||!plan||typeof plan!=='object')throw Error('Invalid saved war lineup.');
      if(plan.deleted===true)continue;
      if(!Array.isArray(plan.tags)||plan.tags.length>50||new Set(plan.tags).size!==plan.tags.length||plan.tags.some(tag=>typeof tag!=='string'||!/^#[0289PYLQGRJCUV]+$/.test(tag)))throw Error('Invalid saved war lineup.');
      const o=plan.options;
      if(!o||o.mode!==mode||!['representative','strength'].includes(o.balance)||typeof o.includeUnknown!=='boolean'||!['max','5','10','15','20','25','30','40','50'].includes(String(o.size)))throw Error('Invalid saved lineup options.');
      if(category==='lineupPlans'&&(!(mode==='CWL'?[15,30]:[5,10,15,20,25,30,40,50]).includes(plan.tags.length)||Number(o.size)!==plan.tags.length))throw Error('A committed lineup must match a supported team size.');
    }
  }
  function mergeData(current, backup) {
    if (tag(current.clanTag) !== tag(backup.clanTag)) throw Error("This backup belongs to a different clan.");
    if (backup.schemaVersion !== 1) throw Error("Unsupported backup version.");
    validateLineupPlans(backup.edits || {});
    const restored = { ...current };
    const newer = time(backup.lastSuccessfulSync) > time(current.lastSuccessfulSync);
    if (newer) {
      for (const k of ["roster", "clanName", "clanProfile", "lastSuccessfulSync", "lastRaidSync", "keyInfo", "automaticUpdates", "sharedActions"]) if (backup[k] !== void 0) restored[k] = backup[k];
    }
    for (const field of ["wars", "raids"]) {
      const map = new Map((current[field] || []).map((v) => [v.id, v]));
      for (const value of backup[field] || []) {
        if (!value.id) continue;
        const old = map.get(value.id);
        if (!old || !old.final && value.final || old.final === value.final && time(value.observedAt) > time(old.observedAt)) map.set(value.id, value);
      }
      restored[field] = [...map.values()];
    }
    restored.honors = { ...current.honors || {} };
    for (const [key, value] of Object.entries(backup.honors || {})) {
      const old = restored.honors[key];
      if (!old || time(value.observedAt) < time(old.observedAt)) restored.honors[key] = value;
    }
    restored.leagueBadgeImages = { ...backup.leagueBadgeImages || {}, ...current.leagueBadgeImages || {} };
    restored.memberHistory = mergeMemberHistory(current.memberHistory, backup.memberHistory);
    restored.clanHistory = ClanProgress.merge(current.clanHistory || [], backup.clanHistory || [], false);
    restored.leagueHistory = Leadership.mergeHistory(current.leagueHistory || [], backup.leagueHistory || []);
    restored.leaguePointScale = current.leaguePointScale || backup.leaguePointScale || [];
    restored.memberProgressHistory = { ...current.memberProgressHistory || {} };
    for (const [key, records] of Object.entries(backup.memberProgressHistory || {})) restored.memberProgressHistory[key] = ClanProgress.merge(restored.memberProgressHistory[key] || [], records);
    restored.memberProgress = { ...current.memberProgress || {} };
    for (const [key, value] of Object.entries(backup.memberProgress || {})) if (!restored.memberProgress[key] || time(value.at) > time(restored.memberProgress[key].at)) restored.memberProgress[key] = value;
    if (!restored.progressionInfo) restored.progressionInfo = backup.progressionInfo;
    restored.profiles = { ...current.profiles || {} };
    for (const [k, p] of Object.entries(backup.profiles || {})) if (!restored.profiles[k] || time(p.profileCheckedAt) > time(restored.profiles[k].profileCheckedAt)) restored.profiles[k] = p;
    restored.activity = [...new Map([...backup.activity || [], ...current.activity || []].map((v) => [JSON.stringify(v), v])).values()].sort((a, b) => time(a.detectedAt) - time(b.detectedAt)).slice(-300);
    restored.leagueGroups = { ...backup.leagueGroups || {}, ...current.leagueGroups || {} };
    restored.leagueWarSummaries = { ...backup.leagueWarSummaries || {}, ...current.leagueWarSummaries || {} };
    const starts = [time(current.policyStart), time(backup.policyStart)].filter(Boolean);
    if (starts.length) restored.policyStart = new Date(Math.min(...starts)).toISOString();
    restored.trackingStarted = Boolean(current.trackingStarted || backup.trackingStarted);
    return restored;
  }
  function mergeMemberHistory(a = {}, b = {}) {
    const merged = { ...a }, latest = (x) => Math.max(time(x.lastSeen), time(x.leftAt));
    for (const [key, value] of Object.entries(b || {})) {
      if (!value || typeof value !== "object") continue;
      const old = merged[key];
      if (!old) {
        merged[key] = value;
        continue;
      }
      const stints = /* @__PURE__ */ new Map();
      for (const record of [...old.pastStints || [], old, ...value.pastStints || [], value]) {
        if (!record || !time(record.since)) continue;
        const id2 = new Date(time(record.since)).toISOString(), prior = stints.get(id2), current2 = { ...!prior || latest(record) > latest(prior) ? record : prior };
        delete current2.pastStints;
        if (prior) for (const field of ["donationIntervals", "capitalSamples"]) current2[field] = [...new Map([...prior[field] || [], ...record[field] || []].map((v) => [JSON.stringify(v), v])).values()].sort((x, y) => time(x.at || x.end) - time(y.at || y.end));
        stints.set(id2, current2);
      }
      const current = latest(value) > latest(old) ? value : old, id = time(current.since) ? new Date(time(current.since)).toISOString() : "";
      merged[key] = { ...stints.get(id) || current, pastStints: [...stints].filter(([k]) => k !== id).map(([, v]) => v).sort((x, y) => time(x.since) - time(y.since)) };
    }
    return merged;
  }
  const count = (v) => Number.isSafeInteger(v) && v >= 0;
  function donationEvidence(history = {}, asOf = Date.now()) {
    const since = time(history.since), end = Math.min(asOf, time(history.leftAt) || asOf), intervals = [];
    let previous = since, total = 0;
    for (const v of [...history.donationIntervals || []].sort((a, b) => time(a.end) - time(b.end) || a.count - b.count)) {
      if (!count(v.count) || !v.count || !time(v.start) || time(v.start) < previous || time(v.end) <= time(v.start) || time(v.end) > end) continue;
      total += v.count;
      previous = time(v.end);
      intervals.push({ ...v, total });
    }
    return { total, intervals, since: history.donationTrackingSince || intervals[0]?.start || history.since || null };
  }
  function capitalEvidence(history = {}, asOf = Date.now()) {
    const samples = /* @__PURE__ */ new Map(), since = time(history.since), end = Math.min(asOf, time(history.leftAt) || asOf);
    for (const v of history.capitalSamples || []) {
      const at = time(v.at);
      if (!at || at < since || at > end) continue;
      const old = samples.get(at), total2 = count(v.total) ? v.total : null;
      samples.set(at, { at: v.at, total: old ? old.total === null || total2 === null ? null : Math.max(old.total, total2) : total2 });
    }
    let high = null, previous = null, total = 0, baselineAt = null, lastAt = null;
    const series = [], intervals = [];
    for (const sample of [...samples.values()].sort((a, b) => time(a.at) - time(b.at))) {
      if (sample.total === null) {
        previous = null;
        continue;
      }
      baselineAt = baselineAt || sample.at;
      lastAt = sample.at;
      const delta = previous && high !== null ? Math.max(0, sample.total - high) : 0;
      if (delta) {
        total += delta;
        intervals.push({ start: previous, end: sample.at, count: delta, total });
      }
      series.push({ at: sample.at, total, delta, lifetime: sample.total });
      high = Math.max(high ?? sample.total, sample.total);
      previous = sample.at;
    }
    return { total: baselineAt ? total : null, baselineAt, lastAt, series, intervals };
  }
  function contributionsFor(data, playerTag, asOf = time(data.lastSuccessfulSync) || Date.now()) {
    const key = tag(playerTag), history = data.memberHistory?.[key] || {}, capital = capitalEvidence(history, asOf), donations = donationEvidence(history, asOf);
    const raids = [...new Map((data.raids || []).map((r) => [r.id || r.startTime, r])).values()].flatMap((r) => {
      const m = (r.members || []).find((v) => tag(v.tag) === key);
      if (!m) return [];
      const max = count(m.attackLimit) && count(m.bonusAttackLimit) ? m.attackLimit + m.bonusAttackLimit : null;
      return [{ id: r.id, start: r.startTime, end: r.endTime, state: r.state, loot: count(m.capitalResourcesLooted) ? m.capitalResourcesLooted : null, used: count(m.attacks) ? m.attacks : null, allowed: max && count(m.attacks) && m.attacks <= max ? max : null }];
    }).sort((a, b) => time(a.start) - time(b.start));
    const completed = raids.filter((r) => r.state === "ended"), known = completed.filter((r) => r.used !== null && r.allowed !== null), used = known.reduce((s, r) => s + r.used, 0), allowed = known.reduce((s, r) => s + r.allowed, 0), loot = completed.reduce((s, r) => s + (r.loot || 0), 0);
    const allCapital = [history, ...history.pastStints || []].map((h) => capitalEvidence(h, asOf)).filter((c) => c.total !== null), lootKnown = known.filter((r) => r.loot !== null), lootAttacks = lootKnown.reduce((s, r) => s + r.used, 0);
    return { since: history.since || null, days: time(history.since) && time(history.lastSeen) >= time(history.since) ? Math.max(0, Math.floor((Math.min(asOf, time(history.lastSeen)) - time(history.since)) / 864e5)) : null, capital, donations, allCapital: allCapital.length ? allCapital.reduce((s, c) => s + c.total, 0) : null, raids, raidCount: completed.length, raidLoot: completed.some((r) => r.loot !== null) ? loot : null, raidUsed: used, raidAllowed: allowed, raidUse: allowed ? used / allowed : null, goldPerAttack: lootAttacks ? lootKnown.reduce((s, r) => s + r.loot, 0) / lootAttacks : null };
  }
  function warsFor(data, edits = {}) {
    const map = new Map((data.wars || []).map((w) => [w.id, w]));
    for (const w of Object.values(edits.manualWars || {})) if (!w.deleted) map.set(w.id, w);
    return [...map.values()].sort((a, b) => time(a.endTime) - time(b.endTime) || String(a.id).localeCompare(String(b.id)));
  }
  const warNow = () => typeof WarHavenUI !== "undefined" && WarHavenUI.now ? WarHavenUI.now() : Date.now();
  function warTiming(w, asOf = warNow()) {
    const start = time(w.startTime), end = time(w.endTime);
    if ((w.state === "warEnded" || w.final === true) && !(end > asOf)) return { phase: "ended", label: "War ended", timeLabel: "Awaiting final refresh", target: null };
    if (end > 0 && end <= asOf) return { phase: "awaiting-update", label: "Awaiting war update", timeLabel: "Saved timer elapsed", target: null };
    if (start > asOf || w.state === "preparation" && !start) return { phase: "preparation", label: "Preparation day", timeLabel: "War starts in", target: start ? new Date(start).toISOString() : null };
    if (w.state === "inWar" || end > asOf && (w.state === "warEnded" || w.final === true) || w.state === "preparation" && start > 0 && start <= asOf) return { phase: "in-progress", label: "In progress", timeLabel: "War ends in", target: end ? new Date(end).toISOString() : null };
    return { phase: "unknown", label: "Status unavailable", timeLabel: "Refresh to check war timing", target: null };
  }
  function countdown(target, asOf = warNow(), seconds = true) {
    const stamp = typeof target === "number" ? target : time(target);
    if (!stamp) return "—";
    const total = Math.max(0, Math.ceil((stamp - asOf) / 1e3));
    if (!seconds) {
      const minutes2 = Math.ceil(total / 60), hours2 = Math.floor(minutes2 / 60);
      return hours2 + "h " + String(minutes2 % 60).padStart(2, "0") + "m";
    }
    const hours = Math.floor(total / 3600), minutes = Math.floor(total % 3600 / 60), remaining = total % 60;
    return String(hours).padStart(2, "0") + ":" + String(minutes).padStart(2, "0") + ":" + String(remaining).padStart(2, "0");
  }
  function isClosed(w, asOf = warNow()) {
    return !(time(w.endTime) > asOf) && (w.state === "warEnded" || w.final === true || time(w.endTime) > 0 && time(w.endTime) <= asOf);
  }
  function isExcused(edits, w, playerTag) {
    return Boolean(edits.exceptions?.[pair(w.id, playerTag)]?.value);
  }
  function playersFor(data, edits = {}, asOf = Date.now()) {
    const wars = warsFor(data, edits);
    const roster = new Map((data.roster || []).map((p) => [tag(p.tag), { ...p, tag: tag(p.tag), inClan: true }]));
    for (const w of wars) for (const p of w.participants || []) if (!roster.has(tag(p.tag))) roster.set(tag(p.tag), { ...p, tag: tag(p.tag), inClan: false });
    for (const r of [...data.raids || []].sort((a, b) => time(b.startTime) - time(a.startTime))) for (const p of r.members || []) if (!roster.has(tag(p.tag))) roster.set(tag(p.tag), { ...p, name: p.name || p.tag, tag: tag(p.tag), inClan: false });
    for (const [key, h] of Object.entries(data.memberHistory || {})) if (!roster.has(tag(key))) roster.set(tag(key), { tag: tag(key), name: h.name || key, inClan: false });
    const manualStarts = Object.values(edits.manualWars || {}).filter((w) => w.kind === "Regular").map((w) => time(w.endTime)).filter(Boolean);
    const policyStart = Math.min(time(data.policyStart) || asOf, ...manualStarts);
    const closed = wars.filter((w) => w.kind === "Regular" && isClosed(w, asOf) && time(w.endTime) >= policyStart);
    const current = wars.filter((w) => !isClosed(w, asOf) && w.kind === "Regular").at(-1);
    const rows = [];
    for (const p of roster.values()) {
      let streak = 0, highest = 0, kick = false, possibleKick = false, missedBefore = false, returnedAfterMiss = false, uncertain = false, lastMiss = -1, used = 0, allowed = 0, played = 0, missedOne = 0, misses = 0;
      const history = [], gaps = [];
      closed.forEach((w, index) => {
        const member = (w.participants || []).find((m) => tag(m.tag) === p.tag);
        if (!member) {
          if (!w.rosterComplete) {
            uncertain = true;
            gaps.push(w.id);
            missedBefore = false;
            returnedAfterMiss = false;
          }
          return;
        }
        const excused = isExcused(edits, w, p.tag), reviewedThrough = time(edits.flagResolutions?.[p.tag]?.through), reviewed = reviewedThrough && time(w.endTime) <= reviewedThrough;
        const complete = w.final === true && w.rosterComplete === true && number(member.attacksUsed) && member.attacksUsed >= 0 && member.attacksUsed <= 2 && Number.isInteger(member.attacksUsed);
        history.push({ war: w, player: member, excused, complete });
        if (reviewed) {
          if (complete) {
            played++;
            if (!excused) {
              used += member.attacksUsed;
              allowed += 2;
            }
          }
          return;
        }
        if (!complete) {
          if (!excused) {
            // Unknown or provisional results cannot connect a repeat-miss pattern.
            missedBefore = false;
            returnedAfterMiss = false;
          }
          if (number(member.attacksUsed) && member.attacksUsed > 0 && !excused) {
            streak = 0;
            uncertain = false;
          } else if (!excused) {
            uncertain = true;
            gaps.push(w.id);
          }
          return;
        }
        played++;
        if (excused) return;
        used += member.attacksUsed;
        allowed += 2;
        if (member.attacksUsed > 0) {
          if (missedBefore) returnedAfterMiss = true;
          streak = 0;
          uncertain = false;
          if (member.attacksUsed === 1) missedOne++;
        } else {
          if (missedBefore && returnedAfterMiss) possibleKick = true;
          missedBefore = true;
          returnedAfterMiss = false;
          streak++;
          misses++;
          lastMiss = index;
          if (!uncertain) {
            highest = Math.max(highest, streak);
            if (streak >= 2) kick = true;
          }
        }
      });
      // Keep the repeat warning until leadership reviews it; a later attack only
      // resets the consecutive-miss streak. A confirmed kick flag takes priority.
      possibleKick = possibleKick && !kick;
      const bench = !kick && lastMiss >= 0 && lastMiss === closed.length - 1;
      const live = (current?.participants || []).find((m) => tag(m.tag) === p.tag);
      let status = !p.inClan ? "Departed" : kick ? "Kick" : possibleKick ? "Possible kick" : bench ? "Bench" : uncertain ? "Review" : p.warPreference === "out" ? "Opted out" : "Eligible";
      const reason = status === "Kick" ? "Two consecutive confirmed 0/2 appearances." : status === "Possible kick" ? "Missed both attacks, participated, then missed both again. Review for a possible kick." : status === "Review" ? "A final result is missing. Fill the gap before deciding." : status === "Bench" ? "Sit out the next regular war." : status === "Opted out" ? "Current war preference is out." : status === "Departed" ? "Not in the latest saved clan roster." : streak ? `${streak} missed-both appearance${streak === 1 ? "" : "s"}. Bench served.` : "No attendance penalty.";
      rows.push({ ...p, status, reason, streak, highest, kick, possibleKick, uncertain, bench, used, allowed, played, missedOne, misses, rate: allowed ? used / allowed : null, history, gaps, live: live || null, benchViolation: Boolean(bench && live), notes: edits.notes?.[p.tag]?.text || "", cwlMissed: wars.filter((w) => w.kind === "CWL" && w.final && w.rosterComplete && !isExcused(edits, w, p.tag) && (w.participants || []).some((m) => tag(m.tag) === p.tag && m.attacksUsed === 0)).length });
    }
    const priority = { Kick: 0, "Possible kick": 1, Review: 2, Bench: 3, Eligible: 4, "Opted out": 5, Departed: 6 };
    return rows.sort((a, b) => priority[a.status] - priority[b.status] || a.name.localeCompare(b.name));
  }
  function csv(rows) {
    const fields = ["Player", "Tag", "Town Hall", "Status", "0/2 streak", "Regular wars", "Attacks used", "Attacks allowed", "Attack use %", "Missed single attacks", "CWL missed", "Captured attack stars", "Average attack stars", "Triple rate %", "Donations this season", "Donations received", "Lifetime Capital contributions", "Latest raid loot", "Capital donated to this clan (current stint)", "Capital donation baseline", "Troop donations observed in current stint", "War preference", "Estimated chance of at least one regular-war attack %", "Confirmed appearances for estimate", "Appearances with at least one attack", "Notes"];
    const quote = (v) => {
      let s = String(v ?? "");
      if (/^[\s\u0000-\u001f]*[=+\-@]/.test(s)) s = "'" + s;
      return '"' + s.replace(/"/g, '""') + '"';
    };
    return [fields, ...rows.map((p) => [p.name, p.tag, p.townHallLevel || "", p.status, p.streak, p.played, p.used, p.allowed, p.rate === null ? "" : (p.rate * 100).toFixed(1), p.missedOne, p.cwlMissed, p.performance?.stars, p.performance?.averageStars?.toFixed(2), p.performance?.tripleRate === null ? "" : p.performance?.tripleRate === void 0 ? "" : (p.performance.tripleRate * 100).toFixed(1), p.donations, p.donationsReceived, p.capitalContributions, p.raidLoot, p.contributions?.capital.total, p.contributions?.capital.baselineAt, p.contributions?.donations.total, ["in", "out"].includes(p.warPreference) ? p.warPreference : "unknown", p.attackLikelihood?.probability == null ? "" : Math.round(100 * p.attackLikelihood.probability), p.attackLikelihood?.appearances, p.attackLikelihood?.attacked, p.notes])].map((r) => r.map(quote).join(",")).join("\r\n");
  }
  function attackLikelihoodFor(data, edits = {}, asOf = Date.now()) {
    const wars = warsFor(data, edits), players = new Set((data.roster || []).map((p) => tag(p.tag)));
    for (const w of wars) for (const p of w.participants || []) players.add(tag(p.tag));
    const estimates = {};
    for (const player of players) {
      const entry = data.memberHistory?.[player], since = time(entry?.since), first = time(entry?.firstEverObserved);
      const cutoff = first && since > first ? since : 0;
      const appearances = wars.filter((w) => {
        const end = time(w.endTime), p = (w.participants || []).find((m) => tag(m.tag) === player);
        return w.kind === "Regular" && w.final === true && w.rosterComplete === true && end > cutoff && end <= asOf && isClosed(w, asOf) && (w.attacksPerMember === void 0 || w.attacksPerMember === 2) && !isExcused(edits, w, player) && p && Number.isInteger(p.attacksUsed) && p.attacksUsed >= 0 && p.attacksUsed <= 2;
      }).slice(-10);
      const count2 = appearances.length, attacked = appearances.filter((w) => w.participants.find((p) => tag(p.tag) === player).attacksUsed > 0).length;
      estimates[player] = {
        probability: count2 ? (attacked + 1) / (count2 + 2) : null,
        appearances: count2,
        attacked,
        observedRate: count2 ? attacked / count2 : null,
        limited: count2 < 5,
        lastWarAt: appearances.at(-1)?.endTime || null,
        old: count2 ? asOf - time(appearances.at(-1).endTime) > 30 * 864e5 : false
      };
    }
    return estimates;
  }
  function validAttacks(p) {
    const seen = /* @__PURE__ */ new Set();
    return (p.attacks || []).filter((a, i) => {
      if (!a || typeof a !== "object") return false;
      const key = a.order ?? "i:" + i;
      if (!["number", "string"].includes(typeof key)) return false;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  function mergeManual(existing, next) {
    if (!existing) return next;
    const old = new Map((existing.participants || []).map((p) => [tag(p.tag), p]));
    const participants = next.participants.map((p) => {
      const before = old.get(tag(p.tag));
      if (!before) return p;
      if (before.attacksUsed === p.attacksUsed) return { ...before, ...p };
      const changed = { ...before, ...p };
      delete changed.attacks;
      delete changed.stars;
      delete changed.starsEarned;
      delete changed.destructionPercentage;
      return changed;
    });
    return { ...existing, ...next, opponent: { ...existing.opponent, ...next.opponent }, participants };
  }
  function performanceFor(data, edits = {}) {
    const stats = {};
    for (const w of warsFor(data, edits)) {
      if (!w.final || !w.rosterComplete || !["Regular", "CWL"].includes(w.kind)) continue;
      for (const p of w.participants || []) {
        const k = tag(p.tag), s = stats[k] || (stats[k] = { tag: k, stars: 0, knownAttacks: 0, triples: 0, destruction: 0, destructionCount: 0, used: 0, regularStars: 0, cwlStars: 0 });
        s.used += Number.isInteger(p.attacksUsed) && p.attacksUsed >= 0 && p.attacksUsed <= (w.kind === "CWL" ? 1 : 2) ? p.attacksUsed : 0;
        for (const attack of validAttacks(p)) {
          if (Number.isInteger(attack.stars) && attack.stars >= 0 && attack.stars <= 3) {
            s.stars += attack.stars;
            s.knownAttacks++;
            if (attack.stars === 3) s.triples++;
            if (w.kind === "Regular") s.regularStars += attack.stars;
            else s.cwlStars += attack.stars;
          }
          if (number(attack.destructionPercentage) && attack.destructionPercentage >= 0 && attack.destructionPercentage <= 100) {
            s.destruction += attack.destructionPercentage;
            s.destructionCount++;
          }
        }
      }
    }
    for (const s of Object.values(stats)) {
      s.averageStars = s.knownAttacks ? s.stars / s.knownAttacks : null;
      s.tripleRate = s.knownAttacks ? s.triples / s.knownAttacks : null;
      s.averageDestruction = s.destructionCount ? s.destruction / s.destructionCount : null;
    }
    return stats;
  }
  function trendsFor(data, edits = {}, options = {}) {
    const player = tag(options.player), kind = options.kind || "";
    let wars = warsFor(data, edits).filter((w) => w.final && w.rosterComplete && ["Regular", "CWL"].includes(w.kind) && time(w.endTime) && (!kind || w.kind === kind) && (!player || (w.participants || []).some((p) => tag(p.tag) === player)));
    const limit = Number(options.limit);
    if (Number.isFinite(limit) && limit > 0) wars = wars.slice(-Math.floor(limit));
    return wars.map((w) => {
      const members = (w.participants || []).filter((p) => !player || tag(p.tag) === player), max = number(w.attacksPerMember) ? w.attacksPerMember : w.kind === "CWL" ? 1 : 2;
      let used = 0, allowed = 0, stars = 0, knownAttacks = 0, triples = 0, destruction = 0, destructionCount = 0;
      for (const p of members) {
        if (!isExcused(edits, w, p.tag) && number(p.attacksUsed) && Number.isInteger(p.attacksUsed) && p.attacksUsed >= 0 && p.attacksUsed <= max) {
          used += p.attacksUsed;
          allowed += max;
        }
        for (const a of validAttacks(p)) {
          if (Number.isInteger(a.stars) && a.stars >= 0 && a.stars <= 3) {
            stars += a.stars;
            knownAttacks++;
            if (a.stars === 3) triples++;
          }
          if (number(a.destructionPercentage) && a.destructionPercentage >= 0 && a.destructionPercentage <= 100) {
            destruction += a.destructionPercentage;
            destructionCount++;
          }
        }
      }
      return { warId: w.id, kind: w.kind, endTime: w.endTime, opponent: w.opponent?.name || "Unknown opponent", used, allowed, attackUse: allowed ? used / allowed : null, stars, knownAttacks, triples, averageStars: knownAttacks ? stars / knownAttacks : null, tripleRate: knownAttacks ? triples / knownAttacks : null, averageDestruction: destructionCount ? destruction / destructionCount : null };
    });
  }
  function validateManual(w, clanTag) {
    if (!w || !["Regular", "CWL"].includes(w.kind) || !time(w.endTime) || time(w.endTime) > Date.now() || !w.opponent?.name || !Array.isArray(w.participants) || !w.participants.length) throw Error("Enter a completed war, end time, opponent, and selected players.");
    const seen = /* @__PURE__ */ new Set(), max = w.kind === "CWL" ? 1 : 2;
    for (const p of w.participants) {
      p.tag = tag(p.tag);
      if (!p.tag || seen.has(p.tag) || !number(p.attacksUsed) || !Number.isInteger(p.attacksUsed) || p.attacksUsed < 0 || p.attacksUsed > max) throw Error("Every selected player needs a unique tag and a confirmed attack count.");
      seen.add(p.tag);
    }
    w.id = `${w.kind.toLowerCase()}:${tag(clanTag)}:${new Date(w.endTime).toISOString()}`;
    w.endTime = new Date(w.endTime).toISOString();
    w.state = "warEnded";
    w.final = true;
    w.rosterComplete = true;
    w.source = "Manual";
    w.updatedAt = (/* @__PURE__ */ new Date()).toISOString();
    w.teamSize = w.participants.length;
    w.attacksPerMember = max;
    return w;
  }
  function rosterView(rows, options = {}) {
    const numeric = (v) => v !== "" && v != null && Number.isFinite(Number(v)) ? Number(v) : null;
    const min = numeric(options.minimum), max = numeric(options.maximum), q = String(options.search || "").toLowerCase(), status = options.status || "";
    const matchesStatus = (p) => status === "all" || (status === "Kick" ? ["Kick", "Possible kick"].includes(p.status) : status === "Bench" ? p.status === "Bench" || p.inClan && p.bench : status ? p.status === status : p.inClan);
    const shown = rows.filter((p) => matchesStatus(p) && `${p.name} ${p.tag}`.toLowerCase().includes(q) && (!options.townHall || String(p.townHallLevel) === String(options.townHall)) && (min === null || number(p.rate) && p.rate * 100 >= min) && (max === null || number(p.rate) && p.rate * 100 <= max));
    const keys = { attack: (p) => p.rate, likelihood: (p) => p.attackLikelihood?.probability, stars: (p) => p.performance?.averageStars, hall: (p) => p.townHallLevel, streak: (p) => p.uncertain ? null : p.streak };
    const [key, direction] = String(options.sort || "default").split("-");
    return shown.sort((a, b) => {
      if (key === "name") return a.name.localeCompare(b.name) || a.tag.localeCompare(b.tag);
      if (!keys[key]) return 0;
      const x = keys[key](a), y = keys[key](b);
      return number(x) && number(y) ? (direction === "asc" ? x - y : y - x) || a.name.localeCompare(b.name) : number(x) ? -1 : number(y) ? 1 : a.name.localeCompare(b.name);
    });
  }
  function missedBothRecency(data, edits, player, asOf = Date.now()) {
    const wars = warsFor(data, edits).filter((w) => ["Regular", "CWL"].includes(w.kind) && isClosed(w, asOf) && time(w.endTime) > 0), key = tag(player.tag);
    let event = null, recovery = 0;
    for (let index = 0; index < wars.length; index++) {
      const w = wars[index], p = w.participants?.find((m) => tag(m.tag) === key);
      if (isExcused(edits, w, key)) continue;
      if (!p) {
        if (!w.rosterComplete) recovery = 0;
        continue;
      }
      const max = w.attacksPerMember ?? (w.kind === "CWL" ? 1 : 2), known = w.final === true && w.rosterComplete === true && Number.isInteger(p.attacksUsed) && p.attacksUsed >= 0 && p.attacksUsed <= max;
      if (!known) {
        recovery = 0;
        continue;
      }
      if (w.kind === "Regular" && max === 2 && p.attacksUsed === 0) {
        event = { warId: w.id, at: w.endTime, index };
        recovery = 0;
      } else if (event) {
        if (p.attacksUsed > 0) {
          recovery++;
          if (recovery >= 5) {
            event = null;
            recovery = 0;
          }
        } else recovery = 0;
      }
    }
    return event && recovery < 5 ? { warId: event.warId, at: event.at, warsAgo: wars.length - event.index, recoveryStreak: recovery, recoveryTarget: 5 } : null;
  }
  function missedBothLastWar(data, edits, player, asOf = Date.now()) {
    if (!Number.isInteger(player.streak) || player.streak < 1 || player.uncertain) return false;
    const latest = warsFor(data, edits).filter((w) => w.kind === "Regular" && isClosed(w, asOf)).sort((a, b) => time(a.endTime) - time(b.endTime)).at(-1);
    if (!latest || !latest.final || !latest.rosterComplete || latest.attacksPerMember !== 2 || isExcused(edits, latest, player.tag)) return false;
    return latest.participants?.some((p) => tag(p.tag) === tag(player.tag) && p.attacksUsed === 0) || false;
  }
  return { rosterView, missedBothRecency, missedBothLastWar, tag, time, pair, number, emptyEdits, validateLineupPlans, mergeEdits, mergeData, mergeMemberHistory, warsFor, isClosed, warTiming, countdown, isExcused, playersFor, csv, validateManual, mergeManual, validAttacks, performanceFor, trendsFor, attackLikelihoodFor, capitalEvidence, donationEvidence, contributionsFor };
});
(function(root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./tracker.js"));
  else root.ClanPromotions = factory(root.WarTracker);
})(typeof globalThis === "object" ? globalThis : this, function(T) {
  "use strict";
  const DAY = 864e5;
  const weights = { tenure: 15, donations: 25, war: 30, performance: 10, capital: 10, capitalDonations: 10 };
  const requirements = { Elder: { days: 14, roleDays: 0, wars: 3, attackUse: 0.9, donations: 200, donationDates: 2, donationSpan: 7, raids: 0, score: 60 }, "Co-leader": { days: 60, roleDays: 30, wars: 8, attackUse: 0.95, donations: 1e3, donationDates: 3, donationSpan: 14, raids: 2, raidUse: 0.9, score: 80 } };
  const validCount = (n) => T.number(n) && Number.isInteger(n) && n >= 0;
  const fraction = (n, max) => Math.min(1, Math.max(0, n / max));
  const roleName = (role) => ({ member: "Member", admin: "Elder", elder: "Elder", coLeader: "Co-leader", leader: "Leader" })[role] || "Unknown";
  function measure(data, edits, playerTag, start, end, since) {
    const wars = T.warsFor(data, edits), history = data.memberHistory?.[playerTag] || {}, stintStart = Math.max(start, since || end);
    let used = 0, allowed = 0, appearances = 0, missedBoth = 0, knownAttacks = 0, stars = 0, triples = 0, missingWars = 0;
    for (const war of wars) {
      const ended = T.time(war.endTime), prepared = T.time(war.preparationStartTime) || T.time(war.startTime);
      if (!["Regular", "CWL"].includes(war.kind) || !ended || ended <= stintStart || ended > end || prepared && since && prepared < since) continue;
      const member = (war.participants || []).find((v) => T.tag(v.tag) === playerTag);
      if (!member) {
        if (war.rosterComplete !== true) missingWars++;
        continue;
      }
      if (T.isExcused(edits, war, playerTag)) continue;
      const max = war.kind === "CWL" ? 1 : 2;
      if (!war.final || !war.rosterComplete || !validCount(member.attacksUsed) || member.attacksUsed > max) {
        missingWars++;
        continue;
      }
      appearances++;
      used += member.attacksUsed;
      allowed += max;
      if (member.attacksUsed === 0) missedBoth++;
      for (const attack of T.validAttacks(member).slice(0, member.attacksUsed)) if (Number.isInteger(attack.stars) && attack.stars >= 0 && attack.stars <= 3) {
        knownAttacks++;
        stars += attack.stars;
        if (attack.stars === 3) triples++;
      }
    }
    const attackUse = allowed ? used / allowed : null, averageStars = knownAttacks ? stars / knownAttacks : null;
    const intervals = [];
    let lastDonationEnd = stintStart;
    for (const v of [...history.donationIntervals || []].sort((a, b) => T.time(a.end) - T.time(b.end) || a.count - b.count)) {
      if (validCount(v.count) && v.count > 0 && T.time(v.start) >= lastDonationEnd && T.time(v.start) < T.time(v.end) && T.time(v.end) <= end) {
        intervals.push(v);
        lastDonationEnd = T.time(v.end);
      }
    }
    const donationTotal = intervals.reduce((sum, v) => sum + v.count, 0), dates = [...new Set(intervals.map((v) => new Date(T.time(v.end)).toISOString().slice(0, 10)))].sort();
    const donationSpan = dates.length > 1 ? (T.time(dates.at(-1)) - T.time(dates[0])) / DAY : 0;
    const weeks = new Set(intervals.map((v) => Math.floor((T.time(v.end) - start) / (7 * DAY)))).size;
    let raids = 0, raidUsed = 0, raidAllowed = 0, capitalGold = 0;
    for (const raid of data.raids || []) {
      if (raid.state !== "ended" || T.time(raid.startTime) < stintStart || !T.time(raid.endTime) || T.time(raid.endTime) > end) continue;
      const member = (raid.members || []).find((v) => T.tag(v.tag) === playerTag);
      if (!member || !validCount(member.attacks) || !validCount(member.attackLimit) || !validCount(member.bonusAttackLimit)) continue;
      const max = member.attackLimit + member.bonusAttackLimit;
      if (!max || member.attacks > max) continue;
      raids++;
      raidUsed += member.attacks;
      raidAllowed += max;
      if (T.number(member.capitalResourcesLooted) && member.capitalResourcesLooted >= 0) capitalGold += member.capitalResourcesLooted;
    }
    const raidUse = raidAllowed ? raidUsed / raidAllowed : null;
    return { war: { appearances, used, allowed, attackUse, missedBoth, missingWars, knownAttacks, stars, averageStars, triples }, donations: { total: donationTotal, intervals: intervals.length, dates: dates.length, span: donationSpan, weeks }, capital: { raids, used: raidUsed, allowed: raidAllowed, attackUse: raidUse, gold: capitalGold } };
  }
  function evaluate(data, edits = {}, now = Date.now()) {
    const sync = T.time(data.lastSuccessfulSync), end = Math.min(sync || now, now), start = end - 30 * DAY;
    const rows = T.playersFor(data, edits, end);
    return rows.filter((p) => p.inClan && ["Member", "Elder", "Unknown"].includes(roleName(p.role))).map((p) => {
      const history = data.memberHistory?.[p.tag] || {}, since = T.time(history.since), lastSeen = Math.min(T.time(history.lastSeen) || sync, end);
      const days = since && lastSeen >= since ? Math.floor((lastSeen - since) / DAY) : null;
      const roleSince = T.time(history.roleSince), roleDays = roleSince && history.role === p.role && lastSeen >= roleSince ? Math.floor((lastSeen - roleSince) / DAY) : null;
      const target = roleName(p.role) === "Elder" ? "Co-leader" : "Elder", rule = requirements[target];
      const measured = measure(data, edits, p.tag, start, end, since);
      const { appearances, used, allowed, attackUse, missedBoth, missingWars, knownAttacks, stars, averageStars, triples } = measured.war;
      const { total: donationTotal, span: donationSpan, weeks, dates: donationDates } = measured.donations;
      const { raids, used: raidUsed, allowed: raidAllowed, attackUse: raidUse, gold: capitalGold } = measured.capital;
      const capitalDonations = T.capitalEvidence(history, end);
      const points = { tenure: days === null ? 0 : 15 * fraction(days, 30), donations: 15 * fraction(donationTotal, 1e3) + 10 * fraction(weeks, 3), war: attackUse === null ? 0 : 25 * attackUse + 5 * fraction(appearances, 8), performance: knownAttacks >= 6 ? 10 * averageStars / 3 : 0, capital: raidUse === null ? 0 : 7 * raidUse + 3 * fraction(raids, 3), capitalDonations: 10 * fraction(capitalDonations.total || 0, 1e5) };
      const score = Math.round(Object.values(points).reduce((a, b) => a + b, 0));
      const gaps = [];
      if (roleName(p.role) === "Unknown") gaps.push("Refresh the player role.");
      if (history.inClan === false) gaps.push("Confirm this player’s current clan stint with a new scan.");
      if (!sync) gaps.push("Complete a successful roster refresh.");
      else if (now - sync > 2 * DAY) gaps.push("Refresh this report; it is more than two days old.");
      if (data.warnings?.some((v) => String(v).startsWith("Sync failed."))) gaps.push("Resolve the failed refresh before promoting.");
      if (["Kick", "Possible kick", "Bench", "Review"].includes(p.status) || p.uncertain) gaps.push("Resolve the " + p.status.toLowerCase() + " attendance status.");
      if (days === null || days < rule.days) gaps.push("Observe at least " + rule.days + " days in the current clan stint.");
      if (rule.roleDays && (roleDays === null || roleDays < rule.roleDays)) gaps.push("Observe at least " + rule.roleDays + " days as an Elder.");
      if (appearances < rule.wars) gaps.push("Capture at least " + rule.wars + " completed regular/CWL appearances in this 30-day window.");
      if (attackUse !== null && attackUse < rule.attackUse) gaps.push("Reach " + Math.round(100 * rule.attackUse) + "% attack use.");
      if (missedBoth) gaps.push("Recent confirmed zero-attack appearances: " + missedBoth + ".");
      if (missingWars) gaps.push("Confirm final lineups/attack counts for " + missingWars + " war(s) with incomplete results.");
      if (donationTotal < rule.donations) gaps.push("Observe at least " + rule.donations + " donations between scans in this window.");
      if (donationDates < rule.donationDates || donationSpan < rule.donationSpan) gaps.push("Observe donation increases on " + rule.donationDates + " different dates spanning at least " + rule.donationSpan + " days.");
      if (raids < rule.raids) gaps.push("Capture contributions in at least " + rule.raids + " completed Capital weekends.");
      if (rule.raidUse && (raidUse === null || raidUse < rule.raidUse)) gaps.push("Reach " + Math.round(100 * rule.raidUse) + "% attack use in completed Capital reports.");
      if (score < rule.score) gaps.push("Build a contribution score of at least " + rule.score + "/100.");
      return {
        tag: p.tag,
        name: p.name,
        role: roleName(p.role),
        target,
        status: p.status,
        days,
        roleDays,
        since: history.since || null,
        score,
        points,
        ready: gaps.length === 0,
        gaps,
        war: { appearances, used, allowed, attackUse, missedBoth, missingWars, knownAttacks, stars, averageStars, triples },
        donations: measured.donations,
        capital: measured.capital,
        capitalDonations,
        windowStart: new Date(start).toISOString(),
        asOf: new Date(end).toISOString()
      };
    }).sort((a, b) => Number(b.ready) - Number(a.ready) || b.score - a.score || (b.days || 0) - (a.days || 0) || a.name.localeCompare(b.name));
  }
  function demotions(data, edits = {}, now = Date.now()) {
    const sync = T.time(data.lastSuccessfulSync), end = Math.min(sync || now, now);
    return (data.roster || []).filter((p) => ["Elder", "Co-leader"].includes(roleName(p.role))).map((p) => {
      const key = T.tag(p.tag), history = data.memberHistory?.[key] || {}, since = T.time(history.since), roleSince = T.time(history.roleSince), lastSeen = Math.min(T.time(history.lastSeen) || sync, end);
      const roleDays = roleSince && history.role === p.role && lastSeen >= roleSince ? Math.floor((lastSeen - roleSince) / DAY) : null;
      const windows = [{ start: end - 60 * DAY, end: end - 30 * DAY }, { start: end - 30 * DAY, end }].map((v) => ({ ...measure(data, edits, key, v.start, v.end, since), start: new Date(v.start).toISOString(), end: new Date(v.end).toISOString() }));
      const gaps = [];
      if (!sync || now - sync > 2 * DAY || data.warnings?.some((v) => String(v).startsWith("Sync failed."))) gaps.push("Get a successful refresh within the last two days.");
      if (!since || since > end - 60 * DAY || roleDays === null || roleDays < 60) gaps.push("Observe at least 60 days in the clan and in the current role.");
      windows.forEach((window, i) => {
        const label = i ? "Recent 30 days" : "Previous 30 days";
        if (window.war.appearances < 4) gaps.push(label + ": at least 4 final war appearances are required.");
        if (window.war.missingWars) gaps.push(label + ": resolve incomplete war appearances.");
        if (window.war.attackUse === null || window.war.attackUse >= 0.5 || window.war.missedBoth < 2) gaps.push(label + ": sustained war concerns are not established (below 50% attack use and at least 2 unexcused zero-attack appearances).");
        if (window.capital.raids < 2) gaps.push(label + ": capture at least 2 completed raid contributions.");
        if (window.capital.attackUse === null || window.capital.attackUse >= 0.5) gaps.push(label + ": sustained raid concerns are not established (below 50% of available attacks used).");
      });
      return { tag: key, name: p.name, role: roleName(p.role), target: roleName(p.role) === "Elder" ? "Member" : "Elder", roleDays, ready: gaps.length === 0, gaps, windows };
    }).sort((a, b) => Number(b.ready) - Number(a.ready) || a.name.localeCompare(b.name));
  }
  return { evaluate, demotions, weights, requirements, roleName };
});
(function(root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./tracker.js"));
  else {
    const value = factory(root.WarTracker);
    root.LeagueAvatars = value.LeagueAvatars;
    root.ClanHonors = value.ClanHonors;
  }
})(typeof globalThis === "object" ? globalThis : this, function(T) {
  "use strict";
  const safeURL = (value) => typeof value === "string" && /^https:\/\/api-assets\.clashofclans\.com\/(?:leaguetiers|leagues)\/[A-Za-z0-9_\/-]+\.png$/.test(value);
  const safeImage = (value) => typeof value === "string" && /^data:image\/png;base64,[A-Za-z0-9+/]+={0,2}$/.test(value) && value.length < 35e4;
  function leagueFor(data, player) {
    const key = T.tag(player.tag), current = (data.roster || []).find((p) => T.tag(p.tag) === key), profile = data.profiles?.[key] || player.profile || {};
    const modern = [current?.leagueTier, player.leagueTier, profile.leagueTier].find((v) => v && (v.name || v.id));
    const league = modern || [current?.league, player.league, profile.league].find((v) => v && (v.name || v.id)) || {};
    const name = String(league.name || "League not captured"), field = modern ? "leagueTier" : "league";
    const matching = [league, current?.[field], player[field], profile[field]].filter((v) => v && (league.id && v.id === league.id || !league.id && v.name === league.name));
    const urls = matching.map((v) => v.iconUrls || {}).flatMap((v) => [v.small, v.medium, v.large]).filter(safeURL), url = urls[0] || "";
    const cached = urls.map((v) => data.leagueBadgeImages?.[v]?.dataUrl).find(safeImage);
    const role = current?.role || "", ring = ["admin", "elder"].includes(role) ? "elder" : role === "coLeader" ? "coleader" : "member";
    const roleLabel = { admin: "Elder", elder: "Elder", coLeader: "Co-leader", leader: "Leader", member: "Member" }[role] || "";
    const family = name.replace(/\s+League.*$/i, "").replace(/[^a-z]/gi, "").toLowerCase();
    const tier = name.match(/(?:\s)(\d+|III|II|I)$/)?.[1] || "";
    return { name, ring, role: roleLabel, family, tier, image: cached || url, inClan: Boolean(current), known: Boolean(league.name || league.id) };
  }
  function captured(data, edits = {}) {
    const awards = [], seen = /* @__PURE__ */ new Set(), add = (award) => {
      if (!seen.has(award.id)) {
        seen.add(award.id);
        awards.push(award);
      }
    };
    const wars = T.warsFor(data, edits), tags = new Set((data.roster || []).map((p) => T.tag(p.tag)));
    wars.forEach((w) => (w.participants || []).forEach((p) => tags.add(T.tag(p.tag))));
    for (const key of tags) {
      let fullStreak = 0, tripleStreak = 0, cwlTriples = 0, capturedStars = 0;
      for (const war of wars) {
        if (!["Regular", "CWL"].includes(war.kind) || !T.isClosed(war) || !T.time(war.endTime) || T.time(war.endTime) > Date.now()) continue;
        const member = (war.participants || []).find((p) => T.tag(p.tag) === key);
        if (!war.final || !war.rosterComplete) {
          if (war.kind === "Regular") {
            fullStreak = 0;
            tripleStreak = 0;
          }
          continue;
        }
        if (!member || T.isExcused(edits, war, key)) continue;
        const max = war.kind === "CWL" ? 1 : 2, used = member.attacksUsed;
        if (!Number.isInteger(used) || used < 0 || used > max) {
          if (war.kind === "Regular") {
            fullStreak = 0;
            tripleStreak = 0;
          }
          continue;
        }
        const attacks = T.validAttacks(member).slice(0, used), known = attacks.filter((a) => Number.isInteger(a.stars) && a.stars >= 0 && a.stars <= 3), stars = known.reduce((sum, a) => sum + a.stars, 0), allTriples = used === max && known.length === used && known.every((a) => a.stars === 3);
        const base = { tag: key, name: member.name || key, observedAt: war.observedAt || war.endTime, occurredAt: war.endTime, alreadyReached: false, source: "Captured final war results", warId: war.id };
        const previousStars = capturedStars;
        capturedStars += stars;
        for (const goal of [100, 250, 500, 1e3]) if (previousStars < goal && capturedStars >= goal) add({ ...base, id: key + "::capturedStars:" + goal, title: goal + " captured attack stars", detail: "Reached " + goal + " individual attack stars across saved regular and CWL results. These can differ from new clan stars.", category: "War", priority: 90 + goal / 100 });
        if (war.kind === "CWL") {
          if (allTriples) {
            cwlTriples++;
            for (const goal of [10, 25, 50]) if (cwlTriples === goal) add({ ...base, id: key + "::cwlTriples:" + goal, title: goal + " captured CWL triples", detail: "Three-star attacks in " + goal + " saved completed CWL rounds.", category: "War", priority: 100 });
          }
          continue;
        }
        fullStreak = used === 2 ? fullStreak + 1 : 0;
        tripleStreak = allTriples ? tripleStreak + 1 : 0;
        for (const goal of [10, 25, 50]) if (fullStreak === goal) add({ ...base, id: key + "::reliable:" + goal + ":" + war.id, title: goal + " full-attack appearances", detail: "Used both attacks in " + goal + " consecutive captured regular-war appearances. Approved exceptions and known non-selection are skipped; missing results break the streak.", category: "Reliability", priority: 85 + goal / 10 });
        for (const goal of [3, 5, 10]) if (tripleStreak === goal) add({ ...base, id: key + "::perfect:" + goal + ":" + war.id, title: goal + " consecutive six-star appearances", detail: "Two three-star attacks in each of " + goal + " consecutive captured regular-war appearances. Individual attack stars can overlap on the same base.", category: "War", priority: 110 + goal });
      }
    }
    for (const raid of data.raids || []) {
      if (raid.state !== "ended" || !T.time(raid.endTime) || T.time(raid.endTime) > Date.now()) continue;
      for (const member of raid.members || []) if (T.number(member.capitalResourcesLooted) && member.capitalResourcesLooted >= 5e4 && Number.isInteger(member.attacks) && member.attacks > 0) {
        const goal = member.capitalResourcesLooted >= 1e5 ? 1e5 : member.capitalResourcesLooted >= 75e3 ? 75e3 : 5e4, key = T.tag(member.tag);
        add({ id: key + "::raidLoot:" + raid.id, tag: key, name: member.name || key, title: goal.toLocaleString() + "+ Gold raid weekend", detail: member.capitalResourcesLooted.toLocaleString() + " Capital Gold captured in this completed weekend.", category: "Capital", priority: 100 + goal / 1e4, observedAt: raid.observedAt || raid.endTime, occurredAt: raid.endTime, alreadyReached: false, source: "Captured final raid report" });
      }
    }
    return awards;
  }
  function forData(data, edits = {}) {
    const earnedHere = a => {
      if (!a || !a.id || !a.tag || a.alreadyReached !== false) return false;
      const before = T.time(a.previousObservedAt), after = T.time(a.observedAt);
      if (!before || !after || before >= after) return false;
      if (a.earnedInClan === true && T.tag(a.clanTag) === T.tag(data.clanTag) && T.time(a.membershipSince) && T.time(a.membershipSince) <= before) return true;
      // Older crossing receipts can be retained when the saved membership
      // history covers their entire observation window. Baselines never qualify.
      const history = data.memberHistory?.[T.tag(a.tag)];
      return history && [...(history.pastStints || []), history].some(stint => {
        const start = T.time(stint.since), end = T.time(stint.leftAt || stint.lastSeen);
        return start && end && start <= before && after <= end;
      });
    };
    const map = new Map(Object.values(data.honors || {}).filter(earnedHere).map((a) => [a.id, a]));
    for (const award of captured(data, edits)) map.set(award.id, award);
    const current = new Map((data.roster || []).map((p) => [T.tag(p.tag), p]));
    return [...map.values()].map((a) => ({ ...a, tag: T.tag(a.tag), name: current.get(T.tag(a.tag))?.name || a.name, inClan: current.has(T.tag(a.tag)) })).sort((a, b) => Number(a.alreadyReached) - Number(b.alreadyReached) || T.time(b.observedAt) - T.time(a.observedAt) || (b.priority || 0) - (a.priority || 0) || String(a.name).localeCompare(String(b.name)));
  }
  return { LeagueAvatars: { forPlayer: leagueFor, safeURL, safeImage }, ClanHonors: { captured, forData } };
});
(function(root, factory) {
  const value = factory();
  if (typeof module === "object" && module.exports) module.exports = value;
  else root.ClanProgress = value;
})(typeof globalThis === "object" ? globalThis : this, function() {
  "use strict";
  const cumulative = [0, 500, 1700, 3600, 6700, 10500, 15e3, 20200, 26100, 34e3, 42600, 51900, 61900, 72600, 88300, 104700, 121800, 139600, 158100, 181600, 205800, 230700, 256300, 282600, 313900, 345900, 378600, 412e3, 446100, 485200, 525e3, 565500, 606700, 648600, 695500, 743100, 791400, 840400, 890100, 944800, 1000200, 1056300, 1113100, 1170600, 1233100, 1296300, 1360200, 1424800, 1490100, 1560400, 1631400];
  const time = (v) => Number.isFinite(Date.parse(v)) ? Date.parse(v) : 0;
  const number = (v) => typeof v === "number" && Number.isFinite(v);
  function merge(a = [], b = [], daily = false) {
    const records = /* @__PURE__ */ new Map();
    for (const v of [...a, ...b]) {
      if (!v || !time(v.at)) continue;
      const key = daily ? new Date(time(v.at)).toISOString().slice(0, 10) + ":" + v.clanLevel : new Date(time(v.at)).toISOString();
      const old = records.get(key);
      if (!old || time(v.at) >= time(old.at)) records.set(key, v);
    }
    return [...records.values()].sort((x, y) => time(x.at) - time(y.at));
  }
  function cutoff(range, asOf) {
    if (range === "all") return 0;
    const d = new Date(asOf), months = Number(range);
    const day = d.getUTCDate();
    d.setUTCDate(1);
    d.setUTCMonth(d.getUTCMonth() - months);
    const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate();
    d.setUTCDate(Math.min(day, last));
    return d.getTime();
  }
  const within = (points, range, asOf) => points.filter((v) => time(v.at) >= cutoff(range, asOf) && time(v.at) <= asOf);
  const floor = (level) => Number.isInteger(level) && level >= 1 && level <= cumulative.length ? cumulative[level - 1] : null;
  const requirement = (level) => floor(level) !== null && floor(level + 1) !== null ? floor(level + 1) - floor(level) : null;
  function checkpoint(v) {
    if (!v || !time(v.at) || !Number.isInteger(v.level) || requirement(v.level) === null || !Number.isInteger(v.xp) || v.xp < 0 || v.xp >= requirement(v.level)) throw Error("Enter a valid level and the XP shown within that level (below " + (requirement(v?.level) ?? "the next level requirement") + ").");
    return { ...v, total: floor(v.level) + v.xp };
  }
  function screenshotReading(text) {
    const digits = (v) => Number(v.replace(/[, .]/g, "")), levelMatch = String(text).match(/(?:clan\s*)?level\s*[:]?\s*(\d{1,2})/i), level = levelMatch ? Number(levelMatch[1]) : null, candidates = [];
    for (const m of String(text).matchAll(/(\d[\d, .]*)\s*[/|]\s*(\d[\d, .]*)/g)) {
      const xp = digits(m[1]), limit = digits(m[2]);
      for (let l = 1; l < 51; l++) if (requirement(l) === limit && (!level || level === l) && Number.isSafeInteger(xp) && xp >= 0 && xp < limit) candidates.push({ level: l, xp });
    }
    const unique = [...new Map(candidates.map((v) => [v.level + ":" + v.xp, v])).values()];
    if (unique.length !== 1) throw Error("Could not identify one clear clan XP counter. Crop to the clan level and XP bar, try again, or enter the reading below.");
    return unique[0];
  }
  function xpRewards(data, since) {
    const rows = [...new Map((data.wars || []).map((w) => [w.id, w])).values()].filter((w) => ["Regular", "CWL"].includes(w.kind) && w.state === "warEnded" && time(w.endTime) > time(since) && Number.isInteger(w.expEarned) && w.expEarned >= 0).map((w) => ({ at: w.endTime, kind: w.kind, xp: w.expEarned, opponent: w.opponent?.name || "Opponent" }));
    return { rows, regular: rows.filter((w) => w.kind === "Regular").reduce((n, w) => n + w.xp, 0), cwl: rows.filter((w) => w.kind === "CWL").reduce((n, w) => n + w.xp, 0) };
  }
  function xpSeries(data, edits) {
    const checkpoints = Object.entries(edits.xpCheckpoints || {}).filter(([, v]) => !v.deleted).flatMap(([id, v]) => {
      try {
        return [{ ...checkpoint(v), id }];
      } catch {
        return [];
      }
    }).sort((a, b) => time(a.at) - time(b.at));
    const levels = [];
    let previous = null;
    for (const v of merge(data.clanHistory || [])) if (floor(v.clanLevel) !== null && v.clanLevel !== previous) {
      levels.push({ at: v.at, value: floor(v.clanLevel), level: v.clanLevel, lowerBound: true, detail: "Level " + v.clanLevel + " first observed here; at least " + floor(v.clanLevel).toLocaleString() + " cumulative XP. The exact level-up time is unknown." });
      previous = v.clanLevel;
    }
    const history = merge(data.clanHistory || []), latest = history.at(-1), manual = checkpoints.at(-1), manualCurrent = Boolean(manual && time(manual.at) >= Math.max(time(data.lastSuccessfulSync), time(latest?.at)));
    const level = manualCurrent ? manual.level : latest?.clanLevel ?? data.clanProfile?.clanLevel;
    const total = manualCurrent ? manual.total : null;
    const targets = [level + 1, level + 2].filter((l) => floor(l) !== null).map((l) => ({ level: l, value: floor(l), remaining: total === null ? null : Math.max(0, floor(l) - total) }));
    return { checkpoints, levels, level, total, targets, latestManual: manual, manualCurrent };
  }
  return { time, number, merge, cutoff, within, floor, requirement, checkpoint, screenshotReading, xpRewards, xpSeries };
});
(function(root, factory) {
  const value = factory(root.WarTracker, root.ClanProgress);
  if (typeof module === "object" && module.exports) module.exports = value;
  else root.Leadership = value;
})(typeof globalThis === "object" ? globalThis : this, function(T, P) {
  "use strict";
  const DAY = 864e5, valid = P.number;
  function week(at) {
    const d = new Date(T.time(at) - 5 * 36e5);
    d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7);
    d.setUTCHours(5, 0, 0, 0);
    return d.toISOString();
  }
  function mergeHistory(a = [], b = []) {
    const out = /* @__PURE__ */ new Map();
    for (const s of [...a, ...b]) {
      if (!s || !T.time(s.at) || !Array.isArray(s.members)) continue;
      const key = new Date(T.time(s.at)).toISOString(), old = out.get(key);
      if (!old || T.time(s.at) >= T.time(old.at)) out.set(key, s);
    }
    return [...out.values()].sort((a2, b2) => T.time(a2.at) - T.time(b2.at));
  }
  function compare(a, b, metric = "league") {
    if (!a || !b) return null;
    const before = new Map(a.members.map((p) => [T.tag(p.tag), p])), after = new Map(b.members.map((p) => [T.tag(p.tag), p])), value = (p) => metric === "trophies" ? p?.trophies : p?.league?.points;
    const existing = [], joined = [], departed = [];
    let change = 0, joinPoints = 0, leavePoints = 0, comparable = 0, up = 0, down = 0, same = 0;
    for (const [tag, p] of after) {
      const old = before.get(tag);
      if (old) {
        const x = value(old), y = value(p), delta2 = valid(x) && valid(y) ? y - x : null;
        existing.push({ tag, name: p.name, before: x, after: y, delta: delta2, oldLeague: old.league, newLeague: p.league });
        if (delta2 !== null) {
          change += delta2;
          comparable++;
          if (delta2 > 0) up++;
          else if (delta2 < 0) down++;
          else same++;
        }
      } else {
        joined.push(p);
        if (valid(value(p))) joinPoints += value(p);
      }
    }
    for (const [tag, p] of before) if (!after.has(tag)) {
      departed.push(p);
      if (valid(value(p))) leavePoints -= value(p);
    }
    const sum = (s) => s.members.reduce((n, p) => n + (valid(value(p)) ? value(p) : 0), 0), delta = sum(b) - sum(a), coverage = delta - change - joinPoints - leavePoints;
    return { existing, joined, departed, existingChange: change, joinPoints, leavePoints, coverage, delta, comparable, up, down, same, before: sum(a), after: sum(b), beforeKnown: a.members.filter((p) => valid(value(p))).length, afterKnown: b.members.filter((p) => valid(value(p))).length };
  }
  function reports(data) {
    const samples = mergeHistory(data.leagueHistory || []), groups = /* @__PURE__ */ new Map();
    for (const s of samples) {
      const key = week(s.at);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(s);
    }
    const asOf = Math.max(T.time(data.lastSuccessfulSync), Date.now()), out = [];
    let prior = null;
    for (const [key, entries] of groups) {
      const current = entries.at(-1), baseline = prior || (entries.length > 1 ? entries[0] : null), end = T.time(key) + 7 * DAY, change = compare(baseline, current), wars = T.warsFor(data, data.edits || {}).filter((w) => ["Regular", "CWL"].includes(w.kind) && T.isClosed(w) && T.time(w.endTime) >= T.time(key) && T.time(w.endTime) < end), raids = (data.raids || []).filter((r) => r.state === "ended" && T.time(r.endTime) >= T.time(key) && T.time(r.endTime) < end);
      let used = 0, allowed = 0;
      for (const w of wars) if (w.final && w.rosterComplete) for (const p of w.participants || []) {
        const max = valid(w.attacksPerMember) ? w.attacksPerMember : w.kind === "CWL" ? 1 : 2;
        if (Number.isInteger(p.attacksUsed) && p.attacksUsed >= 0 && p.attacksUsed <= max) {
          used += p.attacksUsed;
          allowed += max;
        }
      }
      const distribution = /* @__PURE__ */ new Map();
      for (const p of current.members) {
        const league = p.league || {}, k = league.known ? league.id : "unknown", v = distribution.get(k) || { name: league.known ? league.name : "Not captured", tier: league.tier ?? -1, points: league.points ?? null, count: 0 };
        v.count++;
        distribution.set(k, v);
      }
      out.push({ key, end: new Date(end).toISOString(), current, baseline, change, closed: end <= asOf, gapWeeks: prior ? Math.max(0, Math.round((T.time(key) - T.time(week(prior.at))) / (7 * DAY)) - 1) : 0, distribution: [...distribution.values()].sort((a, b) => b.tier - a.tier), wars, raids, used, allowed });
      prior = current;
    }
    return out.reverse();
  }
  function eligibility(p, mode, includeUnknown = false) {
    if (!p.inClan) return "Departed";
    if (p.status === "Kick" || p.kick) return "Kick flag";
    if (p.status === "Possible kick" || p.possibleKick) return "Possible kick · review attendance";
    if (mode === "Regular" && (p.status === "Bench" || p.bench)) return "Regular-war bench";
    if (p.uncertain || p.status === "Review") return "Missing final results";
    if (p.warPreference === "out") return "Opted out";
    if (p.warPreference !== "in" && !includeUnknown) return "Preference unknown";
    return "";
  }
  function priority(p) {
    const a = p.attackLikelihood, attendance = valid(a?.probability) ? a.probability : 0.5, quality = valid(p.performance?.averageStars) ? p.performance.averageStars / 3 : 0.5, army = valid(p.armyPercent) ? Math.max(0, Math.min(1, p.armyPercent / 100)) : 0.5;
    return attendance * 0.65 + quality * 0.2 + army * 0.15;
  }
  function suggest(members, options = {}) {
    const mode = options.mode || "Regular", allowed = mode === "CWL" ? options.cwl15Only ? [15] : [15, 30] : [5, 10, 15, 20, 25, 30, 40, 50], pool = members.filter((p) => !eligibility(p, mode, options.includeUnknown)), size = options.size && options.size !== "max" ? Number(options.size) : allowed.filter((n) => n <= pool.length).at(-1) || 0;
    const target = allowed.includes(size) ? size : 0, selected = [], byHall = /* @__PURE__ */ new Map();
    for (const p of pool) {
      const th = Number(p.townHallLevel) || 0;
      if (!byHall.has(th)) byHall.set(th, []);
      byHall.get(th).push(p);
    }
    const ranked = (a, b) => priority(b) - priority(a) || T.tag(a.tag).localeCompare(T.tag(b.tag));
    for (const group of byHall.values()) group.sort(ranked);
    if (options.balance === "strength") {
      selected.push(...[...pool].sort((a, b) => (b.townHallLevel || 0) - (a.townHallLevel || 0) || ranked(a, b)).slice(0, target));
    } else if (pool.length && target) {
      const quotas = [...byHall].map(([th, group]) => ({ th, group, exact: group.length * target / pool.length, count: Math.min(group.length, Math.floor(group.length * target / pool.length)) }));
      let left = Math.min(target, pool.length) - quotas.reduce((n, q) => n + q.count, 0);
      quotas.sort((a, b) => b.exact - b.count - (a.exact - a.count) || b.th - a.th);
      while (left > 0) {
        let changed = false;
        for (const q of quotas) if (left && q.count < q.group.length) {
          q.count++;
          left--;
          changed = true;
        }
        if (!changed) break;
      }
      for (const q of quotas) selected.push(...q.group.slice(0, q.count));
    }
    const tags = new Set(selected.map((p) => T.tag(p.tag)));
    return { mode, target, allowed, pool, selected: selected.sort((a, b) => (b.townHallLevel || 0) - (a.townHallLevel || 0) || ranked(a, b)), reserves: pool.filter((p) => !tags.has(T.tag(p.tag))).sort(ranked), excluded: members.filter((p) => p.inClan && !pool.includes(p)).map((p) => ({ ...p, excludedReason: eligibility(p, mode, options.includeUnknown) })), shortfall: Math.max(0, target - pool.length) };
  }
  return { week, mergeHistory, compare, reports, eligibility, priority, suggest };
});
