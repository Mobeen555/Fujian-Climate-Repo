"""Water-only scope, provider failures, evidence binding and single-call interpretation."""
import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app as a
import environment as e
import evidence
import interpretation as ai
import water_data as water

@pytest.fixture
def run():
    study=e.make_study('SYNTHETIC QA WATER ONLY',0,0,1,date(2025,1,1),date(2025,12,31))
    study['waterbody_type']='Reservoir'
    r=e.execute_analysis(study,{'modules':[]})
    m=e.result('Field observations')
    m['tables']['Included field observations']=pd.DataFrame({'date':pd.to_datetime(['2025-01-10','2025-02-10']),
        'site':['A','B'],'latitude':[0,np.nan],'longitude':[0,np.nan],
        'chlorophyll_ug_l':[10,20],'temperature_c':[20,21]})
    m['sources']=[e.source_record('U1','Synthetic test fixture','Unverified measurements','2025-03-01','2025','point','QA only')]
    m['facts']=['[U1] Two synthetic reference samples for testing.']
    r['results']['Field observations']=m
    return r


def test_scope_and_field_only(run):
    assert water.available_modules('River')==['Satellite','River outlook']
    assert water.available_modules('Sea / coastal waters')==['Satellite','Marine outlook']
    assert water.available_modules('Lake')==['Satellite']
    assert set(e.MODULES)=={'Satellite','River outlook','Marine outlook'}
    assert e.execute_analysis(run['study'],{'modules':[]})['results']=={}
    failed=e.execute_analysis(run['study'],{'modules':['Marine outlook','Air quality']})
    assert len(failed['errors'])==2 and not failed['results']
    assert not (ROOT/'agents').exists()
    assert 'crewai' not in (ROOT/'requirements.txt').read_text().lower()


def test_trophic_restriction_and_units(run):
    f=run['results']['Field observations']['tables']['Included field observations'].copy()
    f['chlorophyll_ug_l']=[10,0];f['secchi_m']=[2,0];f['total_phosphorus_ug_l']=[30,np.nan]
    for kind in ('River','Sea / coastal waters'):
        with pytest.raises(ValueError):a.research_compute('trophic',f,{'waterbody_type':kind,'confirmed':True})
    with pytest.raises(ValueError):a.research_compute('trophic',f,{'waterbody_type':'Lake','confirmed':False})
    t=a.research_compute('trophic',f,{'waterbody_type':'Reservoir','confirmed':True})['tables']['Measured trophic indices']
    assert t.tsi_chlorophyll.iloc[0]==pytest.approx(53.18835976)
    assert t.tsi_secchi.iloc[0]==pytest.approx(50.01174913)
    assert t.iloc[1][['tsi_chlorophyll','tsi_secchi','tsi_phosphorus']].isna().all()


def test_water_summary_does_not_fill_absent_months(run):
    f=run['results']['Field observations']['tables']['Included field observations'].copy()
    f['date']=['2025-01-10','2025-03-10'];f['site']='A'
    o=a.research_compute('water_summary',f,{'columns':['chlorophyll_ug_l']})
    t=o['tables']['Monthly observed means']
    assert list(t.month)==['2025-01','2025-03']
    assert list(t['mean'])==[10,20]
    fig=a.research_plot(o['plots'][0],o['tables'])
    assert fig.axes[0].get_xlabel()=='date'
    a.plt.close(fig)


def test_coastal_field_units_flag_bad_values(run):
    f=pd.DataFrame({'site':['A','A'],'date':['2025-01-01','2025-01-02'],'salinity_psu':[35,-1],
                    'conductivity_us_cm':[52000,-2],'latitude':[0,0],'longitude':[0,0]})
    s={'mapping':{c:c for c in f},**{k:run['study'][k] for k in ('geometry','start','end')},'timezone':'UTC'}
    t=a.research_clean(f,s)['tables']['Cleaned observations']
    assert t.salinity_psu.iloc[0]==35 and np.isnan(t.salinity_psu.iloc[1])
    assert np.isnan(t.conductivity_us_cm.iloc[1])


def marine_fixture():
    return {'latitude':25,'longitude':120,'hourly':{'time':['2025-10-01T00:00','2025-10-01T01:00'],
            'sea_surface_temperature':[25,None],'wave_height':[1,2], 'ocean_current_velocity':[None,None]},
            'hourly_units':{'sea_surface_temperature':'°C','wave_height':'m','ocean_current_velocity':'km/h'}}


def test_marine_nulls_units_and_attribution():
    m=water.parse_marine(marine_fixture(),'2025-10-01T00:00:00Z')
    t=m['tables']['Marine hourly forecast']
    assert pd.isna(t.sea_surface_temperature.iloc[1])
    assert m['metrics']['Mean modelled sea-surface temperature (°C)']==25
    assert 'Marine model forecast' in m['sources'][0]['evidence_type']
    assert any('Unavailable variables' in n for n in m['notes'])
    raw=marine_fixture();raw['hourly']={'time':['2025-01-01'],'sea_surface_temperature':[None]}
    with pytest.raises(e.DataError):water.parse_marine(raw,'2025')


