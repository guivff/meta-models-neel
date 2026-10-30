import importlib.util,sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];late=R/'cache/g_agreement/i2/e85_retained_section223_a2/runtime/results/g_agreement/understand/late198';sys.path.insert(0,str(late));sp=importlib.util.spec_from_file_location('e84full',Path(__file__).with_name('e84_fullprefix223.py'));M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
def grid():
 items=[dict(id=str(i),input_ids=[1]*(71574 if i==0 else 12),prompt='opaque',read_position=71573 if i==0 else 11,reader_allowed=i>=100,split='dev'if i<100 else'test')for i in range(300)]
 base=[dict(id=x['id'],input_ids=x['input_ids'],prompt=x['prompt'],read_position=x['read_position'])for x in items[100:]];return items,base
def test_full_frozen_grid_no_crop():
 a,b=grid();v=M.validate(a,b);assert len(v[0]['input_ids'])==71574 and len(v)==300
@pytest.mark.parametrize('change',['crop','promote_dev','drop','position','private'])
def test_source_changes_rejected(change):
 a,b=grid()
 if change=='crop':a[0]['input_ids']=[1]*512;a[0]['read_position']=511
 if change=='promote_dev':a[0]['reader_allowed']=True
 if change=='drop':a.pop()
 if change=='position':a[1]['read_position']=3
 if change=='private':a[0]['truth']='private'
 with pytest.raises(ValueError):M.validate(a,b)
def test_fit_retains_all_remaining_and_margin():
 d=M.measured_fit(100,[2,3,4],297,500,1000);assert d['need_seconds']==100+1.25*(4*297+500+1000)+60 and d['status']=='PASS'
 assert M.measured_fit(100,[20],297,500,1000)['status']=='NO_FIT'
def test_reader_gates_independent_and_bow_descriptive():
 sp=importlib.util.spec_from_file_location('gate84',Path(__file__).with_name('e84_cpu_gate223.py'));g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
 assert g.disposition(.90,.66)==dict(native_pass=True,text_readable=True,descriptive_only=True)
 assert not g.disposition(.899,.65)['native_pass']
 assert not g.disposition(.95,.65)['descriptive_only']
def test_auroc_ties_and_direction():
 sp=importlib.util.spec_from_file_location('gate84',Path(__file__).with_name('e84_cpu_gate223.py'));g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
 assert g.auc([0,1],[0,1])==1 and g.auc([0,1],[1,1])==.5
