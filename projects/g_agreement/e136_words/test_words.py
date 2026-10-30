import unittest,json,tempfile,hashlib
from pathlib import Path
from .run_once import load_readouts,active_scope,CUES
from .words import analyze,assignments,predictor_text
class Tests(unittest.TestCase):
 def rows(self,empty=False):
  return [dict(id=f'{t}:{k}:{a}',base_task=t,pair_id=f'{t}:{k}',split='test',label=a,correct='truth',wrong='decoy',fact_sentence='a benign fact',text='' if empty else ('positive' if a else 'negative')+f' heldword{t}') for t in range(20) for k in range(4) for a in (0,1)]
 def test_positive_and_folds(self):
  rows=self.rows();r,p,models,audit=analyze(rows,20);self.assertEqual(r['oof_auroc'],1.);self.assertEqual(r['carried_component'],'MET')
  for f,(v,m) in zip(audit,models):
   held=[x for x in rows if x['id'] in f['held_ids']]
   for t in {r['base_task'] for r in held}:self.assertNotIn(f'heldword{t}',v.vocabulary_)
 def test_empty_prior(self):
  r,*_=analyze(self.rows(True),20);self.assertEqual(r['oof_auroc'],.5);self.assertEqual(r['carried_component'],'NOT MET');self.assertEqual(r['empty_fold_vocabularies'],5)
 def test_missing_rejected(self):
  with self.assertRaises(ValueError):analyze(self.rows()[:-1],5)
 def test_missing_text_rejected(self):
  rows=self.rows();rows[0]['text']=None
  with self.assertRaises(ValueError):analyze(rows,5)
 def test_dev_rejected(self):
  rows=self.rows();rows[0]['split']='dev'
  with self.assertRaises(ValueError):analyze(rows,5)
 def test_excluded_echo_vs_unexcluded(self):
  rows=self.rows()
  for r in rows:r['text']='TRUTH benign FACT' if r['label'] else 'decoy benign fact'
  excluded,*_=analyze(rows,20);raw,*_=analyze(rows,20,exclude=False)
  self.assertEqual(excluded['oof_auroc'],.5);self.assertEqual(excluded['carried_component'],'NOT MET')
  self.assertEqual(raw['oof_auroc'],1.);self.assertEqual(raw['role'],'DESCRIPTIVE_UNEXCLUDED');self.assertNotIn('carried_component',raw)
 def test_per_item_all_predictor_filter(self):
  a=dict(correct='Paris',wrong='Rome',fact_sentence='the capital of France is Paris',text='PARIS Rome FRANCE capital the is user confident amber')
  self.assertEqual(predictor_text(a),'user confident amber')
  b=dict(correct='Tokyo',wrong='Kyoto',fact_sentence='Japan has Tokyo as its capital',text='PARIS Rome FRANCE capital the is user confident amber')
  self.assertIn('paris',predictor_text(b));self.assertIn('rome',predictor_text(b))
 def test_no_exclusion_metadata_guess(self):
  rows=self.rows();rows[0].pop('fact_sentence')
  with self.assertRaises(ValueError):analyze(rows,20)
 def test_deterministic_groups(self):self.assertEqual(assignments(self.rows()),assignments(list(reversed(self.rows()))))
class SourceTests(unittest.TestCase):
 def test_two_cue_scope_original_rows_unchanged(self):
  xs=[dict(id=f'{cue}:{split}:{i}',cue=cue,split=split,label=i%2) for cue in ('unreliable_tool','sycophancy_pressure','misuse_intent','instruction_to_withhold') for split,n in [('dev',40),('test',160)] for i in range(n)]
  selected=active_scope(xs);self.assertEqual(len(selected),400)
  self.assertEqual({r['cue'] for r in selected},{'sycophancy_pressure','misuse_intent'})
  self.assertEqual(sum(r['split']=='test' for r in selected),320)
  for r in selected:self.assertIs(next(x for x in xs if x['id']==r['id']),r)
  with self.assertRaises(ValueError):active_scope(selected[:-1])

 def test_source_identity_tamper_and_duplicate(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);keys={f'i{i}':dict(base_task=i//32,pair_id=f'p{i//2}',split='test',label=i%2,cue='synthetic',correct='truth',wrong='decoy',fact_sentence='a benign fact') for i in range(320)}
   records=[];entries=[]
   for ident in keys:
    for b in (44,):
     entries.append(dict(item_id=ident,block=b,root=d,seal_name='SEAL.json',seal_sha256='',member='native.json',record_path=[len(records)],identity={'id':ident,'block':b},text_field='text'))
     records.append(dict(id=ident,block=b,text='synthetic only'))
   (root/'native.json').write_text(json.dumps(records));h=hashlib.sha256((root/'native.json').read_bytes()).hexdigest();(root/'SEAL.json').write_text(json.dumps({'files':{'native.json':h}}));sh=hashlib.sha256((root/'SEAL.json').read_bytes()).hexdigest()
   for e in entries:e['seal_sha256']=sh
   spec={'entries':entries};self.assertEqual(len(load_readouts(spec,keys)),320)
   bad={'entries':entries[:-1]+[entries[0]]}
   with self.assertRaises(ValueError):load_readouts(bad,keys)
   entries[0]['identity']['id']='wrong'
   with self.assertRaises(ValueError):load_readouts(spec,keys)
   entries[0]['identity']['id']=entries[0]['item_id'];(root/'native.json').write_text('[]')
   with self.assertRaises(ValueError):load_readouts(spec,keys)
if __name__=='__main__':unittest.main()
