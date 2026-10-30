"""CPU-only, once-only E68 probe per position and native reader source layer."""
import argparse
from worker import *
from cpu_capture import compute
from contract56 import auc

def validate_cpu_grid(items):
 for row in {x['feature'] for x in items}:
  for split in ('dev','test'):
   xs=[x for x in items if x['feature']==row and x['split']==split]
   require(len(xs)==84 and {x['label'] for x in xs}=={0,1},'84 frozen examples with both classes per split/cell')
 require(len({x['id'] for x in items})==len(items),'no repeated dev/test unit')

def run(spec):
 s=read(spec);cmd=read(HERE/'PROBE_COMMAND.json');require(sha(spec)==cmd['spec_sha256'],'sealed CPU spec');verify(HERE,'SOURCE_SEAL.json',cmd['source_seal_sha256']);require(sha(s['private_items'])==s['private_items_sha256'],'CPU private pin');private={x['id']:x for x in read(s['private_items'])};receipt=read(s['receipt']);require(receipt['verified'] is True,'integrator verified capture pull');items=[];parts={42:[],44:[]};seen=set()
 req=read(s['request']);require(sha(s['request'])==s['request_sha256'] and req['experiment']=='E68','bound E68 request')
 require(len(receipt['shards'])==len(req['shards']),'all shards before fit')
 for sh in req['shards']:
  rec=receipt['shards'][str(sh['shard'])];cap=Path(rec['capture']);c=verify(cap,'CAPTURE_SEAL.json',rec['capture_seal_sha256']);require(c['source_seal_sha256']==req['source_seal_sha256'] and c['input_seal_sha256']==sh['input_seal_sha256'],'capture/source/input identity');order=read(cap/'items.order.json');require(order==sh['item_ids'] and not seen.intersection(order),'exact disjoint order');seen.update(order)
  for k in order:
   x=private[k];require(x['label'] in (0,1) and x['position'] in POSITIONS,'CPU labels/position');items.append(dict(x,feature=x['feature']+'|'+x['position']))
  for l in parts:
   h=np.load(cap/f'acts{l}.npy',allow_pickle=False);require(h.shape==(len(order),5120) and np.isfinite(h).all(),'capture tensor');parts[l].append(h)
 require(set(private)==seen,'complete sealed private grid');validate_cpu_grid(items);out=Path(s['out']);out.mkdir(parents=True,exist_ok=False);dump(out/'ONCE_ONLY.json',dict(spec_sha256=sha(spec)))
 for l,hs in parts.items():
  scores,_=compute(items,np.concatenate(hs));by={x['id']:x for x in items};rates={row:auc([by[x['id']]['label'] for x in scores if x['feature']==row],[x['score'] for x in scores if x['feature']==row]) for row in {x['feature'] for x in items}}
  require(len(rates)==9,'three rows by three positions');dump(out/f'PROBE{l}.json',dict(AUROC=rates,scores=scores,fit_split='dev',eval_split='test'))
 seal(out,'PROBE_SEAL.json',dict(experiment='E68',request_sha256=sha(s['request']),private_items_sha256=s['private_items_sha256'],receipt_sha256=sha(s['receipt'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);run(p.parse_args().spec)
