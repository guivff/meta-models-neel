import unittest
from .rules import classify,summarize,CONDITIONS
from .adapter import validate_record,output_header,verify,sha
import tempfile,json
from pathlib import Path
class Tokenizer:
    def decode(self,ids,skip_special_tokens=False):return ' new'
class Tests(unittest.TestCase):
    def rows(self,n=84):
        return [dict(id=f'{i}:{c}',base_id=str(i),condition=c,**classify('new' if i<n else 'old','old','new',-1,'old')) for i in range(84) for c in CONDITIONS]
    def test_frozen_parser(self):
        for t,w in [(' \n NEW','new'),('old','old'),('old and new','neither'),('newness','neither'),('','neither'),('unknown','neither')]:
            self.assertEqual(classify(t,'old','new',1,'new')['text_value'],w)
    def test_order_and_ties(self):
        self.assertTrue(classify('new','old','new',-1,'old')['agreement'])
        self.assertTrue(classify('new','old','new',1,'new')['agreement'])
        self.assertFalse(classify('new','old','new',0,'new')['agreement'])
    def test_primary_and_falsifier(self):
        self.assertEqual(summarize(self.rows())['R_TX1'],'MET')
        self.assertEqual(summarize(self.rows(67))['R_TX1'],'NOT MET')
        self.assertTrue(summarize(self.rows(42))['falsifier'])
        self.assertFalse(summarize(self.rows(43))['falsifier'])
    def test_agreement_denominator(self):
        xs=self.rows()
        for x in xs:
            if x['base_id']=='0':x.update(classify('neither','old','new',0,'new'))
        r=summarize(xs)['conditions']['e104_steered_8']
        self.assertEqual(r['text_pair_agreement']['n'],83)
        self.assertEqual(r['no_unique_value']['k'],1)
        for x in xs:x.update(classify('neither','old','new',0,'new'))
        self.assertIsNone(summarize(xs)['conditions']['none']['text_pair_agreement']['rate'])
    def test_grid_fail_closed(self):
        for xs in (self.rows()[:-1],self.rows()[:-1]+[self.rows()[0]]):
            with self.assertRaises(ValueError):summarize(xs)
    def test_cohort(self):
        xs=self.rows()
        for x in xs:
            if x['condition']=='none':x.update(classify('old','old','new',-1,'old'))
        r=summarize(xs);self.assertEqual(len(r['E127_text_flipped_bases']),84);self.assertEqual(r['E128_alpha_min_text'],2)
    def test_record_validation(self):
        x=dict(id='i',base_id='b',condition='none')
        r=dict(**x,token_ids=[1],text=' new',text_with_special_tokens=' new',greedy_max_new_tokens=64,first_greedy_token_id=1,stop_reason='eos',pair_logprobs=[[-2,-1]],pair_logits=[[0,1]],pair_mean_a_minus_b=-1)
        self.assertEqual(validate_record(r,x,Tokenizer()),-1)
        for k,v in [('text','other'),('pair_mean_a_minus_b',1),('greedy_max_new_tokens',16),('token_ids',[]),('stop_reason','length')]:
            with self.assertRaises((ValueError,IndexError)):validate_record(dict(r,**{k:v}),x,Tokenizer())
    def test_seal_tamper_and_header(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'data.json').write_text('{}')
            (p/'seal.json').write_text(json.dumps({'files':{'data.json':sha(p/'data.json')}}))
            h=sha(p/'seal.json');verify(p,'seal.json',h)
            (p/'data.json').write_text('[]')
            with self.assertRaises(ValueError):verify(p,'seal.json',h)
        good=dict(experiment='E131',status='COMPLETE',cells=840,max_new_tokens=64,reader_calls=0,judging_calls=0)
        output_header(good)
        for k,v in [('status','NO_FIT'),('cells',839),('max_new_tokens',16),('judging_calls',1)]:
            with self.assertRaises(ValueError):output_header(dict(good,**{k:v}))
    def test_nonfinite(self):
        with self.assertRaises(ValueError):classify('new','old','new',float('nan'),'new')
if __name__=='__main__':unittest.main()
