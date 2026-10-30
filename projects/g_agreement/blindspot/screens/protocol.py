"""§79 compute admission and sealed interfaces, separate from W1 protocol."""
from __future__ import annotations
import hashlib,json,os,time,uuid
from functools import lru_cache
from pathlib import Path
from . import corpus as C

SITES={'olens':44,'nla':42};SCIENCE_SECONDS=7200;STAGING_SECONDS=1500;RETRIEVAL_SECONDS=600;GUARD_SLACK_SECONDS=30
CAP_SECONDS=STAGING_SECONDS+SCIENCE_SECONDS+RETRIEVAL_SECONDS+GUARD_SLACK_SECONDS
PRIOR_SCIENCE_SECONDS=1145.1 # Already booked; separate from Guiv's new attempt allowance.
WARMUP_ITERATIONS=2
WARMUP_PATHS=('target','olens-active','olens-base','nla-active','nla-base')
RUN_ID=str(uuid.uuid4())

def files_hashes():
 paths=[Path(__file__).parent/p for p in ['__init__.py','corpus.py','features.py','sampling.py','protocol.py','run.py','analyse.py','stage.py','chain.py','operator.py','bundle.py','kernel_preflight.py']]
 paths += [C.ROOT/'common/__init__.py',C.OUT/'FREEZE.json',C.OUT/'RUNTIME_PINS.json',C.OUT/'KERNEL_PREPARATION.json',C.OUT/'KERNEL_WHEEL_MANIFEST.json',C.OUT/'RUNTIME_AMENDMENT.md',Path(__file__).parent/'bootstrap.sh']
 paths += sorted((C.ROOT/'external/mats-nla-workspace/src/mats').rglob('*.py'))
 return {str(p.relative_to(C.ROOT)) if p.is_absolute() else str(p):C.sha(p) for p in paths}

def verify_freeze():
 freeze=json.loads((C.OUT/'FREEZE.json').read_text())
 if freeze['status']!='FROZEN_BEFORE_CAPTURE':raise ValueError('no frozen feature/corpus contract')
 for name,h in freeze['files'].items():
  if C.sha(C.ROOT/name)!=h:raise ValueError('feature/corpus freeze changed '+name)
 return freeze

def inputs(bank):
 bank=Path(bank);freeze=verify_freeze()
 if C.sha(bank/'INPUT_SEAL.json')!=freeze['input_seal_sha256']:raise ValueError('bank differs from frozen input seal')
 seal=json.loads((bank/'INPUT_SEAL.json').read_text())
 if any(bank.glob('*DO_NOT_STAGE*')):raise ValueError('label-bearing files staged')
 for name,h in seal['files'].items():
  if Path(name).is_absolute() or '..' in Path(name).parts or C.sha(bank/name)!=h:raise ValueError('input seal mismatch '+name)
 if seal['corpus_manifest_sha256']!=C.sha(C.OUT/'CORPUS_MANIFEST.json'):raise ValueError('wrong corpus')
 docs=C.rows(bank/'documents.input.jsonl');positions=C.rows(bank/'positions.input.jsonl');assign=C.rows(bank/'assignments.input.jsonl');registry=json.loads((bank/'features.input.json').read_text())
 dmap={r['id']:r for r in docs};pmap={r['id']:r for r in positions};amap={(r['feature'],r['id']):r for r in assign}
 if len(dmap)!=len(docs) or len(pmap)!=len(positions) or len(amap)!=len(assign):raise ValueError('duplicate input identity')
 if set(registry['templates'])!=set(registry['feature_order']):raise ValueError('template coverage')
 used=set()
 for r in assign:
  key=(r['feature'],r['donor_id']);donor=amap.get(key)
  if r['feature'] not in registry['templates'] or donor is None or donor['donor_id']!=r['id'] or r['id']==r['donor_id']:raise ValueError('broken donor involution')
  a,b=pmap[r['id']],pmap[r['donor_id']]
  if a['position']!=b['position'] or a['document_id']==b['document_id']:raise ValueError('unmatched donor position/document')
  used|={r['id'],r['donor_id']}
 if used!=set(pmap):raise ValueError('orphan/missing captured position')
 for r in positions:
  if r['document_id'] not in dmap or not 0<=r['position']<len(dmap[r['document_id']]['ids'])<=512:raise ValueError('position outside document')
 return docs,positions,assign,registry

