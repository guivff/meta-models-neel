"""2026-10-25 CPU checks: causal suffix likelihood, seals and timing admission."""
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import torch
from worker import encode_frame, score_batch, forecast_gate, validate_assignment, dump, sha


class ToyModel:
    device=torch.device('cpu')
    def __call__(self,input_ids,attention_mask,position_ids,use_cache,logits_to_keep):
        assert use_cache is False
        # Different context-dependent distributions expose off-by-one and padding bugs.
        n=input_ids.shape[1]
        vocab=torch.arange(11,dtype=torch.float32)
        logits=-(vocab[None,None,:]-(input_ids[:,:,None]+1)%11).abs()
        return SimpleNamespace(logits=logits[:,-logits_to_keep:])


class WorkerTests(unittest.TestCase):
    def test_real_transformer_full_logits_reference(self):
        from transformers import LlamaConfig,LlamaForCausalLM
        torch.manual_seed(20261025)
        model=LlamaForCausalLM(LlamaConfig(vocab_size=11,hidden_size=16,intermediate_size=24,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2)).eval()
        frames=[{'ids':[1,2,3,4,5],'candidate_start':3,'token_count':2},
                {'ids':[7,8,2],'candidate_start':2,'token_count':1}]
        actual=score_batch(model,frames,0)
        for frame,value in zip(frames,actual):
            ids=torch.tensor([frame['ids']])
            with torch.inference_mode():lp=model(ids,use_cache=False).logits[0].log_softmax(-1)
            expected=sum(float(lp[j-1,frame['ids'][j]]) for j in range(frame['candidate_start'],len(frame['ids'])))/frame['token_count']
            self.assertAlmostEqual(value,expected,places=6)

    def test_candidate_mean_and_causal_alignment(self):
        frames=[{'ids':[1,2,3,4,5],'candidate_start':3,'token_count':2},
                {'ids':[7,8,2],'candidate_start':2,'token_count':1}]
        got=score_batch(ToyModel(),frames,0)
        for f,observed in zip(frames,got):
            terms=[]
            for j in range(f['candidate_start'],len(f['ids'])):
                logits=-(torch.arange(11)-(f['ids'][j-1]+1)%11).abs().float()
                terms.append(float(logits.log_softmax(-1)[f['ids'][j]]))
            self.assertAlmostEqual(observed,sum(terms)/len(terms),places=6)
        self.assertNotAlmostEqual(got[0],2*got[0])

    def test_padding_batch_equivalence(self):
        frames=[{'ids':[1,2,3,4,5],'candidate_start':3,'token_count':2},
                {'ids':[7,8,2],'candidate_start':2,'token_count':1}]
        self.assertEqual(score_batch(ToyModel(),frames,0),[score_batch(ToyModel(),[f],0)[0] for f in frames])

    def test_boundary_merge_rejected(self):
        tok=lambda *a,**k:{'input_ids':[1,2],'offset_mapping':[(0,1),(1,4)]}
        with self.assertRaises(ValueError):encode_frame(tok,'x','ab')

    def test_forecast_caps_and_retrieval_reserve(self):
        gate=forecast_gate(20,100,1000,4000,1020)
        self.assertEqual(gate['science_cap_s'],540)
        self.assertEqual(gate['status'],'FIT')
        self.assertEqual(forecast_gate(200,1800,1000,5000,1200)['status'],'NO_FIT')
        self.assertEqual(forecast_gate(20,100,1000,1250,1020)['status'],'NO_FIT')

    def test_literal_frame_and_candidate_only(self):
        seen=[]
        def tok(text,**kwargs):
            seen.append((text,kwargs))
            return {'input_ids':list(range(len(text))), 'offset_mapping':[(i,i+1) for i in range(len(text))]}
        f=encode_frame(tok,'item\n','- value')
        self.assertEqual(seen[0][0],'item\n\n- value')
        self.assertFalse(seen[0][1]['add_special_tokens'])
        self.assertEqual(f['token_count'],7)

    def test_assignment_requires_clarification(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'plan.json';dump(path,{'source_files':{}})
            a={'issuer':'integrator','experiment':'E25','pod_id':'test','plan_sha256':sha(path),
               'source_files':{},'source_published':True,'inputs_published':True,
               'registration_published':True,'external_hardstop_verified':True,
               'previous_science_seconds':0,'setup_allowance_seconds':1500,'science_ceiling_seconds':1800,
               'provider_created_epoch':100,'deadline_epoch':2000}
            old=os.environ.get('RUNPOD_POD_ID');os.environ['RUNPOD_POD_ID']='test'
            try:
                with self.assertRaisesRegex(ValueError,'D clarification'):validate_assignment(a,{'source_files':{}},path,101)
                a['clarification_commit']='e4225a1e'
                choices={'D_definition':'AUROC(s_A-s_B,value_is_A)','clarification_commit':'e4225a1e',
                         'phrasing_aggregation':'mean_of_two_W1_pairs','integrator_acknowledged':True}
                validate_assignment(a,{'source_files':{},'clarifications':choices},path,101)
                with self.assertRaisesRegex(ValueError,'matching plan'):
                    validate_assignment(a,{'source_files':{},'clarifications':choices|{'integrator_acknowledged':False}},path,101)
            finally:
                if old is None:os.environ.pop('RUNPOD_POD_ID',None)
                else:os.environ['RUNPOD_POD_ID']=old


if __name__=='__main__':unittest.main()
