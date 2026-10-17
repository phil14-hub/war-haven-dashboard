import ast
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

def constant(name):
 for node in ast.parse((ROOT/'Clash_War_Tracker.py').read_text()).body:
  if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id==name:
   return ast.literal_eval(node.value)
 raise AssertionError(name)

class HoverTests(unittest.TestCase):
 def test_hover_click_touch_and_keyboard_dismissal(self):
  source=constant('EXTRA_JS');start=source.index('function wireChartInspection(');end=source.index('\nfunction trendMetric',start)
  program=r'''
const assert=require('node:assert/strict');
class Element {
 constructor(){this.hidden=false;this.style={};this.attrs={};this.children=[];this.offsetWidth=100;this.offsetHeight=40;this.classList={add(){},remove(){}};}
 setAttribute(k,v){this.attrs[k]=v;}
 replaceChildren(){this.children=[];}
 appendChild(v){this.children.push(v);}
 getBoundingClientRect(){return {left:30,top:80,width:200,height:20};}
 querySelector(){return this;}
}
const point=new Element(),container=new Element(),events={},windowEvents={};
point.closest=()=>point;
container.querySelectorAll=()=>[point];container.contains=target=>target===point||target===container;
const document={activeElement:point,createElement:()=>new Element(),querySelectorAll:()=>[container],addEventListener:(name,fn)=>events[name]=fn};
const window={addEventListener:(name,fn)=>windowEvents[name]=fn};
let chartTooltipSequence=0,chartDismissBound=false,chartInspectors=new Map(),selected=null;
'''+source[start:end]+r'''
wireChartInspection(container,'point',()=>({value:'42',label:'Value'}),v=>selected=v,()=>selected=null);
const tooltip=container.children[0];
point.onpointerenter({pointerType:'mouse'});assert.equal(tooltip.hidden,false);assert.equal(selected.value,'42');
point.onpointerleave({pointerType:'mouse'});assert.equal(tooltip.hidden,true);assert.equal(selected,null);
point.onpointerenter({pointerType:'mouse'});point.onclick({detail:1});assert.equal(point.attrs['aria-pressed'],'false');point.onpointerleave({pointerType:'mouse'});assert.equal(tooltip.hidden,true);assert.equal(point.attrs['aria-pressed'],'false');
point.onpointerenter({pointerType:'touch'});point.onclick();point.onpointerleave({pointerType:'touch'});assert.equal(tooltip.hidden,false);
events.pointerdown({target:{}});assert.equal(tooltip.hidden,true);assert.equal(selected,null);
point.onfocus();assert.equal(tooltip.hidden,false);point.onblur();assert.equal(tooltip.hidden,true);
point.onfocus();point.onkeydown({key:'Escape',preventDefault(){},stopPropagation(){}});assert.equal(tooltip.hidden,true);
point.onpointerenter({pointerType:'mouse'});container.onpointerleave({pointerType:'mouse'});assert.equal(tooltip.style.display,'none');assert.equal(tooltip.children.length,0);
point.onpointerenter({pointerType:'mouse'});events.pointermove({pointerType:'mouse',target:point});assert.equal(tooltip.hidden,false);events.pointermove({pointerType:'mouse',target:{}});assert.equal(tooltip.hidden,true);
for(const name of ['blur','resize']){point.onpointerenter({pointerType:'mouse'});windowEvents[name]();assert.equal(tooltip.hidden,true);}
point.onpointerenter({pointerType:'mouse'});events.scroll();assert.equal(tooltip.hidden,true);
point.onpointerenter({pointerType:'mouse'});document.hidden=true;events.visibilitychange();assert.equal(tooltip.hidden,true);document.hidden=false;
point.onpointerenter({pointerType:'touch'});point.onpointercancel();assert.equal(tooltip.hidden,true);
console.log('Point/host leave, mouse click, global pointer movement, scrolling, window blur, touch cancellation and keyboard dismissal passed.');
'''
  result=subprocess.run(['node','-e',program],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)

 def test_all_chart_detail_rows_clear_and_have_no_automatic_selected_value(self):
  source=constant('EXTRA_JS')
  common=(ROOT/'shared/dashboard-ui.js').read_text()
  self.assertIn("addEventListener('pointerleave'",common)
  self.assertIn("addEventListener('blur',hide)",common)
  self.assertIn("if(e.key==='Escape')hide()",common)
  self.assertIn("target().textContent=''",common)
  self.assertIn('WarHavenUI.chart',source)
  self.assertNotIn('inspect(trendPoints.findLastIndex',source)

 def test_ohio_and_utah_use_independent_local_clock_times(self):
  source=constant('HTML_TEMPLATE')
  date_fn=next(line for line in source.splitlines() if line.startswith('function date('))
  program=(ROOT/'shared/dashboard-ui.js').read_text()+"\nconst WarTracker={time:Date.parse},preferences={clock24:false};"+date_fn+";process.stdout.write(date('2026-10-16T05:20:00Z'));"
  outputs={}
  for zone in ('America/Denver','America/New_York'):
   result=subprocess.run(['node','-e',program],env={**os.environ,'TZ':zone},capture_output=True,text=True,check=True)
   outputs[zone]=result.stdout
  self.assertIn('11:20:00 PM',outputs['America/Denver'])
  self.assertIn('1:20:00 AM',outputs['America/New_York'])
  self.assertNotIn('Mountain',outputs['America/New_York'])

if __name__=='__main__':unittest.main()