def validate_warmup(meta,first_science):
 if meta.get('setup_only') is not True or meta.get('unscored') is not True or meta.get('outcome_rows')!=0:raise ValueError('warmup must be unscored setup only')
 if meta.get('iterations')!=WARMUP_ITERATIONS or meta.get('completed_paths')!=list(WARMUP_PATHS)*WARMUP_ITERATIONS:raise ValueError('warmup path coverage expected='+repr(list(WARMUP_PATHS)*WARMUP_ITERATIONS)+' observed='+repr(meta.get('completed_paths')))
 if not meta['started_at']<=meta['completed_at']<=first_science:raise ValueError('warmup after first science')
 return meta

def runtime_choice(a):
 choice=a.get('runtime_environment',{'mode':'current'})
 if choice=={'mode':'current'}:return '/workspace/s79-venv'
 if choice.get('mode')=='integrator-verified' and choice.get('path')=='/weights/venv-kernels' and choice.get('verified_by_integrator') is True and len(choice.get('receipt_sha256',''))==64 and all(c in '0123456789abcdef' for c in choice['receipt_sha256']):return choice['path']
 raise ValueError('unverified runtime environment')

def budget_check(a,now):
 start=float(a['provider_created_epoch']);hard=float(a['deadline_epoch']);science=float(a['science_deadline_epoch']);setup=float(a['setup_deadline_epoch'])
 if a.get('science_cap_seconds')!=SCIENCE_SECONDS or a.get('staging_allowance_seconds')!=STAGING_SECONDS:raise ValueError('wrong science/staging allowance')
 if not start<=now<science<=hard-RETRIEVAL_SECONDS-GUARD_SLACK_SECONDS or not 0<hard-start<=CAP_SECONDS:raise ValueError('invalid/expired creation-relative booking')
 if setup!=start+STAGING_SECONDS or science>setup+SCIENCE_SECONDS:raise ValueError('setup/science deadline reset')
 return a

def science_deadline(a,first_science):
 if first_science>a['setup_deadline_epoch']:raise TimeoutError('setup allowance exceeded before first science')
 return min(first_science+SCIENCE_SECONDS,a['science_deadline_epoch'])

def admit(path,now=None,native_id=None):
 a=json.loads(Path(path).read_text());now=time.time() if now is None else now
 if native_id is None:
  native_id=next((x.split(b'=',1)[1].decode() for x in Path('/proc/1/environ').read_bytes().split(b'\0') if x.startswith(b'RUNPOD_POD_ID=')),None)
 if a.get('issuer')!='integrator' or a.get('section')!=79 or a.get('pod_id')!=native_id:raise ValueError('requires exact integrator S79 assignment')
 if a.get('source_files')!=files_hashes() or a.get('freeze_sha256')!=C.sha(C.OUT/'FREEZE.json'):raise ValueError('assigned source/freeze mismatch')
 budget_check(a,now);runtime_choice(a)
 for k in ['publication_verified','guards_verified','outgoing_retired','staging_productivity_guard_verified','weights_volume_go','shared_weights_readonly']:
  if a.get(k) is not True:raise ValueError('missing integrator attestation '+k)
 return a

@lru_cache(maxsize=1)
def code_hash():return C.digest(C.canonical(files_hashes()))
def stamp(kind):return {'run_id':RUN_ID,'run_kind':kind,'code_sha256':code_hash()}
def seal(directory,names,name,**extra):C.save(Path(directory)/name,{'files':{n:C.sha(Path(directory)/n) for n in names},**extra})
def verify(directory,name):
 d=Path(directory);v=json.loads((d/name).read_text())
 for n,h in v['files'].items():
  if Path(n).is_absolute() or '..' in Path(n).parts or C.sha(d/n)!=h:raise ValueError('score seal mismatch '+n)
 return v

def score_coverage(scores,assign,kind):
 expected={(x['feature'],x['id'],reader,site,arm) for x in assign for reader,site in SITES.items() for arm in ['true','mismatched']};seen=[]
 for r in scores:
  seen.append((r['feature'],r['id'],r['reader'],r['site'],r['arm']))
  if r['run_kind']!=kind or not r['run_id'] or not r['code_sha256']:raise ValueError('score stamp/kind decoy')
  if not isinstance(r['score'],(float,int)) or not __import__('math').isfinite(r['score']):raise ValueError('nonfinite score')
 if len(seen)!=len(set(seen)) or set(seen)!=expected:raise ValueError('SMOKE FAILED: reader×feature×arm/site cells; extra='+repr(sorted(set(seen)-expected))+'; missing='+repr(sorted(expected-set(seen)))+'; duplicate='+repr([k for k in set(seen) if seen.count(k)>1]))
 identities={(r['run_id'],r['code_sha256']) for r in scores}
 if len(identities)!=1:raise ValueError('mixed run_id/code_sha256 identities '+repr(sorted(identities)))
