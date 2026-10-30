"""CPU-only integration. No component execution or paid imports. Guard after preflight."""
import argparse,hashlib,json,subprocess
from functools import lru_cache
from datetime import datetime,timezone
from pathlib import Path
from .analysis import analyze,CUES,SCOPES
from projects.g_agreement.e136_named.named import messages,validate
ROOT=Path(__file__).resolve().parents[3]
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e136/OVERALL_ANALYSIS_ONCE.json'
PINS={'probe':'57c28890e88b5a8dc535a5078689e0cb860775c9be0ec28fcf5c6556e5a2988e','words':'ed1bef02dbe289357f090972bcf18ca1e962443f323d289ffdb6382a81664d40','judge':'ccb07e2c2cda80d296d1eae71495f757ff6222d839d1b728cd1d37ae0d4f5f5b','phase':'a419843f1957a7945c02af78eaf5eb086a79a3f797d0912c979566e7e4422eeb','input':'e3801a76e9f14810268cc877524bcfaeec491675b97cb5e08f2cdb21fad2dfb2'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
@lru_cache(maxsize=None)
def read(p):return json.loads(Path(p).read_text())
def require(x,msg):
 if not x:raise ValueError(msg)
def checked(ref):
 p=Path(ref['path']);require(sha(p)==ref['sha256'],'exact file hash');return p
def sealed(ref):return sealed_cached(str(ref['path']),ref['sha256'])
@lru_cache(maxsize=None)
def sealed_cached(path,digest):
 p=checked(dict(path=path,sha256=digest));s=read(p);files=s.get('members',s.get('files',{}));require(files,'nonempty seal')
 for n,h in files.items():
  f=(p.parent/n).resolve();require(f.is_relative_to(p.parent.resolve()) and sha(f)==h,'exact member hash')
 return p,s
def pointer(ref):
 p,s=sealed(dict(path=ref['seal'],sha256=ref['sha256']));require(ref['member'] in s.get('files',s.get('members',{})),'sealed pointer member')
 v=read(p.parent/ref['member'])
 for k in ref['keys']:v=v[k]
 return v
def preflight(spec):
 require(spec.get('primary_scope') == 'test_present' and spec.get('denominator_authority'),'explicit human denominator')
 for k,h in PINS.items():require(spec[k]['sha256']==h,'only original eligible component '+k)
 bundles={k:sealed(spec[k]) for k in PINS}
 jp,js=bundles['judge'];pp,ps=bundles['phase'];ip,ins=bundles['input']
 require(js['experiment']==ps['experiment']==ins['experiment']=='E136R','new bank ONLY')
 require(js['source_prompt_on_wire'] is False and ps['source_prompt_on_wire'] is False and ps['status']=='COMPLETE' and ps['input_sha256']==sha(ip),'terminal readout-only provenance')
 for ref in ins['source_seals']:sealed(dict(path=ref['seal'],sha256=ref['sha256']))
 probe=read(bundles['probe'][0].parent/'RESULTS.json');words=read(bundles['words'][0].parent/'METRICS.json')
 oldspec=read(bundles['probe'][0].parent/'BINDING.PRIVATE.json')
 rows=read(checked(oldspec['measurements']));meta={r['id']:r for r in rows};require(len(rows)==len(meta)==400,'original probe400 census')
 oof=read(bundles['words'][0].parent/'OOF.PRIVATE.json')
 for view in ('excluded','unexcluded_descriptive'):
  xs=[r for r in oof if r['view']==view];require(len(xs)==320 and {r['id'] for r in xs}=={r['id'] for r in rows if r['split']=='test'},'full original TEST words census')
  for r in xs:
   m=meta[r['id']];require(r['label']==m['label'] and r['cue']==m['cue'] and r['base_task']==m['base_task'] and r['block']==44,'word/probe literal joins')
 refs=read(jp.parent/'READOUT_CODE_BINDINGS.PRIVATE.json');require(len(refs)==400 and {r['item_id'] for r in refs.values()}==set(meta),'new bank exact original400')
 calls=read(ip.parent/'CALLS.json');require(len(calls)==1200,'full frozen request census')
 # Validate exact readout-only data for every first/retry request against original native text.
 native={r['id']:(pointer(r['source_ref']),r['cue']) for r in refs.values()}
 for call in calls:
  rendered=call['rendered'];data=json.loads(rendered['user']);require(set(data)=={'id','readout'} and data['id'] in native,'opaque readout-only wire')
  txt,cue=native[data['id']];expected=messages(data['id'],txt,cue)
  require(data['readout']==txt and rendered['system']==expected[0]['content'],'literal native readout and frozen question')
 normalized=[]
 for r in refs.values():
  m=meta[r['item_id']];require(r['cue']==m['cue'] and r['split']==m['split'] and r['layer']==44,'native/probe scope join')
  require(r['judgment_source']['sha256']==PINS['phase'] and r['code_source']['sha256']==PINS['phase'],'new bank literal code refs')
  code=pointer(r['judgment_source']);record=pointer(r['code_source'])
  require(code in ('YES','NO','UNPARSEABLE') and (r['status']=='KEPT')==(code in ('YES','NO')),'missing not NO')
  if record is not None:
   validate(record,native[r['id']][0]);require(record['code']==code,'literal code correspondence')
  else:require(code=='UNPARSEABLE','null remains missing')
  normalized.append(dict(id=m['id'],cue=m['cue'],split=m['split'],label=m['label'],code=code))
 return normalized,probe,words

def main(spec_path):
 receipt=read(Path(__file__).with_name('SOURCE_RECEIPT.json'))
 for n,h in receipt['files'].items():
  require(sha(ROOT/n)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)).hexdigest()==h,'committed source exact')
 require(not GUARD.exists(),'consumed guard NEVER REPLAY')
 spec=read(spec_path);rows,probe,words=preflight(spec)
 # Validate all shapes and calculate only under the sole guard below.
 out=Path(spec['output_dir']);require(not out.exists(),'fresh output only')
 with GUARD.open('x') as f:json.dump(dict(spec_sha256=sha(spec_path),source_sha256=sha(Path(__file__).with_name('SOURCE_RECEIPT.json')),claimed_utc=datetime.now(timezone.utc).isoformat()),f)
 out.mkdir(mode=0o700)
 result=analyze(rows,probe,words,spec['primary_scope'])
 for name,value in [('RESULTS.json',result),('BINDING.PRIVATE.json',spec),('NAMED_ROWS.PRIVATE.json',rows)]:
  p=out/name;p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');p.chmod(0o600)
 (out/'ANALYSIS_SEAL.json').write_text(json.dumps(dict(status='COMPLETE_ONCE',experiment='E136_OVERALL',members={p.name:sha(p) for p in sorted(out.iterdir())}),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',required=True);main(p.parse_args().spec)
