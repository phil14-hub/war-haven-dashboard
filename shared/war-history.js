function installWarHistory(){
 'use strict';
 if(globalThis.WarHavenWarHistory?.version===1)return;
 const labels={win:'Victory',victory:'Victory',lose:'Defeat',loss:'Defeat',defeat:'Defeat',tie:'Tie',draw:'Tie'};
 const score=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
 function outcome(w,asOf=globalThis.WarHavenUI?.now?.()??Date.now()){
  const recorded=labels[String(w.result||'').toLowerCase()];
  const final=w.state==='warEnded'||w.final===true||Boolean(recorded&&!['preparation','inWar'].includes(w.state));
  if(!final)return {label:Date.parse(w.endTime)<=asOf?'Awaiting final result':null,code:'pending'};
  if(Date.parse(w.endTime)>asOf||w.source==='API'&&(!w.final||!w.rosterComplete||!Number.isFinite(Date.parse(w.observedAt))||Date.parse(w.observedAt)<Date.parse(w.endTime)))return {label:'Awaiting final result',code:'pending'};
  if(recorded)return {label:recorded,code:recorded.toLowerCase()};
  if(score(w.stars)&&score(w.opponentStars)){
   if(w.stars!==w.opponentStars)return w.stars>w.opponentStars?{label:'Victory',code:'victory'}:{label:'Defeat',code:'defeat'};
   if(score(w.destruction)&&w.destruction<=100&&score(w.opponentDestruction)&&w.opponentDestruction<=100){
    return w.destruction>w.opponentDestruction?{label:'Victory',code:'victory'}:w.destruction<w.opponentDestruction?{label:'Defeat',code:'defeat'}:{label:'Tie',code:'tie'};
   }
  }
  return {label:'Awaiting final result',code:'pending'};
 }
 function decorate(){
  const list=document.getElementById('history-list');
  if(!list||typeof WarTracker==='undefined'||typeof data==='undefined'||typeof edits==='undefined')return;
  const kind=document.getElementById('war-kind')?.value;
  const wars=WarTracker.warsFor(data,edits).filter(w=>!kind||w.kind===kind).reverse();
  [...list.querySelectorAll(':scope > .history-card')].forEach((card,index)=>{
   const war=card.dataset.warId?wars.find(w=>w.id===card.dataset.warId):wars[index],heading=card.querySelector('.war-heading');if(!war||!heading)return;
   card.dataset.warId=war.id;
   const result=outcome(war);if(!result.label)return;
   let group=heading.querySelector('.history-result-badges');
   if(!group){group=document.createElement('div');group.className='history-result-badges';for(const pill of [...heading.children].filter(n=>n.classList.contains('pill')))group.append(pill);heading.append(group);}
   let pill=group.querySelector('[data-war-result]');
   if(!pill){pill=document.createElement('span');pill.dataset.warResult='';group.prepend(pill);}
   pill.className='pill war-result '+result.code;pill.textContent=result.label;pill.setAttribute('aria-label','War result: '+result.label);
  });
 }
 function install(){
  if(typeof renderHistory!=='function'||renderHistory.warResultsInstalled)return;
  const original=renderHistory;
  renderHistory=function(...args){const result=original.apply(this,args);decorate();return result;};
  renderHistory.warResultsInstalled=true;decorate();
 }
 if(!document.getElementById('war-history-result-styles')){
  const style=document.createElement('style');style.id='war-history-result-styles';
  style.textContent='.history-result-badges{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px}.history-result-badges .war-result{border:1px solid currentColor}.war-result.victory{background:#245645;color:#a2e5c3}.war-result.defeat{background:#713c47;color:#ffb8bf}.war-result.tie{background:#254765;color:#b6d8f4}.war-result.pending{background:#685130;color:#f5d29c}html[data-theme=light] .war-result.victory{background:var(--success-bg);color:var(--green);border-color:var(--success-line)}html[data-theme=light] .war-result.defeat{background:var(--danger-bg);color:var(--red);border-color:var(--danger-line)}html[data-theme=light] .war-result.tie{background:var(--info-bg);color:var(--blue);border-color:var(--info-line)}html[data-theme=light] .war-result.pending{background:var(--warning-bg);color:var(--amber);border-color:var(--warning-line)}';
  document.head.append(style);
 }
 document.addEventListener?.('war-haven:history-rendered',decorate);
 globalThis.WarHavenWarHistory={version:1,outcome,install};install();
}

