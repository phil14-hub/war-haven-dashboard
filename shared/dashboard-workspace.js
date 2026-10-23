"use strict";
const townHallImages = __TOWN_HALL_IMAGES__;
function townHallIcon(value) {
  const level = Number(value), src = Number.isInteger(level) ? townHallImages[level] : null;
  if (!src) return `<span class="townhall-icon" role="img" aria-label="Town Hall ${Number.isInteger(level) && level > 0 ? level : "unknown"}">${icon("castle")}</span>`;
  return `<span class="townhall-icon" role="img" aria-label="Town Hall ${level}" title="Town Hall ${level}"><img src="${src}" alt="" loading="lazy" decoding="async"></span>`;
}
const formatNumber = (v) => typeof v === "number" && Number.isFinite(v) ? v.toLocaleString() : "—";
const latestRaids = () => [...data.raids || []].sort((a, b) => WarTracker.time(b.startTime) - WarTracker.time(a.startTime));
function icon(name) {
  const paths = {
    refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 7a7 7 0 0 1 11.5-1L20 9M4 15l2.4 3A7 7 0 0 0 18 17"/>',
    home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
    recruit: '<circle cx="9" cy="7" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M19 7v8m-4-4h8"/>',
    users: '<circle cx="9" cy="7" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 4v2"/>',
    swords: '<path d="m4 3 4 1 9 10-3 3L4 7Zm16 0-4 1-4 4m-3 5-4 4m-2-2 6 6m6-6 6 6m-4-1 3-3M4 20l3-3"/>',
    castle: '<path d="M3 21V10h4v3h3v-3h4v3h3v-3h4v11ZM9 21v-5h6v5M8 10V4h8v6M12 4V1l5 1-5 2"/>',
    more: '<circle cx="4" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="20" cy="12" r="1.4"/>',
    star: '<path d="m12 2 3.1 6.4 7 .9-5.1 5 1.2 7.1L12 18l-6.2 3.4 1.2-7.1-5.1-5 7-.9Z"/>',
    stars: '<path d="m12 2 2.3 4.7 5.2.8-3.8 3.7.9 5.2L12 14l-4.6 2.4.9-5.2-3.8-3.7 5.2-.8ZM3 16l1 2 2 .3-1.5 1.4.4 2.1L3 21l-1.9.8.4-2.1L0 18.3l2-.3m19-2 1 2 2 .3-1.5 1.4.4 2.1L21 21l-1.9.8.4-2.1-1.5-1.4 2-.3"/>',
    shield: '<path d="M12 2 3 6v6c0 5 4 8 9 10 5-2 9-5 9-10V6ZM8 12l3 3 5-6"/>',
    flag: '<path d="M5 22V3m0 1c5-4 8 4 14 0v11c-6 4-9-4-14 0"/>',
    bench: '<circle cx="9" cy="6" r="3"/><path d="M3 21v-2a6 6 0 0 1 9-5"/><circle cx="17" cy="17" r="5"/><path d="m13.5 13.5 7 7"/>',
    trophy: '<path d="M8 3h8v7a4 4 0 0 1-8 0Zm0 2H3v2a5 5 0 0 0 5 5m8-7h5v2a5 5 0 0 1-5 5M12 14v5m-5 2h10m-8-2h6"/>',
    settings: '<path d="m10 2 4 0 1 3 3 1 3-1 2 4-2 2v3l2 2-2 4-3-1-3 1-1 3h-4l-1-3-3-1-3 1-2-4 2-2v-3L1 9l2-4 3 1 3-1Z"/><circle cx="12" cy="12" r="3"/>',
    search: '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
    chevron: '<path d="m9 5 7 7-7 7"/>',
    plus: '<path d="M12 3v18M3 12h18"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
    gift: '<path d="M3 9h18v4H3Zm2 4v8h14v-8M12 9v12"/><path d="M12 9C6 10 3 4 6 3s6 3 6 6Zm0 0c6 1 9-5 6-6s-6 3-6 6Z"/>',
    promote: '<path d="m3 17 4-10 5 5 5-5 4 10ZM4 21h16M12 2v4m-2-2h4"/>',
    activity: '<path d="M2 12h5l3-8 4 16 3-8h5"/>',
    archive: '<path d="M3 3h18v4H3Zm2 4v14h14V7m-10 5h6"/>',
    download: '<path d="M12 2v14m-5-5 5 5 5-5M3 17v4h18v-4"/>',
    upload: '<path d="M12 16V2m-5 5 5-5 5 5M3 17v4h18v-4"/>',
    table: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18M3 15h18"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    check: '<path d="m4 12 5 5L20 6"/>',
    gold: '<path d="m5 6 7-3 7 3v12l-7 3-7-3Zm0 0 7 3 7-3M12 9v12"/>'
  };
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[name] || paths.shield}</svg>`;
}
function clanHeroBadgeUrl(clan = {}) {
  for (const value of [clan.badgeUrls?.large, clan.badgeUrls?.medium, clan.badgeUrls?.small]) {
    if (typeof value !== "string") continue;
    try {
      const url = new URL(value);
      if (url.origin === "https://api-assets.clashofclans.com" && url.pathname.startsWith("/badges/") && !url.username && !url.password) return url.href;
    } catch {
    }
  }
  return "";
}
function updateClanFavicon(clan = {}) {
  const badge2 = clanHeroBadgeUrl(clan), icon2 = document.getElementById("clan-favicon");
  if (badge2 && icon2) {
    const href = "https://war-haven-actions.readydrake18.chatgpt.site/members/favicon.svg?v=" + encodeURIComponent(badge2);
    if (icon2.getAttribute("href") !== href) {
      icon2.type = "image/svg+xml";
      icon2.href = href;
    }
  }
}
function shieldGraphic(clan = {}) {
  const badge2 = clanHeroBadgeUrl(clan);
  return `<svg class="hero-art" viewBox="0 0 280 200" aria-hidden="true" focusable="false"><path d="m0 157 37-34 16 9 40-61 23 28 28-36 43 59 26-20 67 50v48H0Z" fill="#263c52" opacity=".55"/><path d="m53 132 40-61 23 28-25-13-9 21-7-1Z" fill="#96a5b3" opacity=".22"/><path d="M15 187v-36h10v-13h8v13h8v-18h8v18h10v36m156 0v-44h8v-13h8v13h8v-19h7v19h10v44" fill="#0b1a2b"/><ellipse cx="156" cy="181" rx="68" ry="9" fill="#071322" opacity=".65"/><g transform="rotate(-40 155 115)"><path d="M149 23h12l-2 114h-8Z" fill="#d6e1e8" stroke="#b4c3c9"/><path d="m149 23 6-12 6 12-6 9Z" fill="#e9ece5"/><path d="M138 133h34v8h-34Z" fill="#e9bd68" stroke="#edc873"/><path d="M151 141h8v33h-8Z" fill="#8c5929" stroke="#eac267"/><path d="M151 146h8m-8 7h8m-8 7h8" stroke="#d2a454"/><path d="M149 173h12v8h-12Z" fill="#e9bd68"/></g><g transform="rotate(40 155 115)"><path d="M149 23h12l-2 114h-8Z" fill="#d6e1e8" stroke="#b4c3c9"/><path d="m149 23 6-12 6 12-6 9Z" fill="#e9ece5"/><path d="M138 133h34v8h-34Z" fill="#e9bd68" stroke="#edc873"/><path d="M151 141h8v33h-8Z" fill="#8c5929" stroke="#eac267"/><path d="M151 146h8m-8 7h8m-8 7h8" stroke="#d2a454"/><path d="M149 173h12v8h-12Z" fill="#e9bd68"/></g><path d="m153 56 52 18v42c0 24-18 46-52 61-34-15-52-37-52-61V74Z" fill="#e9bd68" stroke="#ffe3a2" stroke-width="2"/><path d="m153 66 41 15v34c0 20-15 38-41 51-26-13-41-31-41-51V81Z" fill="#704615" stroke="#be8a34"/><path d="m153 71 37 13v30c0 18-13 35-37 47-24-12-37-29-37-47V84Z" fill="#c39742" stroke="#e9be63"/><path d="m153 72 0 89c-24-12-37-29-37-47V84Z" fill="#f8d883" opacity=".3"/><path d="m153 75 30 11-30 12-31-12Z" fill="#fff0b7" opacity=".27"/><path d="M154 99v58c19-11 31-26 33-43V89Z" fill="#67431b" opacity=".15"/>${badge2 ? `<defs><clipPath id="clan-hero-crest-clip"><path d="m153 71 37 13v30c0 18-13 35-37 47-24-12-37-29-37-47V84Z"/></clipPath></defs><image class="clan-hero-crest" href="${esc(badge2)}" x="111" y="68" width="84" height="96" preserveAspectRatio="xMidYMid slice" clip-path="url(#clan-hero-crest-clip)"/><path d="m153 71 37 13v30c0 18-13 35-37 47-24-12-37-29-37-47V84Z" fill="none" stroke="#e9be63"/>` : ""}</svg>`;
}
function avatar(p) {
  const league = LeagueAvatars.forPlayer(data, p), label = league.name + (league.role ? " · " + league.role : "") + (league.inClan ? "" : " · last saved league");
  return `<span class="avatar league-avatar ring-${league.ring} family-${esc(league.family)}" role="img" aria-label="${esc(label)}" title="${esc(label)}"><span class="league-fallback" aria-hidden="true">${icon("trophy")}${league.tier ? `<small>${esc(league.tier)}</small>` : ""}</span>${league.image ? `<img class="league-image" data-league-image src="${esc(league.image)}" alt="" referrerpolicy="no-referrer" decoding="async">` : ""}</span>`;
}
function wireLeagueBadges(element) {
  element.querySelectorAll("[data-league-image]").forEach((img) => {
    img.onload = () => {
      img.hidden = false;
      img.parentElement.classList.add("league-icon-loaded");
    };
    img.onerror = () => {
      img.hidden = true;
      img.parentElement.classList.remove("league-icon-loaded");
    };
    if (img.complete && img.naturalWidth > 0) img.onload();
  });
}
function emptyPanel(title, text, graphic = "shield") {
  return `<div class="panel empty"><div class="empty-icon">${icon(graphic)}</div><h2>${esc(title)}</h2><p>${esc(text)}</p></div>`;
}
function statCard(label, value, graphic = "star", context = "", tone = "", action = "") {
  const element = action ? "button" : "div", content = action ? "span" : "div";
  return `<${element} class="card${action ? " card-link" : ""}"${action ? ` type="button" data-home-card="${esc(action)}" aria-label="${esc(label)}: ${esc(value)}. Open details"` : ""}><span class="card-icon ${esc(tone)}">${icon(graphic)}</span><${content} class="card-value"><strong>${esc(value)}</strong><span class="label">${esc(label)}</span>${context ? `<small>${esc(context)}</small>` : ""}</${content}></${element}>`;
}
function miniCards(values) {
  return `<div class="cards compact-cards">${values.map(([label, value, graphic, context]) => statCard(label, value, graphic, context)).join("")}</div>`;
}
function enrichRows() {
  const performance = WarTracker.performanceFor(data, edits), likelihood = WarTracker.attackLikelihoodFor(data, edits), raid = latestRaids()[0];
  for (const p of rows) {
    p.profile = data.profiles?.[p.tag] || {};
    p.performance = performance[p.tag];
    p.attackLikelihood = likelihood[p.tag];
    p.capitalContributions = p.profile.clanCapitalContributions;
    p.contributions = WarTracker.contributionsFor(data, p.tag);
    p.raidLoot = raid?.members?.find((m) => WarTracker.tag(m.tag) === p.tag)?.capitalResourcesLooted;
  }
}
function warPreferenceBadge(p) {
  const pref = ["in", "out"].includes(p.warPreference) ? p.warPreference : "unknown", label = pref === "in" ? "Opted in" : pref === "out" ? "Opted out" : "Preference unknown", saved = p.warPreferenceCheckedAt ? "Last checked " + date(p.warPreferenceCheckedAt) : "Saved preference; check time unavailable";
  return `<span class="war-preference pref-${pref}" title="${esc(saved)}">${icon(pref === "in" ? "check" : pref === "out" ? "close" : "info")}${label}</span>`;
}
function attackSignals(p) {
  const a = p.attackLikelihood, value = a?.probability == null ? "—" : Math.round(100 * a.probability) + "%", evidence = a?.appearances ? `${a.attacked}/${a.appearances} appearances with ≥1 attack${a.limited ? " · limited history" : ""}${a.old ? " · history over 30 days old" : ""}` : "Not enough history", method = "Estimated chance of using at least one attack if selected for a regular war. Last 10 confirmed, unexcused appearances. Estimate = (appearances with an attack + 1) / (appearances + 2); no history gives no estimate. This is a history-based estimate, not a calibrated prediction.";
  return `<span class="player-card-signals">${warPreferenceBadge(p)}<span class="attack-likelihood" title="${esc(method)}"><strong>${value}</strong><small>chance of ≥1 attack</small></span></span><span class="likelihood-evidence">${esc(evidence)}</span>`;
}
function bars(items, label) {
  const max = Math.max(1, ...items.map((x) => x.value || 0));
  return `<div aria-label="${esc(label)}">${items.map((x) => `<div class="chart-row"><span>${esc(x.label)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0, Math.min(100, 100 * (x.value || 0) / max))}%"></div></div><strong>${formatNumber(x.value)}</strong></div>`).join("")}</div>`;
}
function renderExtended() {
  renderOverview();
  renderWeeklyHome();
  renderProgressHome();
  renderSyncDetails();
  renderActivePage(document.body.dataset.page || "overview");
}
function renderActivePage(page) {
  const renderers = { weekly: renderWeeklyReports, progress: renderProgress, townhalls: renderTownHallProgress, planner: renderWarPlanner, performance: renderPerformance, capital: renderCapital, donations: renderDonations, activity: renderActivity, promotions: renderPromotions, achievements: renderAchievements };
  renderers[page]?.();
}
function renderOverview() {
  const clan = data.clanProfile || {}, active = rows.filter((p) => p.inClan), wars = WarTracker.warsFor(data, edits), eligible = active.filter((p) => !Leadership.eligibility(p,"Regular",false)).length;
  updateClanFavicon(clan);
  $("overview-hero").innerHTML = active.length ? `<div class="hero">${shieldGraphic(clan)}<div class="hero-copy"><h2>Ready for the next war</h2><div class="hero-number">${eligible}</div><div class="hero-label">available for regular war</div><div class="hero-note">Confirmed opt-in and saved attendance. Unknown preferences require confirmation.</div></div></div>` : `<div class="hero empty-hero">${shieldGraphic(clan)}<div class="hero-copy"><h2>Your clan, at a glance</h2><p>Run the collector to load your roster and start tracking wars.</p><button class="primary" data-open="rules">Setup steps</button></div></div>`;
  const flagged = active.filter((p) => ["Kick", "Possible kick", "Bench", "Review"].includes(p.status));
  let actions = flagged.length ? `<ul class="action-list">${flagged.map((p) => `<li><button class="action-row" data-extended-player="${esc(p.tag)}" data-attendance-evidence="${esc(p.tag)}">${avatar(p)}<span><b class="player-name-with-hall">${townHallIcon(p.townHallLevel)}<span>${esc(p.name)}</span></b><small>${esc(p.reason)}</small></span><span class="row-status">${badge(p.status)}</span></button></li>`).join("")}</ul>` : '<div class="action-note">' + icon("check") + "<div><b>No attendance actions pending</b><small>Keep capturing final results after each war.</small></div></div>";
  for (const w of wars.filter((w2) => WarTracker.warTiming(w2).phase === "in-progress")) {
    const pending = (w.participants || []).filter((p) => Number.isInteger(p.attacksUsed) && p.attacksUsed < w.attacksPerMember);
    if (pending.length) actions += `<div class="action-note">${icon("swords")}<div><b>${pending.length} players still have attacks</b><small>${esc(w.kind)} vs ${esc(w.opponent?.name || "Opponent")} · saved war snapshot.</small></div></div>`;
  }
  const latest = [...wars].reverse().find((w) => WarTracker.isClosed(w));
  const finalRegular = wars.filter((w) => w.kind === "Regular" && w.final && w.rosterComplete), missing = wars.filter((w) => ["Regular", "CWL"].includes(w.kind) && WarTracker.isClosed(w) && WarTracker.time(w.endTime) >= WarTracker.time(data.policyStart) && (!w.final || !w.rosterComplete));
  const th = {};
  active.forEach((p) => {
    if (p.townHallLevel) th[p.townHallLevel] = (th[p.townHallLevel] || 0) + 1;
  });
  $("overview-content").innerHTML = `${missing.length ? `<div class="capture-alert"><b>${missing.length} completed war${missing.length === 1 ? "" : "s"} need final player results</b><p>Missing details are kept unknown and create no missed-both penalty.</p><button data-open="history">Review war history ${icon("chevron")}</button></div>` : ""}<div class="split-grid"><div><div class="section-heading"><h2>Needs your attention</h2><span class="muted">${icon("shield")}</span></div>${active.length ? actions : '<p class="small muted">Your first successful refresh will load roster actions.</p>'}<button class="overview-roster-button" data-open="roster">View roster ${icon("chevron")}</button>${latest ? `<button class="panel score-tile full-width" data-open="history" style="margin-top:18px;text-align:left">${icon("swords")}<span><span class="score-label">Latest saved war</span><strong>${formatNumber(latest.stars)} <span class="enemy-score">– ${formatNumber(latest.opponentStars)}</span></strong><small>${esc(latest.opponent?.name || "Opponent")} · ${latest.final && latest.rosterComplete ? "Final player results saved" : "Clan summary / incomplete details"}</small></span><span>${icon("chevron")}</span></button>` : ""}</div><div><div class="panel"><h2>Town Hall distribution</h2>${active.length ? bars(Object.entries(th).sort((a, b) => b[0] - a[0]).map(([n, value]) => ({ label: "TH " + n, value })), "Current roster Town Halls") : '<p class="small muted">Awaiting your roster.</p>'}</div><div class="panel"><h2>Captured history</h2><div class="capture-strip"><div><strong>${finalRegular.length}</strong><span>Regular wars with final counts</span></div><div><strong>${data.raids?.length || 0}</strong><span>Raid weekends</span></div><div><strong>${Object.keys(data.profiles || {}).length}</strong><span>Player profiles</span></div></div><p class="clan-description">${esc(clan.description || "Your clan description will appear after the first refresh.")}</p><div class="meta"><span>Level ${formatNumber(clan.clanLevel)}</span><span>${esc(clan.warLeague?.name || "League not loaded")}</span><span>${esc(clan.location?.name || "")}</span></div></div></div></div>`;
  wireExtendedPlayers($("overview-content"));
  wireOpenLinks($("overview"));
}
let trendOptions = { kind: "", limit: "7", player: "", metric: "averageStars" };
let trendPoints = [];
function renderPerformance() {
  trendPoints = WarTracker.trendsFor(data, edits, trendOptions);
  const ids = new Set(trendPoints.map((p) => p.warId));
  const selectedWars = WarTracker.warsFor(data, edits).filter((w) => ids.has(w.id)).map((w) => ({ ...w, participants: (w.participants || []).filter((p) => !trendOptions.player || WarTracker.tag(p.tag) === trendOptions.player) }));
  const stats = WarTracker.performanceFor({ ...data, wars: selectedWars }, {}), shown = rows.filter((p) => stats[p.tag]?.knownAttacks).map((p) => ({ ...p, performance: stats[p.tag] })).sort((a, b) => b.performance.averageStars - a.performance.averageStars || b.performance.knownAttacks - a.performance.knownAttacks);
  const n = shown.reduce((s, p) => s + p.performance.knownAttacks, 0), stars = shown.reduce((s, p) => s + p.performance.stars, 0), triples = shown.reduce((s, p) => s + p.performance.triples, 0), used = trendPoints.reduce((s, p) => s + p.used, 0), allowed = trendPoints.reduce((s, p) => s + p.allowed, 0);
  const destruction = shown.reduce((s, p) => s + p.performance.destruction, 0), dc = shown.reduce((s, p) => s + p.performance.destructionCount, 0);
  const playerOptions = rows.map((p) => `<option value="${esc(p.tag)}" ${p.tag === trendOptions.player ? "selected" : ""}>${esc(p.name)}${p.inClan ? "" : " · departed"}</option>`).join("");
  const rangeOptions = [["7", "Last 7 captured wars"], ["15", "Last 15 captured wars"], ["30", "Last 30 captured wars"], ["all", "All captured wars"]].map(([v, t]) => `<option value="${v}" ${v === trendOptions.limit ? "selected" : ""}>${t}</option>`).join("");
  $("performance").innerHTML = `<div class="trend-controls"><select id="trend-kind" aria-label="War type for performance"><option value="">Regular + CWL</option><option ${trendOptions.kind === "Regular" ? "selected" : ""}>Regular</option><option ${trendOptions.kind === "CWL" ? "selected" : ""}>CWL</option></select><select id="trend-range" aria-label="Performance history range">${rangeOptions}</select><select id="trend-player" aria-label="Player for performance"><option value="">All captured players</option>${playerOptions}</select></div>` + miniCards([["Stars / attack", n ? (stars / n).toFixed(2) : "—", "star"], ["Three-star rate", n ? Math.round(100 * triples / n) + "%" : "—", "stars"], ["Attack use", allowed ? Math.round(100 * used / allowed) + "%" : "—", "swords"], ["Avg destruction", dc ? (destruction / dc).toFixed(1) + "%" : "—", "trophy"]]) + `<div class="panel trend-panel"><h2 id="trend-heading">${trendMetric().label}</h2><p class="small muted">${trendPoints.length} completed war${trendPoints.length === 1 ? "" : "s"} with final player counts.</p><div class="filter-scroll"><button class="chip" data-metric="averageStars" aria-pressed="${trendOptions.metric === "averageStars"}">Stars / attack</button><button class="chip" data-metric="attackUse" aria-pressed="${trendOptions.metric === "attackUse"}">Attack use</button><button class="chip" data-metric="tripleRate" aria-pressed="${trendOptions.metric === "tripleRate"}">Three-star rate</button></div><div id="trend-chart"></div><div id="chart-inspect" class="chart-inspect" aria-live="polite"></div><details class="notice"><summary>View exact captured values</summary><div class="table-scroll chart-data-table"><table><thead><tr><th>War ended</th><th>Opponent</th><th class="num">Stars / attack</th><th class="num">Attack use</th><th class="num">Triples</th></tr></thead><tbody>${trendPoints.map((p) => `<tr><td>${shortDate(p.endTime)}</td><td>${esc(p.opponent)}</td><td class="num">${p.averageStars === null ? "—" : p.averageStars.toFixed(2)}</td><td class="num">${p.attackUse === null ? "—" : Math.round(100 * p.attackUse) + "%"}</td><td class="num">${p.tripleRate === null ? "—" : Math.round(100 * p.tripleRate) + "%"}</td></tr>`).join("")}</tbody></table></div></details></div><div class="section-heading"><h2>Top attackers</h2><span class="small muted">Avg stars</span></div>${shown.length ? `<div class="leaderboard">${shown.map((p, i) => `<button class="leaderboard-row" data-extended-player="${esc(p.tag)}"><span class="rank ${i === 1 ? "silver" : i === 2 ? "bronze" : ""}">${i + 1}</span>${avatar(p)}<span><span class="player-name player-name-with-hall">${townHallIcon(p.townHallLevel)}<span>${esc(p.name)}</span></span><span class="player-sub">${p.performance.stars} attack stars · ${p.performance.knownAttacks} known attacks<br>${Math.round(100 * p.performance.tripleRate)}% triples · ${p.performance.averageDestruction === null ? "—" : p.performance.averageDestruction.toFixed(1) + "%"} destruction</span></span><span class="leaderboard-score"><strong>${p.performance.averageStars.toFixed(2)}</strong><small>avg stars</small></span></button>`).join("")}</div>` : emptyPanel("No captured attack stars yet", "Capture final war results to start the leaderboard. Manual attack counts without stars still contribute to attack use.", "star")}<p class="notice">Individual attack stars can overlap on the same base. They can differ from the new stars added to the clan score. History gaps and live wars are excluded.</p>${leaguePanel()}`;
  for (const [id, key] of [["trend-kind", "kind"], ["trend-range", "limit"], ["trend-player", "player"]]) $(id).onchange = () => {
    trendOptions[key] = $(id).value;
    renderPerformance();writeLeadershipRoute(true);
  };
  $("performance").querySelectorAll("[data-metric]").forEach((b) => b.onclick = () => {
    trendOptions.metric = b.dataset.metric;
    renderPerformance();writeLeadershipRoute(true);
  });
  drawTrend();
  wireExtendedPlayers($("performance"));
}
let chartTooltipSequence = 0, chartDismissBound = false;
const chartInspectors = /* @__PURE__ */ new WeakMap();
function wireChartInspection(container, selector, read, inspect, clearInspection = () => {
}) {
  if (!container) return;
  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  tooltip.id = "chart-tooltip-" + ++chartTooltipSequence;
  tooltip.setAttribute("role", "tooltip");
  tooltip.hidden = true;
  container.classList.add("chart-tooltip-host");
  container.appendChild(tooltip);
  let active = null, pinned = null, pointerType = "mouse";
  const hide = () => {
    if (active) active.classList.remove("chart-tip-active");
    container.querySelectorAll(selector).forEach((el) => el.setAttribute("aria-pressed", "false"));
    active = null;
    pinned = null;
    tooltip.hidden = true;
    tooltip.style.display = "none";
    tooltip.replaceChildren();
    clearInspection();
  };
  const show = (el) => {
    if (active === el && !tooltip.hidden) return;
    const entry = read(el);
    if (!entry) return;
    if (active && active !== el) active.classList.remove("chart-tip-active");
    active = el;
    el.classList.add("chart-tip-active");
    tooltip.replaceChildren();
    for (const [tag, text] of [["strong", entry.value], ["span", entry.label], ["span", entry.date], ["small", entry.detail]]) {
      if (!text) continue;
      const item = document.createElement(tag);
      item.textContent = text;
      tooltip.appendChild(item);
    }
    tooltip.hidden = false;
    tooltip.style.display = "block";
    const host = container.getBoundingClientRect(), point = (el.querySelector(".dot") || el).getBoundingClientRect();
    const center = point.left + point.width / 2 - host.left, top = point.top - host.top;
    tooltip.style.left = Math.max(8, Math.min(center - tooltip.offsetWidth / 2, host.width - tooltip.offsetWidth - 8)) + "px";
    tooltip.style.top = (top - tooltip.offsetHeight - 12 >= 8 ? top - tooltip.offsetHeight - 12 : top + point.height + 12) + "px";
    inspect(entry);
  };
  chartInspectors.set(container, { hide, overPoint: (target) => Boolean(target?.closest?.(selector) && container.contains(target)) });
  container.querySelectorAll(selector).forEach((el) => {
    el.setAttribute("aria-describedby", tooltip.id);
    el.setAttribute("aria-pressed", "false");
    el.onpointerenter = (event) => {
      pointerType = event.pointerType || "mouse";
      if (pointerType !== "touch" && pinned && pinned !== el) hide();
      show(el);
    };
    el.onpointermove = (event) => {
      if (event.pointerType !== "touch") show(el);
    };
    el.onpointerleave = (event) => {
      if (event.pointerType !== "touch") hide();
    };
    el.onpointercancel = hide;
    el.onfocus = () => {
      if (!el.matches || el.matches(":focus-visible")) show(el);
    };
    el.onblur = hide;
    const toggle = () => {
      if (pinned === el) {
        hide();
        return;
      }
      container.querySelectorAll(selector).forEach((point) => point.setAttribute("aria-pressed", "false"));
      pinned = el;
      el.setAttribute("aria-pressed", "true");
      show(el);
    };
    el.onclick = (event) => {
      if (pointerType === "touch" || event?.detail === 0) {
        toggle();
        return;
      }
      pinned = null;
      el.setAttribute("aria-pressed", "false");
      show(el);
    };
    el.onkeydown = (event) => {
      if (["Enter", " "].includes(event.key)) {
        event.preventDefault();
        toggle();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        hide();
      }
    };
  });
  WarHavenUI.chartKeys(container, selector);
  container.onpointerleave = (event) => {
    if (event.pointerType !== "touch") hide();
  };
  container.onpointercancel = hide;
  container.onclick = (event) => {
    if (!event.target.closest(selector)) hide();
  };
  if (!chartDismissBound) {
    chartDismissBound = true;
    const dismiss = (event) => document.querySelectorAll(".chart-tooltip-host").forEach((host) => {
      if (!event || !host.contains(event.target)) chartInspectors.get(host)?.hide();
    });
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("pointermove", (event) => {
      if (event.pointerType === "touch") return;
      document.querySelectorAll(".chart-tooltip-host").forEach((host) => {
        const handler = chartInspectors.get(host);
        if (!handler?.overPoint(event.target)) handler?.hide();
      });
    }, true);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) dismiss();
    });
    document.addEventListener("scroll", () => dismiss(), true);
    window.addEventListener("blur", () => dismiss());
    window.addEventListener("resize", () => dismiss());
  }
}
function trendMetric() {
  return { averageStars: { label: "Stars per attack", max: 3, percent: false }, attackUse: { label: "Attack use over time", max: 1, percent: true }, tripleRate: { label: "Three-star rate over time", max: 1, percent: true } }[trendOptions.metric];
}
function drawTrend() {
  const metric = trendMetric(), points = trendPoints.map((p) => ({ at: p.endTime, value: typeof p[trendOptions.metric] === "number" ? p[trendOptions.metric] * (metric.percent ? 100 : 1) : null, detail: p.kind + " · " + p.opponent }));
  $("trend-chart").innerHTML = progressChart(points, metric.label, { percent: metric.percent, step: false, precision: metric.percent ? 1 : 2 });
  WarHavenUI.wire($("trend-chart"));
  $("chart-inspect").textContent = "";
}
function leaguePanel() {
  const groups = data.leagueGroups || {}, season = Object.keys(groups).sort().at(-1), group = groups[season];
  if (!group) return "";
  const standings = new Map((group.clans || []).map((c) => [WarTracker.tag(c.tag), { name: c.name, stars: 0, won: 0, finished: 0 }])), tags = new Set((group.rounds || []).flatMap((r) => r.warTags || []));
  for (const summary of Object.values(data.leagueWarSummaries || {})) {
    if (!tags.has(summary.warTag)) continue;
    for (const [side, enemy] of [[summary.clan, summary.opponent], [summary.opponent, summary.clan]]) {
      const rec = standings.get(WarTracker.tag(side?.tag));
      if (!rec) continue;
      if (typeof side.stars === "number") rec.stars += side.stars;
      if (summary.state === "warEnded") {
        rec.finished++;
        if (side.stars > enemy.stars || side.stars === enemy.stars && side.destructionPercentage > enemy.destructionPercentage) rec.won++;
      }
    }
  }
  return `<div class="panel" style="margin-top:20px"><h2>CWL group · ${esc(season)}</h2><p class="small muted">Saved attack stars exclude league win bonuses. These standings use the captured rounds for this season.</p><div class="table-scroll"><table><thead><tr><th>Clan</th><th class="num">Stars</th><th class="num">Wins</th><th class="num">Completed</th></tr></thead><tbody>${[...standings.values()].sort((a, b) => b.stars - a.stars).map((r) => `<tr><td>${esc(r.name)}</td><td class="num">${r.stars}</td><td class="num">${r.won}</td><td class="num">${r.finished}</td></tr>`).join("")}</tbody></table></div></div>`;
}
function renderCapital() {
  const raids = latestRaids(), clan = data.clanProfile || {}, prior = $("raid-select")?.value, chosen = raids.find((r) => r.id === prior) || raids[0], districts = clan.clanCapital?.districts || [];
  const contributors = rows.filter((p) => p.inClan).sort((a, b) => (b.contributions.capital.total ?? -1) - (a.contributions.capital.total ?? -1) || a.name.localeCompare(b.name)), known = contributors.filter((p) => p.contributions.capital.total !== null), total = known.reduce((s, p) => s + p.contributions.capital.total, 0);
  const contributionRow = (p) => `<button type="button" class="clan-contributor" data-extended-player="${esc(p.tag)}" aria-label="View ${esc(p.name)} clan contributions">${avatar(p)}<span><b class="player-name-with-hall">${townHallIcon(p.townHallLevel)}<span>${esc(p.name)}</span></b><small>${p.contributions.capital.baselineAt ? "Tracked since " + shortDate(p.contributions.capital.baselineAt) : "Capital baseline pending"}</small></span><span><strong>${formatNumber(p.contributions.capital.total)}</strong><small>donated here</small></span>${icon("chevron")}</button>`;
  $("capital").innerHTML = `<div class="panel"><div class="section-heading"><h2>Clan Capital</h2><span class="pill">Hall ${clan.clanCapital?.capitalHallLevel ?? "—"}</span></div>${districts.length ? `<details class="capital-districts"><summary>Capital districts · ${districts.length}</summary><div class="district-grid">${districts.map((d) => `<div class="district">${icon("castle")}<b>${esc(d.name)}</b><span>Hall ${d.districtHallLevel ?? "—"}</span></div>`).join("")}</div></details>` : '<p class="small muted">Your district levels will appear after a successful clan refresh.</p>'}</div><div class="panel capital-donations"><div class="section-heading"><h2>Capital donated to this clan</h2>${icon("gold")}</div><div class="capital-total">${known.length ? formatNumber(total) : "—"}<small>Observed donations · current members’ current stints</small></div><p class="small muted">Tap a player for clan totals, graphs and promotion credit. Earlier donations before their first saved baseline are unknown.</p>${contributors.slice(0, 5).map(contributionRow).join("")}${contributors.length > 5 ? `<details><summary>All ${contributors.length} current members · ${known.length} with a Capital baseline</summary>${contributors.slice(5).map(contributionRow).join("")}</details>` : ""}${!contributors.length ? '<p class="notice">Your first successful scan will load clan members.</p>' : ""}</div><div class="raid-picker"><label for="raid-select">Raid weekend</label><select id="raid-select">${raids.map((r) => `<option value="${esc(r.id)}" ${r.id === chosen?.id ? "selected" : ""}>${shortDate(r.startTime)} · ${esc(r.state)}</option>`).join("")}</select></div><div id="raid-detail"></div><div class="panel"><h2>Capital Gold looted over time</h2>${raids.length ? bars([...raids].slice(0, 8).reverse().map((r) => ({ label: shortDate(r.startTime), value: r.capitalTotalLoot })), "Captured raid weekend loot") : '<p class="small muted">Available raid reports will appear after a refresh.</p>'}</div>`;
  const draw = () => {
    const raid = raids.find((r) => r.id === $("raid-select").value) || raids[0];
    if (!raid) {
      $("raid-detail").innerHTML = emptyPanel("No raid report yet", "Run the collector to request the available Capital raid weekends.", "castle");
      return;
    }
    const members = [...raid.members || []].sort((a, b) => (b.capitalResourcesLooted || 0) - (a.capitalResourcesLooted || 0)), reported = new Set(members.map((m) => WarTracker.tag(m.tag))), notReported = rows.filter((p) => p.inClan && !reported.has(p.tag));
    $("raid-detail").innerHTML = miniCards([["Capital Gold looted", formatNumber(raid.capitalTotalLoot), "gold"], ["Attacks", formatNumber(raid.totalAttacks), "swords"], ["Raids completed", formatNumber(raid.raidsCompleted), "castle"], ["Rewards", `${formatNumber(raid.offensiveReward)} / ${formatNumber(raid.defensiveReward)}`, "trophy", "Offensive / defensive"]]) + `<div class="section-heading"><h2>Raid contributions</h2><span class="small muted">${esc(raid.state)}</span></div><p class="small muted">${shortDate(raid.startTime)} · ends ${date(raid.endTime)} · tap any player</p>${members.map((m) => {
      const limit = typeof m.attackLimit === "number" && typeof m.bonusAttackLimit === "number" ? m.attackLimit + m.bonusAttackLimit : null, c = rows.find((p) => p.tag === WarTracker.tag(m.tag))?.contributions.capital;
      return `<button type="button" class="panel raid-member full-width" data-extended-player="${esc(WarTracker.tag(m.tag))}" aria-label="View ${esc(m.name)} clan statistics"><span class="contribution-top"><span class="person">${avatar(m)}<span><span class="player-name">${esc(m.name)}</span><span class="tag">${esc(m.tag)}</span></span></span><span class="raid-gold"><strong>${formatNumber(m.capitalResourcesLooted)}</strong><small>raid loot</small></span>${icon("chevron")}</span><span class="contribution-metrics"><span><strong>${formatNumber(m.attacks)} / ${limit ?? "—"}</strong> attacks</span><span><strong>${m.attacks > 0 && typeof m.capitalResourcesLooted === "number" ? Math.round(m.capitalResourcesLooted / m.attacks).toLocaleString() : "—"}</strong> gold / attack</span></span><span class="progress-track"><span class="progress-fill" style="width:${limit ? Math.max(0, Math.min(100, 100 * m.attacks / limit)) : 0}%"></span></span><span class="raid-donated">${icon("gift")} <b>${formatNumber(c?.total)}</b> Capital donated to this clan <small>${c?.baselineAt ? "since " + shortDate(c.baselineAt) : "· baseline pending"}</small></span></button>`;
    }).join("")}<details class="panel notice"><summary>${notReported.length} current members absent from this report</summary><p>${notReported.map((p) => esc(p.name)).join(", ") || "Everyone in the current roster appears."}</p><p>They may have joined later or not taken part. This does not prove inactivity and creates no war penalty.</p></details>`;
    wireExtendedPlayers($("raid-detail"));
  };
  $("raid-select").onchange = draw;
  draw();
  wireExtendedPlayers($("capital"));
}
const donationCount = (v) => Number.isSafeInteger(v) && v >= 0;
function renderDonations() {
  const shown = rows.filter((p) => p.inClan).sort((a, b) => (b.donations || 0) - (a.donations || 0)), known = shown.filter(p => donationCount(p.donations)), total = known.reduce((s, p) => s + p.donations, 0);
  $("donations").innerHTML = WarHavenUI.seasonDonations(shown, {asOf: data.lastSuccessfulSync}) + miniCards([["Season donations", known.length ? (known.length < shown.length ? "≥ " : "") + formatNumber(total) : "—", "gift", known.length < shown.length ? known.length + " / " + shown.length + " members with known counts" : "Current in-game season counters"], ["Current members", shown.length, "users"]]) + `<p class="notice" style="margin-top:0;margin-bottom:18px">In-game season counters from the latest clan roster. Player profiles show the same season totals alongside increases observed since tracking began. Lifetime Capital contributions can include other clans.</p>${shown.map((p) => `<button class="panel donation-card full-width" data-extended-player="${esc(p.tag)}" style="display:block;text-align:left;font-weight:400"><div class="contribution-top"><span class="person">${avatar(p)}<span><span class="player-name player-name-with-hall">${townHallIcon(p.townHallLevel)}<span>${esc(p.name)}</span></span><span class="player-sub">${esc(p.role || "Member")} · war ${esc(p.warPreference || "preference unknown")}</span></span></span>${icon("chevron")}</div><div class="donation-grid"><div><strong class="gold">${formatNumber(p.donations)}</strong><small>Donated this season</small></div><div><strong>${formatNumber(p.donationsReceived)}</strong><small>Received this season</small></div><div><strong>${donationCount(p.donationsReceived) && p.donationsReceived > 0 && donationCount(p.donations) ? (p.donations / p.donationsReceived).toFixed(2) : "—"}</strong><small>Ratio</small></div></div><div class="donation-bottom"><span>Lifetime Capital ${formatNumber(p.capitalContributions)}</span><span>Latest raid ${formatNumber(p.raidLoot)}</span></div></button>`).join("")}${!shown.length ? emptyPanel("No roster yet", "Run the collector to load your clan’s donation counts.", "gift") : ""}`;
  wireExtendedPlayers($("donations"));
  WarHavenUI.wire($("donations"));
}
function renderActivity() {
  const events = [...data.activity || []].reverse(), graphics = { Donations: "gift", Upgrade: "star", Progress: "activity", Joined: "users", Left: "users", Name: "users", Role: "shield" };
  $("activity").innerHTML = `<div class="panel"><h2>Changes between scans</h2><p class="small muted">These are detection times, not exact upgrade, join, leave, or last-online times. The first scan establishes a baseline.</p></div>${events.length ? `<div class="event-list">${events.slice(0, 100).map((e) => `<article class="event-card"><span class="event-icon">${icon(graphics[e.kind] || "activity")}</span><div><b>${esc(e.name)}</b><div class="meta"><span>${esc(e.kind)}</span><span>${date(e.detectedAt)}</span></div><p>${esc(e.message)}</p></div></article>`).join("")}</div>` : emptyPanel("No changes observed yet", "Run another scan to see observed donations, upgrades, and membership changes.", "activity")}`;
}
function renderSyncDetails() {
 const wars=WarTracker.warsFor(data,edits),final=wars.filter(w=>w.final&&w.rosterComplete&&Date.parse(w.endTime)<=WarHavenUI.now());
 $('sync-details').innerHTML=`<div class="section-heading"><h2>Refresh status</h2>${icon('clock')}</div><p class="small">Last successful clan capture<br><b>${data.lastSuccessfulSync?date(data.lastSuccessfulSync):'Not captured yet'}</b></p><p>Clan and recruitment updates run separately in the cloud. You can close the dashboard after an update request is accepted.</p><p>${final.length} wars have complete final captures. Final results are confirmed only after the API-reported war end. A late update is acceptable; an early result stays pending.</p><button id="sync-request-clan" type="button">Update clan data</button><p class="small muted">The existing saved dashboard stays available if an update fails. The owner can review workflow failures, stuck jobs and data freshness in Management → Operations.</p>`;
 $('sync-request-clan').onclick=()=>$('refresh-data').click();
}

function wireExtendedPlayers(element) {
  wireLeagueBadges(element);
  element.querySelectorAll("[data-extended-player]").forEach((b) => b.onclick = () => openPlayer(b.dataset.extendedPlayer));
}
function wireOpenLinks(element) {
  element.querySelectorAll("[data-open]").forEach((b) => b.onclick = () => setTab(b.dataset.open));
}
const playerChartChoices = /* @__PURE__ */ new Map();
function contributionFactors(candidate) {
  const labels = { tenure: "Observed tenure", donations: "Troop donation habits", war: "War reliability", performance: "Attack stars", capital: "Raid participation", capitalDonations: "Capital donated here" };
  return Object.entries(ClanPromotions.weights).map(([key, max]) => `<div class="promotion-factor"><span>${labels[key]}</span><div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, 100 * candidate.points[key] / max)}%"></div></div><b>${candidate.points[key].toFixed(1)} / ${max}</b></div>`).join("");
}
function usageDiagram(label, value, used, allowed) {
  const amount = value === null ? 0 : Math.max(0, Math.min(1, value));
  return `<div class="usage-diagram"><svg viewBox="0 0 100 100" role="img" aria-label="${esc(label)}: ${value === null ? "unknown" : Math.round(100 * amount) + " percent"}"><circle class="usage-track" cx="50" cy="50" r="39"/><circle class="usage-value" cx="50" cy="50" r="39" stroke-dasharray="${(245.044 * amount).toFixed(2)} 245.044" transform="rotate(-90 50 50)"/><text x="50" y="54" text-anchor="middle">${value === null ? "—" : Math.round(100 * amount) + "%"}</text></svg><span><b>${esc(label)}</b><small>${allowed ? used + " / " + allowed + " attacks used" : "No complete attack counts"}</small></span></div>`;
}
function clanPlayerReport(p) {
  const c = p.contributions, h = data.memberHistory?.[p.tag] || {}, candidate = ClanPromotions.evaluate(data, edits).find((v2) => v2.tag === p.tag), v = p.profile || {};
  const seasonCards = p.inClan ? `<div class="section-heading"><h3>In-game donations</h3></div>${miniCards([["Donated this season", donationCount(p.donations) ? formatNumber(p.donations) : "—", "gift"], ["Received this season", donationCount(p.donationsReceived) ? formatNumber(p.donationsReceived) : "—", "gift"]])}<p class="notice contribution-method">Same season counters as the clan Donations tab, saved ${date(data.lastSuccessfulSync)}. These reset each season. Observed donations below count only increases recorded after tracking began.</p>` : "";
  const warReports = WarTracker.warsFor(data, edits).filter((w) => ["Regular", "CWL"].includes(w.kind) && w.final && w.rosterComplete).flatMap((w) => {
    const m = (w.participants || []).find((v2) => WarTracker.tag(v2.tag) === p.tag), max = w.kind === "CWL" ? 1 : 2;
    return m && !WarTracker.isExcused(edits, w, p.tag) && Number.isInteger(m.attacksUsed) && m.attacksUsed >= 0 && m.attacksUsed <= max ? [{ used: m.attacksUsed, allowed: max }] : [];
  }), warUsed = warReports.reduce((s, r) => s + r.used, 0), warAllowed = warReports.reduce((s, r) => s + r.allowed, 0);
  return `<section class="clan-player-report" aria-label="Contributions to this clan">${seasonCards}<div class="clan-contribution-hero"><div class="eyebrow">Contributions to ${esc(data.clanName || "this clan")}</div><h3>Capital Gold donated</h3><strong>${formatNumber(c.capital.total)}</strong><p>${c.capital.baselineAt ? "Observed since " + date(c.capital.baselineAt) : "Awaiting a matched player profile to establish the Capital baseline."}</p><span class="pill">${p.inClan ? "Current clan stint" : "Last tracked clan stint"}</span></div><p class="notice contribution-method">This total counts observed increases while the player is in this clan. Donations before the first baseline are unknown. Raid loot is earned gold; donations are gold spent on clan upgrades.</p>${miniCards([["Observed troop donations", c.donations.since ? formatNumber(c.donations.total) : "—", "gift", c.donations.since ? "Tracked since " + shortDate(c.donations.since) : "Tracking pending"], ["Days observed here", c.days ?? "—", "clock", c.since ? "Current stint since " + shortDate(c.since) : "Join date not available"], ["Saved raid loot", formatNumber(c.raidLoot), "gold", c.raidCount + " completed weekends in this clan"], ["Gold / raid attack", c.goldPerAttack === null ? "—" : formatNumber(Math.round(c.goldPerAttack)), "swords", "Completed reports with known loot and attack counts"]])}${h.pastStints?.length ? `<p class="small muted">Across all recorded stints in this clan: <b>${formatNumber(c.allCapital)}</b> Capital Gold donated. Promotion credit uses the current stint.</p>` : ""}<div class="panel player-chart-panel"><div class="section-heading"><h3>Contribution history</h3>${icon("activity")}</div><div class="player-chart-controls"><select id="player-chart-metric" aria-label="Player chart metric"><option value="capital">Capital donated · cumulative</option><option value="donations">Observed troop donations · cumulative</option><option value="raids">Raid loot per weekend</option><option value="raidUse">Raid attack use</option><option value="warUse">War attack use</option></select><select id="player-chart-range" aria-label="Player chart period"><option value="all">All saved history</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option></select></div><div id="player-contribution-chart"></div></div><div class="usage-diagrams">${usageDiagram("Raid attack use", c.raidUse, c.raidUsed, c.raidAllowed)}${usageDiagram("War attack use", warAllowed ? warUsed / warAllowed : null, warUsed, warAllowed)}</div>${candidate ? `<div class="panel player-promotion"><div class="promotion-top"><span><div class="eyebrow">${esc(candidate.target)} ${candidate.target === "Co-leader" ? "review" : "promotion"}</div><h3>Contribution score</h3><p class="small muted">${candidate.ready ? "Ready for your review" : "Building evidence"}</p></span>${promotionRing(candidate.score)}</div><p class="small">Capital donated here earns <b>${candidate.points.capitalDonations.toFixed(1)} / 10 points</b>. Full credit at 100,000 observed gold in the current stint.</p>${contributionFactors(candidate)}<details class="promotion-details"><summary>Promotion requirements and remaining evidence</summary>${candidate.gaps.length ? `<ul class="promotion-gaps">${candidate.gaps.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : "<p>All saved contribution requirements are met. Review reliability and leadership before changing their role in Clash.</p>"}</details></div>` : `<div class="panel"><h3>Capital contribution credit</h3><p class="small muted">${p.inClan ? "This player already holds a leadership role." : "Departed members are excluded from promotion recommendations."} Capital totals stay saved for their recorded time in this clan.</p></div>`}<details class="profile-section contribution-evidence"><summary>Contribution tracking details</summary><p>Clan presence first observed ${c.since ? date(c.since) : "not yet"}. This is not an exact join date. A departure and return between scans may go undetected.</p><p>Capital baseline ${c.capital.baselineAt ? date(c.capital.baselineAt) : "pending"}; last matched sample ${c.capital.lastAt ? date(c.capital.lastAt) : "pending"}. Repeated scans and imported backups do not add the same evidence twice. Failed profile lookups retain the previous baseline; a fresh profile in another clan breaks continuity.</p><p>Troop totals keep all future observations. Older releases retained only 90 days, so previously discarded data and donations around season resets may be missing. Raid and war charts use saved reports for this clan and can predate the first membership observation. Missing reports stay unknown.</p><p>Lifetime Capital across all clans: ${formatNumber(v.clanCapitalContributions)}. That total does not earn clan donation points.</p></details></section>`;
}
function playerChartPoints(p, metric) {
  const c = p.contributions;
  if (metric === "capital") return c.capital.series.map((v) => ({ at: v.at, value: v.total, detail: v.delta ? "+" + formatNumber(v.delta) + " donated since the preceding matched scan" : "No new donation credited at this observation" }));
  if (metric === "donations") return [...c.donations.since ? [{ at: c.donations.since, value: 0, detail: "Start of retained troop donation evidence" }] : [], ...c.donations.intervals.map((v) => ({ at: v.end, value: v.total, detail: "+" + formatNumber(v.count) + " troops observed between " + shortDate(v.start) + " and " + shortDate(v.end) }))];
  if (metric === "warUse") return WarTracker.warsFor(data, edits).filter((w) => ["Regular", "CWL"].includes(w.kind) && w.final && w.rosterComplete).flatMap((w) => {
    const m = (w.participants || []).find((v) => WarTracker.tag(v.tag) === p.tag), max = w.kind === "CWL" ? 1 : 2;
    return m && Number.isInteger(m.attacksUsed) && m.attacksUsed >= 0 && m.attacksUsed <= max ? [{ at: w.endTime, value: Math.round(1e3 * m.attacksUsed / max) / 10, detail: w.kind + " vs " + (w.opponent?.name || "Opponent") + " · " + m.attacksUsed + "/" + max + " attacks" + (WarTracker.isExcused(edits, w, p.tag) ? " · excused" : "") }] : [];
  });
  return c.raids.filter((r) => r.state === "ended").map((r) => ({ at: r.start, value: metric === "raids" ? r.loot : r.allowed === null || r.used === null ? null : Math.round(1e3 * r.used / r.allowed) / 10, detail: metric === "raids" ? "Capital Gold looted in this clan’s raid weekend" : r.allowed === null ? "Attack limit unavailable" : r.used + "/" + r.allowed + " raid attacks used" }));
}
function wirePlayerContributionCharts(p) {
  const saved = playerChartChoices.get(p.tag) || { metric: "capital", range: "all" };
  $("player-chart-metric").value = saved.metric;
  $("player-chart-range").value = saved.range;
  const draw = () => {
    const metric = $("player-chart-metric").value, range = $("player-chart-range").value, asOf = WarTracker.time(data.lastSuccessfulSync) || Date.now(), all = playerChartPoints(p, metric).filter((v) => WarTracker.time(v.at)).sort((a, b) => WarTracker.time(a.at) - WarTracker.time(b.at));
    let points = all.filter((v) => range === "all" || WarTracker.time(v.at) >= asOf - Number(range) * 864e5);
    const preceding = all.filter((v) => range !== "all" && WarTracker.time(v.at) < asOf - Number(range) * 864e5).at(-1);
    if (preceding) points = [preceding, ...points];
    playerChartChoices.set(p.tag, { metric, range });
    $("player-contribution-chart").innerHTML = progressChart(points, $("player-chart-metric").selectedOptions[0].textContent, { percent: ["raidUse", "warUse"].includes(metric), step: !["raids", "raidUse", "warUse"].includes(metric) });
    WarHavenUI.wire($("player-contribution-chart"));
  };
  $("player-chart-metric").onchange = draw;
  $("player-chart-range").onchange = draw;
  draw();
}
function renderProfile(p) {
  renderUnifiedProfile(p);
}
let roleReviewMode = "promotions", roleReviewFilter = "all";
const pct = (value) => value === null ? "Unknown" : Math.round(100 * value) + "%";
function promotionRing(score) {
  return `<svg class="promotion-ring" viewBox="0 0 76 76" role="img" aria-label="Contribution score ${score} out of 100"><circle class="ring-track" cx="38" cy="38" r="29"/><circle class="ring-value" cx="38" cy="38" r="29" stroke-dasharray="${(score / 100 * 182.212).toFixed(2)} 182.212" transform="rotate(-90 38 38)"/><text x="38" y="37" text-anchor="middle">${score}</text><text class="ring-label" x="38" y="50" text-anchor="middle">/ 100</text></svg>`;
}
function contributionEvidence(candidate) {
  const w = candidate.war, d = candidate.donations, c = candidate.capital, g = candidate.capitalDonations;
  return `<div class="promotion-evidence"><div>${icon("clock")}<span><b>${candidate.days === null ? "Tenure not observed yet" : "At least " + candidate.days + " days observed"}</b><small>${candidate.since ? "In current clan stint since " + shortDate(candidate.since) : "Starts with your next successful scan"}${candidate.role === "Elder" && candidate.roleDays !== null ? " · " + candidate.roleDays + " days as Elder" : ""}</small></span></div><div>${icon("gift")}<span><b>${formatNumber(d.total)} troop donations observed in 30 days</b><small>${d.dates} positive scan date${d.dates === 1 ? "" : "s"} · spanning ${Math.floor(d.span)} days · ${d.weeks} observed weeks</small></span></div><div>${icon("swords")}<span><b>${pct(w.attackUse)} war attack use · ${w.appearances} appearances</b><small>${w.used}/${w.allowed} regular + CWL attacks · ${w.missedBoth} unexcused zero-attack appearances</small></span></div><div>${icon("star")}<span><b>${w.averageStars === null ? "Stars not captured" : w.averageStars.toFixed(2) + " stars per captured attack"}</b><small>${w.knownAttacks} attacks with known stars · ${w.triples} triples · 6 known attacks needed for score points</small></span></div><div>${icon("castle")}<span><b>${c.raids} completed Capital report${c.raids === 1 ? "" : "s"} · ${pct(c.attackUse)} attack use</b><small>${c.used}/${c.allowed} available attacks · ${formatNumber(c.gold)} captured raid loot in 30 days</small></span></div><div>${icon("gold")}<span><b>${formatNumber(g.total)} Capital Gold donated to this clan</b><small>${g.baselineAt ? "Since " + shortDate(g.baselineAt) + " in the current stint" : "Baseline not captured yet"} · ${candidate.points.capitalDonations.toFixed(1)} / 10 promotion points</small></span></div></div>`;
}
function promotionCard(candidate) {
  const breakdown = contributionFactors(candidate);
  return `<article class="panel promotion-card ${candidate.ready ? "promotion-ready" : ""}"><div class="promotion-top"><button class="promotion-person" data-extended-player="${esc(candidate.tag)}">${avatar(candidate)}<span><b>${esc(candidate.name)}</b><small>${esc(candidate.role)} → ${esc(candidate.target)}</small></span></button>${promotionRing(candidate.score)}</div><span class="promotion-label ${candidate.ready ? "ready-label" : ""}">${candidate.ready ? candidate.target === "Co-leader" ? "Co-leader review candidate" : "Elder candidate" : "Building evidence"}</span>${contributionEvidence(candidate)}<details class="promotion-details"><summary>Why this ${candidate.ready ? "player qualifies" : "player is still being observed"}</summary>${candidate.ready ? '<p class="small">All contribution requirements are met in saved data. Confirm attitude, reliability and leadership yourself before changing the role in Clash.</p>' : `<ul class="promotion-gaps">${candidate.gaps.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>`}${breakdown}</details></article>`;
}
function demotionCard(candidate) {
  return `<article class="panel promotion-card ${candidate.ready ? "demotion-review" : ""}"><div class="promotion-top"><button class="promotion-person" data-extended-player="${esc(candidate.tag)}">${avatar(candidate)}<span><b>${esc(candidate.name)}</b><small>${esc(candidate.role)} → ${esc(candidate.target)} if approved</small></span></button></div><span class="promotion-label ${candidate.ready ? "review-label" : ""}">${candidate.ready ? "Sustained concerns: review role" : "No demotion recommendation"}</span><p class="small muted">${candidate.roleDays === null ? "Current role tenure is not recorded yet" : candidate.roleDays + " days observed in this role"}. Donations alone do not trigger demotion.</p><div class="demotion-windows">${candidate.windows.map((w, i) => `<div><h3>${i ? "Recent" : "Previous"} 30 days</h3><p class="small muted">${shortDate(w.start)} – ${shortDate(w.end)}</p><p><b>${pct(w.war.attackUse)}</b> war attack use · ${w.war.appearances} appearances<br><b>${w.war.missedBoth}</b> unexcused zero-attack appearances<br><b>${pct(w.capital.attackUse)}</b> Capital attack use · ${w.capital.raids} completed reports</p></div>`).join("")}</div><details class="promotion-details"><summary>${candidate.ready ? "Review before deciding" : "Evidence and conditions"}</summary>${candidate.ready ? "<p>Both periods show sustained missed war and raid attacks. Check circumstances, approved exceptions and leadership before demoting one level in Clash. Existing kick flags still need a separate membership decision.</p>" : `<ul class="promotion-gaps">${candidate.gaps.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>`}</details></article>`;
}
function roleCriteria() {
  return `<details class="panel promotion-method"><summary>Promotion and demotion criteria</summary><p class="small muted">These are your dashboard defaults. Points describe captured contributions, not a probability or a trust rating.</p><div class="table-scroll"><table><thead><tr><th>Promotion requirement</th><th>Member → Elder</th><th>Elder → Co-leader review</th></tr></thead><tbody><tr><td>Observed current clan stint</td><td>14 days</td><td>60 days</td></tr><tr><td>Observed time as Elder</td><td>—</td><td>30 days</td></tr><tr><td>Completed regular/CWL appearances</td><td>3 in 30 days</td><td>8 in 30 days</td></tr><tr><td>Attack use</td><td>At least 90%</td><td>At least 95%</td></tr><tr><td>Donations observed between scans</td><td>200 in 30 days</td><td>1,000 in 30 days</td></tr><tr><td>Donation consistency</td><td>2 scan dates spanning 7 days</td><td>3 scan dates spanning 14 days</td></tr><tr><td>Completed Capital contributions</td><td>Optional score boost</td><td>2 in 30 days, with at least 90% attack use</td></tr><tr><td>Capital Gold donated to this clan</td><td colspan="2">Optional: up to 10 score points; full credit at 100,000 observed gold in the current stint</td></tr><tr><td>Contribution score</td><td>60 / 100</td><td>80 / 100</td></tr></tbody></table></div><p>Both require no unexcused zero-attack appearances in the window, no pending bench/kick or attendance review, and a successful refresh within two days.</p><p class="small">Score: tenure 15 points (full at 30 days), troop donations 25 (15 for up to 1,000 observed donations + 10 for up to 3 observed weeks), war reliability 30 (25 for attack use + 5 for up to 8 appearances), captured stars 10 (with at least 6 known attacks), raid participation 10 (7 for attack use + 3 for up to 3 weekends), and Capital donated to this clan 10 (full at 100,000 observed gold in the current stint). Total: 100 points. War, troop and raid evidence uses 30 days; clan Capital donations accumulate across the current stint. Lifetime Capital from other clans, raid loot and unknown earlier donations earn no donation credit. Missing evidence earns no points.</p><h3>Demotion is much harder</h3><p>At least 60 days observed in the current role, followed by review of two separate 30-day periods. <b>Each period</b> must have at least 4 final war appearances, below 50% attack use, at least 2 unexcused zero-attack appearances, and at least 2 completed raid contributions with below 50% attack use. All conditions must hold with complete results.</p><p>One poor war, low stars, low donations, or being absent from a war/raid roster cannot trigger this review. Elder reviews suggest Member; Co-leader reviews suggest Elder. Leader transfers remain your decision.</p><p class="small muted">Exact join dates, chat help, leadership, respect and trust are not measurable here. Tenure covers presence observed at successful scans; a leave and return between scans may be missed. Donation timestamps are observation windows, and their counts can undercount around season resets. Approved war exceptions are excluded.</p></details>`;
}
function renderPromotions() {
  const demoting = roleReviewMode === "demotions", all = demoting ? ClanPromotions.demotions(data, edits) : ClanPromotions.evaluate(data, edits), shown = all.filter((c) => roleReviewFilter === "all" || (roleReviewFilter === "ready" ? c.ready : !c.ready)), ready = all.filter((c) => c.ready);
  $("promotions").innerHTML = `<div class="segmented role-segments" aria-label="Role review views"><button data-role-view="promotions" aria-selected="${!demoting}">Promotions</button><button data-role-view="demotions" aria-selected="${demoting}">Demotion review</button></div><div class="panel"><div class="section-heading"><h2>${demoting ? "Sustained role concerns" : "Who is earning the next role?"}</h2><span class="gold">${icon("promote")}</span></div><p class="small muted">${demoting ? "Demotion requires sustained concerns in BOTH 30-day periods. Unknown results hold the recommendation." : "Recommendations use recent war, troop and raid contributions, current-stint Capital donations, observed tenure and role history. New scans build the evidence."}</p><div class="capture-strip"><div><strong>${ready.length}</strong><span>${demoting ? "Role reviews" : "Candidates"}</span></div><div><strong>${all.length - ready.length}</strong><span>${demoting ? "No recommendation" : "Building evidence"}</span></div><div><strong>${demoting ? "60" : "30"}</strong><span>Day contribution window</span></div></div><p class="notice">${demoting ? "Review circumstances and leadership before changing roles." : "For Co-leader, confirm leadership and trust personally."} All role changes are made by you in Clash.</p></div><div class="toolbar"><label for="promotion-filter" class="small muted">Show</label><select id="promotion-filter"><option value="all">Everyone being assessed</option><option value="ready">${demoting ? "Demotion reviews" : "Promotion candidates"}</option><option value="watch">${demoting ? "No demotion recommendation" : "Building evidence"}</option></select></div>${shown.length ? `<div class="promotion-grid">${shown.map(demoting ? demotionCard : promotionCard).join("")}</div>` : emptyPanel(demoting ? "No demotion reviews" : "No promotion candidates yet", all.length ? "Try showing everyone being assessed. Each report explains its evidence." : "Run the collector to load current members and roles. Co-leaders and Leaders are excluded from promotion suggestions.", "promote")}${roleCriteria()}`;
  $("promotion-filter").value = roleReviewFilter;
  $("promotion-filter").onchange = () => {
    roleReviewFilter = $("promotion-filter").value;
    renderPromotions();
  };
  $("promotions").querySelectorAll("[data-role-view]").forEach((b) => b.onclick = () => {
    roleReviewMode = b.dataset.roleView;
    roleReviewFilter = "all";
    renderPromotions();
  });
  wireExtendedPlayers($("promotions"));
}
let honorsFilters = { members: "current", category: "", when: "all" }, honorsPage = 0;
function recognitionCard(award) {
  const graphic = { War: "swords", Capital: "castle", Donations: "gift", Ranked: "trophy", "Heroes & equipment": "star", Reliability: "shield" }[award.category] || "stars", player = rows.find((p) => p.tag === award.tag), timing = award.occurredAt ? "Event ended " + date(award.occurredAt) : "First recorded " + date(award.observedAt);
  return `<article class="panel honor-card"><div class="honor-header"><span class="honor-medal">${icon(graphic)}</span><span class="honor-category">${esc(award.category)}</span></div><h3>${esc(award.title)}</h3><button class="honor-player" data-extended-player="${esc(award.tag)}" ${player ? "" : "disabled"}>${avatar({ tag: award.tag, name: award.name })}<span><b>${esc(award.name)}</b><small>${esc(award.tag)}${award.inClan ? "" : " · departed"}</small></span>${player ? icon("chevron") : ""}</button><p class="honor-evidence">${esc(award.detail)}</p><div class="honor-footer"><span>${award.occurredAt ? "Clan result" : "Milestone reached in this clan"}</span><small>${esc(timing)}</small></div><details class="honor-source"><summary>Evidence</summary><p>${esc(award.source)}.</p>${award.previousObservedAt && !award.alreadyReached ? `<p>Observed between ${date(award.previousObservedAt)} and ${date(award.observedAt)}. Exact completion time is not provided.</p>` : ""}<p>The milestone was observed during a recorded stay in this clan. Earlier lifetime progress can count toward the threshold; joining itself never creates an achievement.</p></details></article>`;
}
function renderAchievements() {
  const all = ClanHonors.forData(data, edits), current = all.filter((a) => a.inClan), shown = all.filter((a) => (honorsFilters.members === "all" || a.inClan) && (!honorsFilters.category || a.category === honorsFilters.category) && (honorsFilters.when === "all" || (honorsFilters.when === "captured" ? Boolean(a.occurredAt) : !a.occurredAt)));
  const pageSize = 12, pages = Math.max(1, Math.ceil(shown.length / pageSize));
  honorsPage = Math.min(honorsPage, pages - 1);
  const visible = shown.slice(honorsPage * pageSize, (honorsPage + 1) * pageSize);
  const categories = ["War", "Capital", "Donations", "Ranked", "Game achievement", "Heroes & equipment", "Reliability"];
  $("achievements").innerHTML = `<div class="honor-hero panel"><div class="honor-hero-copy"><div class="eyebrow">Clan recognition</div><h2>Hall of achievements</h2><p>Milestones reached while in this clan, backed by profile comparisons and captured clan results.</p></div><div class="honor-hero-art" aria-hidden="true">${icon("trophy")}</div><div class="capture-strip"><div><strong>${current.length}</strong><span>Current member honors</span></div><div><strong>${new Set(current.map((a) => a.tag)).size}</strong><span>Players recognized</span></div><div><strong>${current.filter((a) => a.occurredAt).length}</strong><span>Captured clan feats</span></div></div></div><div class="honor-controls"><select id="honors-members" aria-label="Members for achievements"><option value="current">Current members</option><option value="all">Include departed members</option></select><select id="honors-category" aria-label="Achievement category"><option value="">All categories</option>${categories.map((c) => `<option>${esc(c)}</option>`).join("")}</select><select id="honors-when" aria-label="Achievement capture type"><option value="all">All clan achievements</option><option value="profile">Lifetime milestones crossed here</option><option value="captured">Captured clan feats</option></select></div>${shown.length ? `<div class="honor-grid">${visible.map(recognitionCard).join("")}</div><div class="honor-pagination"><button id="honors-prev" ${honorsPage === 0 ? "disabled" : ""} aria-label="Previous achievement page">Previous</button><span>Page ${honorsPage + 1} of ${pages}<small>${shown.length} matching honors</small></span><button id="honors-next" ${honorsPage >= pages - 1 ? "disabled" : ""} aria-label="Next achievement page">Next</button></div>` : emptyPanel("Great achievements deserve recognition", all.length ? "No honors match these filters. Try another category or include departed members." : "Joining establishes a baseline. New milestones crossed while in the clan and captured war/raid feats will appear here after future updates.", "trophy")}<details class="panel honor-method"><summary>What earns recognition?</summary><p>Selected three-star achievements: War Hero, League Master, Friend in Need, Sharing is Caring, Games Champion, Aggressive Capitalism, Most Valuable Clanmate, Unbreakable, Conqueror, Heroic Heist, Gold Grab and Elixir Escapade. The API must report three stars and a completed target.</p><p>Lifetime milestones: 1,000 / 2,500 / 5,000 / 10,000 / 20,000 war stars; 1 / 5 / 10 / 25 million Capital Gold contributed; 100,000 / 250,000 / 1 million troops donated; 1 / 5 / 10 / 25 / 100 / 500 million and 1 / 5 billion gold or elixir looted. Legend League and API-max heroes (cap 50+) or equipment (cap 27+) are honored too.</p><p>Captured feats: 3 / 5 / 10 consecutive six-star regular-war appearances; 10 / 25 / 50 full-attack regular appearances; 10 / 25 / 50 CWL three-star attacks; 100 / 250 / 500 / 1,000 captured individual war attack stars; and 50,000+ Capital Gold in a completed raid weekend.</p><p>Unknown results never become stars or successes. Missing results break streaks. Known non-selection and approved exceptions are skipped. War awards are recalculated after corrections; lifetime receipts remain as first recorded. Individual attack stars may overlap on the same base.</p><p>Your first profile in a clan stay is a baseline and earns no achievements. A later profile must cross a milestone while you are still in this clan. Earlier lifetime progress counts toward the threshold: 500,000 gold before joining plus 500,000 here can earn the 1 million milestone. Returning starts a new baseline; each milestone is recorded only once per player. Observation dates are not exact completion times. Future game updates may raise a hero or equipment cap.</p></details>`;
  for (const [id, key] of [["honors-members", "members"], ["honors-category", "category"], ["honors-when", "when"]]) {
    $(id).value = honorsFilters[key];
    $(id).onchange = () => {
      honorsFilters[key] = $(id).value;
      honorsPage = 0;
      renderAchievements();
    };
  }
  if ($("honors-prev")) $("honors-prev").onclick = () => {
    honorsPage = Math.max(0, honorsPage - 1);
    renderAchievements();
  };
  if ($("honors-next")) $("honors-next").onclick = () => {
    honorsPage = Math.min(pages - 1, honorsPage + 1);
    renderAchievements();
  };
  wireExtendedPlayers($("achievements"));
}
let progressView = "clan", progressRange = "all", progressMetric = "leaguePoints", progressSearch = "", progressHall = "", progressSort = "hall";
const progressLabels = { leaguePoints: "League points (100 per division)", totalTrophies: "Total member trophies", clanPoints: "Clan points", clanBuilderBasePoints: "Builder Base clan points", clanCapitalPoints: "Capital trophies", members: "Members", averageTownHall: "Average Town Hall", warWins: "Lifetime regular war wins", warWinStreak: "Regular war win streak", seasonDonations: "Current-season donations" };
const progressGroups = { troops: "Troops", spells: "Spells", heroes: "Heroes", pets: "Pets", siege: "Siege machines", equipment: "Owned equipment" };
const progressPercent = (v) => typeof v === "number" && Number.isFinite(v) ? (v >= 100 ? "100" : v.toFixed(1)) + "%" : "Unknown";
function progressRangeOptions() {
  return '<option value="1">Past month</option><option value="3">Past 3 months</option><option value="6">Past 6 months</option><option value="12">Past year</option><option value="all">All saved history</option>';
}
function progressMeter(label, value, extra = "") {
  return WarHavenUI.meter(label, value, extra);
}
function progressChart(points, label, options = {}) {
  return WarHavenUI.chart(label, points, { asOf: data.lastSuccessfulSync, ...options });
}
function wireProgressChart(container) {
  WarHavenUI.wire(container);
}
function setProgressView(view) {
  if (view === "members") {
    setTab("townhalls");
    return;
  }
  progressView = view;
  renderProgress();
  setTab("progress");
}
function renderProgressHome() {
  const clan = data.clanProfile || {}, sample = ClanProgress.merge(data.clanHistory || [], [], false).at(-1) || {};
  $("home-progression").innerHTML = `<div class="panel growth-home"><div class="section-heading"><h2>Growing together</h2><span class="gold">${icon("activity")}</span></div>${miniCards([["League points", formatNumber(sample.leaguePoints), "trophy", sample.leagueKnown == null ? "League history starts with your next scan" : sample.leagueKnown + " / " + sample.leagueMembers + " leagues captured"], ["Clan points", formatNumber(clan.clanPoints), "star"], ["Capital trophies", formatNumber(clan.clanCapitalPoints), "castle"], ["Clan level", formatNumber(clan.clanLevel), "shield"]])}<div class="growth-shortcuts"><button data-progress-view="clan">Clan growth ${icon("chevron")}</button><button data-progress-view="members">Town Hall progress ${icon("chevron")}</button><button data-progress-view="xp">Clan XP ${icon("chevron")}</button></div></div>`;
  $("home-progression").querySelectorAll("[data-progress-view]").forEach((b) => b.onclick = () => setProgressView(b.dataset.progressView));
}
function renderProgress() {
  const node = $("progress");
  if (!node) return;
  node.innerHTML = `<div class="segmented growth-tabs" aria-label="Progress views">${[["clan", "Clan growth"], ["xp", "Clan XP"]].map(([key, label]) => `<button data-progress-view="${key}" aria-selected="${progressView === key}">${label}</button>`).join("")}</div><div id="growth-content"></div>`;
  node.querySelectorAll("[data-progress-view]").forEach((b) => b.onclick = () => {
    progressView = b.dataset.progressView;
    renderProgress();writeLeadershipRoute(true);
  });
  if (progressView === "xp") renderClanXP();
  else renderClanGrowth();
}
function renderClanGrowth() {
  const history = ClanProgress.merge(data.clanHistory || [], [], false), asOf = ClanProgress.time(data.lastSuccessfulSync) || Date.now(), points = ClanProgress.within(history, progressRange, asOf).map((s) => ({ at: s.at, value: s[progressMetric] ?? null, detail: s.members + " members · level " + s.clanLevel + (progressMetric === "leaguePoints" ? " · " + (s.leagueKnown ?? "?") + " / " + (s.leagueMembers ?? s.members) + " leagues captured" : "") })), known = points.filter((v) => ClanProgress.number(v.value)), first = known[0], last = known.at(-1), delta = first && last && known.length > 1 ? last.value - first.value : null;
  $("growth-content").innerHTML = `<div class="panel"><div class="eyebrow">Your clan over time</div><h2>Clan growth</h2><p class="small muted">A new graph point is added when this metric changes. The line continues to the latest successful sync.</p><div class="growth-controls"><label>Metric<select id="growth-metric">${Object.entries(progressLabels).map(([key, label]) => `<option value="${key}">${label}</option>`).join("")}</select></label><label>Period<select id="growth-range">${progressRangeOptions()}</select></label></div>${miniCards([["Latest saved value", last ? formatNumber(last.value) : "—", "trophy"], ["Change in saved period", delta === null ? "—" : (delta > 0 ? "+" : "") + formatNumber(delta), "activity", known.length > 1 ? "Between first and last saved points" : "Needs two observations"]])}<div id="clan-growth-chart">${progressChart(points, progressLabels[progressMetric])}</div><p class="notice">${history.length ? "History available since " + date(history[0].at) + "." : "The first successful scan starts this history."} Earlier months appear as new observations accumulate. Lines connect saved values; unobserved days are unknown.</p></div><details class="panel"><summary>How these totals work</summary><p>League points adds every captured member league, with 100 points per division. Confirmed Unranked is zero; unknown leagues stay unknown. Weekly trophy resets do not reset this score. Promotions, demotions, membership and data coverage can change it; the Weekly report explains each effect.</p><p>Total member trophies adds every current member’s trophies. Clan points is the score returned by the game; it is a different metric.</p><p>Roster changes affect totals and averages. Donations are the current-season counter and may fall when a season resets or a member leaves. Average Town Hall is shown only when every current member has a captured Town Hall.</p><p>Past month, 3 months, 6 months and year use calendar periods ending at the last successful scan. The change tile compares available observations inside that period.</p></details>`;
  $("growth-metric").value = progressMetric;
  $("growth-range").value = progressRange;
  $("growth-metric").onchange = () => {
    progressMetric = $("growth-metric").value;
    renderClanGrowth();
  };
  $("growth-range").onchange = () => {
    progressRange = $("growth-range").value;
    renderClanGrowth();
  };
  wireProgressChart($("clan-growth-chart"), points);
}
function progressForPlayer(p) {
  const v = data.memberProgress?.[p.tag];
  if (v?.method !== "th-work-v2") return null;
  const profile = data.profiles?.[p.tag] || p.profile;
  if (!ClanProgress.time(profile?.profileCheckedAt)) return null;
  if (p.townHallLevel && v.townHall !== p.townHallLevel) return { ...v, townHall: p.townHallLevel, percent: null, completionPercent: null, groups: {}, issues: [...v.issues || [], "Town Hall changed; refresh this player profile."] };
  if (ClanProgress.time(v.at) !== ClanProgress.time(profile.profileCheckedAt)) return { ...v, percent: null, completionPercent: null, groups: {}, issues: ["Run the collector to calculate progress for the newer imported profile."] };
  return v;
}
function progressStatus(p, v) {
  const profile = data.profiles?.[p.tag] || p.profile;
  if (!ClanProgress.time(profile?.profileCheckedAt)) return "No successful player profile has been saved yet.";
  if (p.townHallLevel && profile.townHallLevel !== p.townHallLevel) return "Town Hall changed; waiting for a matching player profile.";
  if (Number.isFinite(v?.completionPercent)) return "All available army upgrades counted, including every pet.";
  return v?.issues?.[0] || "Saved profile is available; army progress needs recalculation.";
}
function villageForPlayer(p) {
  const v = edits.villageProgress?.[p.tag], th = progressForPlayer(p)?.townHall ?? p.townHallLevel;
  return v && !v.deleted && v.townHall === th ? v : null;
}
function renderTownHallProgress() {
  const current = rows.filter((p) => p.inClan), halls = [...new Set(current.map((p) => p.townHallLevel).filter(Boolean))].sort((a, b) => b - a);
  let shown = current.filter((p) => (!progressSearch || (p.name + " " + p.tag).toLowerCase().includes(progressSearch.toLowerCase())) && (!progressHall || String(p.townHallLevel) === progressHall));
  shown.sort((a, b) => progressSort === "name" ? a.name.localeCompare(b.name) : progressSort === "completion" ? (WarHavenUI.completion(progressForPlayer(b)) ?? -Infinity) - (WarHavenUI.completion(progressForPlayer(a)) ?? -Infinity) : (b.townHallLevel || 0) - (a.townHallLevel || 0) || a.name.localeCompare(b.name));
  $("townhall-content").innerHTML = `<section class="panel"><span class="eyebrow">Every village’s upgrade work</span><h2>Town Hall progress</h2><p>Army completion credits all finished upgrades available at each member’s Town Hall, weighted by standard upgrade time. 100% means every available army upgrade is complete.</p><p class="notice">Open a player for all pet and hero levels, remaining upgrades, the separate current Town Hall work score, and imported building progress. Buildings and equipment are separate from army completion.</p></section><div class="growth-controls member-progress-controls"><label>Find a member<input id="progress-search" type="search" value="${esc(progressSearch)}" placeholder="Name or player tag"></label><label>Town Hall<select id="progress-hall"><option value="">All Town Halls</option>${halls.map((th) => `<option value="${th}">TH ${th}</option>`).join("")}</select></label><label>Sort<select id="progress-sort"><option value="hall">Highest Town Hall</option><option value="completion">Most army completion</option><option value="name">Name</option></select></label></div><p class="small muted growth-results">${shown.length} current members</p><div class="upgrade-members">${shown.map((p) => {
    const v = progressForPlayer(p);
    return `<button class="panel upgrade-member" data-extended-player="${esc(p.tag)}"><div class="upgrade-member-top">${avatar(p)}<span><b class="player-name-with-hall">${townHallIcon(p.townHallLevel)}<span>${esc(p.name)}</span></b><small>TH ${formatNumber(p.townHallLevel)} · ${esc(p.tag)}</small></span><span class="upgrade-big">${progressPercent(WarHavenUI.completion(v))}<small>army completion</small></span></div>${[["laboratory", "Laboratory"], ["heroes", "Heroes"], ["pets", "Pets"]].map(([g, label]) => v?.groups?.[g]?.count === 0 ? `<div class="wh-meter"><div class="between"><span>${label}</span><strong>Not unlocked</strong></div></div>` : progressMeter(label, WarHavenUI.completion(v?.groups?.[g]), v?.groups?.[g] ? formatNumber(v.groups[g].maxed) + " / " + formatNumber(v.groups[g].count) + " maxed · " + formatNumber(v.groups[g].remainingLevels) + " levels left" : "")).join("")}<p class="small muted">${esc(progressStatus(p, v))}</p><p class="small muted">Profile ${(data.profiles?.[p.tag] || p.profile)?.profileCheckedAt ? date((data.profiles?.[p.tag] || p.profile).profileCheckedAt) : "not yet captured"}</p><span class="upgrade-card-link">View upgrade breakdown ${icon("chevron")}</span></button>`;
  }).join("") || '<div class="panel">No members match these filters.</div>'}</div><p class="notice">Catalog: ${esc(data.progressionInfo?.source || "Current bundled game data")}. Equipment is reported separately. These scores measure upgrade work rather than war strength.</p>`;
  $("progress-hall").value = progressHall;
  $("progress-sort").value = progressSort;
  $("progress-search").oninput = () => {
    const input = $("progress-search"), position = input.selectionStart;
    progressSearch = input.value;
    renderTownHallProgress();
    $("progress-search").focus();
    try {
      $("progress-search").setSelectionRange(position, position);
    } catch {
    }
  };
  $("progress-hall").onchange = () => {
    progressHall = $("progress-hall").value;
    renderTownHallProgress();
  };
  $("progress-sort").onchange = () => {
    progressSort = $("progress-sort").value;
    renderTownHallProgress();
  };
  wireExtendedPlayers($("townhall-content"));
}
function renderClanXP() {
  const state = ClanProgress.xpSeries(data, edits), asOf = Math.max(ClanProgress.time(data.lastSuccessfulSync), ...state.checkpoints.map((v) => ClanProgress.time(v.at)), Date.now()), manualPoints = state.checkpoints.map((v) => ({ at: v.at, value: v.total, detail: "Verified checkpoint: level " + v.level + ", " + formatNumber(v.xp) + " / " + formatNumber(ClanProgress.requirement(v.level)) + " XP within level." })), points = ClanProgress.within([...state.levels, ...manualPoints].sort((a, b) => ClanProgress.time(a.at) - ClanProgress.time(b.at)), progressRange, asOf);
  const level = state.level ?? data.clanProfile?.clanLevel, latest = state.latestManual, rewards = ClanProgress.xpRewards(data, latest?.at), required = ClanProgress.requirement(level), within = state.manualCurrent ? latest.xp : null;
  $("growth-content").innerHTML = `<div class="panel"><div class="eyebrow">The road to the next level</div><h2>Clan XP &amp; level milestones</h2><p class="small">Clan levels are captured automatically. Record the XP shown in Clash, or read it from a screenshot, for an exact dated checkpoint. Later scans keep that reading as history; they cannot verify a live XP counter.</p>${miniCards([["Observed clan level", formatNumber(level), "shield"], ["XP at latest verified reading", latest ? formatNumber(latest.xp) : "Not recorded", "star", latest && ClanProgress.requirement(latest.level) ? formatNumber(ClanProgress.requirement(latest.level)) + " needed at level " + latest.level : required === null ? "" : formatNumber(required) + " needed for next level"]])}${latest ? `<p class="small muted">Verified reading ${date(latest.at)} · level ${latest.level}. ${state.manualCurrent ? "No newer scan is recorded." : "Current exact XP is unknown after this reading."}</p>` : ""}${progressMeter(latest ? "Verified progress at level " + latest.level : "Progress to next level", latest && ClanProgress.requirement(latest.level) ? 100 * latest.xp / ClanProgress.requirement(latest.level) : null)}<div class="growth-controls"><label>Period<select id="xp-range">${progressRangeOptions()}</select></label></div><div class="xp-legend"><span><i></i>Exact verified XP checkpoint</span><span><i class="floor"></i>Automatic level floor (at least)</span></div><div id="clan-xp-chart">${progressChart(points, "Cumulative clan XP", { targets: state.targets, xp: true, id: "clan-xp" })}</div><p class="notice">Hollow level markers are minimum cumulative XP, observed on that scan date. Dashed lines mark upcoming levels, with no predicted completion dates. Exact XP is not exposed by the clan profile.</p>${latest && !state.manualCurrent ? `<p class="small muted">Last verified checkpoint: ${date(latest.at)}, level ${latest.level} + ${formatNumber(latest.xp)} XP. A later scan exists, so current exact XP remains unknown.</p>` : ""}</div><div class="xp-target-cards">${state.targets.map((t) => `<div class="panel xp-target-card"><span class="eyebrow">Upcoming milestone</span><h3>Level ${t.level}</h3><strong>${formatNumber(t.value)} XP</strong><p class="small muted">Cumulative threshold${t.remaining !== null ? "<br>" + formatNumber(t.remaining) + " XP from latest current checkpoint" : ""}</p></div>`).join("")}</div><details class="panel" id="xp-entry-details"><summary>Update XP from screenshot or enter a reading</summary><p class="small muted">Open your clan’s level/XP bar. Enter the level and the XP already earned <b>within that level</b>, rather than lifetime XP. Older dated checkpoints can be added too.</p><div class="xp-screenshot-controls"><label>Screenshot of the clan level and XP bar<input id="xp-screenshot" type="file" accept="image/png,image/jpeg,image/webp"></label><button type="button" id="xp-read-screenshot">Read screenshot</button><button type="button" id="xp-cancel-screenshot" hidden>Cancel reading</button><p class="small muted" id="xp-screenshot-status" role="status">Your screenshot stays on this device. Crop to the clan XP bar for the clearest reading.</p><img id="xp-screenshot-preview" class="xp-screenshot-preview" alt="Selected clan XP screenshot" hidden><details id="xp-ocr-details" hidden><summary>Recognized text</summary><pre id="xp-ocr-text" class="raw-data"></pre></details></div><form id="xp-form"><div class="growth-controls"><label>Observed date and time · device time<input id="xp-date" type="datetime-local" required></label><label>Clan level<input id="xp-level" type="number" min="1" max="50" step="1" value="${level <= 50 ? level : 1}" required></label><label>XP within this level<input id="xp-amount" type="number" min="0" step="1" required placeholder="For example, 950"></label></div><p class="small muted" id="xp-limit"></p><p id="xp-error" class="error-text" role="alert"></p><label class="planner-option"><input id="xp-confirm" type="checkbox" required> I checked the level, XP and observation time against Clash.</label><button class="primary" type="submit">Save verified XP checkpoint</button></form></details><details class="panel"><summary>Saved XP checkpoints (${state.checkpoints.length})</summary><div class="xp-records">${state.checkpoints.map((v) => `<div class="xp-record"><span><b>Level ${v.level} · ${formatNumber(v.xp)} XP into level</b><small>${esc(date(v.at))} · ${formatNumber(v.total)} cumulative XP</small></span><button data-remove-xp="${esc(v.id)}" aria-label="Remove XP checkpoint from ${esc(date(v.at))}">Remove</button></div>`).join("") || '<p class="small muted">No verified checkpoints yet.</p>'}</div></details><section class="panel"><h2>Everything that earns Clan XP</h2><div class="xp-sources"><article><h3>Regular Clan Wars</h3><p class="small muted">Defeating enemy war bases, earning the clan’s star milestones, and the win bonus. A base rewards XP once; extra attacks on it do not repeat that reward.</p><p><b>${formatNumber(rewards.regular)} XP captured</b>${latest ? " since your last reading" : " in retained war reports"}</p></article><article><h3>Clan War Leagues</h3><p class="small muted">Each CWL war awards Clan XP similarly to a regular war, from base defeats, star milestones and winning.</p><p><b>${formatNumber(rewards.cwl)} XP captured</b>${latest ? " since your last reading" : " in retained war reports"}</p></article><article><h3>Clan Games</h3><p class="small muted">The reward tiers your clan reaches award Clan XP. The amount depends on the event’s completed tiers.</p><p class="small">Tier XP is not available in the clan API.</p></article><article><h3>Capital Raid Weekends</h3><p class="small muted">Weekly Clan XP is based on your clan’s Capital League. Higher Capital leagues award more XP.</p><p class="small">A league or Raid Medal total alone does not verify the XP credited to your clan.</p></article></div><p class="notice">Captured war XP includes only explicit XP rewards in retained completed reports. Missing reports, Clan Games and Capital XP make this an incomplete breakdown; it is never added to a checkpoint as an exact current total. Troop donations, multiplayer trophies and individual player XP do not directly add Clan XP.</p><details><summary>Captured war rewards (${rewards.rows.length})</summary>${rewards.rows.length ? rewards.rows.map((r) => `<div class="xp-record"><span><b>${esc(r.kind)} · ${esc(r.opponent)}</b><small>${date(r.at)}</small></span><b>+${formatNumber(r.xp)} XP</b></div>`).join("") : '<p class="small muted">No explicit war XP rewards have been captured for this period.</p>'}</details><p class="small"><a class="link" href="https://support.supercell.com/clash-of-clans/en/articles/clan-score-and-xp.html" target="_blank" rel="noopener">War XP</a> · <a class="link" href="https://support.supercell.com/clash-of-clans/en/articles/clan-war-leagues-rewards-2.html" target="_blank" rel="noopener">CWL rewards</a> · <a class="link" href="https://supercell.com/en/games/clashofclans/blog/news/new-in-clan-games" target="_blank" rel="noopener">Clan Games</a> · <a class="link" href="https://supercell.com/en/games/clashofclans/blog/game-updates/new-in-clan-capital/" target="_blank" rel="noopener">Capital leagues</a></p></section><details class="panel"><summary>Level threshold source</summary><p>Thresholds are cumulative, so XP does not reset on this graph when the clan levels up. The form accepts the in-game counter within each level.</p><a class="link" href="https://clashofclans.fandom.com/wiki/Clan_Perks#Clan_XP_Chart" target="_blank" rel="noopener">Clan XP table</a><p class="small muted">Changes use the saving status shown above. Export private backup makes an optional readable copy.</p></details>`;
  $("xp-range").value = progressRange;
  $("xp-range").onchange = () => {
    progressRange = $("xp-range").value;
    renderClanXP();
  };
  wireProgressChart($("clan-xp-chart"), points, "clan-xp");
  const now = /* @__PURE__ */ new Date();
  $("xp-date").value = new Date(now.getTime() - now.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
  const showLimit = () => {
    const n = Number($("xp-level").value), limit = ClanProgress.requirement(n);
    $("xp-limit").textContent = limit === null ? "This level is outside the threshold table." : formatNumber(limit) + " XP needed to reach level " + (n + 1) + ".";
    $("xp-amount").max = limit === null ? "" : String(limit - 1);
  };
  $("xp-level").oninput = showLimit;
  showLimit();
  wireXPScreenshot(showLimit);
  $("xp-form").onsubmit = (e) => {
    e.preventDefault();
    try {
      if (!$("xp-confirm").checked) throw Error("Review the reading and check the confirmation before saving.");
      const v = { at: new Date($("xp-date").value).toISOString(), level: Number($("xp-level").value), xp: Number($("xp-amount").value), source: $("xp-form").dataset.screenshot === "1" ? "screenshot-reviewed" : "manual-reviewed", updatedAt: (/* @__PURE__ */ new Date()).toISOString() };
      if (ClanProgress.time(v.at) > Date.now() + 6e4) throw Error("Choose an observation time in the past or present.");
      ClanProgress.checkpoint(v);
      edits.xpCheckpoints ||= {};
      edits.xpCheckpoints["xp:" + v.at] = v;
      persist();
      renderClanXP();
      toast("XP checkpoint recorded. "+leadershipSaveHint());
    } catch (err) {
      $("xp-error").textContent = err.message;
    }
  };
  $("growth-content").querySelectorAll("[data-remove-xp]").forEach((b) => b.onclick = () => {
    edits.xpCheckpoints[b.dataset.removeXp] = { ...edits.xpCheckpoints[b.dataset.removeXp], deleted: true, updatedAt: (/* @__PURE__ */ new Date()).toISOString() };
    persist();
    renderClanXP();
    toast("Checkpoint removed. "+leadershipSaveHint());
  });
}
let xpOCRScript = null;
function loadXPOCR() {
  if (globalThis.Tesseract?.createWorker) return Promise.resolve(globalThis.Tesseract);
  if (!xpOCRScript) xpOCRScript = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.nonce = window.warHavenScriptNonce || "";
    script.src = "https://cdn.jsdelivr.net/npm/tesseract.js@6.0.1/dist/tesseract.min.js";
    script.crossOrigin = "anonymous";
    script.integrity = "sha384-r1ru3tcf6FhnCFR4B7pIFG+BhFF9LlFtz/P1y4pblWn3AGs9y3lBx5SKLNf4+rED";
    script.onload = () => resolve(globalThis.Tesseract);
    script.onerror = () => {
      script.remove();
      xpOCRScript = null;
      reject(Error("Screenshot reading could not load. You can enter the XP counter below."));
    };
    document.head.appendChild(script);
  });
  return xpOCRScript;
}
function wireXPScreenshot(showLimit) {
  const input = $("xp-screenshot"), button = $("xp-read-screenshot"), status = $("xp-screenshot-status"), preview = $("xp-screenshot-preview"), form = $("xp-form"), cancel = $("xp-cancel-screenshot");
  let previewURL = null, activeWorker = null, cancelled = false;
  cancel.onclick = async () => {
    cancelled = true;
    if (activeWorker) await activeWorker.terminate().catch(() => {
    });
    activeWorker = null;
    button.disabled = false;
    cancel.hidden = true;
    status.textContent = "Screenshot reading cancelled. You can retry or enter the numbers manually.";
  };
  input.onchange = () => {
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
    preview.hidden = true;
    form.dataset.screenshot = "";
    $("xp-confirm").checked = false;
    const file = input.files?.[0];
    if (file && file.size <= 12e6 && /^image\/(png|jpeg|webp)$/.test(file.type)) {
      previewURL = URL.createObjectURL(file);
      preview.src = previewURL;
      preview.hidden = false;
      status.textContent = "Ready to read. Set the observation time to when you took this screenshot.";
    } else status.textContent = "Choose a PNG, JPEG or WebP image under 12 MB.";
  };
  button.onclick = async () => {
    const file = input.files?.[0];
    if (!file || file.size > 12e6 || !/^image\/(png|jpeg|webp)$/.test(file.type)) {
      status.textContent = "Choose a PNG, JPEG or WebP image under 12 MB first.";
      return;
    }
    button.disabled = true;
    cancel.hidden = false;
    cancelled = false;
    let worker;
    try {
      status.textContent = "Preparing screenshot reader…";
      const engine = await loadXPOCR();
      worker = await engine.createWorker("eng", 1, { workerPath: "https://cdn.jsdelivr.net/npm/tesseract.js@6.0.1/dist/worker.min.js", corePath: "https://cdn.jsdelivr.net/npm/tesseract.js-core@6.0.0", logger: (m) => {
        if (status.isConnected && m.status === "recognizing text") status.textContent = "Reading screenshot… " + Math.round((m.progress || 0) * 100) + "%";
      } });
      activeWorker = worker;
      if (cancelled) {
        await worker.terminate();
        return;
      }
      const result = await worker.recognize(file);
      if (cancelled || !form.isConnected) return;
      $("xp-ocr-text").textContent = result.data.text;
      $("xp-ocr-details").hidden = false;
      const reading = ClanProgress.screenshotReading(result.data.text);
      $("xp-level").value = reading.level;
      $("xp-amount").value = reading.xp;
      form.dataset.screenshot = "1";
      $("xp-confirm").checked = false;
      showLimit();
      status.textContent = "Read level " + reading.level + " and " + formatNumber(reading.xp) + " XP. Review both numbers and the observation time, then confirm below.";
    } catch (error) {
      if (status.isConnected && !cancelled) status.textContent = (error.message || "Could not read the image.") + " Retry reading, or enter the numbers manually.";
    } finally {
      if (worker) await worker.terminate().catch(() => {
      });
      activeWorker = null;
      button.disabled = false;
      cancel.hidden = true;
    }
  };
}
function playerProgressReport(p) {
  const v = progressForPlayer(p);
  return `<section class="player-upgrades panel">${WarHavenUI.army(v)}<details class="wh-upgrade-category"><summary>Army completion over time</summary><p class="small muted">Completion history begins with the updated calculation. Earlier signed work scores stay available as a separate metric; a Town Hall change adds new available upgrades.</p><div class="growth-controls"><label>Metric<select id="upgrade-history-metric"><option value="completion">Army completion</option><option value="overall">Current TH work score · signed</option>${[["laboratory", "Laboratory"], ["heroes", "Heroes"], ["pets", "Pets"]].map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select></label><label>Period<select id="upgrade-history-range">${progressRangeOptions()}</select></label></div><div id="upgrade-player-chart"></div></details><details class="wh-upgrade-category"><summary>Buildings, defenses, traps & walls</summary><div id="player-village-import"><p class="small muted">Loading saved village export…</p></div><p class="small muted">Players import village data in My progress on their personal dashboard. A new import confirms completed upgrades.</p></details></section>`;
}
function wirePlayerProgress(p) {
  const chart = $("upgrade-player-chart");
  if (!chart) return;
  $("upgrade-history-range").value = "all";
  const draw = () => {
    const metric = $("upgrade-history-metric").value, range = $("upgrade-history-range").value, history = (data.memberProgressHistory?.[p.tag] || []).filter((s) => s.method === "th-work-v2"), points = ClanProgress.within(history, range, ClanProgress.time(data.lastSuccessfulSync) || Date.now()).map((s) => ({ at: s.at, value: metric === "completion" ? s.completionPercent ?? null : metric === "overall" ? s.percent : s.groups?.[metric]?.completionPercent ?? null, townHall: s.townHall, detail: "TH " + s.townHall + (metric === "overall" ? " work relative to previous TH maximum" : " army completion") }));
    chart.innerHTML = progressChart(points, metric === "overall" ? "Current TH work score" : "Army completion", { percent: true, id: "upgrade-player" });
    wireProgressChart(chart);
  };
  $("upgrade-history-metric").onchange = draw;
  $("upgrade-history-range").onchange = draw;
  draw();
  const target = $("player-village-import");
  memberFeatureRequest("village-import", { read: true, playerTag: p.tag }).then((r) => {
    if (target?.isConnected) {
      target.innerHTML = WarHavenUI.village(r.villageImport);
      WarHavenUI.timers(target);
    }
  }).catch((e) => {
    if (target?.isConnected) target.textContent = e.message;
  });
}
let weeklyReportKey = "", weeklyMemberFilter = "all";
let lineupOptions = { mode: "Regular", size: "max", balance: "representative", includeUnknown: false }, lineupSelection = null, lineupLoaded = "", lineupBaseCommitId = null;
const profileTabs = /* @__PURE__ */ new Map();
const signedNumber = (v) => v === null || v === void 0 ? "Unknown" : (v > 0 ? "+" : "") + formatNumber(v);
function latestLeagueSample() {
  return Leadership.mergeHistory(data.leagueHistory || []).at(-1);
}
function currentLeague(p) {
  return latestLeagueSample()?.members?.find((m) => WarTracker.tag(m.tag) === p.tag)?.league || { known: false, points: null, name: "League not captured" };
}
function renderWeeklyHome() {
  const report = Leadership.reports({ ...data, edits })[0], sample = report?.current;
  $("weekly-home").innerHTML = `<div class="panel weekly-home-panel"><div class="section-heading"><h2>This week in ${esc(data.clanName || "your clan")}</h2><span class="gold">${icon("table")}</span></div>${sample ? `<div class="weekly-highlight"><strong>${formatNumber(sample.points)}</strong><span>league points<small>${sample.known} / ${sample.count} member leagues captured</small></span><b class="${report.change?.delta < 0 ? "negative" : "positive"}">${report.change ? signedNumber(report.change.delta) : "Baseline"}</b></div><p class="small muted">${report.change ? `${report.change.up} members moved up · ${report.change.down} moved down · ${report.change.joined.length} joined · ${report.change.departed.length} departed` : "Future scans build league and roster comparisons."}</p>` : '<p class="small muted">Run the tracker to capture the first league-points report.</p>'}<div class="growth-shortcuts"><button data-open="weekly">Weekly report ${icon("chevron")}</button><button data-open="planner">Plan the next war ${icon("chevron")}</button></div></div>`;
  wireOpenLinks($("weekly-home"));
}
function renderWeeklyReports() {
  const reports = Leadership.reports({ ...data, edits }), report = reports.find((r) => r.key === weeklyReportKey) || reports[0];
  if (report) weeklyReportKey = report.key;
  const node = $("weekly");
  if (!report) {
    node.innerHTML = emptyPanel("Your first weekly report starts here", "Run the tracker to capture leagues. Later scans add changes, roster effects, war results and raid participation.", "table");
    return;
  }
  const c = report.change, s = report.current, unknown = s.count - s.known, changed = c?.existing.filter((p) => p.delta !== null && p.delta !== 0) || [], start = new Date(report.key), end = new Date(WarTracker.time(report.key) + 6 * 864e5), range = start.toLocaleDateString(void 0, { month: "short", day: "numeric", timeZone: "UTC" }) + " – " + end.toLocaleDateString(void 0, { month: "short", day: "numeric", timeZone: "UTC" });
  const families = /* @__PURE__ */ new Map();
  for (const l of report.distribution) {
    const name = l.name.replace(/ League.*$/, "");
    families.set(name, (families.get(name) || 0) + l.count);
  }
  const playerMap = new Map(rows.map((p) => [p.tag, p])), memberRows = s.members.filter((p) => weeklyMemberFilter === "all" || (weeklyMemberFilter === "unknown" ? !p.league?.known : c?.existing.some((x) => x.tag === p.tag && x.delta !== null && x.delta !== 0))).sort((a, b) => a.name.localeCompare(b.name));
  node.innerHTML = `<div class="panel"><div class="section-heading"><div><div class="eyebrow">Weekly leadership report</div><h2>${esc(range)}</h2></div><span class="pill">${report.closed ? "Week ended" : "In progress"}</span></div><label class="small muted">Report week<select id="weekly-picker" class="full-width">${reports.map((r) => `<option value="${esc(r.key)}">Week of ${esc(new Date(r.key).toLocaleDateString(void 0, { month: "short", day: "numeric", timeZone: "UTC" }))}${r.closed ? "" : " · in progress"}</option>`).join("")}</select></label><p class="notice">Latest observation ${date(s.at)}. ${report.baseline ? "Changes compare with " + date(report.baseline.at) + "." : "This is the first baseline; no earlier change is assumed."}${report.gapWeeks ? " " + report.gapWeeks + " week(s) have no saved report." : ""}</p>${miniCards([["League points", formatNumber(s.points), "trophy", `${s.known} / ${s.count} leagues known`], ["Change in known points", c ? signedNumber(c.delta) : "—", "activity"], ["League promotions / demotions", c ? c.up + " / " + c.down : "—", "stars", "Members present in both observations"], ["Current members", s.count, "users"]])}${unknown ? `<p class="warning">${unknown} league${unknown === 1 ? " is" : "s are"} unknown. The point total covers captured leagues only; unknown leagues are not scored as zero.</p>` : ""}</div><div class="split-grid"><div class="panel"><h2>League distribution</h2>${[...families].map(([name, count]) => `<div class="league-distribution"><span><b>${esc(name)}</b></span><strong>${count}</strong></div>`).join("")}<details class="division-details"><summary>View each division</summary><div>${report.distribution.map((l) => `<div class="league-distribution"><span><b>${esc(l.name)}</b><small>${l.points === null ? "Unknown" : formatNumber(l.points) + " points per member"}</small></span><strong>${l.count}</strong></div>`).join("")}</div></details></div><div class="panel"><h2>Where the change came from</h2>${c ? `<div class="score-equation"><div><span>Existing members (${c.comparable} comparable)</span><b>${signedNumber(c.existingChange)}</b></div><div><span>Members joining (${c.joined.length})</span><b>${signedNumber(c.joinPoints)}</b></div><div><span>Members departing (${c.departed.length})</span><b>${signedNumber(c.leavePoints)}</b></div><div><span>League data becoming known / unavailable</span><b>${signedNumber(c.coverage)}</b></div><div class="score-total"><span>Total observed change</span><b>${signedNumber(c.delta)}</b></div></div><p class="notice">Existing means present in both endpoint rosters. This separates league progress from membership changes. Arrivals and departures between scans may be missed.</p>` : '<p class="small muted">A second saved observation is needed to explain changes.</p>'}</div></div><div class="panel"><h2>War &amp; raid capture</h2>${miniCards([["Regular / CWL wars ended", report.wars.length, "swords"], ["Captured war attack use", report.allowed ? Math.round(100 * report.used / report.allowed) + "%" : "—", "shield", report.used + " / " + report.allowed + " attacks with final counts"], ["Completed raid reports", report.raids.length, "castle"], ["Raid Gold looted", report.raids.length ? formatNumber(report.raids.reduce((n, r) => n + (r.capitalTotalLoot || 0), 0)) : "—", "gold"]])}<p class="notice">Events are grouped by end time in this report week. Only final, complete player results count toward attack use. Missing events are not assumed to be zero.</p></div><div class="panel"><div class="section-heading"><h2>Member leagues</h2><button id="weekly-export">${icon("download")}Export report</button></div><select id="weekly-member-filter" aria-label="Weekly member filter"><option value="all">All members at this observation</option><option value="changed">League changed</option><option value="unknown">League not captured</option></select><div class="table-scroll"><table><thead><tr><th>Player</th><th>League</th><th class="num">Points</th><th class="num">Change</th></tr></thead><tbody>${memberRows.map((p) => {
    const prior = c?.existing.find((v) => v.tag === p.tag), joined = c?.joined.some((v) => v.tag === p.tag);
    return `<tr><td>${playerMap.has(p.tag) ? `<button class="table-player" data-extended-player="${esc(p.tag)}">${esc(p.name)}</button>` : esc(p.name)}<small class="chart-observation-detail">TH ${formatNumber(p.townHallLevel)}</small></td><td>${esc(p.league?.name || "Unknown")}</td><td class="num">${formatNumber(p.league?.points)}</td><td class="num">${joined ? "Joined" : prior ? signedNumber(prior.delta) : "Baseline"}</td></tr>`;
  }).join("") || '<tr><td colspan="4">No members match this filter.</td></tr>'}</tbody></table></div></div>${c?.departed.length ? `<details class="panel"><summary>Members no longer in the endpoint roster (${c.departed.length})</summary>${c.departed.map((p) => `<p>${esc(p.name)} · ${esc(p.league?.name || "Unknown")} · ${formatNumber(p.league?.points)} prior points</p>`).join("")}</details>` : ""}<details class="panel"><summary>League points and report timing</summary><p>Each ranked division is worth 100 points: Skeleton 1 = 100, Skeleton 2 = 200, and so on through Legend I = 3,600. Confirmed Unranked = 0. Unknown leagues remain unknown.</p><p>These are your dashboard’s league-placement points. They do not reset with weekly trophies. Promotions add points and demotions remove points; this is not an endlessly accumulating XP balance. The game’s official clan score uses its own rules.</p><p>Report weeks run Monday 05:00 UTC through the following Monday 05:00 UTC. A weekly report uses its last saved observation and compares it with the previous saved report, or its first observation while history is starting. Missing days and weeks cannot be reconstructed.</p><div class="league-scale">${(data.leaguePointScale || []).map((l) => `<span>${esc(l.name)}<b>${formatNumber(l.points)}</b></span>`).join("")}</div></details>`;
  $("weekly-picker").value = weeklyReportKey;
  $("weekly-picker").onchange = () => {
    weeklyReportKey = $("weekly-picker").value;
    renderWeeklyReports();
  };
  $("weekly-member-filter").value = weeklyMemberFilter;
  $("weekly-member-filter").onchange = () => {
    weeklyMemberFilter = $("weekly-member-filter").value;
    renderWeeklyReports();
  };
  wireExtendedPlayers(node);
  $("weekly-export").onclick = () => {
    const lines = [`${data.clanName} — weekly clan report`, range, `Observed: ${date(s.at)}`, `League points: ${s.points} (${s.known}/${s.count} leagues captured)`, c ? `Change: ${signedNumber(c.delta)}; existing members ${signedNumber(c.existingChange)}, joins ${signedNumber(c.joinPoints)}, departures ${signedNumber(c.leavePoints)}, coverage ${signedNumber(c.coverage)}` : "First baseline", `Captured war attacks: ${report.used}/${report.allowed}`, `Completed raid reports: ${report.raids.length}`, "", ...s.members.map((p) => `${p.name}: ${p.league?.name || "Unknown"} — ${p.league?.points ?? "unknown"} points`)];
    download("weekly_clan_report_" + report.key.slice(0, 10) + ".txt", lines.join("\n"), "text/plain;charset=utf-8");
  };
}
function plannerMembers() {
  return rows.filter((p) => p.inClan).map((p) => ({ ...p, armyPercent: WarHavenUI.completion(progressForPlayer(p)), missedBoth: WarTracker.missedBothRecency(data, edits, p) }));
}
function planner15Only() {
  return /^(Champion|Titan|Legend)/.test(data.clanProfile?.warLeague?.name || "");
}
function renderWarPlanner() {
  const members = plannerMembers(), saved = edits.lineupPlans?.[lineupOptions.mode]?.deleted ? null : edits.lineupPlans?.[lineupOptions.mode], draft=edits.lineupDrafts?.[lineupOptions.mode]?.deleted?null:edits.lineupDrafts?.[lineupOptions.mode];
  if (lineupLoaded !== lineupOptions.mode) {
    lineupLoaded = lineupOptions.mode;
    const source=draft||saved;lineupBaseCommitId=draft?draft.baseCommitId:(saved?.commitId||null);
    if (source) {
      lineupOptions = { ...lineupOptions, ...source.options, mode: lineupOptions.mode };
      lineupSelection = new Set((source.tags || []).filter((t) => members.some((p) => p.tag === t)));
    } else lineupSelection = null;
  }
  const suggestion = Leadership.suggest(members, { ...lineupOptions, cwl15Only: planner15Only() }), target = suggestion.target;
  if (lineupSelection === null) lineupSelection = new Set(suggestion.selected.map((p) => p.tag));
  for (const tag of [...lineupSelection]) if (!members.some((p) => p.tag === tag)) lineupSelection.delete(tag);
  const selected = members.filter((p) => lineupSelection.has(p.tag)), pool = suggestion.pool, warnings = selected.filter((p) => Leadership.eligibility(p, lineupOptions.mode, false)), validSize = suggestion.allowed.includes(selected.length), hallCount = /* @__PURE__ */ new Map();
  for (const p of selected) {
    const th = p.townHallLevel || 0;
    hallCount.set(th, (hallCount.get(th) || 0) + 1);
  }
  const memberCard = (p) => {
    const reason = Leadership.eligibility(p, lineupOptions.mode, false), selected2 = lineupSelection.has(p.tag);
    const checkboxId = 'war-lineup-' + p.tag.slice(1);
    return `<div class="lineup-player ${selected2 ? "selected" : ""} ${p.missedBoth ? "lineup-missed" : ""}"><input id="${esc(checkboxId)}" type="checkbox" data-lineup-player="${esc(p.tag)}" ${selected2 ? "checked" : ""}><label class="lineup-identity" for="${esc(checkboxId)}"><b class="player-name-with-hall" title="${esc(p.name)}">${townHallIcon(p.townHallLevel)}<span>${esc(p.name)}</span></b></label>${p.missedBoth ? `<button type="button" class="lineup-warning" data-attendance-evidence="${esc(p.tag)}" title="${esc(missedBothLabel(p.missedBoth))} · View evidence" aria-label="${esc(p.name)}: ${esc(missedBothLabel(p.missedBoth))}. View evidence"><span class="lineup-warning-symbol" aria-hidden="true">!</span><span class="lineup-warning-text" aria-hidden="true">Both missed · ${p.missedBoth.warsAgo} ${p.missedBoth.warsAgo === 1 ? "war" : "wars"} ago</span><span class="sr-only">${missedBothLabel(p.missedBoth)} · View evidence</span></button>` : ""}<button class="icon-button" data-extended-player="${esc(p.tag)}" aria-label="Open ${esc(p.name)} player report">${icon("chevron")}</button><small class="lineup-availability" title="TH ${formatNumber(p.townHallLevel)} · ${esc(reason || "Opted in · available by saved status")}">TH ${formatNumber(p.townHallLevel)} · ${esc(reason || "Opted in · available by saved status")}</small><div class="lineup-evidence"><span>${p.attackLikelihood?.probability == null ? "No attendance estimate" : Math.round(100 * p.attackLikelihood.probability) + "% chance of at least one attack"}</span><span>${p.performance?.knownAttacks ? `${p.performance.averageStars.toFixed(2)} stars / attack · ${p.performance.knownAttacks} captured` : "Attack quality not yet captured"}</span></div></div>`;
  };
  $("planner").innerHTML = `<div class="panel"><div class="eyebrow">Participation first</div><h2>Plan the next war</h2><p class="small muted">Suggest the largest supported team from available members, then balance Town Halls and use saved attendance and attack performance to choose within each group.</p><div class="growth-controls"><label>War type<select id="planner-mode"><option value="Regular">Regular war</option><option value="CWL">CWL</option></select></label><label>Team size<select id="planner-size"><option value="max">Largest available</option>${suggestion.allowed.map((n) => `<option value="${n}">${n} vs ${n}</option>`).join("")}</select></label><label>Town Hall balance<select id="planner-balance"><option value="representative">Reflect available Town Halls</option><option value="strength">Favor stronger Town Halls</option></select></label></div><label class="planner-option"><input id="planner-unknown" type="checkbox" ${lineupOptions.includeUnknown ? "checked" : ""}>Consider members whose war preference is unknown</label><div class="growth-shortcuts planner-actions"><button class="primary" id="planner-suggest">${icon("users")}Suggest lineup</button><button id="planner-save">Commit lineup</button><button id="planner-export">${icon("download")}Export committed checklist</button></div>${miniCards([["Selected", selected.length + " / " + target, "users"], ["Available by saved status", pool.length, "check"], ["Available reserves", pool.filter((p) => !lineupSelection.has(p.tag)).length, "bench"], ["Availability reviews", warnings.length, "flag"]])}${!target ? '<p class="warning">Not enough available members for a supported war size. Confirm unknown preferences or review exclusions before planning.</p>' : selected.length !== target ? `<p class="warning">${selected.length} selected for a ${target}-player plan. Adjust the checklist until the counts match.</p>` : ""}${warnings.length ? '<p class="warning">Some selections need your override or confirmation. The planner does not change bench/kick rules or war preferences.</p>' : ""}${lineupStatePanel(saved,selected,target)}</div><div class="panel"><h2>Selected Town Halls</h2>${selected.length ? bars([...hallCount].sort((a, b) => b[0] - a[0]).map(([th, value]) => ({ label: th ? "TH " + th : "TH unknown", value })), "Planned Town Hall distribution") : '<p class="small muted">No members selected.</p>'}<p class="notice">${selected.length ? `Average Town Hall: ${(selected.reduce((n, p) => n + (p.townHallLevel || 0), 0) / selected.length).toFixed(1)}. ` : ""}Town Hall balance is a planning aid, not Supercell’s hidden matchmaking weight. Verify availability and war eligibility in Clash.</p></div><div class="section-heading"><h2>Selected participants</h2><span class="small muted">${selected.length}</span></div><div class="lineup-grid">${selected.sort((a, b) => (b.townHallLevel || 0) - (a.townHallLevel || 0) || a.name.localeCompare(b.name)).map(memberCard).join("") || '<p class="small muted">Use Suggest lineup or select members below.</p>'}</div><details class="panel planner-reserves" open><summary>Available reserves (${members.filter((p) => !lineupSelection.has(p.tag) && !Leadership.eligibility(p, lineupOptions.mode, lineupOptions.includeUnknown)).length})</summary><div class="lineup-grid">${members.filter((p) => !lineupSelection.has(p.tag) && !Leadership.eligibility(p, lineupOptions.mode, lineupOptions.includeUnknown)).sort((a, b) => Leadership.priority(b) - Leadership.priority(a)).map(memberCard).join("") || '<p class="small muted">No available reserves.</p>'}</div></details><details class="panel"><summary>Excluded or awaiting confirmation (${members.filter((p) => !lineupSelection.has(p.tag) && Leadership.eligibility(p, lineupOptions.mode, lineupOptions.includeUnknown)).length})</summary><p class="small muted">Selecting one is an explicit leadership override. Their underlying status stays unchanged.</p><div class="lineup-grid">${members.filter((p) => !lineupSelection.has(p.tag) && Leadership.eligibility(p, lineupOptions.mode, lineupOptions.includeUnknown)).map(memberCard).join("")}</div></details><details class="panel"><summary>How suggestions work</summary><p>Regular teams: 5, 10, 15, 20, 25, 30, 40 or 50. CWL uses 15 or 30; Champion and higher are restricted to 15 in this planner. Confirm your league’s current options in-game.</p><p>Automatic selections exclude opted-out members, kick flags, unresolved final results, and regular-war benches in Regular mode. Unknown preferences are excluded unless you choose to consider them. Missing attendance evidence gets a neutral selection priority, not an invented attendance percentage.</p><p>Balanced mode preserves the eligible roster’s Town Hall proportions using whole-player quotas. Within each Town Hall, priority uses recorded attendance (65%), captured stars per attack (20%), and army completion (15%). This is a selection heuristic, not a prediction of winning. Larger participation is prioritized before ranking.</p><p>The missed-both reminder counts completed clan wars since the latest confirmed unexcused 0/2. It clears after five consecutive confirmed appearances with at least one attack, including CWL. Sit-outs and approved excuses do not advance recovery; unknown final results interrupt it. It never prevents selection.</p><p>This checklist does not start a war, enroll a player, or check whether they are already in another clan’s war. You make the final selection in Clash.</p></details>`;
  $("planner-mode").value = lineupOptions.mode;
  $("planner-size").value = String(lineupOptions.size);
  $("planner-balance").value = lineupOptions.balance;
  $("planner-mode").onchange = () => {
    lineupOptions.mode = $("planner-mode").value;
    lineupOptions.size = "max";
    lineupLoaded = "";
    lineupSelection = null;
    renderWarPlanner();saveLineupDraft();
  };
  const adjust = () => {
    lineupOptions = { ...lineupOptions, size: $("planner-size").value, balance: $("planner-balance").value, includeUnknown: $("planner-unknown").checked };
    lineupSelection = null;
    renderWarPlanner();saveLineupDraft();
  };
  $("planner-size").onchange = adjust;
  $("planner-balance").onchange = adjust;
  $("planner-unknown").onchange = adjust;
  $("planner-suggest").onclick = () => {
    lineupSelection = null;
    renderWarPlanner();saveLineupDraft();
  };
  $("planner").querySelectorAll("[data-lineup-player]").forEach((input) => input.onchange = () => {
    if (input.checked) lineupSelection.add(input.dataset.lineupPlayer);
    else lineupSelection.delete(input.dataset.lineupPlayer);
    renderWarPlanner();saveLineupDraft();
  });
  $("planner-save").onclick = () => {
    if (!target) {
      toast("Choose a supported team size with enough available members first.");
      return;
    }
    if (!validSize || selected.length !== target) {
      toast("Choose exactly " + target + " participants, or adjust the team size.");
      return;
    }
    if(lineupBaseCommitId!==(saved?.commitId||null)){toast("The committed lineup changed. Review it before replacing it.");return;}
    edits.lineupPlans ||= {};
    const commitId=crypto.randomUUID();
    edits.lineupPlans[lineupOptions.mode] = { committed:true,commitId,options: { ...lineupOptions,size:String(target) }, tags: [...lineupSelection], updatedAt:new Date().toISOString() };
    lineupBaseCommitId=commitId;saveLineupDraft();
    persist();
    renderWarPlanner();
    toast("Lineup committed. "+leadershipSaveHint());
  };
  $("planner-export").disabled=!saved;
  $("planner-export").onclick=()=>{
    if(!saved){toast('Commit a supported lineup first.');return;}
    const people=saved.tags.map(tag=>rows.find(p=>p.tag===tag)||{tag,name:tag});
    const text=[data.clanName+' — '+lineupOptions.mode+' committed lineup',people.length+' participants · committed '+date(saved.updatedAt),'Recheck availability in Clash before starting a war.','',...people.map(p=>'[ ] '+p.name+' · TH '+(p.townHallLevel||'?')+' · '+p.tag+(Leadership.eligibility(p,lineupOptions.mode,false)?' · REVIEW: '+Leadership.eligibility(p,lineupOptions.mode,false):''))].join('\n');
    download('war_lineup_'+lineupOptions.mode.toLowerCase()+'.txt',text,'text/plain;charset=utf-8');
  };
  $('planner-review-latest')?.addEventListener('click',()=>reviewCommittedLineup(saved));
  $('planner-load-committed')?.addEventListener('click',()=>{if(!confirm('Replace the shared draft with the committed lineup?'))return;lineupOptions={...saved.options};lineupSelection=new Set(saved.tags.filter(tag=>members.some(p=>p.tag===tag)));lineupBaseCommitId=saved.commitId||null;saveLineupDraft();renderWarPlanner();});
  wireExtendedPlayers($("planner"));
}
function missedBothLabel(v) {
  return "Both attacks missed " + v.warsAgo + " " + (v.warsAgo === 1 ? "war" : "wars") + " ago";
}
function renderUnifiedProfile(p) {
  const history = $("player-history");
  if (history) history.remove();
  const missedBoth = WarTracker.missedBothRecency(data, edits, p), v = p.profile || {}, perf = p.performance || {}, league = currentLeague(p), activeTab = profileTabs.get(p.tag) || "war", captured = WarTracker.warsFor(data, edits), live = savedCurrentWars().flatMap((w) => {
    const member = (w.participants || []).find((m) => WarTracker.tag(m.tag) === p.tag);
    return member ? [{ war: w, member }] : [];
  }), cwl = captured.filter((w) => w.kind === "CWL" && w.final && w.rosterComplete && (w.participants || []).some((m) => WarTracker.tag(m.tag) === p.tag));
  $("player-profile").innerHTML = `<div class="profile-identity">${avatar(p)}<span><b>${esc(LeagueAvatars.forPlayer(data, p).role || "Role not captured")} · TH ${formatNumber(p.townHallLevel)}</b><small>${esc(league.name)}${league.known ? " · " + formatNumber(league.points) + " league points" : ""}</small></span>${badge(p.status)}</div><div class="profile-signals">${attackSignals(p)}</div>${missedBoth ? `<p class="lineup-warning" role="status"><b>${missedBothLabel(missedBoth)}</b><br>${missedBoth.recoveryStreak} / 5 consecutive participated wars with at least one attack. The reminder clears at 5; sit-outs and approved excuses do not count.</p>` : ""}<div class="profile-war-summary">${miniCards([["Regular attack use", p.rate === null ? "—" : Math.round(100 * p.rate) + "%", "swords", p.used + " / " + p.allowed + " captured attacks"], ["Stars / attack", validProfileNumber(perf.averageStars) ? perf.averageStars.toFixed(2) : "—", "star", "Regular + CWL captured attacks"], ["Three-star rate", validProfileNumber(perf.tripleRate) ? Math.round(100 * perf.tripleRate) + "%" : "—", "stars"], ["0/2 streak", p.uncertain ? "Unknown" : p.streak, "shield"]])}</div>${live.map(({ war, member }) => `<div class="panel profile-live-war"><div class="eyebrow">${esc(war.kind)} · ${timingBadge(war)}</div><h3>${esc(war.opponent?.name || "Current opponent")}</h3><p><b>${Number.isInteger(member.attacksUsed) ? member.attacksUsed + " / " + war.attacksPerMember : "Unknown"} attacks used</b></p>${warClock(war)}<small class="muted">Last saved war snapshot; rerun the script for updates.</small></div>`).join("")}<nav class="segmented profile-tabs" aria-label="Player report sections">${[["war", "War"], ["contributions", "Contributions"], ["upgrades", "Upgrades"], ["profile", "Profile"]].map(([key, label]) => `<button data-profile-tab="${key}" aria-selected="${activeTab === key}">${label}</button>`).join("")}</nav><section data-profile-panel="war"><div class="section-heading"><h3>Regular war attendance</h3><span class="small muted">${p.played} captured appearances</span></div><div id="unified-attendance"></div><div class="section-heading"><h3>CWL attendance</h3></div>${miniCards([["Captured CWL appearances", cwl.length, "archive"], ["Missed CWL attacks", formatNumber(p.cwlMissed), "flag"], ["Captured CWL attack stars", formatNumber(perf.cwlStars), "star"], ["Regular appearances missing one attack", p.missedOne, "swords"]])}${cwl.length ? cwl.slice(-10).reverse().map((w) => {
    const m = w.participants.find((m2) => WarTracker.tag(m2.tag) === p.tag);
    return `<div class="attendance-row"><span><b>${esc(w.opponent?.name || "Opponent")}</b><small>${date(w.endTime)}</small></span><span class="count">${formatNumber(m.attacksUsed)} / ${formatNumber(w.attacksPerMember || 1)}</span></div>`;
  }).join("") : '<p class="small muted">No final CWL player results captured.</p>'}<p class="notice">Attendance decisions use confirmed results and approved exceptions. Unknown results never become missed attacks. Attack stars can overlap on the same base.</p></section><section data-profile-panel="contributions">${clanPlayerReport(p)}</section><section data-profile-panel="upgrades">${playerProgressReport(p)}</section><section data-profile-panel="profile">${miniCards([["Lifetime war stars", formatNumber(v.warStars), "star"], ["Lifetime Capital donated", formatNumber(v.clanCapitalContributions), "gold", "Across all clans"], ["Current trophies", formatNumber(p.inClan ? p.trophies : v.trophies), "trophy", p.inClan ? "Latest clan roster" : "Last captured profile"], ["Season attack wins", formatNumber(v.attackWins), "swords"]])}<p class="small muted">Profile checked ${date(v.profileCheckedAt)}. Exact last-online times and active building or hero upgrade queues are unavailable.</p>${v.achievements?.length ? `<details class="profile-section"><summary>Game achievements</summary><div class="level-grid">${v.achievements.map((a) => `<div class="level-item"><b>${esc(a.name)}</b><span class="level">${formatNumber(a.value)}</span><small>${formatNumber(a.stars)} stars · target ${formatNumber(a.target)}</small></div>`).join("")}</div></details>` : ""}<details class="profile-section"><summary>All captured profile data</summary><pre class="raw-data">${esc(JSON.stringify(v, null, 2))}</pre></details></section>`;
  if (history) $("unified-attendance").appendChild(history);
  const choose = (key) => {
    profileTabs.set(p.tag, key);
    if(!leadershipRouteApplying)writeLeadershipRoute(true);
    $("player-profile").querySelectorAll("[data-profile-panel]").forEach((s) => s.classList.toggle("hidden", s.dataset.profilePanel !== key));
    $("player-profile").querySelectorAll("[data-profile-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.profileTab === key)));
  };
  $("player-profile").querySelectorAll("[data-profile-tab]").forEach((b) => b.onclick = () => choose(b.dataset.profileTab));
  choose(activeTab);
  wirePlayerProgress(p);
  wirePlayerContributionCharts(p);
  wireLeagueBadges($("player-profile"));
}
function validProfileNumber(v) {
  return typeof v === "number" && Number.isFinite(v);
}

function saveLineupDraft(){edits.lineupDrafts||={};edits.lineupDrafts[lineupOptions.mode]={options:{...lineupOptions},tags:[...lineupSelection],baseCommitId:lineupBaseCommitId,updatedAt:new Date().toISOString()};persist();}
function lineupStatePanel(saved,selected,target){const changed=lineupBaseCommitId!==(saved?.commitId||null);return `<div class="notice"><b>Working draft · ${selected.length} / ${target} selected</b><p>Draft changes are shared separately. Commit lineup confirms a complete team; it never starts a war in Clash.</p>${saved?`<details><summary>Committed lineup · ${saved.tags.length} players · ${date(saved.updatedAt)}</summary><p>${saved.tags.map(tag=>esc(rows.find(p=>p.tag===tag)?.name||tag)).join(', ')}</p><button type="button" id="planner-load-committed">Use committed lineup as draft</button></details>`:'<p>No committed lineup yet.</p>'}${changed?'<p class="warning">Another committed lineup is available. Review it before replacing it.</p><button type="button" id="planner-review-latest">Review committed lineup</button>':''}</div>`;}
function reviewCommittedLineup(saved){const dialog=document.createElement('dialog');dialog.className='panel';dialog.setAttribute('aria-label','Review committed lineup');dialog.innerHTML='<h2>Review the committed lineup</h2><p>'+esc(saved?saved.tags.map(tag=>rows.find(p=>p.tag===tag)?.name||tag).join(', '):'The committed lineup was removed.')+'</p><p>Your draft stays separate. Continuing lets you commit your draft as the next revision after checking availability.</p><button class="primary" id="ack-lineup-review">I reviewed it · keep working on my draft</button><button id="cancel-lineup-review">Cancel</button>';document.body.append(dialog);const close=()=>{dialog.close();dialog.remove();};dialog.querySelector('#cancel-lineup-review').onclick=close;dialog.querySelector('#ack-lineup-review').onclick=()=>{lineupBaseCommitId=saved?.commitId||null;saveLineupDraft();renderWarPlanner();close();};dialog.oncancel=()=>dialog.remove();dialog.showModal();}
function leadershipSaveHint(){return data.sharedActions?.enabled&&window.warHavenSession?.proof?'Check the shared saving status for confirmation.':'Saved on this device. Export a private backup to keep a separate copy.';}
