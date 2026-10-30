"""E115b capture/dev metadata binding, no fraction or outcome comparison."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];WT=ROOT.parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def bind():
 pins={};groups={}
 def pin(p,h=None):
  p=Path(p).resolve();v=sha(p);assert h is None or v==h,str(p);pins[str(p)]=v;return p
 def seal(p):
  p=pin(p);d=read(p)
  for n,h in d['files'].items():pin(p.parent/n,h if isinstance(h,str) else h['sha256'])
  return d
 src=WT/'wt-wsae/cache/g_agreement/understand/e94/SOURCES.PRIVATE.json';pin(src,'ef4242932b3cbb8c796ee247b5817896998525553f35c05d8e78043f12d29b36');sources=read(src)
 outcome=WT/'wt-wsae/cache/g_agreement/understand/e94/ITEM_CLASSES.PRIVATE.json';pin(outcome)
 for bank in ['E56','E57','E59']:
  spec=next(x['spec'] for x in sources['banks'] if x['bank']==bank)
  private=read(pin(spec['private_items'],spec['private_items_sha256']));meta={r['id']:r for r in private}
  if bank in ['E56','E57']:
   caps=[WT/f'wt-wmech/cache/g_agreement/understand/e56_e57/verified_pull_single_v1/shard_{i}/out/{bank.lower()}/capture' for i in range(3)]
  else:caps=[ROOT/'cache/g_agreement/understand/e59/capture_delivery']
  seen=set()
  for cap in caps:
   seal(cap/'CAPTURE_SEAL.json');order=read(cap/'items.order.json')
   for i,ident in enumerate(order):
    assert ident in meta and ident not in seen;seen.add(ident);r=meta[ident];key=bank+'|'+r['feature'];g=groups.setdefault(key,dict(bank=bank,row=r['feature'],dev=[],test=[]));assert r['split'] in ['dev','test'];g[r['split']].append(dict(id=ident,file=str(cap/'acts44.npy'),index=i))
  for g in [v for v in groups.values() if v['bank']==bank]:assert len(g['dev'])==len(g['test'])==84
 a=read(ROOT/'cache/g_agreement/understand/e115/PART_A_INPUTS.PRIVATE.json')
 pin(a['basis'],a['pins'][a['basis']]);pin(a['mean_source'],a['pins'][a['mean_source']])
 return dict(status='BOUND_DEV_AND_TEST_METADATA_NO_METRICS',groups=groups,pins=pins,outcomes=str(outcome),basis=a['basis'],mean_source=a['mean_source'],unavailable={'E73':'No sealed dev-split capture bound in existing delivered J bundles: records are explicitly all test; dev-decile gate NOT EVALUABLE. No test quantiles substituted.','E56_injection':'Synthetic direction-control units have no corresponding original dev cohort for dev-decile threshold; gate NOT EVALUABLE.','E62':'Original E94 has no paired Oracle/NLA acquisition.','E67':'Original E94 excludes incompatible claim rubric from value-grounded ensemble.'})
if __name__=='__main__':
 p=ROOT/'cache/g_agreement/understand/e115/PART_B_INPUTS.PRIVATE.json';assert not p.exists();d=bind();p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps(dict(groups=len(d['groups']),files=len(d['pins']),sha256=sha(p))))
