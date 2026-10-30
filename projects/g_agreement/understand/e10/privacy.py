"""Fail-closed E10 privacy gates; no inference or alternative destination."""
import re,requests
from . import protocol as P,io as I
ENDPOINT='https://openrouter.ai/api/v1/chat/completions'

def check_wire(stage,items,wire,taxonomy=None):
 provider=wire['provider']
 if wire['model']!=P.MODEL or provider.get('data_collection')!='deny' or provider.get('zdr') is not True or provider.get('allow_fallbacks') is not False or provider.get('only')!=[P.PROVIDER]:
  raise ValueError('privacy routing policy')
 keys={'extract':{'id','readout'},'match':{'id','a','b'},'taxonomy':{'id','claim'},'classify':{'id','claim'}}[stage]
 if any(set(x)!=keys for x in items):raise ValueError('unapproved payload metadata')
 if taxonomy is not None and any(set(x)!={'id','name','definition'} for x in taxonomy):raise ValueError('taxonomy metadata')
 def strings(x):
  if isinstance(x,str):return [x]
  if isinstance(x,dict):return [s for v in x.values() for s in strings(v)]
  if isinstance(x,list):return [s for v in x for s in strings(v)]
  return []
 data='\n'.join(strings({'items':items,'taxonomy':taxonomy}))
 patterns=[r'\b(?:hf_|sk-or-v1-|sk-proj-)[A-Za-z0-9_-]{16,}',r'/(?:Users|home|workspace|private|var|tmp|etc)/',r'(?<![A-Za-z])[A-Za-z]:\\[A-Za-z0-9_.-]+',r'\b(?:projects|results|cache)/[A-Za-z0-9_.-]+/',r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+']
 if any(re.search(x,data) for x in patterns):raise ValueError('forbidden key/path/address pattern; no send')

def check_route(key):
 # Read-only metadata query; never includes research content.
 q=requests.get('https://openrouter.ai/api/v1/endpoints/zdr',headers={'Authorization':'Bearer '+key},timeout=30);q.raise_for_status();v=q.json()
 I.save(I.CACHE/'last_zdr_route_inventory.json',v)
 routes=[x for x in v['data'] if x.get('model_id')==P.MODEL and x.get('tag')==P.PROVIDER and x.get('provider_name')==P.PROVIDER_NAME]
 if not routes:raise RuntimeError('NO_APPROVED_ZDR_ROUTE: no inference sent; no alternative model/provider selected')
 proof=I.CACHE/'OPENROUTER_PRIVACY_PROOF.json'
 if not proof.exists():raise RuntimeError('OpenRouter own logging/training toggles not verified off; no inference')
 observed=I.read(proof)
 if observed.get('private_input_output_logging') is not False or observed.get('openrouter_use_inputs_outputs') is not False or not observed.get('verified_at'):raise RuntimeError('OpenRouter own logging/training proof invalid; no inference')
 return routes
