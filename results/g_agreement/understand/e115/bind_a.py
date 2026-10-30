"""Bind sealed E115a metadata; never compute fractions or load activations."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WT=ROOT.parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def bind():
 pins={}
 def pin(p,expected=None):
  p=Path(p).resolve();h=sha(p)
  if expected is not None:assert h==expected,str(p)
  pins[str(p)]=h
  return p
 def seal(p,expected=None):
  p=pin(p,expected);d=read(p)
  for k,h in d['files'].items():pin(p.parent/k,h if isinstance(h,str) else h['sha256'])
  return d
 e104=read(HERE.parent/'e104/analysis_once/BINDING.json')
 seal(e104['input_seal'],e104['input_sha256'])
 cap=WT/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E104/U_test/fact_recall/out'
 cs=seal(cap/'OUTPUT_SEAL.json','276968c827ffc1c4163f4351d871e85141d1c43fbbcb7467809b5656910d278c')
 assert cs['status']=='COMPLETE'
 grid=read(cap/'JOB_GRID.json');vectors={c:[] for c in ('steered','random')}
 for n,g in enumerate(grid):
  if g['kind']!='logits':continue
  assert g['arm']=='U' and g['row']=='fact_recall' and g['alpha']==8
  job=read(cap/f'jobs/{n:06d}.json');assert len(job)==len(g['indices'])
  for j,item in enumerate(job):
   assert item['condition']==g['condition']
   vectors[g['condition']].append(dict(item_id=item['item_id'],file=str(cap/f'read_vectors/{n:06d}.npy'),index=j))
 prior=read(pin(e104['private']))
 cohort=[x['item_id'] for x in prior if x['arm']=='U' and x['row']=='fact_recall' and x['condition']=='steered' and x['flipped']]
 assert len(cohort)==len(set(cohort))==84
 for c,v in vectors.items():assert len(v)==84 and {x['item_id'] for x in v}==set(cohort)
 bp=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_e109/binding_v1/E109_BINDING_SEAL.json')
 bs=seal(bp,'01275a58b0bf65075e470b06594c12c08138fc7e0d0d77275c974c689a0915e7')
 source=bs['source_seals'][0];seal(source['seal'],source['sha256'])
 unhook=read(bp.parent/'MEASUREMENTS.json')['fact_recall']['44']['test']['unhooked']
 assert unhook['seal_index']==0 and unhook['keys']==[]
 inv=read(pin(HERE.parent/'e109/cpu_only/INVENTORY.json'))['fact_recall']
 assert set(inv['test_ids'])==set(cohort)
 basis=WT/'wt-blindspot-internals/cache/g_agreement/understand/e80c/inputs_v1/pod_inputs/J384.npy'
 pin(basis,'a8f4b64c010aa2f3a72aac70e087ce5204d463c2bb93d1ebf3b22b21a0bdb4fb')
 original=ROOT/'cache/g_agreement/understand/e80/capture_delivery'
 seal(original/'CAPTURE_SEAL.json','25d02e881f2c5ceb99959a6d6c8a0a640bf1daed4e1ba71491dd0f4b34e09a32')
 return dict(status='BOUND_METADATA_NO_METRICS',cohort=cohort,vectors=vectors,unhooked=dict(file=str(Path(source['seal']).parent/unhook['member']),ids=inv['test_ids']),basis=str(basis),mean_source=str(original/'acts44.npy'),mean_recipe='Original E80c: float64 original518 capture mean(axis=0), frozen source; no E104/E109 centering fit',pins=pins,nla='NOT AVAILABLE: E104 sealed production is Oracle-only; no matched NLA42 readouts',part_c='NOT RUN: E104 reader internals absent')
if __name__=='__main__':
 p=ROOT/'cache/g_agreement/understand/e115/PART_A_INPUTS.PRIVATE.json'
 assert not p.exists()
 d=bind();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');p.chmod(0o600)
 print(json.dumps(dict(status=d['status'],n=len(d['cohort']),source_files=len(d['pins']),binding_sha256=sha(p))))
