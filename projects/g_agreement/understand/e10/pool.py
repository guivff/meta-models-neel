"""Read source pools read-only, preserve raw generated text, freeze before E10 API."""
from pathlib import Path
from collections import Counter
from . import io as I
W1=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/blindspot/w1-readonly-20261024/w1-units/priority')
S61=Path('/Users/guivff/Documents/Neel_Exploration/wt-p3/.p3_cache/s61')
W6=Path('/Users/guivff/Documents/Neel_Exploration/wt-inverter/cache/g_agreement/blindspot/w6/assigned_6cqsfmucwej2gj/host/terminal_pull')

def build():
 sources=[];pairs=[];missing=[]
 def source(p):
  p=Path(p);sources.append({'path':str(p),'bytes':p.stat().st_size,'sha256':I.sha(p)});return p
 def verify(base,name):
  seal=I.read(source(base/name))
  for rel,h in seal['files'].items():
   p=base/rel
   if Path(rel).is_absolute() or '..' in Path(rel).parts or I.sha(p)!=h:raise ValueError('source seal mismatch '+rel)
  return seal
 def add(dataset,case,oracle,nla,meta):
  pid=I.rank('pair',dataset,case)
  if not isinstance(oracle,str) or not isinstance(nla,str) or not oracle.strip() or not nla.strip():missing.append({'pair_id':pid,'dataset':dataset,'case':case,'reason':'EMPTY_READOUT'});return
  pairs.append({'pair_id':pid,'dataset':dataset,'case':case,'oracle':oracle,'nla':nla,'oracle_sha256':I.digest(oracle),'nla_sha256':I.digest(nla),'examples_eligible':not(dataset=='W1' and meta.get('item_id')==I.EXPOSED_W1_ITEM),**meta})
 for phase in ['target','nla']:verify(W1/phase,'FREE_SEAL.json')
 verify(W1/'target','CAPTURE_SEAL.json')
 a=I.rows(source(W1/'target/unasked.target.jsonl'));b=I.rows(source(W1/'nla/unasked.nla.jsonl'))
 a={(r['id'],r['sample']):r for r in a if r['reader']=='olens'};b={(r['id'],r['sample']):r for r in b if r['reader']=='nla'}
 if set(a)!=set(b):raise ValueError('W1 paired coverage')
 order=I.read(source(W1/'target/items.order.json'))
 for key in sorted(a):
  o,n=a[key],b[key]
  if o['canonical_index']!=n['canonical_index'] or o['id'] not in order:raise ValueError('W1 source-state mismatch')
  add('W1',I.canonical(key),o['raw'],n['raw'],{'item_id':key[0],'sample':key[1],'sites':[44,42],'source_parser_status':[o['status'],n['status']],'activation_match':'same captured item/token at each native site; not identical cross-layer vectors'})
 plan=I.read(source(S61/'PART_A_PLAN.json'))
 for name,meta in plan['files'].items():
  if I.sha(S61/name)!=meta['sha256']:raise ValueError('S61 frozen source changed '+name)
 mapping=I.rows(source(S61/'mapping.DO_NOT_SEND.jsonl'));requests={r['id']:r for r in I.rows(source(S61/'requests.jsonl'))}
 excluded_mismatch=0
 for r in sorted(mapping,key=lambda r:r['id']):
  if r['kind']!='matched':excluded_mismatch+=1;continue
  import json
  texts=json.loads(requests[r['request_id']]['payload']['messages'][1]['content']);values=list(texts.values())
  oracle=next((s for s in values if I.digest(s)==r['oracle_text_sha256']),None);nla=next((s for s in values if I.digest(s)==r['nla_text_sha256']),None)
  if oracle is None or nla is None:raise ValueError('S61 readout hash mismatch')
  add('S61',r['id'],oracle,nla,{'item_id':r['item_id'],'condition':r['condition'],'source_dataset':r['dataset'],'sites':[44,r['nla_layer']],'activation_match':'original S61 matched case; each reported site preserved'})
 verify(W6,'SCORE_SEAL.json');wr=I.read(source(W6/'experiment/native/raw_scores.json'));wm={}
 for r in wr:
  row,reader,dose,item=r['key'];wm.setdefault((row,dose,item),{})[reader]=r['readout']
 if len(wm)!=480 or any(not v.get('oracle') or (v.get('nla') or '').strip() for v in wm.values()):raise ValueError('W6 missing-partner inventory changed')
 for case,v in sorted(wm.items()):missing.append({'pair_id':I.rank('pair','W6',case),'dataset':'W6','case':case,'reason':'NLA_EMPTY_EXCLUDED_BY_USER','oracle_sha256':I.digest(v['oracle']),'oracle_characters':len(v['oracle'])})
 pairs.sort(key=lambda r:r['pair_id'])
 if len({r['pair_id'] for r in pairs})!=len(pairs):raise ValueError('duplicate pool pair')
 I.CACHE.mkdir(parents=True,exist_ok=True);I.OUT.mkdir(parents=True,exist_ok=True)
 I.jsonl(I.CACHE/'pool.private.jsonl',pairs);I.jsonl(I.CACHE/'missing.private.jsonl',missing)
 blind=[]
 for r in pairs:
  swap=int(I.rank('AB',r['pair_id'])[:8],16)%2;blind.append({'pair_id':r['pair_id'],'READOUT_A':r['nla'] if swap else r['oracle'],'READOUT_B':r['oracle'] if swap else r['nla']})
 I.jsonl(I.CACHE/'pool.blind.jsonl',blind)
 random_ids=[r['pair_id'] for r in sorted((r for r in pairs if r['examples_eligible']),key=lambda r:I.rank('random-example',r['pair_id']))[:2]]
 meta={'section':97,'experiment':'E10','status':'POOL_FROZEN_BEFORE_E10_EXTRACTION','seed':I.SEED,'paired_counts':dict(Counter(r['dataset'] for r in pairs)),'pairs':len(pairs),'excluded_counts':dict(Counter(r['dataset'] for r in missing)),'s61_artificial_mismatched_pairs_excluded':excluded_mismatch,'w6':'480 Oracle readouts inventoried; all NLA counterparts empty; excluded by direct user ruling','w1_text_policy':'Use exact raw generated strings, including format markers and incomplete endings; all NLA parsed text fields empty/extraction_failed, but raw nonempty. No repair/truncation.', 'layer_caveat':'W1 pairs match item/token across native44/42, not identical vectors; S61 site44/42 or44/44 retained. No causal reader comparison.', 'pre_freeze_exposure':{'item_id':I.EXPOSED_W1_ITEM,'dataset':'W1','reason':'one pair raw strings surfaced in metadata inspection before example rule freeze; all samples of this item excluded from illustrative selection, retained in pool'},'random_example_pair_ids':random_ids,'sources':sources,'files':{n:I.sha(I.CACHE/n) for n in ['pool.private.jsonl','pool.blind.jsonl','missing.private.jsonl']}}
 I.save(I.OUT/'POOL_MANIFEST.json',meta)
 print({k:meta[k] for k in ['pairs','paired_counts','excluded_counts','s61_artificial_mismatched_pairs_excluded']})
if __name__=='__main__':build()
