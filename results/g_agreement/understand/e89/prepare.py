"""Read-only source verification and identity split; never open E67 judgments or fit."""
import hashlib,json,sys,os
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];WT=ROOT.parent
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e67'))
from sources67 import Ledger,load_e49
from sources67_wave2 import load_wave2
CACHE=ROOT/'cache/g_agreement/understand/e89'
Q=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6/results/g_agreement/r/e67_analysis')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 with Path(p).open('x')as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
 os.chmod(p,0o600)
def main():
 CACHE.mkdir(parents=True,exist_ok=True,mode=0o700);ledger=Ledger();test=[];excluded=set();judges={};waves={}
 for wave in (1,2):
  private=WT/f'wt-wsae/cache/g_agreement/understand/e67/wave{wave}/integrator_wave{wave}'
  seal=WT/f'wt-wsae/results/g_agreement/understand/e67/integrator_wave{wave}/INTEGRATOR_SEAL.json';ledger.bind(seal)
  for n,h in read(seal)['files'].items():ledger.bind(private/n,h)
  pairs=read(private/'PAIRING_CONDITION_MAP.PRIVATE.json')['pairs']
  judge=WT/f'wt-wsae/results/g_agreement/understand/e67/judge_wave{wave}'
  packet_seal=ledger.verify(judge,'JUDGE_PACKET_SEAL.json');packets={i:{x['id']:x for x in [json.loads(s)for s in (judge/f'packet_{i:02d}.jsonl').read_text().splitlines()]}for i in (1,2)}
  specpath=Q/f'ANALYSIS_SPEC.wave{wave}.json';ledger.bind(specpath);spec=read(specpath)
  ledger.verify(Q/f'wave{wave}_once','ANALYSIS_SEAL.json') # hash verification only; no result values read
  judges[str(wave)]={}
  for packet,g in spec['terminal_grids'].items():
   path=Path(g['dir']);s=ledger.verify(path,'RESULT_SEAL.json',g['result_seal_sha256'])
   assert s['bank']=='E67' and s['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS'
   judges[str(wave)][packet]=str(path/'JUDGMENTS.json')
  for pair in pairs:
   excluded.add((pair['bank'],pair['item_id']))
   for r in pair['records']:
    x=packets[r['packet']][r['id']];assert hashlib.sha256(x['readout'].encode()).hexdigest()==pair['readout_sha256']
    test.append({'wave':wave,'bank':pair['bank'],'reader':pair['reader'],'item_id':pair['item_id'],'condition':r['condition'],'packet':r['packet'],'opaque_id':r['id'],'text':x['readout'],'cohort':pair['truncation_cohort']})
  waves[str(wave)]=len(pairs)
 pools={**load_e49(ledger),**load_wave2(ledger)};train=[]
 for (bank,reader),xs in pools.items():
  for x in xs:train.append({'bank':bank,'reader':reader,'item_id':x['item_id'],'text':x['readout'],'label':0,'arm':'native','group':bank+'|'+x['item_id']})
 # E59's sealed verbatim blind packet is an exhaustive native-only export.
 b=WT/'wt-wmech/cache/g_agreement/understand/analysis5968_verified/E59';ledger.verify(b/'analysis_once','ANALYSIS_SEAL.json')
 bs=ledger.verify(b/'blind','BLIND_SEAL.json');ledger.bind(b/'PRIVATE_KEY.json',bs['private_key_sha256']);ledger.bind(b/'RECEIPT.json',bs['receipt_sha256'])
 assert read(b/'RECEIPT.json')['verified']is True
 keys={x['opaque_id']:x['source_id']for x in read(b/'PRIVATE_KEY.json')};packet=read(b/'blind/JUDGE_PACKET.json');assert len(keys)==len(packet)==1008
 for x in packet:
  item,reader,repeat=keys[x['id']].rsplit(':',2);assert reader in ('oracle','nla')and repeat=='0'
  train.append({'bank':'E59','reader':reader,'item_id':item,'text':x['readout'],'label':0,'arm':'native','group':'E59|'+item})
 # All 500 random and 500 shuffled readouts per reader, including empty/malformed text.
 b=WT/'wt-wsae/cache/g_agreement/understand/e76';receipt=read(b/'verified-pull/VERIFIED_PULL.json');ledger.bind(b/'verified-pull/VERIFIED_PULL.json')
 assert receipt['verified_complete']is True
 ledger.verify(b/'verified-pull/final','OUTPUT_SEAL.json',receipt['output_seal_sha256']);ledger.verify(b/'cpu_only','CPU_MAP_SEAL.json')
 pm=read(b/'cpu_only/POOL_MAP.PRIVATE.json');mapping={x['pool_index']:x for x in pm['pool_map']};assert len(mapping)==500
 for reader in ('oracle','nla'):
  xs=[json.loads(s)for s in (b/f'verified-pull/final/{reader}.jsonl').read_text().splitlines()];assert len(xs)==1000
  assert len({(x['arm'],x['pool_index'])for x in xs})==1000
  for x in xs:
   m=mapping[x['pool_index']];assert x['arm']in ('random','shuffled')and x['repeat']==0
   train.append({'bank':m['bank'],'reader':reader,'item_id':m['original_item_id'],'text':x['text'],'label':1,'arm':x['arm'],'group':m['bank']+'|'+m['original_item_id']})
 removed=[r for r in train if (r['bank'],r['item_id'])in excluded];train=[r for r in train if (r['bank'],r['item_id'])not in excluded]
 # Joint group assignment keeps both readers, real/placebo records and random/shuffled pairs together.
 groups=sorted({r['group']for r in train});permuted=np.random.default_rng(20261028).permutation(groups);fit=set(permuted[:len(groups)//2])
 for r in train:r['split']='train'if r['group']in fit else'validation'
 assert not {r['group']for r in train}&{b+'|'+i for b,i in excluded}
 assert {r['split']for r in train}=={'train','validation'}
 data={'training':train,'test_text':test,'judgments':judges};write(CACHE/'DATA.PRIVATE.json',data)
 write(CACHE/'SOURCE_BINDING.PRIVATE.json',ledger.files)
 counts={f'{split}|{reader}|{label}':sum(r['split']==split and r['reader']==reader and r['label']==label for r in train)for split in ('train','validation')for reader in ('oracle','nla')for label in (0,1)}
 versions={}
 for name in ('numpy','scipy','sklearn'):
  mod=__import__(name);versions[name]=mod.__version__
 plan={'experiment':'E89','authority':'5e5e3f4073771b11a8306b8980fbccf1b88b6388 §201; direct user order','seed':20261028,'data':{'path':str(CACHE/'DATA.PRIVATE.json'),'sha256':sha(CACHE/'DATA.PRIVATE.json')},'source_binding':{'path':str(CACHE/'SOURCE_BINDING.PRIVATE.json'),'sha256':sha(CACHE/'SOURCE_BINDING.PRIVATE.json')},'item_groups':len(groups),'train_item_groups':len(fit),'validation_item_groups':len(groups)-len(fit),'counts':counts,'E67_sampled_readouts_by_wave':waves,'E67_identity_excluded_training_records':len(removed),'E67_identity_excluded_groups':len({r['group']for r in removed}),'versions':versions,'model':{'word_ngram_range':[1,2],'char_wb_ngram_range':[3,5],'lowercase':True,'min_df':2,'max_df':1.0,'sublinear_tf':False,'smooth_idf':True,'norm':'l2 per vectorizer','feature_union_weights':'1 each; no subsequent normalization','logistic':{'C':1,'solver':'liblinear','penalty':'l2','class_weight':None,'max_iter':2000,'tol':0.0001,'random_state':20261028}},'evaluation':{'primary':'E89 pooled both waves per reader, matched judgments only; E67 original analyses remain unchanged','also_report':'each wave, bank, NLA token-limit cohort, and mismatched diagnostic separately','outcomes':['at least one CONTRADICTED claim','no SUPPORTED claim (includes GENERIC)'],'unparseable':'exclude and count, never set to negative','bootstrap':'2000 nonstratified item-cluster percentile draws, seed20261028; undefined one-class replicates counted and omitted','R_H1':'per reader matched: contradicted AUROC>=0.65 and lower95>0.55 AND no-supported AUROC>=0.65','falsifier':'both primary AUROCs<0.55','top_features':'30 most positive and30 most negative coefficients, with word/char prefix','validation':'placebo-vs-real validation AUROC, no tuning/refit; not E67 claim evaluation'},'cpu_only':True,'fit_before_E67_judgment_opening':True}
 (HERE/'RUN_PLAN.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n');print(json.dumps({'groups':len(groups),'counts':counts,'removed_for_test_identity':len(removed),'test_pairs':waves}))
if __name__=='__main__':main()
