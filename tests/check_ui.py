import os,sys,importlib.util,json
from pathlib import Path
from datetime import date
import numpy as np,pandas as pd
from streamlit.testing.v1 import AppTest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
import environment as env
study=env.make_study('SYNTHETIC UI QA ONLY',0,0,4,date(2025,1,1),date(2025,12,31))
study['waterbody_type']='Reservoir'
run={'id':'synthetic-ui-research','version':env.VERSION,'created_utc':'2025-06-01T00:00:00Z','study':study,'options':{'modules':[]},'errors':{},'results':{}}
f=pd.DataFrame({'sample_id':[f'S{i}' for i in range(32)],'site':[f'site-{i%4}' for i in range(32)],'date':pd.date_range('2025-01-01 12:00',periods=32,freq='D',tz='UTC').astype(str),
  'sampling_date_local':pd.date_range('2025-01-01',periods=32,freq='D').strftime('%Y-%m-%d'),'sampling_timezone':'UTC','sampling_time_known':True,
  'latitude':np.zeros(32),'longitude':np.zeros(32),'chlorophyll_ug_l':np.linspace(2,6,32),'turbidity_ntu':np.linspace(3,12,32),'temperature_c':np.linspace(12,24,32),
  'included':True,'satellite_eligible':True,'inside_study':True,'quality_flags':'SYNTHETIC QA only'})
lab={'records':[],'uploads':{},'field':f,'matchups':None,'community':None,'points':[],'scene_snapshots':{},'catalogue':[]}
app=AppTest.from_file(str(root/'app.py'),default_timeout=30)
app.session_state['run']=run
app.session_state['research_'+run['id']]=lab
app.run()
results=[]
def check(label):
  errors=[v.value for v in app.exception]+[v.value for v in app.error]
  results.append({'page':label,'errors':errors})
  if errors:print(label,errors)
for page in ['Overview','Water study','Satellite water maps','River & marine','AI interpretation','Reports & sources','Water research']:
 app.radio(key='page').set_value(page).run();check(page)
for section in ['Field data','Sampling points','Satellite matchups','Statistics','Phytoplankton','External models','Methods & downloads']:
 app.radio(key='research_section').set_value(section).run();check('Research: '+section)
app.radio(key='research_section').set_value('Statistics').run()
next(b for b in app.button if b.label=='Run and record analysis').click().run();check('Correlation executed')
for method in ['Linear regression / GAM','PCA','Clustering','Seasonal decomposition','Evaluate supplied estimates']:
 next(s for s in app.selectbox if s.label=='Method').set_value(method).run();check('Statistics form: '+method)
# Results are printed; no runtime data is written into the source project.
# Exercise recorded water summaries, trophic indices and complete export generation.
app.radio(key='research_section').set_value('Field data').run()
next(b for b in app.button if b.label=='Calculate site and monthly summaries').click().run();check('Water summaries')
next(c for c in app.checkbox if c.label.startswith('This is an appropriate freshwater')).check().run()
next(b for b in app.button if b.label=='Calculate measured trophic indicators').click().run();check('Trophic indicators')
app.radio(key='page').set_value('AI interpretation').run();check('Interpreter form with computed results')
app.radio(key='page').set_value('Reports & sources').run()
next(b for b in app.button if b.label=='Build complete water report package').click().run(timeout=60);check('Complete report and replay ZIP')
assert len(app.get('download_button')) >= 5
# Changing waterbody types changes available water providers; field-only studies remain allowed.
app.radio(key='page').set_value('Water study').run()
for kind in ['River','Lake','Sea / coastal waters']:
 app.selectbox(key='waterbody_kind').set_value(kind).run();check('Study kind: '+kind)
next(b for b in app.button if b.label=='Save water study and run selected analyses').click().run();check('Save field-only marine study')
assert app.session_state['run']['study']['waterbody_type']=='Sea / coastal waters'
assert app.session_state['run']['results']=={}
assert not any(x['errors'] for x in results),results
print('UI checks passed',len(results))
