"""Pin metadata only. Never read native text, judge packets, or placebo records."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
U=ROOT/'results/g_agreement/understand'
HERE=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 files={};seals={};banks={}
 def bind(p):
  p=Path(p).resolve();files[str(p)]=sha(p);return str(p)
 def seal(p):
  p=bind(p);seals[p]=files[p];return p
 for bank in ('E56','E57','E59','E62'):
  specpath=U/('analysis5968' if bank=='E59' else 'analysis402')/(bank+'_SPEC.json')
  s=read(bind(specpath));inp=Path(s['inputs']);blind=Path(s['blind_out'])
  folder=next((U/bank.lower()).glob('analysis*once*'))
  a=seal(folder/'ANALYSIS_SEAL.json');bs=seal(blind/'BLIND_SEAL.json');ins=seal(inp/'INPUT_SEAL.json')
  receipt=bind(s['receipt']);r=read(receipt);raw=[]
  if 'shards' in r:
   for x in r['shards']:raw.append(seal(Path(x['root'])/'OUTPUT_SEAL.json'));assert seals[raw[-1]]==x['output_seal_sha256']
   for x in r['retained_pilot_pulls']:raw.append(seal(Path(x['root'])/x['seal_file']));assert seals[raw[-1]]==x['seal_sha256']
  else:
   raw.append(seal(Path(r['output'])/'OUTPUT_SEAL.json'));assert seals[raw[-1]]==r['output_seal_sha256']
  assert read(a)['status']=='COMPLETE' and read(a)['experiment']==bank
  assert read(bs)['receipt_sha256']==files[receipt]
  assert read(a).get('manifest_sha256',read(a).get('receipt_sha256'))==files[receipt]
  assert files[bind(s['private_items'])]==s['private_items_sha256']
  assert files[bind(s['private_key'])]==read(bs)['private_key_sha256']
  assert seals[ins]==s['input_seal_sha256']
  b=dict(spec=bind(specpath),analysis=a,blind=bs,inputs=ins,receipt=receipt,private=s['private_items'],key=s['private_key'],raw_seals=raw)
  if bank in ('E56','E57'):b['sampling']=bind(inp/('SAMPLING.json' if bank=='E56' else 'RUN_PLAN.json'))
  if bank=='E57':b['annotations']=bind(Path(s['private_items']).parent/'ANNOTATIONS.PRIVATE.json')
  banks[bank]=b
 bind(ROOT/'projects/g_agreement/readerbench/scoring.py')
 catalog=bind(U/'e76/REGEX_CATALOG.json')
 for p,h in read(catalog)['source_sha256'].items():
  # Every prospective catalog source is metadata, never reader output.
  assert files[bind(p)]==h
 oldspec=read(bind(U/'analysis63follow/SPEC.json'))
 pool=seal(Path(oldspec['pool_out'])/'POOL_SEAL.json')
 e63receipt=bind(oldspec['receipt']);er=read(e63receipt)
 output=seal(Path(er['output'])/'OUTPUT_SEAL.json');assert seals[output]==er['output_seal_sha256']==read(pool)['output_seal_sha256']
 cfg=dict(schema='e63-normalizer-spec-v1',banks=banks,catalog=catalog,pool=pool,e63_receipt=e63receipt,e63_output=output,
  destination=str(Path(oldspec['bundle']).parent),receipt_destination=oldspec['bundle_receipt'],analysis_out=oldspec['analysis_out'],
  guard=str(Path(oldspec['pool_out']).parents[1]/'e63/REGEX_ANALYSIS_ONCE.json'),files=files,seals=seals,
  authority='Guiv direct instruction 2026-10-28: W-mech2 owns full E56/E57/E59/E62 normalization and verified receipt; CPU only')
 dest=HERE/'SPEC.json';assert not dest.exists()
 dest.write_text(json.dumps(cfg,indent=2,sort_keys=True)+'\n')
 print('Pinned four banks, all source seals and full800 pool; no payloads opened.')
if __name__=='__main__':main()
