"""CPU-only clarification4 boundary and custody tests; all texts are synthetic."""
import copy, hashlib, json, tempfile, types, unittest
from pathlib import Path
import torch
from . import smoke50 as s
from . import prepare_smoke50 as prep
from .test_smoke import runtime

class Tok:
    def encode(self,text,add_special_tokens=False):
        return ([1]+[ord(x) for x in text[1:].split()]) if text.startswith('*') else [ord(x) for x in text.split()]
    def decode(self,ids): return '*' if ids==[1] else 'x'

def fixtures(text='* a b'):
    return [{'id':hashlib.sha256(str(i).encode()).hexdigest(),'token_ids':[154822,154824,10+i],
             'read_position':2,'expected_readout_sha256':s.core.text_hash(text),
             'expected_token_set_sha256s':sorted(s.token_hashes(Tok().encode(text)))} for i in range(50)]

class Smoke50Tests(unittest.TestCase):
    def test_exact_threshold_requires_eight_of_fifty(self):
        self.assertFalse(s.verdict(7,[.1]*50,0)['passed'])
        self.assertTrue(s.verdict(8,[.1]*50,5)['passed'])
    def test_jaccard_alternative_and_grammar_conjunction(self):
        self.assertTrue(s.verdict(0,[.5]*50,5)['passed'])
        self.assertFalse(s.verdict(50,[1.]*50,6)['passed'])
    def test_partial_and_nonfinite_results_never_pass(self):
        for values in [[1.]*49,[float('nan')]*50]:
            with self.assertRaises(ValueError):s.verdict(50,values,0)
    def test_token_set_jaccard_is_glm_tokens_not_words_or_counts(self):
        x=s.agreement(['* a c']*50,fixtures(),Tok())
        self.assertEqual(x['exact_match_count'],0)
        self.assertEqual(x['median_token_set_jaccard'],.5)
        self.assertTrue(x['passed'])
    def test_empty_missing_marker_and_long_output_fail_grammar(self):
        for output in ['', 'a b', '* '+' '.join(['a']*17), '*']:
            result=s.agreement([output]*50,fixtures(output),Tok())
            self.assertEqual(result['grammar_violation_count'],50)
            self.assertFalse(result['passed'])
    def test_frozen_payload_tamper_fails(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'f';z=Path(td)/'s';f.write_text('{}');z.write_text('{}')
            with self.assertRaises(ValueError):s.load_inputs(f,z)
    def test_separate_weight_archive_and_science_clocks(self):
        q={'allocation_start_epoch':1000,'weight_staging_started_epoch':1000,'weight_staging_finished_epoch':4600,
           'archive_staging_started_epoch':4600,'archive_staging_finished_epoch':5500,'science_start_epoch':5500,'deadline_epoch':6700}
        s.validate_clocks(q,5501)
        for field,value in [('weight_staging_finished_epoch',4601),('deadline_epoch',6701),('archive_staging_started_epoch',4599)]:
            with self.assertRaises(ValueError):s.validate_clocks(q|{field:value},5501)
    def test_e66_rollout_exclusion_and_seeded_selection(self):
        rows=[{'source':'synthetic','tid':str(i),'ids':[154822,154824,11,12],'positions':[2,3],
               'family':'synthetic','truncated':False,'n_tokens_full':4} for i in range(60)]
        a,counts=prep.choose(rows,{('synthetic','0')});b,_=prep.choose(rows,{('synthetic','0')})
        self.assertEqual([(r['tid'],p) for r,p in a],[(r['tid'],p) for r,p in b])
        self.assertEqual(len({r['tid'] for r,p in a}),50)
        self.assertNotIn('0',{r['tid'] for r,p in a})
    def test_native_batch_is_fifty_captures_then_one_greedy_each(self):
        class E:
            n_workers=4;mpos=63;merged=None;tok=Tok()
            prompt_ids=[1]*63+[154518]+[1]*6
            def __init__(self):self.calls=[]
            def capture_h51(self,ids,positions):
                self.calls.append(('capture',len(ids),len(positions)))
                return [torch.ones(1,6144) for _ in ids]
            def set_lens(self,path,keep_base):self.calls.append(('merge',keep_base))
            def verbalize(self,vecs,**kw):
                self.calls.append(('readout',len(vecs),kw));return [['* a b'] for _ in vecs]
        e=E();result=s.run50(fixtures(),runtime(),e,'adapter')
        self.assertTrue(result['passed']);self.assertEqual(result['generated_count'],50)
        self.assertEqual(e.calls[0],('capture',50,50))
        self.assertEqual(e.calls[-1][2],dict(n=1,temperature=0.,cap=16,seed=0,alpha=54.1))
        self.assertNotIn('readout',result)
        self.assertFalse(result['raw_text_retained'])
    def test_suite_rejects_labels_and_wrong_n(self):
        v={'schema_version':2,'authority':'b90325cb','seed':20261027,'source_repo':s.core.DATA_REPO,
           'source_revision':s.core.DATA_REVISION,'fixtures':fixtures()}
        s.validate_fixture(v)
        bad=copy.deepcopy(v);bad['fixtures'][0]['label']='A'
        with self.assertRaises(ValueError):s.validate_fixture(bad)
        bad=copy.deepcopy(v);bad['fixtures'].pop()
        with self.assertRaises(ValueError):s.validate_fixture(bad)
if __name__=='__main__':unittest.main()
