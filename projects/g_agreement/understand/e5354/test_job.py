import ast,json,time
from pathlib import Path
import numpy as np
import pytest
from . import contract as C
from . import e15_scorer as E
from .analyse import score_grid
from .worker import jobs

def test_e15_functions_unchanged():
 original=C.ROOT.parent/'wt-wlens/projects/g_agreement/understand/e15.py'
 if not original.exists():pytest.skip('upstream sibling unavailable; source receipt carries hashes')
 a=ast.parse(original.read_text());b=ast.parse(Path(E.__file__).read_text())
 for name in ('native_score','base_score','valid_pairs'):
  aa=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name==name)
  bb=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name==name)
  assert ast.dump(aa)==ast.dump(bb)

def test_e15_oracle_prompt_and_gate():
 class Fake:
  def paired_logodds_templates(self,h,block,pairs,prefix):return block,prefix,pairs,h
 assert E.native_score('olens',Fake(),[7],[['a','b']])==(44,'- ',[['a','b']],[7])
 assert E.valid_pairs([.799,.8,float('nan'),None,.95])==[1,4]

def test_frozen_pairs_and_donors():
 p=C.ROOT/'cache/g_agreement/understand/e5354/prepared'
 if not p.exists():pytest.skip('staged inputs not present')
 items=C.read(p/'e49_items.json');labels=C.read(C.HERE/'CPU_LABELS.json');pairs=C.read(p/'e49_pairs.json');dm=C.read(p/'e49_donors.json');li={x['id']:x for x in items}
 assert len(items)==1344 and len(dm)==672 and len({x['feature'] for x in items})==8
 for ident,donor in dm.items():
  a,b=li[ident],li[donor]
  assert a['feature']==b['feature'] and a['split']==b['split']=='test'
  assert a['filler_index']==b['filler_index']
  assert labels[ident]['label']!=labels[donor]['label']
  assert pairs[ident]==pairs[donor]
 for row in {x['feature'] for x in items}:
  for split in ('dev','test'):
   group=[x for x in items if x['feature']==row and x['split']==split]
   assert len(group)==84 and sum(labels[x['id']]['label'] for x in group)==42
 assert sum(len(ix) for _,_,ix in jobs(items,pairs,'test'))==672

def test_seal_tamper_and_traversal(tmp_path):
 (tmp_path/'x').write_text('one');C.seal(tmp_path,'s.json');C.verify(tmp_path,'s.json')
 (tmp_path/'x').write_text('two')
 with pytest.raises(ValueError):C.verify(tmp_path,'s.json')
 C.dump(tmp_path/'bad.json',{'files':{'../escape':'abc'}})
 with pytest.raises(ValueError):C.verify(tmp_path,'bad.json')

def assignment():
 now=time.time()-10
 phases=['oracle_setup','parity','e54_capture','e53_base','e53_olens_true','e53_olens_opposite_swap','e36_swap','e54_oracle','nla_setup','e53_nla_true','e53_nla_opposite_swap','e54_nla']
 return dict(issuer='integrator',experiment='E53+E54',gpu_count=1,cap_seconds=5400,gpu_type='H200',external_hardstop_verified=True,pod_id='test',pod_created_epoch=now,deadline_epoch=now+5400,phase_estimates_seconds={k:10. for k in phases})

def test_custody_and_no_fit():
 a=assignment();C.Budget(a)
 for key,value in [('gpu_count',2),('cap_seconds',5401),('external_hardstop_verified',False),('deadline_epoch',a['deadline_epoch']+1)]:
  b=dict(a);b[key]=value
  with pytest.raises(ValueError):C.Budget(b)
 a['phase_estimates_seconds']={k:1000 for k in a['phase_estimates_seconds']}
 with pytest.raises(ValueError,match='NO_FIT'):C.Budget(a)

def test_missing_and_duplicate_grid_rejected():
 i=[{'id':'d','split':'dev'},{'id':'t','split':'test'}]
 raw=[dict(id='d',bank='E49',reader='base',arm='true',scores=[1.])]
 raw +=[dict(id='t',bank='E49',reader=r,arm=a,scores=[1.]) for r in ('olens','nla') for a in ('true','opposite_swap')]
 assert len(score_grid(raw,i,[],[]))==5
 with pytest.raises(ValueError):score_grid(raw[:-1],i,[],[])
 with pytest.raises(ValueError):score_grid(raw+[raw[0]],i,[],[])
 raw[0]['scores']=[float('nan')]
 with pytest.raises(ValueError):score_grid(raw,i,[],[])

def test_signed_auc_and_swap():
 assert C.auc([1,1,0,0],[2,3,0,1])==1
 assert C.auc([1,1,0,0],[0,1,2,3])==0
 assert C.auc([1,0],[2,2])==.5

