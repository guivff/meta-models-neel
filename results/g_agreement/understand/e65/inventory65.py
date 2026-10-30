"""Items-only source inventory. Does not inspect gates, probes or reader outcomes."""
from pathlib import Path
from collections import Counter
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
SOURCES={
'W1':Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/blindspot/w1-readonly-20261024/w1-bank-v2/items.DO_NOT_STAGE.jsonl'),
'W12':ROOT/'cache/g_agreement/blindspot/w12-freeze-2833a200/items.jsonl',
'E36':HERE.parent/'e36/cache/v2_25_2026-10-25/items.input.jsonl',
'E46':HERE.parent/'e46/cache/prepared/items.PRIVATE.json',
'E49':HERE.parent/'e49/cache/frozen_2026-10-26/items.PRIVATE.json',
'E54':HERE.parent/'e54/cache/bank_2026-10-27_v1/items.PRIVATE.json',
'E56':HERE.parent/'e56/cache/bank_2026-10-27_v1/items.PRIVATE.json',
'E57':HERE.parent/'e57/cache/bank_2026-10-27_v1/items.PRIVATE.json',
'E59':HERE.parent/'e59/cache/bank_2026-10-27_v1/items.PRIVATE.json',
'E62':HERE.parent/'e62/cache/bank_2026-10-27_v1/items.PRIVATE.json',
'E61_D3':HERE.parent/'e61/cache/bank_2026-10-27_v1/D3_ITEMS.PRIVATE.json',
'E61_D4':HERE.parent/'e61/cache/bank_2026-10-27_v1/D4_ITEMS.PRIVATE.json'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_items(p):
 s=p.read_text();return [json.loads(x) for x in s.splitlines()] if p.suffix=='.jsonl' else json.loads(s)
def main():
 result={'stage':'ITEMS_ONLY_INVENTORY_NOT_PERSISTENCE_RESULTS','gates_read':False,'reader_or_probe_files_read':False,'gate_filter_owner':'W-lens','sources':{},'unresolved_scope':'Every bank with sealed probe is a downstream eligibility condition. All locally inventoried banks retained; no eligibility inferred from outcomes. E39/E44/E50 require an item-only source pointer if independently included.'}
 for bank,p in SOURCES.items():
  if not p.exists():result['sources'][bank]={'status':'SOURCE_MISSING','path':str(p)};continue
  items=read_items(p);test=[x for x in items if x.get('split')=='test']
  counts=Counter(x.get('feature',x.get('row_id')) for x in test)
  result['sources'][bank]={'path':str(p),'sha256':sha(p),'test_items':len(test),'rows':dict(sorted(counts.items())),'status':'AVAILABLE_UNFILTERED'}
 p=HERE/'SOURCE_INVENTORY_V2_2026-10-27.json'
 with p.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 print('Inventoried',len(SOURCES),'item sources;',sum(len(s.get('rows',{})) for s in result['sources'].values()),'bank/row entries; no gate or outcome reads')
if __name__=='__main__':main()
