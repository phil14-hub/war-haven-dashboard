var WarHavenUI = /* @__PURE__ */ (() => {
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  let preferences = {};
  const number = (v, digits = 2) => Number.isFinite(v) ? v.toLocaleString(void 0, { maximumFractionDigits: digits }) : "Unknown";
  function locale(p) {
    return { mdy: "en-US", dmy: "en-GB", iso: "en-CA" }[p.dateFormat];
  }
  function date(value, p = preferences, short = false) {
    if (!value || !Number.isFinite(Date.parse(value))) return "Not captured";
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
  function chart(label, series, { asOf, percent: pc = false, step = true, targets = [], precision, id = "wh-chart-" + Math.random().toString(36).slice(2) } = {}) {
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
      if (!Number.isFinite(p.value) || p.lowerBound) {
        connected = false;
        continue;
      }
      const xx = x(p.at), yy = y(p.value);
      path += connected ? step ? " H" + xx + " V" + yy : " L" + xx + " " + yy : " M" + xx + " " + yy;
      connected = true;
      previous = p;
    }
    if (connected && previous && Date.parse(previous.at) < end) path += " H" + R;
    const latest = valid.at(-1), unit = pc ? "%" : label, axis = (v) => pc ? fmt(v) : Math.abs(v) >= 1e6 ? number(v / 1e6) + "m" : Math.abs(v) >= 1e3 ? number(v / 1e3) + "k" : number(v);
    return `<div class="wh-chart"><div class="wh-chart-caption"><strong>${esc((latest.lowerBound ? "At least " : "") + fmt(latest.value))}</strong><small>${esc(label)}</small></div><svg viewBox="0 0 ${width} 254" role="group" aria-label="${esc(label)}. Dates on the x axis, ${esc(unit)} on the y axis.">${[0, 0.5, 1].map((n) => {
      const v = min + (max - min) * n;
      return `<line x1="${L}" x2="${R}" y1="${y(v)}" y2="${y(v)}" class="wh-grid"/><text x="${L - 10}" y="${y(v) + 4}" text-anchor="end" class="wh-axis">${esc(axis(v))}</text>`;
    }).join("")}${min < 0 ? `<line x1="${L}" x2="${R}" y1="${y(0)}" y2="${y(0)}" class="wh-zero"/>` : ""}${targets.map((p) => `<line x1="${L}" x2="${R}" y1="${y(p.value)}" y2="${y(p.value)}" class="wh-zero"/><text x="${R - 4}" y="${y(p.value) - 7}" text-anchor="end" class="wh-axis">Level ${p.level}</text>`).join("")}<path d="${path}" class="wh-line"/>${valid.map((p) => {
      const detail = date(p.at) + " · " + (p.lowerBound ? "At least " : "") + exact(p.value) + (p.detail ? " · " + p.detail : "");
      return `<g tabindex="0" role="button" data-wh-inspect="${id}" data-wh-detail="${esc(detail)}" aria-label="${esc(detail)}"><circle cx="${x(p.at)}" cy="${y(p.value)}" r="15" class="wh-hit"/><circle cx="${x(p.at)}" cy="${y(p.value)}" r="${p.lowerBound ? 5 : 4}" class="wh-dot${p.lowerBound ? " wh-floor" : ""}"/></g>`;
    }).join("")}${[0, 0.5, 1].map((n, i) => `<text x="${L + (R - L) * n}" y="238" text-anchor="${i === 0 ? "start" : i === 2 ? "end" : "middle"}" class="wh-axis">${esc(date(new Date(start + (end - start) * n).toISOString(), preferences, true))}</text>`).join("")}</svg><p id="${id}" class="wh-inspect" aria-live="polite"></p><div class="wh-chart-tooltip" role="tooltip" hidden></div><small class="wh-chart-help">Tab enters the chart. Use arrow keys to move, Home/End for first/latest, and Escape to dismiss. Exact values are below.</small><small class="muted">Last synced ${esc(date(asOf || points.at(-1).at))} · ${valid.length} value changes</small><details class="wh-data"><summary>View recorded values</summary><div class="table-scroll table-wrap"><table><thead><tr><th>Observed</th><th>${esc(label)}</th><th>Details</th></tr></thead><tbody>${points.map((p) => `<tr><td>${esc(date(p.at))}</td><td>${Number.isFinite(p.value) ? esc((p.lowerBound ? "≥ " : "") + exact(p.value)) : "Unknown"}</td><td>${esc(p.detail || "")}</td></tr>`).join("")}</tbody></table></div></details></div>`;
  }
  function seasonDonations(roster, {asOf, id = 'season-donations-chart'} = {}) {
    const known = p => Number.isInteger(p.donations) && p.donations >= 0;
    const members = [...(roster || [])].sort((a,b) => Number(known(b))-Number(known(a)) || (b.donations || 0)-(a.donations || 0) || String(a.name).localeCompare(String(b.name)));
    if (!members.length) return '<p class="chart-empty">The season chart will appear when the clan roster is available.</p>';
    const captured = members.filter(known), total = captured.reduce((sum,p) => sum+p.donations,0);
    const width = Math.max(600, members.length*46+100), L = 72, R = width-28, T = 30, B = 222, max = Math.max(1,...captured.map(p=>p.donations));
    const x = i => L+(i+.5)*(R-L)/members.length, y = n => B-n/max*(B-T);
    const description = p => String(p.name || p.tag)+' ('+p.tag+') · '+(known(p)?number(p.donations,0)+' troops donated this season':'Season donations unknown');
    return `<section class="panel season-donations-panel"><h2>Season donations by player</h2><div class="wh-chart" data-chart-start="first"><div class="wh-chart-caption"><strong>${captured.length ? (captured.length<members.length?'≥ ':'')+number(total,0) : 'Unknown'}</strong><small>troops donated · ${members.length} current members</small></div><p class="small muted">Every current member is included, including zero donations. Hover, tap, or focus a dot for their season total. Scroll sideways to see everyone.</p><div class="season-donation-scroll" tabindex="0" role="region" aria-label="Season donations for every current member; scroll horizontally"><svg viewBox="0 0 ${width} 310" style="width:${width}px;min-width:100%" role="group" aria-label="Player names on the x axis; troops donated this season on the y axis">${[0,.5,1].map(n=>`<line x1="${L}" x2="${R}" y1="${y(max*n)}" y2="${y(max*n)}" class="wh-grid"/><text x="${L-10}" y="${y(max*n)+4}" text-anchor="end" class="wh-axis">${number(max*n,0)}</text>`).join('')}${members.map((p,i)=>`<g tabindex="0" role="button" data-wh-inspect="${id}" data-donation-tag="${esc(p.tag)}" data-wh-detail="${esc(description(p))}" aria-label="${esc(description(p))}"><circle cx="${x(i)}" cy="${y(known(p)?p.donations:0)}" r="22" class="wh-hit"/><circle cx="${x(i)}" cy="${y(known(p)?p.donations:0)}" r="5" class="wh-dot${known(p)?'':' wh-floor'}"/><text transform="translate(${x(i)},245) rotate(-40)" text-anchor="end" class="wh-axis">${esc(String(p.name || p.tag).slice(0,14))}</text></g>`).join('')}</svg></div><p id="${id}" class="wh-inspect" aria-live="polite"></p><div class="wh-chart-tooltip" role="tooltip" hidden></div><small class="wh-chart-help">Tap a dot to pin its value; tap elsewhere or press Escape to dismiss. Use arrow keys to move between players, or Home/End for the first/last player.</small><small class="muted">Last synced ${esc(date(asOf))}${captured.length<members.length?' · '+(members.length-captured.length)+' unknown counts excluded from the total':''}</small><details class="wh-data"><summary>View all ${members.length} players and season totals</summary><div class="table-scroll"><table><thead><tr><th>Player</th><th>Tag</th><th>Donated this season</th></tr></thead><tbody>${members.map(p=>`<tr><td>${esc(p.name || p.tag)}</td><td>${esc(p.tag)}</td><td>${known(p)?number(p.donations,0):'Unknown'}</td></tr>`).join('')}</tbody></table></div></details></div></section>`;
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
  function army(a) {
    if (!a || a.method !== "th-work-v2") return '<p class="notice">Upgrade progress is waiting for the next successful player sync.</p>';
    const labels = { laboratory: "Laboratory · troops, spells & siege", heroes: "Heroes", pets: "Pets", equipment: "Owned equipment" };
    return `<div class="wh-upgrade-heading"><div><span class="eyebrow">Available upgrades at TH ${a.townHall}</span><h3>Army completion</h3></div><strong>${percent(completion(a))}</strong></div><p class="small muted">Completion credits every finished upgrade, weighted by standard upgrade time. 100% means all army upgrades available at this Town Hall are complete. Buildings, traps, walls and equipment are shown separately.</p>${Object.entries(labels).map(([key, label]) => {
      const g = a.groups?.[key];
      if (!g || !g.count) return `<p class="small muted">${label}: ${key === "equipment" ? "no owned pieces captured" : "not available at this Town Hall"}.</p>`;
      const value = completion(g);
      return `<details class="wh-upgrade-category"><summary><span>${label}</span><b>${percent(value)}</b></summary>${meter(label, value, number(g.remainingLevels) + " levels remaining · " + number(g.maxed) + " / " + g.count + " maxed")}${g.earlierLevelsRemaining ? `<p class="wh-backlog">${g.earlierLevelsRemaining} unfinished levels are from earlier Town Halls.</p>` : ""}<div class="wh-levels">${g.items.map((i) => `<div class="wh-level"><b>${esc(i.name)}</b><span>${i.level == null ? "Unknown" : i.level} / ${i.maximum}</span><small>${i.level === i.maximum ? "Maxed for this TH" : i.level == null ? "Level needs review" : !i.unlocked ? "Not unlocked · " + i.remainingLevels + " levels left" : i.remainingLevels + " levels left"}${i.earlierLevelsRemaining ? " · " + i.earlierLevelsRemaining + " from earlier THs" : ""}</small>${i.oreRemaining ? `<small>${Object.entries(i.oreRemaining).filter(([, v]) => v).map(([k, v]) => number(v) + " " + k.replace("_", " ")).join(" · ") || "No ore remaining"}</small>` : ""}</div>`).join("")}</div>${key !== "equipment" && Number.isFinite(g.percent) ? `<p class="small muted">Current Town Hall work score: ${percent(g.percent)}. This separate score starts at 0% for the previous Town Hall maximum and subtracts unfinished earlier upgrades.</p>` : ""}</details>`;
    }).join("")}<details class="wh-upgrade-category"><summary><span>Town Hall upgrade details</span></summary><p>${esc(a.explanation)}</p><p>Current Town Hall work score: <b>${percent(a.percent)}</b>. This score can be negative and is separate from the completion percentage above.</p></details>${a.issues?.length ? `<p class="notice">${a.issues.map(esc).join(" ")}</p>` : ""}`;
  }
  function village(v) {
    if (!v) return '<p class="notice">Import your village data to see building, defense, trap and wall progress.</p>';
    return `<p class="small muted">Exported ${esc(date(v.exportedAt))} · Imported ${esc(date(v.importedAt))} · TH ${v.townHall}</p><div class="wh-summary-grid">${["Buildings", "Defenses", "Traps", "Walls"].map((k) => {
      const c = v.categories[k];
      return `<div class="wh-stat"><small>${k}</small><strong>${c?.known ? c.maxed + " / " + c.count : "Unknown"}</strong><small>at max for this TH${c?.known ? " · " + number(c.remainingLevels) + " upgrade levels left" : ""}</small></div>`;
    }).join("")}</div><h3>Upgrades in progress</h3>${v.active.length ? `<div class="wh-timers">${v.active.map((i) => `<div class="item-row"><span><b>${esc(i.name)}</b><small>Level ${i.level}${i.target ? " → " + i.target : " · upgrade in progress"}</small></span><span><b data-wh-timer="${esc(i.endsAt)}"></b><small>Estimated ${esc(date(i.endsAt))}</small></span></div>`).join("")}</div>` : '<p class="small muted">No active upgrade timers were included in this export.</p>'}<p class="notice">Timers are estimates from this export. A finished countdown requires a new import to confirm the completed level.</p>${v.issues.length ? `<p class="notice">${v.issues.map(esc).join(" ")}</p>` : ""}<details class="wh-upgrade-category"><summary><span>All exported levels and remaining upgrades</span></summary><div class="table-scroll table-wrap"><table><thead><tr><th>Upgrade</th><th>Count</th><th>Level / TH max</th><th>Remaining each</th></tr></thead><tbody>${v.rows.map((r) => `<tr><td>${esc(r.name)}${r.missing ? " · Not built" : ""}</td><td>${r.count}</td><td>${r.level} / ${r.maximum ?? "Unknown"}</td><td>${r.remaining ?? "Unknown"}</td></tr>`).join("")}</tbody></table></div></details>`;
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
  return { esc, number, date, shortDate: (v) => date(v, preferences, true), apply, settingsFields, readSettings, chart, seasonDonations, wire, chartKeys, completion, meter, army, village, timers, bell, captureDraft, restoreDraft, busyForms };
})();
