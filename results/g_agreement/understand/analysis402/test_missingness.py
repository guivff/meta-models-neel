"""Synthetic tests only; no reader outcomes opened."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import custody
from missingness import *

def code(category='states_value',values=None,evidence='A'):
 return dict(id='x',category=category,values=['A'] if values is None else values,evidence=evidence)
def bad():return code('UNPARSEABLE',[], '')
def test_denominator_and_bootstrap():
 assert rate([[1],[None],[-1],[0]])==original_rate([[1],[-1],[0]])
 assert signed_value(bad(),1) is None
 assert rate([[None]])['S'] is None
 assert not reported(rate([[None]]))
def test_validator_matches_terminal_adapter():
 validate_judgment(bad(),'anything')
 validate_judgment(code(values=['B','A'],evidence='“A” - B'),'“a” —   b')
 assert signed_value(code(values=['B','A']),1)==0
 with pytest.raises(ValueError):validate_judgment(code('UNPARSEABLE',[], 'x'),'x')
 with pytest.raises(ValueError):validate_judgment(code(evidence='absent'),'present')
def test_grouping_and_strict_missing_flag():
 native=[dict(id=str(i),reader='oracle',feature='r',unit_id=str(i),repeat=0,kind='text') for i in range(20)]
 private={str(i):dict(label=1,feature='r') for i in range(20)}
 jj={str(i):bad() if i==0 else code() for i in range(20)}
 r=native_rates(dict(native=native,private=private),jj)['oracle','r','text']
 assert r['S']==1 and r['items']==19
 assert metrics(private,native,jj)['oracle','r']==r
 counts=audit(native,jj);assert counts['pooled']==dict(total=20,kept=19,UNPARSEABLE=1,over_5_percent=False)
 jj['1']=bad();assert audit(native,jj)['pooled']['over_5_percent']
 jj={str(i):bad() for i in range(20)}
 assert metrics(private,native,jj)['oracle','r']['status']=='NOT EVALUABLE'
def test_empty_rules_do_not_score_missing_as_zero():
 from test_missing_g3 import fixture56
 from rules56_missing_g3 import rules
 from oracle_rules import rules62
 p,j,r=fixture56();r['oracle',next(iter(p)),'text']={'S':None,'CI95':None}
 assert rules(p,j,r)['readers']['oracle']['R2']=='NOT EVALUABLE'
 p={f'S{s}_L{i}':.95 for s in range(1,6) for i in range(5)}
 j={k:dict(J_fraction=.4) for k in p};r={('oracle',k):dict(S=.4) for k in p};r['oracle','S1_L0']['S']=None
 o=rules62(p,r,j);assert o['readers']['oracle']['R_L1']=='NOT EVALUABLE'
