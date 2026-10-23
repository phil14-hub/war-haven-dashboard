"use strict";
const DashboardPreferences = (() => {
  const defaults = Object.freeze({ weeklyHome: true, growthHome: true, compactRoster: false, clock24: false, countdownSeconds: true, rememberPage: true, checkUpdates: true, lastPage: "overview", theme: "device", timeZone: "auto", units: "metric", dateFormat: "local" });
  function normalize(value) {
    const out = { ...defaults };
    if (value && typeof value === "object") {
      for (const key of Object.keys(defaults)) if (typeof defaults[key] === "boolean" && typeof value[key] === "boolean") out[key] = value[key];
      for (const key of ["theme", "timeZone", "units", "dateFormat"]) if (typeof value[key] === "string") out[key] = value[key];
      if (typeof value.lastPage === "string" && /^[a-z]+$/.test(value.lastPage)) out.lastPage = value.lastPage;
    }
    return out;
  }
  return { defaults, normalize };
})();
const preferencesKey = "war-haven-preferences:v1:" + WarTracker.tag(data.clanTag);
let preferences = { ...DashboardPreferences.defaults }, preferencesStored = true;
try {
  preferences = DashboardPreferences.normalize(JSON.parse(localStorage.getItem(preferencesKey) || "{}"));
} catch {
  preferencesStored = false;
}
function savePreferences(shared = true) {
  try {
    localStorage.setItem(preferencesKey, JSON.stringify(preferences));
    preferencesStored = true;
  } catch {
    preferencesStored = false;
  }
  if (shared && typeof sharedPreferencesLoaded !== "undefined" && sharedPreferencesLoaded) persistSharedPreferences();
}
function applyPreferences() {
  WarHavenUI.apply(preferences);
  $("weekly-home").hidden = !preferences.weeklyHome;
  $("home-progression").hidden = !preferences.growthHome;
  document.body.classList.toggle("compact-roster", preferences.compactRoster);
  document.querySelectorAll("[data-preference]").forEach((input) => input.checked = preferences[input.dataset.preference]);
}
function openSettings() {
  applyPreferences();
  loadSharedPreferences();
  if (!$("settings-dialog").open) $("settings-dialog").showModal();
}
function wirePreferences() {
  document.querySelectorAll("[data-preference]").forEach((input) => input.onchange = () => {
    const key = input.dataset.preference;
    preferences[key] = input.checked;
    if (key === "rememberPage") preferences.lastPage = input.checked ? document.body.dataset.page || "overview" : "overview";
    savePreferences();
    applyPreferences();
    if (key === "clock24") {
      render();
      if ($("player-dialog").open && selectedTag) openPlayer(selectedTag);
    }
    tickWarClocks();
    if (key === "checkUpdates" && preferences.checkUpdates) checkPublishedUpdate();
  });
  $("reset-preferences").onclick = () => {
    preferences = { ...DashboardPreferences.defaults };
    savePreferences();
    applyPreferences();
    render();
    tickWarClocks();
    toast("Display settings reset. Your clan records and notes are unchanged.");
  };
  window.addEventListener("storage", (event) => {
    if (event.key !== preferencesKey) return;
    try {
      preferences = DashboardPreferences.normalize(JSON.parse(event.newValue || "{}"));
      applyPreferences();
      render();
      tickWarClocks();
    } catch {
    }
  });
}
function savedCurrentWars() {
  const captured = WarTracker.time(data.lastSuccessfulSync) || Date.now();
  // Keep a recently elapsed API timer visible during the final-capture retry window.
  // Older incomplete wars stay in History, where attendance gaps remain visible.
  return WarTracker.warsFor(data, edits).filter((w) => !WarTracker.isClosed(w, captured) || !w.final && ["preparation", "inWar"].includes(w.state) && WarTracker.time(w.endTime) >= captured - 6 * 3600000);
}
function timingBadge(w) {
  const timing = WarTracker.warTiming(w);
  return `<span class="pill ${esc(timing.phase)}" data-war-status="${esc(w.id)}" aria-live="polite">${esc(timing.label)}</span>`;
}
function warClock(w) {
  const timing = WarTracker.warTiming(w);
  return `<div class="war-clock" data-war-clock="${esc(w.id)}"><span class="war-clock-label" data-clock-label>${esc(timing.timeLabel)}</span><strong role="timer" aria-live="off" data-clock-value>${esc(WarTracker.countdown(timing.target, WarHavenUI.now(), preferences.countdownSeconds))}</strong><span class="small muted" data-clock-date>${esc(timing.target ? date(timing.target) : timing.phase === "awaiting-update" ? "Refresh clan data to check the timer. Use the in-game timer until it updates." : timing.phase === "ended" ? "Refresh clan data for final scores and attacks." : "Start time was not captured. Refresh clan data to check it.")}</span></div>`;
}
let warPhaseSignature = "";
function tickWarClocks() {
  const now = WarHavenUI.now(), wars = WarTracker.warsFor(data, edits), byId = new Map(wars.map((w) => [w.id, w]));
  const signature = savedCurrentWars().map((w) => w.id + ":" + WarTracker.warTiming(w, now).phase).join("|");
  if (warPhaseSignature && signature !== warPhaseSignature) {
    renderCurrent();
    renderHistory();
    renderOverview();
    if ($("player-dialog").open && selectedTag) openPlayer(selectedTag);
  }
  warPhaseSignature = signature;
  document.querySelectorAll("[data-war-status]").forEach((element) => {
    const war = byId.get(element.dataset.warStatus);
    if (!war) return;
    const timing = WarTracker.warTiming(war, now);
    if (element.textContent !== timing.label) element.textContent = timing.label;
    element.className = "pill " + timing.phase;
  });
  document.querySelectorAll("[data-war-clock]").forEach((element) => {
    const war = byId.get(element.dataset.warClock);
    if (!war) return;
    const timing = WarTracker.warTiming(war, now);
    const value = WarTracker.countdown(timing.target, now, preferences.countdownSeconds);
    if (element.querySelector("[data-clock-value]").textContent !== value) element.querySelector("[data-clock-value]").textContent = value;
    element.querySelector("[data-clock-label]").textContent = timing.timeLabel;
    element.querySelector("[data-clock-date]").textContent = timing.target ? date(timing.target) : timing.phase === "awaiting-update" ? "Refresh clan data to check the timer. Use the in-game timer until it updates." : timing.phase === "ended" ? "Refresh clan data for final scores and attacks." : "Start time was not captured. Refresh clan data to check it.";
  });
}
const updaterUrl = "https://github.com/phil14-hub/war-haven-dashboard/actions/workflows/update-clan.yml";
async function checkPublishedUpdate(options = {}) {
  return DashboardLiveUpdates.check(options);
}
let requestedRefreshKind = "clan";
function openRefresh(kind = "clan") {
  requestedRefreshKind = kind;
  const recruiting = kind === "recruitment";
  $("refresh-title").textContent = recruiting ? "Refresh recruitment" : "Update clan dashboard";
  const workflowLink = $("refresh-dialog").querySelector("[data-legacy-update] a.button");
  if (workflowLink) workflowLink.href = "https://github.com/phil14-hub/war-haven-dashboard/actions/workflows/" + (recruiting ? "update-recruitment.yml" : "update-clan.yml");
  $("refresh-snapshot").textContent = recruiting ? "Recruitment last scanned " + date(recruiterReport.updatedAt) : data.lastSuccessfulSync ? "Clan data last collected " + date(data.lastSuccessfulSync) : "No successful data collection is recorded.";
  $("automated-refresh-status").textContent = data.automaticUpdates?.lastRunAt ? "Last automated collection: " + date(data.automaticUpdates.lastRunAt) + "." : "Automatic collection has not recorded a successful run yet. Complete the one-time GitHub setup to enable it.";
  if (!$("refresh-dialog").open) $("refresh-dialog").showModal();
}
async function publicationStamp() {
  try {
    const response = await fetch(location.href.split("#")[0], { method: "HEAD", cache: "no-store", credentials: "omit" });
    return response.ok ? response.headers.get("etag") || response.headers.get("last-modified") : null;
  } catch {
    return null;
  }
}
function wireWebsiteUpdate() {
  $("website-update-form").onsubmit = (event) => {
    event.preventDefault();
    $("website-update-error").textContent = "Reload and unlock the latest dashboard to restore update access.";
  };
}
function startDashboardControls() {
  wirePreferences();
  wirePasswordChange();
  wireWebsiteUpdate();
  applyPreferences();
  tickWarClocks();
  $("refresh-data").onclick = () => openRefresh("clan");
  $("refresh-recruiter").onclick = () => openRefresh("recruitment");
  $("settings-refresh").onclick = () => {
    $("settings-dialog").close();
    openRefresh();
  };
  $('password-load')?.addEventListener('click',()=>location.reload());
  setInterval(tickWarClocks, 1e3);
  if (preferences.checkUpdates) checkPublishedUpdate();
  setInterval(() => {
    if (preferences.checkUpdates) checkPublishedUpdate();
  }, 3e4);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      tickWarClocks();
      if (preferences.checkUpdates) checkPublishedUpdate();
    }
  });
}