def test_mock_worker_and_once_analysis(tmp_path,monkeypatch):
 import argparse,shutil,hashlib
 import torch
 from . import worker as W,analyse as A
 from mats import probes
 staged=C.ROOT/'cache/g_agreement/understand/e5354/prepared'
 if not staged.exists():pytest.skip('prepared inputs required')
 inp=tmp_path/'input';inp.mkdir()
 for n in ['e49_items.json','e49_pairs.json','e49_donors.json','e54_items.json','dev_labels.json','e36_items.json','e36_donors.json','e36_pairs.json']:
  shutil.copyfile(staged/n,inp/n)
 i=C.read(inp/'e49_items.json');old=C.read(inp/'e36_items.json');i54=C.read(inp/'e54_items.json')
 for b in (42,44):np.save(inp/f'e49_acts{b}.npy',np.zeros((len(i),5120),np.float32))
 np.save(inp/'e36_acts44.npy',np.zeros((len(old),5120),np.float32))
 C.seal(inp,'INPUT_SEAL.json',{'stage':'BOUND'})
 here=tmp_path/'here';here.mkdir();C.dump(here/'SOURCE_SEAL.json',{'files':{}})
 assets=tmp_path/'assets.json';C.dump(assets,{})
 assign=assignment();assign.update(source_seal_sha256=C.sha(here/'SOURCE_SEAL.json'),input_seal_sha256=C.sha(inp/'INPUT_SEAL.json'),assets_manifest_sha256=C.sha(assets),e49_forecast_commit='a'*40)
 ap=tmp_path/'assignment.json';C.dump(ap,assign)
 state={'parity':False}
 class Fake:
  def __init__(self,*args):self.oracle=self.nla=self;self.tok=self
  def encode(self,*args,**kwargs):return [1]
  def load_oracle(self):pass
  def load_nla(self):pass
  def validate_tokenization(self,items):pass
  def capture(self,items):
   assert state['parity'];return {b:np.zeros((len(items),5120),np.float32) for b in (42,44)}
  def native(self,reader,h):return [{'raw':'text','text':'text','malformed':False} for _ in h]
 def gate(*args):state['parity']=True
 monkeypatch.setattr(W,'Backend',Fake);monkeypatch.setattr(W,'sources',lambda:None);monkeypatch.setattr(W,'HERE',here)
 monkeypatch.setattr(W.parity_gate,'load_inputs',lambda b:None);monkeypatch.setattr(W.parity_gate,'run_gate',gate)
 monkeypatch.setattr(W,'base_score',lambda obj,items,pairs:torch.zeros((len(pairs),len(items))))
 monkeypatch.setattr(W,'native_score',lambda reader,obj,h,pairs:torch.zeros((len(pairs),len(h))))
 out=tmp_path/'output';W.run(argparse.Namespace(inputs=inp,assignment=ap,assets=assets,out=out))
 raw=[json.loads(s) for s in (out/'scores.jsonl').read_text().splitlines()]
 score_grid(raw,i,old,i54);C.verify(out,'OUTPUT_SEAL.json')
 for name in ['CPU_LABELS.json','E36_CPU_LABELS.json','E54_CPU_LABELS.json','EXISTING_ASSEMBLY.json','E54_CHANNELS.json']:shutil.copyfile(C.HERE/name,here/name)
 context=tmp_path/'context';context.mkdir()
 rows={('E49',x['feature']) for x in i}|{(b,x['feature']) for b in ('W1','E36') for x in old}|{('E54',x['feature']) for x in i54}
 C.dump(context/'MAP.json',{'issuer':'integrator','source_seals':{'synthetic':'test'},'rows':[{'bank':b,'row':r,'J_label':'OUT-J','J_label_method':'§169 amendment1 pursuit','probe_auc':None,'oracle_unprompted_mention_rate':None,'class':'structure'} for b,r in sorted(rows)]})
 C.dump(context/'JUDGMENTS.json',[{'id':x['id'],'reader':r,'category':'silent','value':None,'blinded':True,'raw_sha256':hashlib.sha256(b'text').hexdigest()} for x in i54 if x['split']=='test' for r in ('olens','nla')]);C.seal(context,'INPUT_SEAL.json')
 class Fit:
  def decision(self,h):return torch.zeros(len(h))
 monkeypatch.setattr(probes,'fit_logreg',lambda *args,**kwargs:Fit())
 monkeypatch.setattr(A,'sources',lambda:None);monkeypatch.setattr(A,'HERE',here);monkeypatch.setattr(A,'ROOT',tmp_path)
 monkeypatch.setattr(A,'context_binding',lambda *args:None)
 args=argparse.Namespace(inputs=inp,outputs=out,context=context,out=tmp_path/'analysis',output_seal=C.sha(out/'OUTPUT_SEAL.json'),context_seal=C.sha(context/'INPUT_SEAL.json'))
 A.analyse(args);C.verify(args.out,'ANALYSIS_SEAL.json')
 result=C.read(args.out/'E53_RESULTS.json')['R1_pooled']
 assert result['status']=='NOT EVALUABLE' and result['n']==22 and result['missing_rows']==22
 with pytest.raises(FileExistsError):A.analyse(args)
