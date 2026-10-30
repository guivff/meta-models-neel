import copy,json
import numpy as np
import pytest
from .normalize import join_packet,native_status,family_ids,verify,sha,validate,BANKS
from .analyze import patterns,real_scores,pool_scores,score_row
from projects.g_agreement.readerbench.scoring import contrast

def record(i,label='A',text='alpha',family=0):return dict(id=str(i),item_id=str(i),label=label,text=text,family=family)
def row():
 return dict(bank='E56',row='fixture',reader='oracle',native_status='REPORTED',native_status_source={},acquisition_status='ACQUIRED',analysis_seal_sha256='fixture',regex_status='AVAILABLE',regex_reason=None,readouts=[record(i) for i in range(4)],frozen_regex={'families':[dict(patterns=[r'\balpha\b',r'\bbeta\b'],policy='whole_word_or_frozen_regex',ignore_case=True,weight=1)]})
def test_lossless_join_empty_and_duplicate():
 packet=[dict(id='opaqueB',readout=''),dict(id='opaqueA',readout='exact\ntext')];key=[dict(source_id='first',opaque_id='opaqueA'),dict(source_id='second',opaque_id='opaqueB')]
 out=join_packet(packet,key);assert list(out)==['first','second'] and out['second']['readout']=='' and out['first']['readout']=='exact\ntext'
 with pytest.raises(ValueError):join_packet(packet,key+[key[0]])
def test_status_uses_sealed_criterion_only():
 assert native_status(None)=='NOT_EVALUABLE'
 assert native_status({'S':None})=='NOT_EVALUABLE'
 assert native_status({'S':.2,'CI95':[.01,.3]})=='REPORTED'
 assert native_status({'S':.2,'CI95':[0,.3]})=='MISSED'
def test_family_assignment_fixed_order_and_weights():
 ann={'b':{'value_words':['z','y']},'a':{'value_words':['a','b']}}
 entry={'status':'AVAILABLE','families':[dict(patterns=['a','b'],policy='whole_word_or_frozen_regex',weight=1),dict(patterns=['z','y'],policy='whole_word_or_frozen_regex',weight=1)]}
 assert family_ids('E57','multi_token_entity',['b','a'],ann,entry)=={'b':1,'a':0}
 entry['families'][0]['weight']=2
 with pytest.raises(ValueError):family_ids('E57','multi_token_entity',['b','a'],ann,entry)
def test_unavailable_never_zero_or_invented_pattern():
 r=row();r.update(regex_status='NOT_EVALUABLE',regex_reason='No frozen value regex');r['frozen_regex']['families']=[]
 assert score_row(r,[])['metric'] is None
 assert family_ids('E56','x',['a'],{},dict(status='UNAVAILABLE'))=={'a':None}
def test_binary_compatibility_with_registered_scorer():
 r=row();pool=[dict(record(i,text='alpha' if i%2 else 'beta'),reader='oracle',arm='random') for i in range(6)];pools=pool+[dict(x,arm='shuffled') for x in pool]
 actual=score_row(r,pools)['placebo_regex']['random'];expected=contrast(r['readouts'],pool,patterns(r['frozen_regex']['families'][0]),True)
 assert actual==expected

def test_weight_families_on_same_vectors_not_independent_draws():
 r=row();r['frozen_regex']['families'].append(dict(patterns=[r'\bgamma\b',r'\bdelta\b'],policy='whole_word_or_frozen_regex',ignore_case=True,weight=1))
 r['readouts'][-1]=record(3,text='gamma',family=1)
 pool=[record(i,text='alpha gamma') for i in range(5)]
 s,n=pool_scores(r,pool);assert set(n)=={1.0} and set(abs(s))=={1.0}
 s,n=pool_scores(r,[record(i,text='alpha') for i in range(5)]);assert set(n)=={.75} and set(abs(s))=={.75}
 assert np.array_equal(real_scores(r)[0],np.ones(4))
def test_exact_frozen_regex_bytes():
 f=dict(patterns=[r'(?<!\\w)(?:a)(?!\\w)',r'b'],ignore_case=True,policy='whole_word_or_frozen_regex')
 assert patterns(f)['A']=='(?i)'+f['patterns'][0] # no repair of prior escaping

def test_seal_tamper_and_escape(tmp_path):
 p=tmp_path/'x';p.write_text('original');seal=tmp_path/'seal';seal.write_text(json.dumps({'files':{'x':sha(p)}}));h=sha(seal);verify(seal,h)
 p.write_text('changed')
 with pytest.raises(ValueError):verify(seal,h)
 seal.write_text(json.dumps({'files':{'../x':'fake'}}))
 with pytest.raises(ValueError):verify(seal,sha(seal))
def test_scope_cannot_shrink():
 with pytest.raises(ValueError):validate(dict(schema='e63-normalized-v2',banks=BANKS,scope_complete=True,rows=[],expected_rows=[]))

def test_parseable_rate_count_does_not_trim_acquired_inventory():
 from .normalize import rate_grid
 rate_grid({'readouts':73,'items':73},{'total':84,'kept':73,'UNPARSEABLE':11},84)
 with pytest.raises(ValueError):rate_grid({'readouts':73,'items':73},{'total':84,'kept':73,'UNPARSEABLE':11},73)
