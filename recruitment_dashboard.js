const RecruitmentDashboard=(()=>{
 const sections=[['new','New this scan'],['still','Still available'],['joined_my','Joined War Haven'],['no_longer','No longer available']];
 const labels={NEW:'New this scan',STILL_CLANLESS:'Still clanless',JOINED_MY_CLAN:'Joined War Haven',JOINED_OTHER_CLAN:'Joined another clan',BELOW_FILTERS:'Outside filters',ARCHIVED:'Archived',COOLDOWN_CLANLESS:'Duplicate cooldown',VERIFY_ERROR:'Needs verification'};
 let model=null,observer=null,filters={search:'',section:'all',hall:0,stars:0,league:0,sort:'newest'};
 function legacy(report){
  // Read data from older saved reports; none of their markup or scripts enters the dashboard.
  const doc=new DOMParser().parseFromString(report.html||'','text/html'),groups=Object.fromEntries(sections.map(([key])=>[key,[]]));
  for(const card of doc.querySelectorAll('.candidate')){
   const d=card.dataset,read=s=>card.querySelector(s)?.textContent.trim()||'',times=[...card.querySelectorAll('.timing .local-time')].map(t=>t.dataset.iso||'');
   const badges=[...card.querySelectorAll('.badges .badge')].map(t=>t.textContent.trim());
   const row={name:read('h3'),tag:read('.tag'),townHallLevel:Number(d.th),warStars:Number(d.war),bestTrophies:Number(d.best),trophies:Number(d.trophies),expLevel:Number(d.xp),leagueTierScore:Number(d.league),leagueTierName:badges[2],freshness:badges[0],lifecycle:badges[1],observationWindowSeconds:Number(d.window),detectedAt:d.detected,previousRosterAt:times[0],firstClanlessVerifiedAt:times[2],lastVerifiedAt:times[3],sourceClan:read('.source strong'),leftWithin:read('.timing').match(/Leave window:\s*≤?\s*([^]*?)First verified/)?.[1]?.trim()||'unknown',statusText:read('.gone,.joined-note')};
   row.profileLink=card.querySelector('a.open')?.getAttribute('href');(groups[d.section]||[]).push(row);
  }
  return {groups,turnover:[...doc.querySelectorAll('tbody tr')].map(tr=>({cells:[...tr.children].map(td=>td.textContent.trim())})),updatedAt:report.updatedAt};
 }
 function matches(row,section){
  const q=filters.search.toLowerCase().trim();
  return (!q||[row.name,row.tag,row.sourceClan,row.sourceClanTag,row.currentClan,row.leagueTierName].join(' ').toLowerCase().includes(q))&&(filters.section==='all'||section===filters.section)&&(row.townHallLevel||0)>=filters.hall&&(row.warStars||0)>=filters.stars&&(row.leagueTierScore||0)>=filters.league;
 }
 function compare(a,b){
  const number=k=>(Number(b[k])||0)-(Number(a[k])||0);
  if(filters.sort==='hall')return number('townHallLevel');if(filters.sort==='stars')return number('warStars');if(filters.sort==='best')return number('bestTrophies');
  if(filters.sort==='window')return (Number(a.observationWindowSeconds)||Number.MAX_SAFE_INTEGER)-(Number(b.observationWindowSeconds)||Number.MAX_SAFE_INTEGER);
  return (Date.parse(b.detectedAt)||0)-(Date.parse(a.detectedAt)||0);
 }
 function candidate(row,section){
  const time=(label,value)=>`<div><dt>${label}</dt><dd>${esc(date(value))}</dd></div>`,available=['new','still'].includes(section);
  const tag=WarTracker.tag(row.tag),href=tag&&/^#[0289PYLQGRJCUV]+$/.test(tag)?'https://link.clashofclans.com/en/?action=OpenPlayerProfile&tag='+encodeURIComponent(tag):null;
  const state=labels[row.lifecycle]||row.lifecycle||'';
  const status=section==='joined_my'?`Currently in ${row.currentClan||data.clanName||'your clan'}.`:row.lifecycle==='JOINED_OTHER_CLAN'?`Joined ${row.currentClan||'another clan'}.`:row.statusText||(!available?state:'');
  return `<article class="panel recruit-card"><div class="recruit-identity"><div><h3 class="player-name-with-hall">${townHallIcon(row.townHallLevel)}<span>${esc(row.name||'Unknown player')}</span></h3><span class="tag">${esc(row.tag)}</span></div><span class="pill ${available?'recruit-available':''}">${available?'Available':section==='joined_my'?'Joined':'Unavailable'}</span></div><div class="recruit-badges"><span>${esc(row.freshness||state)}</span><span>${esc(row.leagueTierName||'League unknown')}</span><span>TH ${formatNumber(row.townHallLevel)}</span></div><div class="recruit-metrics">${[['War stars',row.warStars],['Best trophies',row.bestTrophies],['Trophies',row.trophies],['XP',row.expLevel]].map(([label,value])=>`<div><strong>${formatNumber(value)}</strong><small>${label}</small></div>`).join('')}</div><p class="recruit-source">Former clan <b>${esc(row.sourceClan||'Unknown')}</b>${row.sourceClanTag?` <span class="tag">${esc(row.sourceClanTag)}</span>`:''}</p>${status?`<p class="small muted">${esc(status)}</p>`:''}<details class="recruit-history"><summary>Verification &amp; departure history</summary><dl>${time('Last seen in clan',row.previousRosterAt)}${time('Departure detected',row.detectedAt)}<div><dt>Observed leave window</dt><dd>${esc(row.leftWithin||'Unknown')}</dd></div>${time('First verified clanless',row.firstClanlessVerifiedAt)}${time('Latest profile check',row.lastVerifiedAt)}${row.joinedMyClanAt?time('First joined our clan',row.joinedMyClanAt):''}</dl></details>${RecruitmentContacts.status(tag)}${href?`<a class="recruit-open" data-recruit-open="${esc(tag)}" data-recruit-name="${esc(row.name||tag)}" href="${esc(href)}" target="_blank" rel="noopener noreferrer">Open in Clash ${icon('chevron')}</a>`:''}</article>`;
 }
 function reveal(){
  observer?.disconnect();
  if(!('IntersectionObserver'in window)||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){entry.target.classList.remove('recruit-scroll-pending');observer.unobserve(entry.target);}},{threshold:.08,rootMargin:'0px 0px -16px 0px'});
  $('recruitment-results').querySelectorAll('.recruit-card').forEach((card,index)=>{card.style.setProperty('--recruit-delay',Math.min(index%3,2)*55+'ms');card.classList.add('recruit-scroll-pending');observer.observe(card);});
 }
 function renderResults(){
  let total=0;
  $('recruitment-results').innerHTML=sections.filter(([key])=>filters.section==='all'||filters.section===key).map(([key,label])=>{
   const shown=(model.groups[key]||[]).filter(row=>matches(row,key)).sort(compare);total+=shown.length;
   const content=`<div class="recruit-grid">${shown.map(row=>candidate(row,key)).join('')||'<p class="small muted recruit-empty">No candidates match these filters.</p>'}</div>`;
   return ['joined_my','no_longer'].includes(key)?`<details class="recruit-section" ${filters.section===key?'open':''}><summary>${label}<span class="pill">${shown.length}</span></summary>${content}</details>`:`<section class="recruit-section"><div class="section-heading"><h2>${label}</h2><span class="pill">${shown.length}</span></div>${content}</section>`;
  }).join('');
  $('recruitment-count').textContent=total+' matching player'+(total===1?'':'s');RecruitmentContacts.wire($('recruitment-results'));reveal();
 }
 function turnover(){
  const list=model.turnover||[];
  if(!list.length)return '';
  return `<details class="panel recruit-turnover"><summary>Clan turnover <span class="small muted">${list.length} clans</span></summary><div class="table-wrap"><table><thead><tr>${['Clan','Pool','Leavers','Qualifying','Turnover','Value'].map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${list.map(r=>`<tr>${(r.cells||[r.clanName+' '+r.clanTag,r.bucket,formatNumber(r.departuresDetected),formatNumber(r.qualifyingClanlessDepartures),formatNumber(r.turnoverRatePercent)+'%',r.recruitingValue]).map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
 }
 function open(){
  RecruitmentContacts.start(()=>{if(model&&$('recruitment-results'))renderResults();});
  const available=Boolean(recruiterReport.groups||recruiterReport.html),summary=data.recruiterSummary||{},failure=data.recruiterStatus?.ok===false;
  $('recruiter-empty').classList.toggle('hidden',available);$('recruitment-content').classList.toggle('hidden',!available);
  $('recruiter-status').textContent=(available?'Last scan '+date(recruiterReport.updatedAt)+(summary.scannedClans?' · '+formatNumber(summary.scannedClans)+' clans checked':''):recruiterReport.error||'The first cloud recruiting scan has not published yet.')+(failure?' · Latest scan did not finish; showing the previous report.':'');
  if(!available)return;
  if(model){reveal();RecruitmentContacts.load(Object.values(model.groups).flat().map(r=>WarTracker.tag(r.tag)));return;}model=recruiterReport.groups?recruiterReport:legacy(recruiterReport);
  const groups=model.groups,stats=model.stats||{};
  const leagueChoices=[...new Map(Object.values(groups).flat().filter(r=>r.leagueTierScore).map(r=>[r.leagueTierScore,r.leagueTierName])).entries()].sort((a,b)=>a[0]-b[0]);
  $('recruitment-content').innerHTML=miniCards([['Available',(groups.new?.length||0)+(groups.still?.length||0),'recruit'],['New this scan',groups.new?.length||0,'stars'],['Joined our clan',groups.joined_my?.length||0,'users'],['Ever joined',stats.everJoinedMyClanCount??groups.joined_my?.length??0,'check']])+`${summary.baselineCreated?'<p class="notice">The first roster baseline is saved. Later scans detect departures and verify which players are clanless.</p>':''}<div class="panel recruit-filters"><div class="section-heading"><h2>Find your next clanmate</h2><button id="recruit-reset" class="text-button">Reset filters</button></div><div class="growth-controls"><label class="recruit-search">Search<input id="recruit-search" type="search" placeholder="Player, tag or former clan"></label><label>Status<select id="recruit-section"><option value="all">All statuses</option>${sections.map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select></label><label>Minimum Town Hall<input id="recruit-hall" type="number" min="0" max="99" value="0"></label><label>Minimum war stars<input id="recruit-stars" type="number" min="0" value="0"></label><label>Minimum league<select id="recruit-league"><option value="0">Any league</option>${leagueChoices.map(([score,label])=>`<option value="${Number(score)}">${esc(label)}+</option>`).join('')}</select></label><label>Sort by<select id="recruit-sort"><option value="newest">Newest departure</option><option value="window">Tightest leave window</option><option value="hall">Highest Town Hall</option><option value="stars">Most war stars</option><option value="best">Best trophies</option></select></label></div></div><p id="recruitment-count" class="small muted" aria-live="polite"></p><p id="recruit-contact-status" class="small muted" role="status">Loading shared invitation history…</p><div id="recruitment-results"></div>${turnover()}<p class="notice">Availability was verified at the saved scan time. Check each profile before inviting. A departure window shows the time between successful scans, rather than an exact leave time. A U.S. clan listing does not confirm a player’s location or language.</p>`;
  for(const key of ['search','section','hall','stars','league','sort'])$('recruit-'+key).oninput=()=>{filters[key]=['hall','stars','league'].includes(key)?Math.max(0,Number($('recruit-'+key).value)||0):$('recruit-'+key).value;renderResults();};
  for(const[key,value]of Object.entries(filters))$('recruit-'+key).value=value;
  $('recruit-reset').onclick=()=>{filters={search:'',section:'all',hall:0,stars:0,league:0,sort:'newest'};for(const[key,value]of Object.entries(filters))$('recruit-'+key).value=value;renderResults();};renderResults();RecruitmentContacts.load(Object.values(model.groups).flat().map(r=>WarTracker.tag(r.tag)));
 }
 return {open,matches,candidate,invalidate(){model=null;}};
})();
function openRecruiter(){RecruitmentDashboard.open();}
