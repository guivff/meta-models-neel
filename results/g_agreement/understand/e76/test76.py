"""E76 CPU synthetic checks; no learned model or real readout scoring."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from contextlib import contextmanager
import common76 as C
import worker76 as W
from regex76 import hits,item_values,bootstrap,validate_grid


def bank(n=500):
    return {'experiment':'E76','schema':'E76_BLIND_V1','source_bank_count':5,
        'items':[{'id':f'{i:032x}','ids':[i+1,2],'bank':i%5} for i in range(n)],'selected_indices':list(range(500))}


class Tests(unittest.TestCase):
    def test_actual_NLA512_wrapper_greedy_stop_uses_generated_suffix(self):
        import torch
        import backend76  # exposes the exact vendored native reader module
        from native_nla512 import native_nla
        class Tok:
            pad_token_id=0
            def batch_decode(self,rows,skip_special_tokens=True):
                words={0:'',1:'<explanation>',2:'fruit',3:'</explanation>',99:'<explanation>',98:'</explanation>'}
                return [''.join(words[int(x)] for x in row) for row in rows]
        class AV:
            def generate(inner,input_ids,**kw):
                self.assertFalse(kw['do_sample']);self.assertEqual(kw['max_new_tokens'],512)
                test=torch.cat([input_ids,torch.tensor([[1,2,3],[1,2,0]])],dim=1)
                self.assertEqual(kw['stopping_criteria'][0](test,None).tolist(),[True,False])
                return torch.cat([input_ids,torch.tensor([[1,2,3],[1,2,3]])],dim=1)
        class NLA:
            device='cpu';prompt_ids=[99,98];tok=Tok();av=AV()
            @contextmanager
            def _inject(self,v):yield
        h=np.ones((2,5120),np.float32);before=h.tobytes();values=native_nla(NLA(),h,k=1,batch=2)
        self.assertEqual([x[0]['text'] for x in values],['fruit','fruit'])
        self.assertTrue(all(x[0]['native_stop']=='</explanation>' and not x[0]['truncated'] for x in values))
        self.assertEqual(h.tobytes(),before)

    def test_source_native_median_and_paired_random_norms(self):
        b=bank();z=np.random.default_rng(20261027).standard_normal((500,5120)).astype(np.float32)
        norms={l:np.array([10+x['bank']+l for x in b['items']],float) for l in (42,44)}
        raw={l:z.copy()*(l/10) for l in (42,44)};pools,meta=C.make_pools(b,norms,raw,z)
        for l in (42,44):
            wanted=np.array([10+x['bank']+l for x in b['items']])
            for arm in C.ARMS:np.testing.assert_allclose(np.linalg.norm(pools[l,arm].astype(float),axis=1),wanted,rtol=1e-6)
        self.assertTrue(meta['random_paired_reference']);self.assertNotEqual(meta['source_bank_median_norms']['42'],meta['source_bank_median_norms']['44'])
        self.assertTrue(np.array_equal(raw[42],z*4.2))

    def test_exact_blind_fields_full_source_scope_selection(self):
        b=bank();self.assertEqual(len(C.validate_bank(b)[0]),500)
        for action in (lambda b:b['items'][0].update(label=1),lambda b:b['selected_indices'].__setitem__(0,1),lambda b:b['items'][0].update(bank=True)):
            bad=copy.deepcopy(b);action(bad)
            with self.assertRaises(ValueError):C.validate_bank(bad)

    def test_negation_and_exact_literal_policy(self):
        f={'patterns':[r'\bopen string\b',r'\bclosed string\b'],'ignore_case':True,'policy':'sentence_negation','negation':r'\bnot\b'}
        self.assertEqual(hits('Not an open string. Closed string.',f),[False,True])
        f={'patterns':[r'(?<!\w)(?:bird|birds)(?!\w)',r'(?<!\w)citrus(?!\w)'],'ignore_case':True,'policy':'whole_word_or_frozen_regex'}
        self.assertEqual(hits('BIRDS, but not birdlike.',f),[True,False])

    def test_any_value_and_random_pseudo_truth_both_neither_zero(self):
        records=[{'pool_index':i,'text':['A-word','B-word','A-word B-word','neither'][i%4]} for i in range(500)]
        row={'status':'AVAILABLE','families':[{'patterns':['A-word','B-word'],'ignore_case':False,'policy':'whole_word_or_frozen_regex','weight':1}]}
        n,s=item_values(records,row);self.assertEqual(n.mean(),.75);self.assertTrue(np.all(s[np.arange(500)%4>=2]==0))
        coins=np.random.default_rng(20261029).integers(0,2,500)
        self.assertEqual(s[0],1 if coins[0]==0 else -1)
        self.assertEqual(bootstrap(np.ones(500))['ci95'],[1.,1.])

    def test_missing_duplicate_or_wrong_layer_grid_stops(self):
        rows=[{'reader':r,'arm':a,'pool_index':i,'layer':44 if r=='oracle' else 42,'repeat':0,'source_bank':i%5,'text':'',
               'native_max_new_tokens':512,'native_stop':'</explanation>'} for r in C.READERS for a in C.ARMS for i in range(500)]
        self.assertEqual(len(validate_grid(rows)),4)
        for bad in (rows[:-1],rows+rows[:1],[{**x,'layer':44} for x in rows]):
            with self.assertRaises(ValueError):validate_grid(bad)

    def test_main_integrator_7000_stage_guard(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(W,'HERE',Path(tmp)),patch.object(W,'CACHE',Path(tmp)):
            p=Path(tmp);(p/'pod_inputs').mkdir()
            for n in ('LAUNCH_REQUEST.json','POD_SOURCE_SEAL.json','pod_inputs/INPUT_SEAL.json'):(p/n).write_text('{}')
            request={'source_seal_sha256':C.sha(p/'POD_SOURCE_SEAL.json'),'input_seal_sha256':C.sha(p/'pod_inputs/INPUT_SEAL.json')}
            a={'issuer':'integrator','track':'Q','experiment':'E76','gpu_count':1,'pod_id':'pod','main_integrator_admitted':True,
               'daily_budget_verified':True,'source_pushed':True,'external_hardstop_verified':True,'hold_renewer_verified':True,
               'source_commit':'a'*40,'request_sha256':C.sha(p/'LAUNCH_REQUEST.json'),**request,
               'stage_started_epoch':0,'absolute_deadline_epoch':7000,'allocated_stage_seconds':7000,'provider_lease_deadline_epoch':7000,
               'phase_forecasts_seconds':{k:100 for k in W.PHASES}}
            self.assertEqual(W.assignment_check(a,request,now=10,pod_id='pod'),6820)
            for k,v in [('allocated_stage_seconds',7001),('main_integrator_admitted',False),('track','I-2'),('absolute_deadline_epoch',7001)]:
                with self.subTest(field=k),self.assertRaises(ValueError):W.assignment_check({**a,k:v},request,now=10,pod_id='pod')

    def test_clock_cannot_bypass_full_remaining_forecast(self):
        with tempfile.TemporaryDirectory() as tmp:
            a={'absolute_deadline_epoch':3600,'phase_forecasts_seconds':{k:100. for k in W.PHASES}}
            clock=W.Clock(a,tmp,clock=lambda:10.);clock.check()
            clock.remaining['nla_readout']=3000
            with self.assertRaises(W.NoFit):clock.check()


if __name__=='__main__':unittest.main()
