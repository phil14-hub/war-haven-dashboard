var WarHavenUI = /* @__PURE__ */ (() => {
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  let preferences = {};
  // Anchor countdowns to server time, then advance with the monotonic clock.
  // This also survives changes to the device's date/time while the page is open.
  let serverClock = null, clockRequest = null;
  const now = () => serverClock ? serverClock.time + performance.now() - serverClock.at : Date.now();
  function syncClock() {
    if (clockRequest) return clockRequest;
    clockRequest = (async () => {
      try {
        const started = performance.now();
        const response = await fetch('/members/api/time', {cache:'no-store', credentials:'same-origin', signal:AbortSignal.timeout(5000)});
        if (!response.ok) return false;
        const value = await response.json(), ended = performance.now(), time = Date.parse(value.serverNow);
        if (!Number.isFinite(time) || ended - started > 5000) return false;
        serverClock = {time:time + (ended - started) / 2, at:ended};
        return true;
      } catch { return false; }
      finally { clockRequest = null; }
    })();
    return clockRequest;
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('focus', syncClock);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) syncClock(); });
    window.setInterval(syncClock, 300000);
    syncClock();
  }
  if(typeof document!=='undefined'&&!document.documentElement.dataset.whFocusWired){
    document.documentElement.dataset.whFocusWired='1';
    document.addEventListener('pointerdown',()=>document.documentElement.dataset.whInput='pointer',true);
    document.addEventListener('touchstart',()=>document.documentElement.dataset.whInput='pointer',{capture:true,passive:true});
    document.addEventListener('keydown',event=>{if(['Tab','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))document.documentElement.dataset.whInput='keyboard';},true);
  }
  const number = (v, digits = 2) => Number.isFinite(v) ? v.toLocaleString(void 0, { maximumFractionDigits: digits }) : "Unknown";
  function locale(p) {
    return { mdy: "en-US", dmy: "en-GB", iso: "en-CA" }[p.dateFormat];
  }
  function date(value, p = preferences, short = false) {
    if (value == null || value === "" || !Number.isFinite(typeof value === "number" ? value : Date.parse(value))) return "Not captured";
    const options = { ...p.timeZone && p.timeZone !== "auto" ? { timeZone: p.timeZone } : {}, ...short ? { month: "short", day: "numeric" } : { year: "numeric", month: p.dateFormat === "iso" ? "2-digit" : "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: !p.clock24 } };
    return new Date(value).toLocaleString(locale(p), options);
  }
  function apply(p = {}) {
    preferences = p;
    const mode = p.theme === "device" || !p.theme ? globalThis.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark" : p.theme;
    document.documentElement.dataset.theme = mode;
    document.documentElement.style.colorScheme = mode;
    document.documentElement.dataset.units = p.units || "metric";
    document.querySelector?.('meta[name="theme-color"]')?.setAttribute("content", mode === "light" ? "#f3f5f9" : "#0d1524");
  }
  const percent = (v) => Number.isFinite(v) ? number(v) + "%" : "Unknown";
  function settingsFields(p = {}) {
    const choices = (values, current) => values.map(([v, label]) => `<option value="${v}" ${v === current ? "selected" : ""}>${label}</option>`).join("");
    return `<div class="wh-settings-grid"><label>Appearance<select name="theme">${choices([["device", "Use device setting"], ["dark", "Dark"], ["light", "Light"]], p.theme || "device")}</select></label><label>Units<select name="units">${choices([["metric", "Metric"], ["us", "US customary"]], p.units || "metric")}</select></label><label>Date format<select name="dateFormat">${choices([["local", "Device default"], ["mdy", "Month / day / year"], ["dmy", "Day / month / year"], ["iso", "Year / month / day"]], p.dateFormat || "local")}</select></label><label>Clock<select name="clock24">${choices([["false", "12-hour"], ["true", "24-hour"]], String(Boolean(p.clock24)))}</select></label><label class="wh-wide">Time zone<select name="zoneMode">${choices([["auto", "Automatic · use this device"], ["manual", "Choose a time zone"]], !p.timeZone || p.timeZone === "auto" ? "auto" : "manual")}</select><input name="timeZone" aria-label="Time zone name" list="wh-zones" value="${esc(p.timeZone && p.timeZone !== "auto" ? p.timeZone : Intl.DateTimeFormat().resolvedOptions().timeZone)}" placeholder="America/New_York"><datalist id="wh-zones">${(Intl.supportedValuesOf?.("timeZone") || ["UTC", "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "Europe/London", "Asia/Jakarta"]).map((z) => `<option value="${esc(z)}"></option>`).join("")}</datalist></label></div><p class="small muted">Game resources, levels, and percentages keep their in-game units. Local time zone: ${esc(Intl.DateTimeFormat().resolvedOptions().timeZone)}.</p>`;
  }
  function readSettings(form) {
    const f = new FormData(form), p = { theme: f.get("theme"), units: f.get("units"), dateFormat: f.get("dateFormat"), clock24: f.get("clock24") === "true", timeZone: f.get("zoneMode") === "auto" ? "auto" : String(f.get("timeZone")).trim() };
    if (p.timeZone !== "auto") new Intl.DateTimeFormat("en", { timeZone: p.timeZone });
    return p;
  }
  function chart(label, series, { asOf, percent: pc = false, step = true, targets = [], precision, xp = false, id = "wh-chart-" + Math.random().toString(36).slice(2) } = {}) {
    const sorted = (series || []).filter((p) => Number.isFinite(Date.parse(p.at))).slice().sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
    const points = [];
    for (const p of sorted) if (!points.length || JSON.stringify([p.value, p.lowerBound || false, p.townHall]) !== JSON.stringify([points.at(-1).value, points.at(-1).lowerBound || false, points.at(-1).townHall])) points.push(p);
    const valid = points.filter((p) => Number.isFinite(p.value));
    if (!valid.length) return '<p class="chart-empty">No observations captured for this metric yet.</p>';
    const first = Date.parse(points[0].at), last = Date.parse(points.at(-1).at), end = Math.max(last, Date.parse(asOf) || last), start = first === end ? first - 864e5 : first;
    const min = Math.min(0, ...valid.map((p) => p.value)), max = Math.max(pc ? 100 : 1, ...valid.map((p) => p.value), ...targets.map((p) => p.value)), mobile = globalThis.innerWidth < 600, width = mobile ? 390 : 640, L = mobile ? 65 : 76, R = mobile ? 370 : 603, T = 24, B = 205;
    const digits = precision ?? (pc ? 1 : valid.every(p => Number.isInteger(p.value)) ? 0 : 2);
    const exact = (v) => number(v, digits) + (pc ? "%" : "");
    const x = (at) => L + (Date.parse(at) - start) / (end - start) * (R - L), y = (v) => B - (v - min) / (max - min || 1) * (B - T), fmt = exact;
    let connected = false, path = "", previous;
    for (const p of points) {
      if (!Number.isFinite(p.value) || p.lowerBound && !xp) {
        if(!xp)connected = false;
        continue;
      }
      const xx = x(p.at), yy = y(p.value);
      path += connected ? step && !xp ? " H" + xx + " V" + yy : " L" + xx + " " + yy : " M" + xx + " " + yy;
      connected = true;
      previous = p;
    }
    if (!xp && connected && previous && Date.parse(previous.at) < end) path += " H" + R;
    const latest = valid.at(-1), unit = pc ? "%" : label, axis = (v) => pc ? fmt(v) : Math.abs(v) >= 1e6 ? number(v / 1e6) + "m" : Math.abs(v) >= 1e3 ? number(v / 1e3) + "k" : number(v);
    return `<div class="wh-chart"><div class="wh-chart-caption"><strong>${esc((latest.lowerBound ? "At least " : "") + fmt(latest.value))}</strong><small>${esc(label)}</small></div><svg viewBox="0 0 ${width} 254" role="group" aria-label="${esc(label)}. Dates on the x axis, ${esc(unit)} on the y axis.">${[0, 0.5, 1].map((n) => {
      const v = min + (max - min) * n;
      return `<line x1="${L}" x2="${R}" y1="${y(v)}" y2="${y(v)}" class="wh-grid"/><text x="${L - 10}" y="${y(v) + 4}" text-anchor="end" class="wh-axis">${esc(axis(v))}</text>`;
    }).join("")}${min < 0 ? `<line x1="${L}" x2="${R}" y1="${y(0)}" y2="${y(0)}" class="wh-zero"/>` : ""}${targets.map((p) => `<line x1="${L}" x2="${R}" y1="${y(p.value)}" y2="${y(p.value)}" class="wh-zero"/><text x="${R - 4}" y="${y(p.value) - 7}" text-anchor="end" class="wh-axis">Level ${p.level}</text>`).join("")}<path d="${path}" class="wh-line${xp?' wh-xp-connector':''}"/>${valid.map((p) => {
      const detail = date(p.at) + " · " + (p.lowerBound ? "At least " : "") + exact(p.value) + (p.detail ? " · " + p.detail : "");
      return `<g tabindex="0" role="button" data-wh-inspect="${id}" data-wh-detail="${esc(detail)}" aria-label="${esc(detail)}"><circle cx="${x(p.at)}" cy="${y(p.value)}" r="15" class="wh-hit"/><circle cx="${x(p.at)}" cy="${y(p.value)}" r="${p.lowerBound ? 5 : 4}" class="wh-dot${p.lowerBound ? " wh-floor" : ""}"/></g>`;
    }).join("")}${[0, 0.5, 1].map((n, i) => `<text x="${L + (R - L) * n}" y="238" text-anchor="${i === 0 ? "start" : i === 2 ? "end" : "middle"}" class="wh-axis">${esc(date(new Date(start + (end - start) * n).toISOString(), preferences, true))}</text>`).join("")}</svg>${xp?'<small class="wh-xp-guide">Dashed lines connect recorded markers; daily XP between them is unknown.</small>':''}<p id="${id}" class="wh-inspect" aria-live="polite"></p><div class="wh-chart-tooltip" role="tooltip" hidden></div><small class="wh-chart-help">Tap a point for details. Use arrow keys on a keyboard.</small><small class="muted">Last synced ${esc(date(asOf || points.at(-1).at))} · ${valid.length} value changes</small><details class="wh-data"><summary>View recorded values</summary><div class="table-scroll table-wrap"><table><thead><tr><th>Observed</th><th>${esc(label)}</th><th>Details</th></tr></thead><tbody>${points.map((p) => `<tr><td>${esc(date(p.at))}</td><td>${Number.isFinite(p.value) ? esc((p.lowerBound ? "≥ " : "") + exact(p.value)) : "Unknown"}</td><td>${esc(p.detail || "")}</td></tr>`).join("")}</tbody></table></div></details></div>`;
  }
  function seasonDonations(roster, {asOf, id = 'season-donations-chart'} = {}) {
    const known = p => Number.isInteger(p.donations) && p.donations >= 0;
    const members = [...(roster || [])].sort((a,b) => Number(known(b))-Number(known(a)) || (b.donations || 0)-(a.donations || 0) || String(a.name).localeCompare(String(b.name)));
    if (!members.length) return '<p class="chart-empty">The season chart will appear when the clan roster is available.</p>';
    const captured = members.filter(known), total = captured.reduce((sum,p) => sum+p.donations,0);
    const max = Math.max(1,...captured.map(p=>p.donations));
    const description = p => String(p.name || p.tag)+' ('+p.tag+') · '+(known(p)?number(p.donations,0)+' troops donated this season':'Season donations unknown');
    return `<section class="panel season-donations-panel"><div class="between"><h2>Season donations</h2><small>${members.length} members</small></div><div class="wh-chart" data-chart-start="first"><div class="wh-chart-caption"><strong>${captured.length ? (captured.length<members.length?'≥ ':'')+number(total,0) : 'Unknown'}</strong><small>troops donated this season</small></div><div class="season-donation-scroll" tabindex="0" role="region" aria-label="Season donations for all current members, ranked from highest to lowest"><div class="wh-donation-axis" aria-hidden="true"><span>Player</span><span class="wh-donation-scale"><span>0</span><span>${number(max,0)}</span></span><span>Donated</span></div><ol class="wh-donation-bars">${members.map(p=>`<li><button type="button" class="wh-donation-row" data-wh-inspect="${id}" data-donation-tag="${esc(p.tag)}" data-wh-detail="${esc(description(p))}" aria-label="${esc(description(p))}"><span class="wh-donation-name">${esc(p.name || p.tag)}</span><span class="wh-donation-track" aria-hidden="true"><svg viewBox="0 0 100 8" preserveAspectRatio="none"><rect x="0" y="0" width="${known(p)?100*p.donations/max:0}" height="8" rx="2"/></svg></span><b>${known(p)?number(p.donations,0):'Unknown'}</b></button></li>`).join('')}</ol></div><p id="${id}" class="wh-inspect" aria-live="polite"></p><div class="wh-chart-tooltip" role="tooltip" hidden></div><small class="muted">Updated ${esc(date(asOf))}${captured.length<members.length?' · '+(members.length-captured.length)+' unknown counts excluded':''}</small></div></section>`;
  }
  // One keyboard stop per chart; arrow keys move within its observations.
  function chartKeys(host, selector) {
    const points = [...host.querySelectorAll(selector)];
    if (!points.length) return;
    points.forEach((point, i) => point.setAttribute('tabindex', i === (host.dataset.chartStart === 'first' ? 0 : points.length - 1) ? '0' : '-1'));
    if (host.dataset.chartKeys) return;
    host.dataset.chartKeys = '1';
    const activate = point => {
      host.querySelectorAll(selector).forEach(p => p.setAttribute('tabindex', p === point ? '0' : '-1'));
    };
    host.addEventListener('focusin', event => { if (event.target.matches(selector)) activate(event.target); });
    host.addEventListener('keydown', event => {
      if (!event.target.matches(selector)) return;
      const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'];
      if (!keys.includes(event.key)) return;
      const current = [...host.querySelectorAll(selector)], index = current.indexOf(event.target);
      let next = event.key === 'Home' ? 0 : event.key === 'End' ? current.length - 1 : index + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -1 : 1);
      next = Math.max(0, Math.min(current.length - 1, next));
      event.preventDefault();event.stopPropagation();activate(current[next]);current[next].focus();current[next].scrollIntoView?.({block:'nearest',inline:'nearest'});
    });
  }
  const chartHandlers = new WeakMap();
  let chartDismissBound = false;
  function wire(root = document) {
    root.querySelectorAll('.wh-chart').forEach(host => {
      if (chartHandlers.has(host)) return;
      const points = [...host.querySelectorAll('[data-wh-inspect]')];
      const target = host.querySelector('.wh-inspect'), tip = host.querySelector('.wh-chart-tooltip');
      let pinned = null, active = null;
      const hide = () => {
        points.forEach(point => point.setAttribute('aria-expanded', 'false'));
        if (target) target.textContent = '';
        if (tip) tip.hidden = true;
        active = null;pinned = null;
      };
      const show = point => {
        points.forEach(p => p.setAttribute('aria-expanded', String(p === point)));
        active = point;
        if (target) target.textContent = point.dataset.whDetail;
        if (tip) {
          tip.textContent = point.dataset.whDetail;tip.hidden = false;
          const p = point.getBoundingClientRect(), h = host.getBoundingClientRect();
          tip.style.left = Math.max(8, Math.min(h.width - tip.offsetWidth - 8, p.left - h.left + p.width / 2 - tip.offsetWidth / 2)) + 'px';
          tip.style.top = Math.max(0, p.top - h.top - tip.offsetHeight - 12) + 'px';
        }
      };
      chartHandlers.set(host, {hide});
      points.forEach(point => {
        point.addEventListener('pointerenter', event => {if (event.pointerType !== 'touch') show(point);});
        point.addEventListener('pointerleave', event => {if (event.pointerType !== 'touch' && pinned !== point) hide();});
        point.addEventListener('pointercancel', hide);point.onfocus = () => show(point);point.onblur = hide;
        point.onclick = () => {if (pinned === point) hide();else {pinned = point;show(point);}};
        point.onkeydown = event => {
          if (event.key === 'Enter' || event.key === ' ') {event.preventDefault();pinned = point;show(point);}
          if (event.key === 'Escape') {event.preventDefault();event.stopPropagation();hide();}
        };
      });
      host.addEventListener('pointerleave', event => {if (event.pointerType !== 'touch') hide();});
      host.addEventListener('click', event => {if (!event.target.closest('[data-wh-inspect]')) hide();});
      chartKeys(host, '[data-wh-inspect]');
    });
    if (!chartDismissBound) {
      chartDismissBound = true;
      document.addEventListener('pointerdown', event => {
        // Query live hosts so the document never retains detached charts.
        document.querySelectorAll('.wh-chart').forEach(host => {if (!host.contains(event.target)) chartHandlers.get(host)?.hide();});
      });
    }
  }
  const completion = (a) => Number.isFinite(a?.completionPercent) ? a.completionPercent : a?.method === "owned-equipment-levels" && Number.isFinite(a.percent) ? a.percent : null;
  function meter(label, value, extra = "") {
    const known = Number.isFinite(value);
    return `<div class="wh-meter ${value < 0 ? "wh-behind" : ""}"><div class="between"><span>${esc(label)}</span><strong>${known ? percent(value) : "Unknown"}</strong></div><progress max="100" value="${known ? Math.max(0, Math.min(100, value)) : 0}" aria-label="${esc(label)}" aria-valuetext="${esc(known ? percent(value) : "Unknown")}"></progress>${value < 0 ? "<small>Earlier Town Hall upgrades still need work.</small>" : ""}${extra ? `<small>${esc(extra)}</small>` : ""}</div>`;
  }

  // Same asset paths and IDs as the planner's verified catalog.
  const gameAssets = {"1000000":["Army Camp","https://assets.clashk.ing/buildings/home-village/army_camp/level_{level}.webp","Buildings"],"1000001":["Town Hall","https://assets.clashk.ing/buildings/home-village/town_hall/level_{level}.webp","Buildings"],"1000002":["Elixir Collector","https://assets.clashk.ing/buildings/home-village/elixir_collector/level_{level}.webp","Buildings"],"1000003":["Elixir Storage","https://assets.clashk.ing/buildings/home-village/elixir_storage/level_{level}.webp","Buildings"],"1000004":["Gold Mine","https://assets.clashk.ing/buildings/home-village/gold_mine/level_{level}.webp","Buildings"],"1000005":["Gold Storage","https://assets.clashk.ing/buildings/home-village/gold_storage/level_{level}.webp","Buildings"],"1000006":["Barracks","https://assets.clashk.ing/buildings/home-village/barracks/level_{level}.webp","Buildings"],"1000007":["Laboratory","https://assets.clashk.ing/buildings/home-village/laboratory/level_{level}.webp","Buildings"],"1000008":["Cannon","https://assets.clashk.ing/buildings/home-village/cannon/level_{level}.webp","Defenses"],"1000009":["Archer Tower","https://assets.clashk.ing/buildings/home-village/archer_tower/level_{level}.webp","Defenses"],"1000010":["Wall","https://assets.clashk.ing/buildings/home-village/wall/level_{level}.webp","Walls"],"1000011":["Wizard Tower","https://assets.clashk.ing/buildings/home-village/wizard_tower/level_{level}.webp","Defenses"],"1000012":["Air Defense","https://assets.clashk.ing/buildings/home-village/air_defense/level_{level}.webp","Defenses"],"1000013":["Mortar","https://assets.clashk.ing/buildings/home-village/mortar/level_{level}.webp","Defenses"],"1000014":["Clan Castle","https://assets.clashk.ing/buildings/home-village/clan_castle/level_{level}.webp","Buildings"],"1000015":["Builder's Hut","https://assets.clashk.ing/buildings/home-village/builder's_hut/level_{level}.webp","Buildings"],"1000019":["Hidden Tesla","https://assets.clashk.ing/buildings/home-village/hidden_tesla/level_{level}.webp","Defenses"],"1000020":["Spell Factory","https://assets.clashk.ing/buildings/home-village/spell_factory/level_{level}.webp","Buildings"],"1000021":["X-Bow","https://assets.clashk.ing/buildings/home-village/x-bow/level_{level}.webp","Defenses"],"1000023":["Dark Elixir Drill","https://assets.clashk.ing/buildings/home-village/dark_elixir_drill/level_{level}.webp","Buildings"],"1000024":["Dark Elixir Storage","https://assets.clashk.ing/buildings/home-village/dark_elixir_storage/level_{level}.webp","Buildings"],"1000026":["Dark Barracks","https://assets.clashk.ing/buildings/home-village/dark_barracks/level_{level}.webp","Buildings"],"1000027":["Inferno Tower","https://assets.clashk.ing/buildings/home-village/inferno_tower/level_{level}.webp","Defenses"],"1000028":["Air Sweeper","https://assets.clashk.ing/buildings/home-village/air_sweeper/level_{level}.webp","Defenses"],"1000029":["Dark Spell Factory","https://assets.clashk.ing/buildings/home-village/dark_spell_factory/level_{level}.webp","Buildings"],"1000031":["Eagle Artillery","https://assets.clashk.ing/buildings/home-village/eagle_artillery/level_{level}.webp","Defenses"],"1000032":["Bomb Tower","https://assets.clashk.ing/buildings/home-village/bomb_tower/level_{level}.webp","Defenses"],"1000033":["Wall","https://assets.clashk.ing/buildings/builder-base/wall/level_{level}.webp","Walls"],"1000034":["Builder Hall","https://assets.clashk.ing/buildings/builder-base/builder_hall/level_{level}.webp","Buildings"],"1000035":["Elixir Collector","https://assets.clashk.ing/buildings/builder-base/elixir_collector/level_{level}.webp","Buildings"],"1000036":["Elixir Storage","https://assets.clashk.ing/buildings/builder-base/elixir_storage/level_{level}.webp","Buildings"],"1000037":["Gold Mine","https://assets.clashk.ing/buildings/builder-base/gold_mine/level_{level}.webp","Buildings"],"1000038":["Gold Storage","https://assets.clashk.ing/buildings/builder-base/gold_storage/level_{level}.webp","Buildings"],"1000039":["Clock Tower","https://assets.clashk.ing/buildings/builder-base/clock_tower/level_{level}.webp","Buildings"],"1000040":["Builder Barracks","https://assets.clashk.ing/buildings/builder-base/builder_barracks/level_{level}.webp","Buildings"],"1000041":["Double Cannon","https://assets.clashk.ing/buildings/builder-base/double_cannon/level_{level}.webp","Defenses"],"1000043":["Hidden Tesla","https://assets.clashk.ing/buildings/builder-base/hidden_tesla/level_{level}.webp","Defenses"],"1000044":["Cannon","https://assets.clashk.ing/buildings/builder-base/cannon/level_{level}.webp","Defenses"],"1000045":["Multi Mortar","https://assets.clashk.ing/buildings/builder-base/multi_mortar/level_{level}.webp","Defenses"],"1000046":["Star Laboratory","https://assets.clashk.ing/buildings/builder-base/star_laboratory/level_{level}.webp","Buildings"],"1000048":["Archer Tower","https://assets.clashk.ing/buildings/builder-base/archer_tower/level_{level}.webp","Defenses"],"1000050":["Firecrackers","https://assets.clashk.ing/buildings/builder-base/firecrackers/level_{level}.webp","Defenses"],"1000051":["Guard Post","https://assets.clashk.ing/buildings/builder-base/guard_post/level_{level}.webp","Buildings"],"1000052":["Mega Tesla","https://assets.clashk.ing/buildings/builder-base/mega_tesla/level_{level}.webp","Defenses"],"1000054":["Air Bombs","https://assets.clashk.ing/buildings/builder-base/air_bombs/level_{level}.webp","Defenses"],"1000055":["Crusher","https://assets.clashk.ing/buildings/builder-base/crusher/level_{level}.webp","Defenses"],"1000056":["Roaster","https://assets.clashk.ing/buildings/builder-base/roaster/level_{level}.webp","Defenses"],"1000057":["Giant Cannon","https://assets.clashk.ing/buildings/builder-base/giant_cannon/level_{level}.webp","Defenses"],"1000058":["Gem Mine","https://assets.clashk.ing/buildings/builder-base/gem_mine/level_{level}.webp","Buildings"],"1000059":["Workshop","https://assets.clashk.ing/buildings/home-village/workshop/level_{level}.webp","Buildings"],"1000063":["Lava Launcher","https://assets.clashk.ing/buildings/builder-base/lava_launcher/level_{level}.webp","Defenses"],"1000065":["B.O.B Control","https://assets.clashk.ing/buildings/builder-base/bob_control/level_{level}.webp","Buildings"],"1000067":["Scattershot","https://assets.clashk.ing/buildings/home-village/scattershot/level_{level}.webp","Defenses"],"1000068":["Pet House","https://assets.clashk.ing/buildings/home-village/pet_house/level_{level}.webp","Buildings"],"1000070":["Blacksmith","https://assets.clashk.ing/buildings/home-village/blacksmith/level_{level}.webp","Buildings"],"1000071":["Hero Hall","https://assets.clashk.ing/buildings/home-village/hero_hall/level_{level}.webp","Buildings"],"1000072":["Spell Tower","https://assets.clashk.ing/buildings/home-village/spell_tower/level_{level}.webp","Defenses"],"1000077":["Monolith","https://assets.clashk.ing/buildings/home-village/monolith/level_{level}.webp","Defenses"],"1000078":["O.T.T.O's Outpost","https://assets.clashk.ing/buildings/builder-base/otto's_outpost/level_{level}.webp","Buildings"],"1000079":["Multi-Gear Tower","https://assets.clashk.ing/buildings/home-village/multi-gear_tower/level_{level}.webp","Defenses"],"1000081":["X-Bow","https://assets.clashk.ing/buildings/builder-base/x-bow/level_{level}.webp","Defenses"],"1000082":["Healing Hut","https://assets.clashk.ing/buildings/builder-base/healing_hut/level_{level}.webp","Buildings"],"1000084":["Multi-Archer Tower","https://assets.clashk.ing/buildings/home-village/multi-archer_tower/level_{level}.webp","Defenses"],"1000085":["Ricochet Cannon","https://assets.clashk.ing/buildings/home-village/ricochet_cannon/level_{level}.webp","Defenses"],"1000086":["Revenge Tower","https://assets.clashk.ing/buildings/home-village/revenge_tower/level_{level}.webp","Defenses"],"1000089":["Firespitter","https://assets.clashk.ing/buildings/home-village/firespitter/level_{level}.webp","Defenses"],"1000102":["Super Wizard Tower","https://assets.clashk.ing/buildings/home-village/super_wizard_tower/level_{level}.webp","Defenses"],"12000000":["Bomb","https://assets.clashk.ing/traps/home-village/bomb/level_{level}.webp","Traps"],"12000001":["Spring Trap","https://assets.clashk.ing/traps/home-village/spring_trap/level_{level}.webp","Traps"],"12000005":["Air Bomb","https://assets.clashk.ing/traps/home-village/air_bomb/level_{level}.webp","Traps"],"12000002":["Giant Bomb","https://assets.clashk.ing/traps/home-village/giant_bomb/level_{level}.webp","Traps"],"12000006":["Seeking Air Mine","https://assets.clashk.ing/traps/home-village/seeking_air_mine/level_{level}.webp","Traps"],"12000008":["Skeleton Trap","https://assets.clashk.ing/traps/home-village/skeleton_trap/level_{level}.webp","Traps"],"12000016":["Tornado Trap","https://assets.clashk.ing/traps/home-village/tornado_trap/level_{level}.webp","Traps"],"12000020":["Giga Bomb","https://assets.clashk.ing/traps/home-village/giga_bomb/level_{level}.webp","Traps"],"12000011":["Push Trap","https://assets.clashk.ing/traps/builder-base/push_trap/level_{level}.webp","Traps"],"12000013":["Mine","https://assets.clashk.ing/traps/builder-base/mine/level_{level}.webp","Traps"],"12000010":["Spring Trap","https://assets.clashk.ing/traps/builder-base/spring_trap/level_{level}.webp","Traps"],"12000014":["Mega Mine","https://assets.clashk.ing/traps/builder-base/mega_mine/level_{level}.webp","Traps"],"4000000":["Barbarian","https://assets.clashk.ing/troops/barbarian/icon.webp","Troops"],"4000001":["Archer","https://assets.clashk.ing/troops/archer/icon.webp","Troops"],"4000002":["Goblin","https://assets.clashk.ing/troops/goblin/icon.webp","Troops"],"4000003":["Giant","https://assets.clashk.ing/troops/giant/icon.webp","Troops"],"4000004":["Wall Breaker","https://assets.clashk.ing/troops/wall_breaker/icon.webp","Troops"],"4000005":["Balloon","https://assets.clashk.ing/troops/balloon/icon.webp","Troops"],"4000006":["Wizard","https://assets.clashk.ing/troops/wizard/icon.webp","Troops"],"4000007":["Healer","https://assets.clashk.ing/troops/healer/icon.webp","Troops"],"4000008":["Dragon","https://assets.clashk.ing/troops/dragon/icon.webp","Troops"],"4000009":["P.E.K.K.A","https://assets.clashk.ing/troops/pekka/icon.webp","Troops"],"4000010":["Minion","https://assets.clashk.ing/troops/minion/icon.webp","Troops"],"4000011":["Hog Rider","https://assets.clashk.ing/troops/hog_rider/icon.webp","Troops"],"4000012":["Valkyrie","https://assets.clashk.ing/troops/valkyrie/icon.webp","Troops"],"4000013":["Golem","https://assets.clashk.ing/troops/golem/icon.webp","Troops"],"4000015":["Witch","https://assets.clashk.ing/troops/witch/icon.webp","Troops"],"4000017":["Lava Hound","https://assets.clashk.ing/troops/lava_hound/icon.webp","Troops"],"4000022":["Bowler","https://assets.clashk.ing/troops/bowler/icon.webp","Troops"],"4000023":["Baby Dragon","https://assets.clashk.ing/troops/baby_dragon/icon.webp","Troops"],"4000024":["Miner","https://assets.clashk.ing/troops/miner/icon.webp","Troops"],"4000026":["Super Barbarian","https://assets.clashk.ing/troops/super_barbarian/icon.webp","Troops"],"4000027":["Super Archer","https://assets.clashk.ing/troops/super_archer/icon.webp","Troops"],"4000028":["Super Wall Breaker","https://assets.clashk.ing/troops/super_wall_breaker/icon.webp","Troops"],"4000029":["Super Giant","https://assets.clashk.ing/troops/super_giant/icon.webp","Troops"],"4000030":["Ice Wizard","https://assets.clashk.ing/troops/ice_wizard/icon.webp","Troops"],"4000031":["Raged Barbarian","https://assets.clashk.ing/troops/raged_barbarian/icon.webp","Troops"],"4000032":["Sneaky Archer","https://assets.clashk.ing/troops/sneaky_archer/icon.webp","Troops"],"4000033":["Beta Minion","https://assets.clashk.ing/troops/beta_minion/icon.webp","Troops"],"4000034":["Boxer Giant","https://assets.clashk.ing/troops/boxer_giant/icon.webp","Troops"],"4000035":["Bomber","https://assets.clashk.ing/troops/bomber/icon.webp","Troops"],"4000036":["Power P.E.K.K.A","https://assets.clashk.ing/troops/power_pekka/icon.webp","Troops"],"4000037":["Cannon Cart","https://assets.clashk.ing/troops/cannon_cart/icon.webp","Troops"],"4000038":["Drop Ship","https://assets.clashk.ing/troops/drop_ship/icon.webp","Troops"],"4000041":["Baby Dragon","https://assets.clashk.ing/troops/baby_dragon/icon.webp","Troops"],"4000042":["Night Witch","https://assets.clashk.ing/troops/night_witch/icon.webp","Troops"],"4000045":["Battle Ram","https://assets.clashk.ing/troops/battle_ram/icon.webp","Troops"],"4000047":["Royal Ghost","https://assets.clashk.ing/troops/royal_ghost/icon.webp","Troops"],"4000048":["Pumpkin Barbarian","https://assets.clashk.ing/troops/pumpkin_barbarian/icon.webp","Troops"],"4000050":["Giant Skeleton","https://assets.clashk.ing/troops/giant_skeleton/icon.webp","Troops"],"4000051":["Wall Wrecker","https://assets.clashk.ing/troops/wall_wrecker/icon.webp","Troops"],"4000052":["Battle Blimp","https://assets.clashk.ing/troops/battle_blimp/icon.webp","Troops"],"4000053":["Yeti","https://assets.clashk.ing/troops/yeti/icon.webp","Troops"],"4000055":["Sneaky Goblin","https://assets.clashk.ing/troops/sneaky_goblin/icon.webp","Troops"],"4000056":["Super Miner","https://assets.clashk.ing/troops/super_miner/icon.webp","Troops"],"4000057":["Rocket Balloon","https://assets.clashk.ing/troops/rocket_balloon/icon.webp","Troops"],"4000058":["Ice Golem","https://assets.clashk.ing/troops/ice_golem/icon.webp","Troops"],"4000059":["Electro Dragon","https://assets.clashk.ing/troops/electro_dragon/icon.webp","Troops"],"4000061":["Skeleton Barrel","https://assets.clashk.ing/troops/skeleton_barrel/icon.webp","Troops"],"4000062":["Stone Slammer","https://assets.clashk.ing/troops/stone_slammer/icon.webp","Troops"],"4000063":["Inferno Dragon","https://assets.clashk.ing/troops/inferno_dragon/icon.webp","Troops"],"4000064":["Super Valkyrie","https://assets.clashk.ing/troops/super_valkyrie/icon.webp","Troops"],"4000065":["Dragon Rider","https://assets.clashk.ing/troops/dragon_rider/icon.webp","Troops"],"4000066":["Super Witch","https://assets.clashk.ing/troops/super_witch/icon.webp","Troops"],"4000067":["M.E.C.H.A","https://assets.clashk.ing/troops/mecha/icon.webp","Troops"],"4000070":["Hog Glider","https://assets.clashk.ing/troops/hog_glider/icon.webp","Troops"],"4000072":["Party Wizard","https://assets.clashk.ing/troops/party_wizard/icon.webp","Troops"],"4000075":["Siege Barracks","https://assets.clashk.ing/troops/siege_barracks/icon.webp","Troops"],"4000076":["Ice Hound","https://assets.clashk.ing/troops/ice_hound/icon.webp","Troops"],"4000080":["Super Bowler","https://assets.clashk.ing/troops/super_bowler/icon.webp","Troops"],"4000081":["Super Dragon","https://assets.clashk.ing/troops/super_dragon/icon.webp","Troops"],"4000082":["Headhunter","https://assets.clashk.ing/troops/headhunter/icon.webp","Troops"],"4000083":["Super Wizard","https://assets.clashk.ing/troops/super_wizard/icon.webp","Troops"],"4000084":["Super Minion","https://assets.clashk.ing/troops/super_minion/icon.webp","Troops"],"4000087":["Log Launcher","https://assets.clashk.ing/troops/log_launcher/icon.webp","Troops"],"4000091":["Flame Flinger","https://assets.clashk.ing/troops/flame_flinger/icon.webp","Troops"],"4000092":["Battle Drill","https://assets.clashk.ing/troops/battle_drill/icon.webp","Troops"],"4000094":["Ram Rider","https://assets.clashk.ing/troops/ram_rider/icon.webp","Troops"],"4000095":["Electro Titan","https://assets.clashk.ing/troops/electro_titan/icon.webp","Troops"],"4000097":["Apprentice Warden","https://assets.clashk.ing/troops/apprentice_warden/icon.webp","Troops"],"4000098":["Super Hog Rider","https://assets.clashk.ing/troops/super_hog_rider/icon.webp","Troops"],"4000101":["Barcher","https://assets.clashk.ing/troops/barcher/icon.webp","Troops"],"4000102":["Witch Golem","https://assets.clashk.ing/troops/witch_golem/icon.webp","Troops"],"4000103":["Hog Wizard","https://assets.clashk.ing/troops/hog_wizard/icon.webp","Troops"],"4000104":["Lavaloon","https://assets.clashk.ing/troops/lavaloon/icon.webp","Troops"],"4000106":["Electrofire Wizard","https://assets.clashk.ing/troops/electrofire_wizard/icon.webp","Troops"],"4000109":["Ruin Witch","https://assets.clashk.ing/troops/ruin_witch/icon.webp","Troops"],"4000110":["Root Rider","https://assets.clashk.ing/troops/root_rider/icon.webp","Troops"],"4000118":["C.O.O.K.I.E","https://assets.clashk.ing/troops/cookie/icon.webp","Troops"],"4000119":["Firecracker","https://assets.clashk.ing/troops/firecracker/icon.webp","Troops"],"4000120":["Azure Dragon","https://assets.clashk.ing/troops/azure_dragon/icon.webp","Troops"],"4000121":["Barbarian Kicker","https://assets.clashk.ing/troops/barbarian_kicker/icon.webp","Troops"],"4000122":["Giant Thrower","https://assets.clashk.ing/troops/giant_thrower/icon.webp","Troops"],"4000123":["Druid","https://assets.clashk.ing/troops/druid/icon.webp","Troops"],"4000125":["Broom Witch","https://assets.clashk.ing/troops/broom_witch/icon.webp","Troops"],"4000130":["Ice Minion","https://assets.clashk.ing/troops/ice_minion/icon.webp","Troops"],"4000132":["Thrower","https://assets.clashk.ing/troops/thrower/icon.webp","Troops"],"4000135":["Troop Launcher","https://assets.clashk.ing/troops/troop_launcher/icon.webp","Troops"],"4000136":["Debt Collector","https://assets.clashk.ing/troops/debt_collector/icon.webp","Troops"],"4000142":["Snake Barrel","https://assets.clashk.ing/troops/snake_barrel/icon.webp","Troops"],"4000147":["Super Yeti","https://assets.clashk.ing/troops/super_yeti/icon.webp","Troops"],"4000150":["Furnace","https://assets.clashk.ing/troops/furnace/icon.webp","Troops"],"4000156":["Giant Giant","https://assets.clashk.ing/troops/giant_giant/icon.webp","Troops"],"4000157":["K.A.N.E","https://assets.clashk.ing/troops/kane/icon.webp","Troops"],"4000158":["The Disarmer","https://assets.clashk.ing/troops/the_disarmer/icon.webp","Troops"],"4000159":["YEETer","https://assets.clashk.ing/troops/yeeter/icon.webp","Troops"],"4000167":["Meteor Golem","https://assets.clashk.ing/troops/meteor_golem/icon.webp","Troops"],"4000177":["Meteor Golem","https://assets.clashk.ing/troops/meteor_golem/icon.webp","Troops"],"4000185":["Elephant Rider","https://assets.clashk.ing/troops/elephant_rider/icon.webp","Troops"],"4000188":["Sky Wagon","https://assets.clashk.ing/troops/sky_wagon/icon.webp","Troops"],"4000190":["Yeti Undertaker","https://assets.clashk.ing/troops/yeti_undertaker/icon.webp","Troops"],"28000000":["Barbarian King","https://assets.clashk.ing/heroes/barbarian_king/icon.webp","Heroes"],"28000001":["Archer Queen","https://assets.clashk.ing/heroes/archer_queen/icon.webp","Heroes"],"28000002":["Grand Warden","https://assets.clashk.ing/heroes/grand_warden/icon.webp","Heroes"],"28000003":["Battle Machine","https://assets.clashk.ing/heroes/battle_machine/icon.webp","Heroes"],"28000004":["Royal Champion","https://assets.clashk.ing/heroes/royal_champion/icon.webp","Heroes"],"28000005":["Battle Copter","https://assets.clashk.ing/heroes/battle_copter/icon.webp","Heroes"],"28000006":["Minion Prince","https://assets.clashk.ing/heroes/minion_prince/icon.webp","Heroes"],"28000007":["Dragon Duke","https://assets.clashk.ing/heroes/dragon_duke/icon.webp","Heroes"],"73000000":["L.A.S.S.I","https://assets.clashk.ing/pets/lassi/icon.webp","Pets"],"73000001":["Mighty Yak","https://assets.clashk.ing/pets/mighty_yak/icon.webp","Pets"],"73000002":["Electro Owl","https://assets.clashk.ing/pets/electro_owl/icon.webp","Pets"],"73000003":["Unicorn","https://assets.clashk.ing/pets/unicorn/icon.webp","Pets"],"73000004":["Phoenix","https://assets.clashk.ing/pets/phoenix/icon.webp","Pets"],"73000007":["Poison Lizard","https://assets.clashk.ing/pets/poison_lizard/icon.webp","Pets"],"73000008":["Diggy","https://assets.clashk.ing/pets/diggy/icon.webp","Pets"],"73000009":["Frosty","https://assets.clashk.ing/pets/frosty/icon.webp","Pets"],"73000010":["Spirit Fox","https://assets.clashk.ing/pets/spirit_fox/icon.webp","Pets"],"73000011":["Angry Jelly","https://assets.clashk.ing/pets/angry_jelly/icon.webp","Pets"],"73000016":["Sneezy","https://assets.clashk.ing/pets/sneezy/icon.webp","Pets"],"73000017":["Greedy Raven","https://assets.clashk.ing/pets/greedy_raven/icon.webp","Pets"],"90000000":["Barbarian Puppet","https://assets.clashk.ing/equipment/barbarian_puppet.webp","Equipment"],"90000001":["Rage Vial","https://assets.clashk.ing/equipment/rage_vial.webp","Equipment"],"90000002":["Archer Puppet","https://assets.clashk.ing/equipment/archer_puppet.webp","Equipment"],"90000003":["Invisibility Vial","https://assets.clashk.ing/equipment/invisibility_vial.webp","Equipment"],"90000004":["Eternal Tome","https://assets.clashk.ing/equipment/eternal_tome.webp","Equipment"],"90000005":["Life Gem","https://assets.clashk.ing/equipment/life_gem.webp","Equipment"],"90000006":["Seeking Shield","https://assets.clashk.ing/equipment/seeking_shield.webp","Equipment"],"90000007":["Royal Gem","https://assets.clashk.ing/equipment/royal_gem.webp","Equipment"],"90000008":["Earthquake Boots","https://assets.clashk.ing/equipment/earthquake_boots.webp","Equipment"],"90000009":["Hog Rider Puppet","https://assets.clashk.ing/equipment/hog_rider_puppet.webp","Equipment"],"90000010":["Giant Gauntlet","https://assets.clashk.ing/equipment/giant_gauntlet.webp","Equipment"],"90000011":["Vampstache","https://assets.clashk.ing/equipment/vampstache.webp","Equipment"],"90000012":["Haste Vial","https://assets.clashk.ing/equipment/haste_vial.webp","Equipment"],"90000013":["Rocket Spear","https://assets.clashk.ing/equipment/rocket_spear.webp","Equipment"],"90000014":["Spiky Ball","https://assets.clashk.ing/equipment/spiky_ball.webp","Equipment"],"90000015":["Frozen Arrow","https://assets.clashk.ing/equipment/frozen_arrow.webp","Equipment"],"90000016":["Monolith Arrow","https://assets.clashk.ing/equipment/monolith_arrow.webp","Equipment"],"90000017":["Giant Arrow","https://assets.clashk.ing/equipment/giant_arrow.webp","Equipment"],"90000019":["Heroic Torch","https://assets.clashk.ing/equipment/heroic_torch.webp","Equipment"],"90000020":["Healer Puppet","https://assets.clashk.ing/equipment/healer_puppet.webp","Equipment"],"90000022":["Fireball","https://assets.clashk.ing/equipment/fireball.webp","Equipment"],"90000024":["Rage Gem","https://assets.clashk.ing/equipment/rage_gem.webp","Equipment"],"90000032":["Snake Bracelet","https://assets.clashk.ing/equipment/snake_bracelet.webp","Equipment"],"90000034":["Healing Tome","https://assets.clashk.ing/equipment/healing_tome.webp","Equipment"],"90000035":["Dark Crown","https://assets.clashk.ing/equipment/dark_crown.webp","Equipment"],"90000039":["Magic Mirror","https://assets.clashk.ing/equipment/magic_mirror.webp","Equipment"],"90000040":["Electro Boots","https://assets.clashk.ing/equipment/electro_boots.webp","Equipment"],"90000041":["Lavaloon Puppet","https://assets.clashk.ing/equipment/lavaloon_puppet.webp","Equipment"],"90000042":["Henchmen Puppet","https://assets.clashk.ing/equipment/henchmen_puppet.webp","Equipment"],"90000043":["Dark Orb","https://assets.clashk.ing/equipment/dark_orb.webp","Equipment"],"90000044":["Metal Pants","https://assets.clashk.ing/equipment/metal_pants.webp","Equipment"],"90000047":["Noble Iron","https://assets.clashk.ing/equipment/noble_iron.webp","Equipment"],"90000048":["Action Figure","https://assets.clashk.ing/equipment/action_figure.webp","Equipment"],"90000049":["Meteor Staff","https://assets.clashk.ing/equipment/meteor_staff.webp","Equipment"],"90000050":["Frost Flake","https://assets.clashk.ing/equipment/frost_flake.webp","Equipment"],"90000051":["Stick Horse","https://assets.clashk.ing/equipment/stick_horse.webp","Equipment"],"90000052":["Fire Heart","https://assets.clashk.ing/equipment/fire_heart.webp","Equipment"],"90000053":["Rocket Backpack","https://assets.clashk.ing/equipment/rocket_backpack.webp","Equipment"],"90000056":["Stun Blaster","https://assets.clashk.ing/equipment/stun_blaster.webp","Equipment"],"90000057":["Flame Blower","https://assets.clashk.ing/equipment/flame_blower.webp","Equipment"],"90000059":["Electro Fangs","https://assets.clashk.ing/equipment/electro_fangs.webp","Equipment"],"90000060":["Revenge Deck","https://assets.clashk.ing/equipment/revenge_deck.webp","Equipment"],"26000000":["Lightning Spell","https://assets.clashk.ing/spells/lightning_spell.webp","Spells"],"26000001":["Healing Spell","https://assets.clashk.ing/spells/healing_spell.webp","Spells"],"26000002":["Rage Spell","https://assets.clashk.ing/spells/rage_spell.webp","Spells"],"26000003":["Jump Spell","https://assets.clashk.ing/spells/jump_spell.webp","Spells"],"26000005":["Freeze Spell","https://assets.clashk.ing/spells/freeze_spell.webp","Spells"],"26000006":["Santa's Surprise","https://assets.clashk.ing/spells/santa's_surprise.webp","Spells"],"26000009":["Poison Spell","https://assets.clashk.ing/spells/poison_spell.webp","Spells"],"26000010":["Earthquake Spell","https://assets.clashk.ing/spells/earthquake_spell.webp","Spells"],"26000011":["Haste Spell","https://assets.clashk.ing/spells/haste_spell.webp","Spells"],"26000016":["Clone Spell","https://assets.clashk.ing/spells/clone_spell.webp","Spells"],"26000017":["Skeleton Spell","https://assets.clashk.ing/spells/skeleton_spell.webp","Spells"],"26000028":["Bat Spell","https://assets.clashk.ing/spells/bat_spell.webp","Spells"],"26000035":["Invisibility Spell","https://assets.clashk.ing/spells/invisibility_spell.webp","Spells"],"26000053":["Recall Spell","https://assets.clashk.ing/spells/recall_spell.webp","Spells"],"26000070":["Overgrowth Spell","https://assets.clashk.ing/spells/overgrowth_spell.webp","Spells"],"26000073":["Bag of Frostmites","https://assets.clashk.ing/spells/bag_of_frostmites.webp","Spells"],"26000098":["Revive Spell","https://assets.clashk.ing/spells/revive_spell.webp","Spells"],"26000109":["Ice Block Spell","https://assets.clashk.ing/spells/ice_block_spell.webp","Spells"],"26000120":["Totem Spell","https://assets.clashk.ing/spells/totem_spell.webp","Spells"],"26000123":["Angry Spell","https://assets.clashk.ing/spells/angry_spell.webp","Spells"],"107000000":["Longshot","https://assets.clashk.ing/guardians/longshot/icon.webp","Guardians"],"107000001":["Smasher","https://assets.clashk.ing/guardians/smasher/icon.webp","Guardians"],"107000008":["Logger","https://assets.clashk.ing/guardians/logger/icon.webp","Guardians"],"93000000":["Builder's Apprentice","https://assets.clashk.ing/helpers/builder's_apprentice.webp","Helpers"],"93000001":["Lab Assistant","https://assets.clashk.ing/helpers/lab_assistant.webp","Helpers"],"93000002":["Alchemist","https://assets.clashk.ing/helpers/alchemist.webp","Helpers"],"93000003":["Prospector","https://assets.clashk.ing/helpers/prospector.webp","Helpers"]};
  const gameAssetNames = new Map(Object.entries(gameAssets).map(([id,e])=>[e[0].toLowerCase().replace(/[^a-z0-9]/g,''),id]));
  const categoryAssets = {laboratory:'Laboratory',heroes:'Archer Queen',pets:'L.A.S.S.I',equipment:'Blacksmith',Buildings:"Builder's Hut",Defenses:'Cannon',Traps:'Bomb',Walls:'Wall',builder:"Builder's Hut"};
  function gameIcon(item,level=1,category='') {
    const name=typeof item==='object'?item?.name:item, id=typeof item==='object'?item?.id:null;
    const alias=categoryAssets[name]||name||categoryAssets[category]||category;
    const asset=gameAssets[id]||gameAssets[gameAssetNames.get(String(alias).toLowerCase().replace(/[^a-z0-9]/g,''))];
    const path=asset?.[1]?.replace('{level}',String(Math.max(1,Math.min(200,Number(level)||1))));
    return `<span class="wh-game-icon" aria-hidden="true"><svg class="wh-game-fallback" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m4 20 9-9m-3-6 3-3 9 9-3 3-4-4-3 3-3-3 3-3-2-2Z"/></svg>${path?`<img data-wh-game-image src="${esc(path)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer">`:''}</span>`;
  }
  if(typeof document!=='undefined'&&!document.documentElement.dataset.whGameIcons){
    document.documentElement.dataset.whGameIcons='1';
    document.addEventListener('load',event=>{const img=event.target;if(img.matches?.('[data-wh-game-image]'))img.previousElementSibling.setAttribute('hidden','');},true);
    document.addEventListener('error',event=>{const img=event.target;if(!img.matches?.('[data-wh-game-image]'))return;
      if(!img.dataset.mirrorTried){img.dataset.mirrorTried='1';img.src=img.src.replace('https://assets.clashk.ing/','https://raw.githubusercontent.com/ClashKingInc/ClashKingAssets/main/assets/');}
      else {img.hidden=true;img.previousElementSibling.removeAttribute('hidden');}
    },true);
  }

  function army(a) {
    if (!a || a.method !== "th-work-v2") return '<p class="notice">Upgrade progress is waiting for the next successful player sync.</p>';
    const labels = { laboratory: "Laboratory · troops, spells & siege", heroes: "Heroes", pets: "Pets", equipment: "Owned equipment" };
    return `<div class="wh-upgrade-heading"><div><span class="eyebrow">Available upgrades at TH ${a.townHall}</span><h3>Army completion</h3></div><strong>${percent(completion(a))}</strong></div><p class="small muted">Completion credits every finished upgrade, weighted by standard upgrade time. 100% means all army upgrades available at this Town Hall are complete. Buildings, traps, walls and equipment are shown separately.</p>${Object.entries(labels).map(([key, label]) => {
      const g = a.groups?.[key];
      if (!g || !g.count) return `<p class="small muted">${label}: ${key === "equipment" ? "no owned pieces captured" : "not available at this Town Hall"}.</p>`;
      const value = completion(g);
      return `<details class="wh-upgrade-category"><summary><span class="wh-icon-label">${gameIcon(key)}<span>${label}</span></span><b>${percent(value)}</b></summary>${meter(label, value, number(g.remainingLevels) + " levels remaining · " + number(g.maxed) + " / " + g.count + " maxed")}${g.earlierLevelsRemaining ? `<p class="wh-backlog">${g.earlierLevelsRemaining} unfinished levels are from earlier Town Halls.</p>` : ""}<div class="wh-levels">${g.items.map((i) => `<div class="wh-level">${gameIcon(i,i.level)}<b>${esc(i.name)}</b><span>${i.level == null ? "Unknown" : i.level} / ${i.maximum}</span><small>${i.level === i.maximum ? "Maxed for this TH" : i.level == null ? "Level needs review" : !i.unlocked ? "Not unlocked · " + i.remainingLevels + " levels left" : i.remainingLevels + " levels left"}${i.earlierLevelsRemaining ? " · " + i.earlierLevelsRemaining + " from earlier THs" : ""}</small>${i.oreRemaining ? `<small>${Object.entries(i.oreRemaining).filter(([, v]) => v).map(([k, v]) => number(v) + " " + k.replace("_", " ")).join(" · ") || "No ore remaining"}</small>` : ""}</div>`).join("")}</div>${key !== "equipment" && Number.isFinite(g.percent) ? `<p class="small muted">Current Town Hall work score: ${percent(g.percent)}. This separate score starts at 0% for the previous Town Hall maximum and subtracts unfinished earlier upgrades.</p>` : ""}</details>`;
    }).join("")}<details class="wh-upgrade-category"><summary><span>Town Hall upgrade details</span></summary><p>${esc(a.explanation)}</p><p>Current Town Hall work score: <b>${percent(a.percent)}</b>. This score can be negative and is separate from the completion percentage above.</p></details>${a.issues?.length ? `<p class="notice">${a.issues.map(esc).join(" ")}</p>` : ""}`;
  }
  function village(v) {
    if (!v) return '<p class="notice">Import your village data to see building, defense, trap and wall progress.</p>';
    return `<p class="small muted">Exported ${esc(date(v.exportedAt))} · Imported ${esc(date(v.importedAt))} · TH ${v.townHall}</p><div class="wh-summary-grid">${["Buildings", "Defenses", "Traps", "Walls"].map((k) => {
      const c = v.categories[k];
      const knownCount = c?.knownCount ?? (c?.known ? c.count : 0), unknownCount = c?.unknownCount ?? 0;
      return `<div class="wh-stat"><small class="wh-icon-label">${gameIcon(k)}<span>${k}</span></small><strong>${knownCount ? c.maxed + " / " + knownCount : "Unknown"}</strong><small>at max for this TH${knownCount ? " · " + number(c.remainingLevels) + (unknownCount ? " known upgrade levels left" : " upgrade levels left") : ""}</small>${unknownCount ? `<small>${number(unknownCount)} additional ${unknownCount === 1 ? "item needs" : "items need"} review</small>` : ""}</div>`;
    }).join("")}</div><h3>Upgrades in progress</h3>${v.active.length ? `<div class="wh-timers">${v.active.map((i) => `<div class="item-row"><span class="wh-icon-label">${gameIcon(i,i.level)}<span><b>${esc(i.name)}</b><small>Level ${i.level ?? "unknown"}${i.target ? " → " + i.target : " · upgrade in progress"}</small></span></span><span><b data-wh-timer="${esc(i.endsAt)}"></b><small>Estimated ${esc(date(i.endsAt))}</small></span></div>`).join("")}</div>` : '<p class="small muted">No active upgrade timers were included in this export.</p>'}<p class="notice">Timers are estimates from this export. A finished countdown requires a new import to confirm the completed level.</p>${v.issues.length ? `<p class="notice">${v.issues.map(esc).join(" ")}</p>` : ""}<details class="wh-upgrade-category"><summary><span>All exported levels and remaining upgrades</span></summary><div class="table-scroll table-wrap"><table><thead><tr><th>Upgrade</th><th>Count</th><th>Level / TH max</th><th>Remaining each</th></tr></thead><tbody>${v.rows.map((r) => `<tr><td><span class="wh-icon-label">${gameIcon(r,r.level)}<span>${esc(r.name)}${r.missing ? " · Not built" : ""}</span></span></td><td>${r.count}</td><td>${r.level ?? "Unknown"} / ${r.maximum ?? "Unknown"}</td><td>${r.remaining ?? "Unknown"}</td></tr>`).join("")}</tbody></table></div></details>`;
  }
  function timers(root = document) {
    root.querySelectorAll("[data-wh-timer]").forEach((el) => {
      const seconds = Math.ceil((Date.parse(el.dataset.whTimer) - Date.now()) / 1e3);
      el.textContent = seconds <= 0 ? "Ready to verify" : seconds >= 86400 ? Math.floor(seconds / 86400) + "d " + Math.floor(seconds % 86400 / 3600) + "h" : Math.floor(seconds / 3600) + "h " + Math.floor(seconds % 3600 / 60) + "m";
    });
  }
  function busyForms(root) {
    root.querySelectorAll("form").forEach((form) => {
      if (form.dataset.busyWired || !form.onsubmit) return;
      form.dataset.busyWired = "1";
      const submit = form.onsubmit;
      form.onsubmit = async function(e) {
        if (this.dataset.submitting) {
          e.preventDefault();
          return;
        }
        this.dataset.submitting = "1";
        const buttons = [...this.querySelectorAll("button[type=submit],button:not([type])")];
        const previouslyDisabled=new Map(buttons.map(button=>[button,button.disabled]));
      buttons.forEach((b) => b.disabled = true);
        try {
          return await submit.call(this, e);
        } finally {
          delete this.dataset.submitting;
          buttons.forEach((b) => {
            if (b.isConnected && !b.dataset.keepDisabled) b.disabled = previouslyDisabled.get(b);
          });
        }
      };
    });
  }
  function captureDraft(root) {
    if (!root) return null;
    const fields = {};
    root.querySelectorAll("input,textarea,select").forEach((el, i) => {
      if (el.type === "password" || el.type === "file" || el.autocomplete === "one-time-code" || /factor|recovery|secret|token|code/i.test(el.name || el.id) || !el.id && !el.name || el.readOnly) return;
      const key = el.id || el.name + ":" + i;
      fields[key] = { value: el.value, checked: el.checked, tag: el.tagName };
    });
    return { fields, focus: root.contains(document.activeElement) ? document.activeElement.id : null };
  }
  function restoreDraft(root, draft) {
    if (!root || !draft) return;
    root.querySelectorAll("input,textarea,select").forEach((el, i) => {
      const saved = draft.fields[el.id || el.name + ":" + i];
      if (!saved || saved.tag !== el.tagName || el.type === "password" || el.type === "file") return;
      el.value = saved.value;
      if (["checkbox", "radio"].includes(el.type)) el.checked = saved.checked;
    });
    if (draft.focus) {
      const focus = document.getElementById(draft.focus);
      if (focus && root.contains(focus)) focus.focus({ preventScroll: true });
    }
  }
  const bell = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg>';
  return { gameIcon, now, syncClock, esc, number, date, shortDate: (v) => date(v, preferences, true), apply, settingsFields, readSettings, chart, seasonDonations, wire, chartKeys, completion, meter, army, village, timers, bell, captureDraft, restoreDraft, busyForms };
})();
