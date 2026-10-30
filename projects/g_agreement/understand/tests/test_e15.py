from contextlib import nullcontext
import json
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.understand import e15 as E,e15_pairs as C


def test_dev_validity_threshold_fixed_no_sign_flip():
    assert E.valid_pairs([.799999,.80])==[1]
    assert E.valid_pairs([.1,float('nan')])==[]
    assert E.valid_pairs([.9,1.])==[0,1]


def test_pairs_match_committed_freeze_and_native_token_counts():
    path=os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    if not path:pytest.skip('pinned Qwen tokenizer required')
    actual=C.frozen_pairs(C.load_pinned_tokenizer(path))
    assert actual==json.loads((E.FROZEN/'CONTINUATION_PAIRS.json').read_text())
    assert len(actual['rows'])==8
    assert all(1<=p['tokens_per_candidate']<=4 and len(p['A_ids'])==len(p['B_ids']) for r in actual['rows'].values() for p in r['pairs'])


def test_oracle_uses_native_prompt_and_own_bullet_prefix():
    seen={}
    class Reader:
        def paired_logodds_templates(self,h,layer,pairs,prefix):
            seen.update(layer=layer,prefix=prefix,pairs=pairs)
            return np.zeros((2,len(h)))
    pairs=[(')','('),(')\n','(\n')]
    E.native_score('olens',Reader(),np.zeros((3,4)),pairs)
    assert seen=={'layer':44,'prefix':'- ','pairs':pairs}


def test_nla_continuations_do_not_gain_explanation_prefix(monkeypatch):
    import mats.readers.nla as N
    seen={}
    def scorer(obj,h,pairs,prefix,batch):
        seen.update(prefix=prefix,batch=batch);return np.zeros((2,len(h)))
    monkeypatch.setattr(N,'paired_logodds_templates',scorer)
    E.native_score('nla',object(),np.zeros((3,4)),[(')','('),(')\n','(\n')])
    assert seen=={'prefix':'','batch':32}


def test_base_reference_predictive_positions_with_mixed_right_padding():
    class Model(torch.nn.Module):
        def __init__(self):super().__init__();self.anchor=torch.nn.Parameter(torch.zeros(()))
        def forward(self,input_ids,attention_mask,logits_to_keep,use_cache):
            logits=torch.zeros((len(input_ids),len(logits_to_keep),7))
            targets=(input_ids[:,logits_to_keep]+1)%7
            logits.scatter_(2,targets[:,:,None],3.)
            return SimpleNamespace(logits=logits)
    class Tok:
        def encode(self,s,add_special_tokens=False):return {'A':[3,4],'B':[5,6]}[s]
        pad_token_id=0
    ol=SimpleNamespace(model=Model(),tok=Tok(),base=nullcontext)
    result=E.base_score(ol,[{'ids':[1,2]},{'ids':[4]}],[('A','B')])
    assert result.shape==(1,2)
    assert result.numpy()[0]==pytest.approx([3.,-3.],abs=1e-6)
