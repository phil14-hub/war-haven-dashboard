import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInContext} from 'node:vm';
import {JSDOM, VirtualConsole} from 'jsdom';

const fixture = process.env.WAR_HAVEN_DASHBOARD_FIXTURE;
if (!fixture) throw Error('Leadership fixture required');
const errors = [], virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', error => errors.push(error.message));
const dom = new JSDOM(readFileSync(fixture, 'utf8'), {
  url:'https://portal.warhavenclan.com/members/leadership', runScripts:'outside-only',
  pretendToBeVisual:true, virtualConsole,
});
const w = dom.window, $ = id => w.document.getElementById(id);
w.TextEncoder = TextEncoder;w.TextDecoder = TextDecoder;
w.crypto.randomUUID = () => crypto.randomUUID();
w.matchMedia = () => ({matches:false, addEventListener(){}});
w.scrollTo = () => {};
w.prompt = () => 'Leadership reviewed recurring misses';
w.HTMLElement.prototype.scrollIntoView = function(){};
w.HTMLDialogElement.prototype.showModal = function(){this.open=true;};
w.HTMLDialogElement.prototype.close = function(){this.open=false;};
w.fetch = async input => {
  const path = new URL(input, w.location.href).pathname;
  const value = path.endsWith('/list') ? {accounts:[], counts:{pending:0,active:0,suspended:0}, capabilities:{individual:true}}
    : path.endsWith('/notifications') ? {notifications:[]}
    : path.endsWith('/preferences/clan') ? {version:0, preferences:{}}
    : {records:[], items:[]};
  return new Response(JSON.stringify(value));
};
try {
  for (const script of w.document.querySelectorAll('script:not([type])')) {
    if (script.textContent.trim()) runInContext(script.textContent, dom.getInternalVMContext());
  }
  for (let i=0;i<200&&!w.document.body.classList.contains('app-ready');i++) await new Promise(resolve=>setTimeout(resolve,3));
  assert.ok(w.document.body.classList.contains('app-ready'));
  w.eval(`
    for (const [i, used] of [[2,2],[3,0]]) data.wars.push({
      id:'repeat'+i, kind:'Regular', state:'warEnded', final:true, rosterComplete:true,
      attacksPerMember:2, endTime:'2026-10-16T'+(10+i)+':00:00Z',
      participants:[{tag:'#P0Q',name:'Omid fixture',attacksUsed:used},{tag:'#P0Y',name:'Attacker fixture',attacksUsed:0}]
    });
    render();
  `);
  const flags = $('cards').querySelector('[data-home-card="kick"]');
  assert.equal(flags.querySelector('strong').textContent, '2');
  assert.match(flags.textContent, /1 kick · 1 possible/);
  assert.equal($('cards').querySelector('[data-home-card="bench"] strong').textContent, '1');
  flags.click();
  assert.equal(w.document.body.dataset.page, 'roster');
  assert.equal($('status').value, 'Kick');
  assert.equal($('roster-table').querySelectorAll('.player-card').length, 2);
  assert.match($('roster-table').querySelector('.player-card').textContent, /Attacker fixture/);
  assert.equal($('roster-table').querySelectorAll('.pill.Kick').length, 1);
  assert.equal($('roster-table').querySelectorAll('.pill.Possiblekick').length, 1);
  assert.equal($('kick-flags-info').hidden, false);
  assert.match(w.location.hash, /status=Kick/);
  for (const theme of ['dark','light']) {
    w.WarHavenUI.apply({theme});
    assert.equal(w.document.documentElement.dataset.theme, theme);
    assert.match($('roster-table').querySelector('.pill.Possiblekick').textContent, /Possible kick/);
  }
  w.eval("openPlayer('#P0Q')");
  assert.match($('player-reason').textContent, /Missed both attacks, participated, then missed both again/);
  assert.ok($('player-profile').querySelector('.pill.Possiblekick'));
  w.eval("setTab('planner')");
  assert.equal($('planner').querySelector('[data-lineup-player="#P0Q"]').disabled, false);
  w.eval("window.warHavenIndividual=true;openPlayer('#P0Q')");
  const attendanceBefore=w.eval('JSON.stringify(edits)');
  $('review-attendance-flag').click();
  assert.equal(w.eval('JSON.stringify(edits)'),attendanceBefore);
  assert.equal($('player-profile').querySelector('[data-profile-tab="war"]').getAttribute('aria-selected'),'true');
  assert.equal(w.eval("rows.find(p=>p.tag==='#P0Q').possibleKick"), true);
  assert.equal(w.eval("rows.find(p=>p.tag==='#P0Q').used"), 2);
  assert.equal(w.eval("rows.find(p=>p.tag==='#P0Q').allowed"), 6);
  assert.equal($('cards').querySelector('[data-home-card="kick"] strong').textContent, '2');
  assert.deepEqual(errors, []);
  console.log('Possible-kick DOM passed: grouped counts/filter, severity order, badges in both themes, profile reason, manual planning and reviewed history.');
} finally {
  await new Promise(resolve=>setTimeout(resolve,30));
  dom.window.close();
}
