/* Optional member-only overview renderer for Sites integration.
   Use only an authenticated, selected-village member projection. */
var WarHavenMemberOverview = (() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const shown = (value, suffix = '') => finite(value) ? value.toLocaleString(undefined, {maximumFractionDigits:2}) + suffix : 'Not captured';
  const placeholders = {wars:'⚔️',army:'🧪',troops:'🧪',spells:'✨',siege:'🛡️',heroes:'👑',pets:'🐾',equipment:'🛡️',buildings:'🏰',defenses:'🛡️',traps:'💣',planner:'🔨',activity:'🏆',lab:'🧪'};
  const safeUrl = url => typeof url === 'string' && (/^https:\/\//i.test(url) || /^\/(?!\/)/.test(url)) && !/[\s"'<>]/.test(url);
  function icon(key, assets = {}, name = '') {
    const asset = assets[key] || (name && assets[name]);
    return safeUrl(asset)
      ? `<img class="whmo-icon" src="${esc(asset)}" alt="" aria-hidden="true" width="32" height="32" loading="lazy" decoding="async">`
      : `<span class="whmo-icon whmo-icon-fallback" aria-hidden="true">${placeholders[key] || '⭐'}</span>`;
  }
  function stat(label, value, note) {
    return `<div class="whmo-stat"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`;
  }
  function card(key, title, html, assets, destination, onNavigate) {
    const label = `${icon(key, assets)}<span>${esc(title)}</span>`;
    const header = typeof onNavigate === 'function'
      ? `<button type="button" class="whmo-card-heading" data-whmo-go="${esc(destination)}" aria-label="View ${esc(title)} details">${label}<span aria-hidden="true">↗</span></button>`
      : `<h3 class="whmo-card-heading">${label}</h3>`;
    return `<section class="whmo-card" aria-label="${esc(title)}">${header}<div class="whmo-stats">${html}</div></section>`;
  }
  function render(member, options = {}) {
    const assets = options.assets || {};
    if (!member || typeof member !== 'object') return '<p class="whmo-empty">Select an approved village to see its overview.</p>';
    const overview = member.overview || {};
    const war = overview.war || {};
    const army = overview.army || {};
    const groups = army.groups || {};
    const activity = overview.activity || {};
    const village = options.village || {};
    const planner = options.planner || {};
    const winLoss = war.confirmedAppearances == null ? 'Not captured'
      : `${shown(war.victories)} / ${shown(war.defeats)} / ${shown(war.ties)}`;
    const warHtml = stat('Confirmed wars', shown(war.confirmedAppearances), 'Completed, verified captures') +
      stat('Victories / defeats / ties', winLoss, war.outcomesUnknown ? `${war.outcomesUnknown} results awaiting confirmation` : 'Confirmed outcomes only') +
      stat('Attacks used', finite(war.attacksAllowed) && war.attacksAllowed > 0 ? `${shown(war.attacksUsed)} / ${shown(war.attacksAllowed)}` : 'Not captured', 'Excused opportunities excluded') +
      stat('Average stars', shown(war.averageStars), 'Per captured attack') +
      stat('Three-star rate', shown(war.threeStarPercent, '%'), 'Per captured attack') +
      stat('Average destruction', shown(war.averageDestructionPercent, '%'), 'When recorded');
    const armyHtml = stat('Army completion', shown(army.completionPercent, '%'), army.available ? 'Current Town Hall profile' : 'Waiting for a matching player profile') +
      ['troops','spells','siege','heroes','pets'].map(key => {
        const group = groups[key] || {};
        return stat(key[0].toUpperCase()+key.slice(1), shown(group.completionPercent, '%'),
          group.available ? `${shown(group.remainingLevels)} levels remaining` : 'Not captured');
      }).join('');
    const categories = village.categories || {};
    const buildHtml = ['Buildings','Defenses','Traps','Walls'].map(category => {
      const entry = categories[category] || {};
      return stat(category, finite(entry.knownCount) ? `${shown(entry.maxed)} / ${shown(entry.knownCount)} maxed` : 'Not captured',
        finite(entry.remainingLevels) ? `${shown(entry.remainingLevels)} levels remaining` : 'Needs a recent in-game village export');
    }).join('');
    const upgradesHtml = stat('Active builders', shown(planner.busyBuilders), 'Based on the saved upgrade plan') +
      stat('Next completion', typeof planner.nextCompletion === 'string' && planner.nextCompletion ? planner.nextCompletion : 'Not captured', 'Estimated unless verified in-game');
    const activityHtml = stat('Season donations', shown(activity.seasonDonations), 'Current recorded season') +
      stat('Capital Gold', shown(activity.capitalGold), 'Observed contributions') +
      stat('Trophies', shown(activity.trophies), 'Last roster capture') +
      stat('Raid loot', shown(activity.raidLoot), 'Completed raids');
    return `<div class="whmo-root"><div class="whmo-title"><h2>My Overview</h2><p>${esc(member.name || member.tag || 'Village')} · TH ${esc(member.townHallLevel ?? 'Unknown')}</p></div><div class="whmo-grid">${card('wars','My wars',warHtml,assets,'wars',options.onNavigate)}${card('army','Laboratory, troops & heroes',armyHtml,assets,'progress',options.onNavigate)}${card('buildings','Village buildings & defenses',buildHtml,assets,'progress',options.onNavigate)}${card('planner','Upgrade planner',upgradesHtml,assets,'planner',options.onNavigate)}${card('activity','Clan contributions',activityHtml,assets,'activity',options.onNavigate)}</div><p class="whmo-freshness">Clan data last synced: ${esc(overview.updatedAt || 'Not captured')}. Village-building data requires an approved export. Estimated upgrade times are not confirmations.</p></div>`;
  }
  function mount(element, member, options = {}) {
    if (!element) throw Error('A dashboard container is required.');
    element.innerHTML = render(member, options);
    for (const button of element.querySelectorAll('[data-whmo-go]')) {
      button.addEventListener('click', () => options.onNavigate?.(button.dataset.whmoGo));
    }
  }
  function plannerTitle(name, assets = {}) {
    return `<span class="whmo-planner-title">${icon('planner',assets)}<span>${esc(name || 'Village')}'s upgrade plan</span></span>`;
  }
  function progressHeading(group, assets = {}) {
    const names = {lab:'Laboratory – troops, spells & siege',troops:'Troops',spells:'Spells',siege:'Siege machines',heroes:'Heroes',pets:'Pets',equipment:'Hero equipment',buildings:'Buildings',defenses:'Defenses',traps:'Traps'};
    return `<span class="whmo-progress-heading">${icon(group,assets)}<span>${esc(names[group] || group)}</span></span>`;
  }
  function levelRow(item, assets = {}) {
    const name = item?.name || 'Unknown item';
    return `<span class="whmo-level-item">${icon(String(item?.id ?? ''),assets,name)}<span>${esc(name)} <small>Level ${esc(item?.level ?? '?')} / ${esc(item?.maximum ?? '?')}</small></span></span>`;
  }
  return {render,mount,plannerTitle,progressHeading,levelRow};
})();
