import importlib.util,json,hashlib
from pathlib import Path
import pytest
P=Path(__file__).with_name('parallel_callables232.py');spec=importlib.util.spec_from_file_location('ops232',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs')

def test_whole_custody_bound_includes_staging_and_all_pending():
 d=m.forecast(100,2000,500,{'native':11,'decoder':3},{'native':[3,7],'decoder':[9,2]});assert d['projected_total_cap_seconds']==1.25*(400+77+27)+60

def test_unknown_pending_phase_never_zero():
 with pytest.raises(AssertionError):m.forecast(0,10000,20,{'future':3},{'native':[1]})

def test_no_fit_includes_25percent_and_60reserve():
 assert m.forecast(0,100,50,{'native':3},{'native':[10]})['status']=='NO_FIT'

def test_equal_length_unpadded_exact_census():
 xs=[{'ids':[1]*n}for n in [2,3,2,4,3,2]];jobs=m.batches(xs,2);assert sorted(i for j in jobs for i in j)==list(range(6));assert all(len({len(xs[i]['ids'])for i in j})==1 and len(j)<=2 for j in jobs)

@pytest.mark.parametrize('exp,part,folder,seal',[('E116','a','e116-inputs-v1/inputs','e7aea4db86d8bcfc9bd4fc838b7a889acb4bb5c1c113fc307d1090bac290c395'),('E120','a','e120-inputs-v1/timing','c511a729dd1fce173cedba8f83734285048a0a1d7d56d24f6d7cca67e8653d97'),('E120','b','e120-inputs-v1/decoder','522295510f3009d49860501cf922f10d03a189fb5b4b6b2994e493f409b31763'),('E120','c','e120c-inputs-v1/inputs','8f295cd6003616ae2b64d923dc44d35a7186dfd20e2220d22df2345e0c1dcf8a'),('E121','a','e121-inputs-v1/inputs','755154672e006d2ded2b6f0479d22a6fe9a8c511421daf2c8aeb3e5ec2bbc038')])
def test_actual_whole_public_packets_exact(exp,part,folder,seal):
 assert m.validate(exp,part,ROOT/folder,seal)

def test_source_calls_retained_and_no_legacy_population_spoof():
 s=P.read_text();assert 'primitive.natural_capture(model,part)'in s and "upstream.READ_BLOCK=42"in s and "upstream.intervene_forward"in s and "b87.sweep(rt,'oracle',v,layer)"in s and 'capture_lens(lens,part)'in s
 assert 'alpha=16000'in s and 'max_new_tokens=128'in s and "b.load_nla"in s and "no label" in s.lower()
