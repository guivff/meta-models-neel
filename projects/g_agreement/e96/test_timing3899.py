import json,math,hashlib
from pathlib import Path
import pytest
from projects.g_agreement.e96 import timing3899 as t,sample_second as s

def fixture(root):
 folders=[]
 for slot,setup in [(0,10),(2,20)]:
  p=root/str(slot);p.mkdir();events=[{'phase':'verify_assets','seconds':5}]
  for phase in t.PHASES:events += [{'phase':phase+'_setup','seconds':setup},{'phase':phase,'seconds':40},{'phase':phase,'seconds':1},{'phase':phase,'seconds':2}]
  (p/'TIMING.json').write_text(json.dumps(events));(p/'RUN.json').write_text(json.dumps({'slot':slot,'status':'COMPLETE'}));(p/'OUTPUT_SEAL.json').write_text(json.dumps({'status':'COMPLETE','files':{'TIMING.json':t.digest(p/'TIMING.json')}}));folders.append(p)
 plan={'rows':[{'slot':1,'readers':['oracle','nla'] if i<10 else ['oracle']} for i in range(18)]};return folders,plan

def test_max_setup_cap_not_first_profile_or_mean(tmp_path):
 folders,plan=fixture(tmp_path);p=t.derive(folders,plan,'frozen',[200,300]);assert p['max_measured_setup_seconds']==80 and p['setup_cap_seconds']==100 and p['registered_custody_cap_seconds']==14400
 assert sum(p['phases'][k]['jobs'] for k in ['generate_oracle','generate_nla'])*32==17920

def test_real_failed_cold_batch_forecast_regression():
 vals=[(360,46.03373812697828,11.656502679952492),(200,26.027532604988664,18.43667362194948),(360,9.453319448046386,.6068952236208458),(200,1.4102308700094,.5125029637067261)]
 p={'margin':1.25,'setup_cap_seconds':927,'phases':{k:{'jobs':n,'first_batch_seconds':first,'steady_batch_seconds':steady} for k,(n,first,steady) in zip(t.PHASES,vals)}}
 old=1.5*44.22770407109056*359;new=t.remaining(p,'generate_oracle',359,[44.22770407109056],33.91980210505426)
 assert old>23000 and new<13000 and new>10000
 # The first batch is retained; slower later measured steady batches increase the forecast.
 assert t.remaining(p,'generate_oracle',358,[44,20],34)>new

def test_runtime_changes_only_timing_expression():
 f,old,new=s.runtime();assert new.replace(s.REPLACEMENT,s.ANCHOR,1)==old
 assert s.original.SEED==20261028 and s.original.BATCH==32 and s.original.CLOSE=='</explanation>'

def test_corrupt_timing_rejected(tmp_path):
 folders,plan=fixture(tmp_path);(folders[0]/'TIMING.json').write_text('[]')
 with pytest.raises(ValueError,match='binding'):t.derive(folders,plan,'frozen',[200,300])

def test_setup_cap_and_original_deadline_enforced(tmp_path,monkeypatch):
 p={'setup_cap_seconds':10};clock=s.Clock(tmp_path,100,p)
 def call(self,phase,fn):self.events.append({'phase':phase,'seconds':11});return None
 monkeypatch.setattr(s.BaseClock,'call',call)
 with pytest.raises(TimeoutError,match='setup cap'):clock.call('generate_oracle_setup',lambda:None)
 assert clock.end==100

def test_no_partial_or_invalid_grid(tmp_path):
 folders,plan=fixture(tmp_path);plan['rows'].pop()
 with pytest.raises(ValueError,match='slot1 grid'):t.derive(folders,plan,'frozen',[200,300])

def test_staging_cap_uses_original_creation_clock():
 assert t.staging_budget(100,430,200)==330
 with pytest.raises(TimeoutError):t.staging_budget(100,430,530)
