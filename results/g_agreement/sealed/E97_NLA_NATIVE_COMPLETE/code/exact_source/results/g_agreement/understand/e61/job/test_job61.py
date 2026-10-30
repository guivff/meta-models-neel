import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from runtime61 import position_jobs,base_answer_probability
from displays61 import select_three,verbatim_records,display_html

def test_every_inclusive_token_and_read_point():
    jobs=position_jobs([{'id':'a','display':'D3','arm':'decline','pair_id':'pair','ids':[11,12,13,14,15],'instruction_end_index':1,'pre_answer_index':4},{'id':'b','display':'D4','arm':'think','pair_id':'pair','ids':[1,2,3,4],'read_index':1}])
    assert [x['position'] for x in jobs]==[1,2,3,4,1]
    assert [x['ids'] for x in jobs]==[[11,12],[11,12,13],[11,12,13,14],[11,12,13,14,15],[1,2]]

def test_fixed_selection_not_outcome_dependent():
    assert select_three(['z','a','c','b'])==select_three(['c','b','a','z'])
    assert select_three(['z','a','c','b'])[0]=='a'
    assert len(set(select_three(['z','a','c','b'])))==3

def test_verbatim_export_keeps_all_repeats_and_refuses_missing():
    records=[{'unit_id':'u','reader':r,'repeat':i,'raw':'<tag>\n  exact & text\n'} for r in ('oracle','nla') for i in range(1)]
    out=verbatim_records(records,['u']);assert len(out)==2 and out==records
    assert display_html('demo',out).count('&lt;tag&gt;\n  exact &amp; text\n')==2
    with pytest.raises(ValueError,match='DISPLAY_NOT_ACQUIRED'):verbatim_records(records[:-1],['u'])

def test_probability_uses_base_context_and_frozen_single_token():
    import torch
    from contextlib import contextmanager
    class Model:
        active=False
        def get_input_embeddings(self):return type('E',(),{'weight':torch.zeros(1)})()
        def __call__(self,**kwargs):
            assert self.active and kwargs['input_ids'].tolist()==[[1,2]]
            return type('O',(),{'logits':torch.tensor([[[0.,0.,0.],[0.,0.,np.log(2.)]]])})()
    class Oracle:
        model=Model()
        @contextmanager
        def base(self):
            self.model.active=True
            try:yield
            finally:self.model.active=False
    backend=type('B',(),{'oracle':Oracle()})()
    p=base_answer_probability(backend,{'completion_ids':[1,2],'answer_token_id':2,'id':'x','pair_id':'p','arm':'none','concept':'birds'})
    assert p['probability']==pytest.approx(.5) and not backend.oracle.model.active

def test_white_bear_matched_ratio_and_zero_denominator():
    from measures61 import paired_ratios,timeline_bands
    p=np.tile([.6,.8,1.],(84,1));m=np.tile([1.,.5,0.],(84,1))
    r=paired_ratios(p,m);assert r['R_W']=='MET' and r['base_ignore_over_none']['ratio']==pytest.approx(.8)
    p[:,2]=0;r=paired_ratios(p,m);assert r['R_W']=='NOT EVALUABLE' and r['base_ignore_over_none']['zero_denominator_draws']==2000
    timeline=timeline_bands({0:[[.5,.5]]*12,1:[[.7,.5]]*12});assert timeline['first_difference_at_least_point_two']==1

def test_frozen_bank_prefixes_and_full_acquisition(tmp_path,monkeypatch):
    import runtime61
    from contract56 import ROOT,read,verify
    p=ROOT/'cache/g_agreement/understand/e61/inputs_v1';verify(p,'INPUT_SEAL.json');items=read(p/'items.json');jobs=position_jobs(items)
    assert len(items)==276 and len(jobs)==586
    assert len([x for x in items if x['display']=='D4'])==252
    mapping={}
    for x in items:
        mapping[x['text']]=x['ids']
        if x['display']=='D4':
            assert x['ids']==x['read_ids'] and x['ids']!=x['completion_ids']
            mapping[x['completion_text']]=x['completion_ids'];mapping[x['answer_text']]=[x['answer_token_id']]
    class Fake:
        oracle=type('O',(),{'tok':type('T',(),{'encode':lambda self,t,**k:mapping[t]})()})()
        def load_oracle(self):pass
        def load_nla(self):pass
        def validate_tokenization(self,items):pass
        def capture(self,xs):return {l:np.zeros((len(xs),5120),np.float32) for l in (42,44)}
        def native_one(self,reader,h):return [[{'raw':'silent','text':'silent','malformed':False} for _ in range(1)] for _ in h]
    class Budget:
        end=10**12;observed={}
        def call(self,phase,fn,remaining_units=0):return fn()
    monkeypatch.setattr(runtime61,'base_answer_probability',lambda b,x:dict(item_id=x['id'],pair_id=x['pair_id'],arm=x['arm'],concept=x['concept'],answer_token_id=x['answer_token_id'],probability=.5))
    runtime61.acquire61(items,Fake(),Budget(),tmp_path,{'source_seal_sha256':'synthetic','input_seal_sha256':'synthetic','pod_id':'synthetic'})
    verify(tmp_path,'OUTPUT_SEAL.json')
    assert len((tmp_path/'oracle.native.jsonl').read_text().splitlines())==586
    assert len(read(tmp_path/'BASE_PROBABILITIES.json'))==252