def test_failed_provider_retains_no_fake_data(run,monkeypatch):
    run['study']['waterbody_type']='Sea / coastal waters'
    def fail(*args,**kwargs):raise e.DataError('Synthetic outage')
    monkeypatch.setattr(water,'marine_module',fail)
    r=e.execute_analysis(run['study'],{'modules':['Marine outlook']})
    assert not r['results'] and r['errors']['Marine outlook']=='Synthetic outage'


class Response:
    status_code=200
    def json(self):return {'model':'test-model','choices':[{'finish_reason':'stop','message':{'content':'AI interpretation: the supplied measurements require independent validation [U1].'}}],'usage':{'total_tokens':30}}


def test_exactly_one_llm_request_and_evidence_binding(run,monkeypatch):
    calls=[]
    def post(url,**kw):calls.append((url,kw));return Response()
    monkeypatch.setattr(ai.requests,'post',post)
    r=ai.interpret_results(run,'gemini','test-model','secret-QA','Explain evidence',enforce_interval=False)
    assert len(calls)==1 and r['request_count']==1
    assert 'tools' not in calls[0][1]['json']
    assert 'secret-QA' not in json.dumps(r)
    assert evidence.interpretation_is_current(run,r)
    run['results']['Field observations']['tables']['Included field observations'].loc[0,'chlorophyll_ug_l']=100
    assert not evidence.interpretation_is_current(run,r)


def test_quota_failure_never_retries(run,monkeypatch):
    calls=[]
    def post(*args,**kwargs):
        calls.append(1);r=Response();r.status_code=429;return r
    monkeypatch.setattr(ai.requests,'post',post)
    with pytest.raises(e.DataError,match='quota'):ai.interpret_results(run,'gemini','test-model','QA','Explain',enforce_interval=False)
    assert len(calls)==1


def test_unknown_ai_citation_rejected(run,monkeypatch):
    class Invalid(Response):
        def json(self):return {'choices':[{'finish_reason':'stop','message':{'content':'Unverified concentration [Z9]'}}]}
    monkeypatch.setattr(ai.requests,'post',lambda *args,**kw:Invalid())
    with pytest.raises(e.DataError,match='source IDs'):ai.interpret_results(run,'gemini','test-model','QA','Explain',enforce_interval=False)


def test_maps_exports_and_pdf_include_current_interpretation(run):
    # Missing coordinates must not crash the map; no position is invented.
    a.map_for_run(run)
    saved={'status':'complete','fingerprint':evidence.run_fingerprint(run),'model':'test','generated_utc':'2025-01-01',
           'answer':'AI interpretation of synthetic test data [U1].','request_count':1}
    ex=e.build_exports({**run,'interpretation':saved})
    assert ex['pdf'].startswith(b'%PDF') and b'Optional AI interpretation' in ex['html']
    assert b'Five-agent' not in ex['html'] and b'Earthquake' not in ex['html']
    with zipfile.ZipFile(io.BytesIO(ex['zip'])) as z:
        assert 'interpretation/provenance.json' in z.namelist()
        assert all('agent' not in n for n in z.namelist())
    stale=dict(saved,fingerprint='outdated')
    with pytest.raises(e.DataError):e.build_exports({**run,'interpretation':stale})


def test_marine_rejects_unit_mismatch():
    raw=marine_fixture();raw['hourly_units']['sea_surface_temperature']='°F'
    with pytest.raises(e.DataError,match='units'):water.parse_marine(raw,'2025')


def test_new_water_calculations_replay(run,tmp_path):
    import subprocess
    f=run['results']['Field observations']['tables']['Included field observations'].copy()
    lab={'records':[],'uploads':{},'field':None,'matchups':None,'community':None,'points':[],'scene_snapshots':{}}
    a.research_record(run,lab,'water_summary',f,{'columns':['chlorophyll_ug_l']})
    a.research_record(run,lab,'trophic',f,{'waterbody_type':'Reservoir','confirmed':True})
    package=a.research_package(run,lab,include_interpretation=False)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:archive.extractall(tmp_path)
    proc=subprocess.run([sys.executable,str(tmp_path/'reproduce.py')],capture_output=True,text=True,timeout=30)
    assert proc.returncode==0,proc.stderr
    table=pd.read_json(io.StringIO((tmp_path/'reproduced/A002/Measured_trophic_indices.json').read_text()),orient='split')
    assert table.tsi_chlorophyll.iloc[0]==pytest.approx(53.18835976)


def test_river_uses_valid_model_parameter_and_retains_history_failure(run,monkeypatch):
    calls=[]
    def response(url,params):
        calls.append(params)
        assert params['models']=='seamless_v4'
        if 'start_date' in params:raise e.DataError('Synthetic history unavailable')
        return {'latitude':0,'longitude':0,'daily':{'time':['2025-01-01'],'river_discharge':[10],'river_discharge_p25':[8],'river_discharge_p75':[12]}},'2025-01-01'
    monkeypatch.setattr(water,'request_json',response)
    run['study']['waterbody_type']='River'
    water.river_module.clear()
    out=water.river_module(run['study'])
    assert len(calls)==2
    assert list(out['tables'])==['Discharge forecast']
    assert any('Historical discharge unavailable' in n for n in out['notes'])
