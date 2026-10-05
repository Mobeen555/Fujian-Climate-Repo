import importlib.util,sys,io,json,zipfile,subprocess
from pathlib import Path
from datetime import date
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('research_update',ROOT/'app.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

@pytest.fixture
def study():return a.make_study('SYNTHETIC QA ONLY',0,0,4,date(2025,1,1),date(2025,12,31))

@pytest.fixture
def run(study):return {'id':'synthetic-research-qa','version':a.VERSION,'created_utc':'2025-06-01T00:00:00Z','study':study,'options':{'modules':[]},'errors':{},'results':{}}

def test_field_clean_local_dates_and_flags(study):
    f=pd.DataFrame({'site':['A','A','A','B'],'sample_id':['s1','s2','dup','dup'],'date':['2025-01-01','2025-05-02 12:00','2025-05-03','2025-05-04'],'latitude':[0,0,0,0],'longitude':[0,0,0,0],'chlorophyll_ug_l':[2,-4,3,4]})
    r=a.research_clean(f,{'mapping':{c:c for c in f},'geometry':study['geometry'],'start':'2025-01-01','end':'2025-12-31','timezone':'Asia/Karachi'})['tables']['Cleaned observations']
    assert r.iloc[0]['included'] and r.iloc[0]['date'].startswith('2024-12-31T19:00')
    assert not r.iloc[0].sampling_time_known and r.iloc[1].sampling_time_known
    assert np.isnan(r.iloc[1].chlorophyll_ug_l)
    assert not r.iloc[2]['included'] and not r.iloc[3]['included']
    assert 'invalid chlorophyll' in r.iloc[1].quality_flags


def test_correlation_and_bh():
    f=pd.DataFrame({'x':np.arange(20.),'y':3*np.arange(20.)+4})
    o=a.research_compute('correlation',f,{'columns':['x','y'],'independent':True,'resamples':99,'seed':4})
    t=o['tables']['Correlations'];assert np.allclose(t.coefficient,1) and np.all(t.permutation_p==.01)
    assert np.allclose(a.research_bh([.01,.04,.03,np.nan])[:3],[.03,.04,.04])
    assert a.research_compute('correlation',f,{'columns':['x','y']})['tables']['Correlations'].permutation_p.isna().all()


def regression_data():
    x=np.linspace(0,10,80)
    return pd.DataFrame({'x':x,'y':4+2*x,'site':np.tile([f'S{i}' for i in range(8)],10),'sample_id':[f'a{i}' for i in range(80)]})

def test_regression_group_split_and_gam():
    f=regression_data();o=a.research_compute('regression',f,{'predictors':['x'],'response':'y','group':'site','seed':42,'model':'Linear'})
    assert o['tables']['Model performance'].RMSE.max()<1e-10
    p=o['tables']['Model predictions']
    assert set(p[p.partition=='Calibration'].site).isdisjoint(p[p.partition=='Held-out evaluation'].site)
    f['y']=1+f.x**2
    o=a.research_compute('regression',f,{'predictors':['x'],'response':'y','group':'site','seed':42,'model':'Gaussian GAM','smoothing':.01})
    assert o['tables']['Model performance'].predictive_R2.min()>.95


def test_regression_blocks_shared_satellite_support():
    f=regression_data();f['support_id']='same pixel'
    with pytest.raises(ValueError,match='satellite'):a.research_compute('regression',f,{'predictors':['x'],'response':'y','group':'site'})


def test_pca_variance():
    f=pd.DataFrame({'x':np.arange(20.),'y':2*np.arange(20.),'z':np.ones(20)})
    t=a.research_compute('pca',f,{'columns':['x','y','z']})['tables']
    assert abs(t['PCA variance'].variance_fraction.iloc[0]-1)<1e-12
    assert len(t['PCA loadings'])==2


def test_community_known_values_and_missing():
    f=pd.DataFrame({'sample_id':['a','a','b','b'],'taxon':['X','Y','X','Y'],'abundance':[1,1,2,0]})
    t=a.research_compute('community',f,{'unlisted_absent':False})['tables']['Community diversity']
    assert abs(t.shannon_ln.iloc[0]-np.log(2))<1e-12
    assert t.simpson_1_D.iloc[0]==.5 and t.shannon_ln.iloc[1]==0
    with pytest.raises(ValueError,match='Unlisted'):a.research_compute('community',f.iloc[:3],{'unlisted_absent':False})


def test_rda_known_gradient():
    x=np.linspace(.05,.95,40);f=pd.DataFrame({'env':x,'taxonA':x*100,'taxonB':(1-x)*100})
    o=a.research_compute('rda',f,{'environment':['env'],'taxa':['taxonA','taxonB'],'independent':True,'resamples':99})
    t=o['tables']['RDA summary'].iloc[0]
    assert t.R2>.95 and t.permutation_p==.01


def test_clustering_separated_groups():
    f=pd.DataFrame({'x':[0,.1,.2,10,10.1,10.2],'y':[0,.1,.2,10,10.1,10.2]})
    o=a.research_compute('cluster',f,{'columns':['x','y'],'clusters':2})['tables']['Cluster assignments']
    assert o.cluster.iloc[:3].nunique()==1 and o.cluster.iloc[3:].nunique()==1 and o.cluster.iloc[0]!=o.cluster.iloc[-1]


def test_monthly_decomposition_and_gap_refusal():
    t=np.arange(48);f=pd.DataFrame({'date':pd.date_range('2021-01-01',periods=48,freq='MS').astype(str),'v':10+t*.1+2*np.sin(2*np.pi*t/12)})
    o=a.research_compute('seasonal',f,{'column':'v'})['tables']['Seasonal decomposition']
    assert np.max(np.abs(o.remainder.dropna()))<1e-10 and o.trend.isna().sum()==12
    with pytest.raises(ValueError,match='24 consecutive'):a.research_compute('seasonal',f.drop(20),{'column':'v'})


def test_agreement_known_errors():
    f=pd.DataFrame({'y':[1,2,3],'pred':[2,3,4]})
    t=a.research_compute('agreement',f,{'reference':'y','estimate':'pred','same_units':True})['tables']['Agreement metrics'].iloc[0]
    assert t.RMSE==t.MAE==t.bias_estimate_minus_reference==1


def snapshot():
    r={'summary':{'scene_id':'QA_SCENE','date':'2025-05-01T05:00:00Z'},'epsg':3857,'transform':(100,0,-250,0,-100,250,0,0,1),'resolution':100,'radiometry':{},'water':np.ones((5,5),bool),'inside':np.ones((5,5),bool),'valid':np.ones((5,5),bool),'arrays':{'NDCI':np.full((5,5),.25),'Water red reflectance':np.full((5,5),.1)}}
    i={'id':'QA_SCENE','properties':{'datetime':'2025-05-01T05:00:00Z'},'geometry':{'type':'Polygon','coordinates':[[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]]}}
    row={'sample_id':'QA_SAMPLE','site':'A','date':'2025-05-01T04:00:00+00:00','latitude':0.,'longitude':0.,'sampling_time_known':True,'satellite_eligible':True,'sampling_timezone':'UTC','sampling_date_local':'2025-05-01','chlorophyll_ug_l':4}
    return r,i,row


def test_satellite_matching_and_shoreline_screen():
    r,i,row=snapshot();s={'hours':3,'pixel_radius':1,'minimum_water_fraction':1.}
    o=a.research_extract_sample(row,i,r,s)
    assert o['matched'] and o['sat_ndci']==.25 and o['time_difference_hours']==1
    r['water'][1,1]=False
    assert not a.research_extract_sample(row,i,r,s)['matched']
    r['water'][:]=True;row['sampling_time_known']=False
    assert not a.research_extract_sample(row,i,r,s)['matched']
    assert a.research_extract_sample(row,i,r,{**s,'allow_date_only':True})['matched']


def test_offline_package_reexecutes_numerical_analysis(run,tmp_path):
    lab={'records':[],'uploads':{},'field':None,'matchups':None,'community':None,'points':[],'scene_snapshots':{}}
    f=regression_data();a.research_record(run,lab,'regression',f,{'predictors':['x'],'response':'y','group':'site','seed':42,'model':'Linear'})
    r,i,row=snapshot();lab['scene_snapshots']={'QA_SCENE':{'item':i,'raster':r}}
    s={'hours':3,'pixel_radius':1,'minimum_water_fraction':1.,'scene_ids':['QA_SCENE']};f=pd.DataFrame([row])
    a.research_record(run,lab,'satellite_matchup',f,s,a.research_offline_match(f,s,lab['scene_snapshots']))
    z=a.research_package(run,lab)
    with zipfile.ZipFile(io.BytesIO(z)) as archive:
        assert archive.testzip() is None
        assert 'reproduce.py' in archive.namelist() and 'satellite/scene_001.tif' in archive.namelist()
        archive.extractall(tmp_path)
    process=subprocess.run([sys.executable,str(tmp_path/'reproduce.py')],capture_output=True,text=True,timeout=60)
    assert process.returncode==0,process.stderr
    out=pd.read_json(io.StringIO((tmp_path/'reproduced/A001/Model_performance.json').read_text()),orient='split')
    assert out.RMSE.max()<1e-9
    matched=pd.read_json(io.StringIO((tmp_path/'reproduced/A002/Field_satellite_matchups.json').read_text()),orient='split')
    assert matched.sat_ndci.iloc[0]==.25 and matched.matched.iloc[0]
