from pathlib import Path
import sys
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B))
import Clash_War_Tracker as t
from tests.test_upgrade_progress import profile
s=t.new_state(t.DEFAULT_CLAN_TAG);s.update(lastSuccessfulSync='2026-10-17T10:00:00Z',clanName='War Haven',policyStart='2026-10-01T00:00:00Z',trackingStarted=True,clanProfile={'tag':t.DEFAULT_CLAN_TAG,'name':'War Haven','clanLevel':4,'members':3,'clanCapital':{},'warLeague':{'name':'Gold I'}},roster=[{'tag':'#P0Q','name':'Omid fixture','townHallLevel':18,'role':'leader','warPreference':'in','trophies':3000,'donations':50},{'tag':'#P0Y','name':'Attacker fixture','townHallLevel':14,'role':'member','warPreference':'in','trophies':2000,'donations':10},{'tag':'#P0U','name':'Unknown fixture','townHallLevel':18,'role':'member','warPreference':'in','trophies':2000,'donations':10}])
p=profile(18)
for v in p['troops']:
 if v['name'] in ('L.A.S.S.I','LASSI'):v['level']=3
 if v['name']=='Mighty Yak':v['level']=7
 if v['name']=='Electro Owl':v['level']=14
s['profiles']={'#P0Q':p,'#P0Y':profile(14)}
s['wars']=[{'id':'w1','kind':'Regular','state':'warEnded','final':True,'rosterComplete':True,'teamSize':2,'endTime':'2026-10-16T10:00:00Z','startTime':'2026-10-15T10:00:00Z','attacksPerMember':2,'expEarned':150,'opponent':{'name':'Fixture clan'},'participants':[{'tag':'#P0Q','name':'Omid fixture','attacksUsed':0,'townHallLevel':18},{'tag':'#P0Y','name':'Attacker fixture','attacksUsed':2,'townHallLevel':14,'attacks':[{'stars':3},{'stars':2}]}]}]
s['clanHistory']=[{'at':'2026-10-15T10:00:00Z','clanLevel':3,'members':3,'leaguePoints':100},{'at':'2026-10-17T10:00:00Z','clanLevel':4,'members':3,'leaguePoints':200}]
t.capture_leadership(s);t.write_dashboard(s,B/'tests/fixtures/leadership.html')
