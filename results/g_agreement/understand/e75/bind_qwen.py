"""Operational binding only; never calculates forecast-performance statistics."""
import json,hashlib,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind():
 p=read(HERE/'QWEN_PREFLIGHT_2026-10-28.json'); refs={}; analyses={}; forecasts={}
 def ref(f):
  f=Path(f).resolve();refs[str(f)]=sha(f);return f
 for b,a in p['analysis_bindings'].items():
  sp=ref(a['analysis_seal']); assert sha(sp)==a['analysis_seal_sha256']
  s=read(sp);assert s['status']=='COMPLETE'
  for name,h in s['files'].items():
   f=ref(sp.parent/name);assert sha(f)==(h['sha256'] if isinstance(h,dict) else h)
  analyses[b]=read(a['results'])
 for b,a in p['forecast_bindings'].items():
  f=ref(a['path']);assert sha(f)==a['sha256']
  assert subprocess.check_output(['git','show',a['original_commit']+':'+str(f.relative_to(ROOT))],cwd=ROOT)==f.read_bytes()
  forecasts[b]=read(f)
 nullpath=ref(ROOT/'cache/g_agreement/understand/e52/sparse-primary/NULL_SEAL.json');null=read(nullpath)
 for n,h in null['files'].items():assert sha(ref(nullpath.parent/n))==h
 assert null['k']==16 and null['n']==200
 # The original CPU channel binds this same E52 null for all seven banks.
 ref(ROOT/'results/g_agreement/understand/e57/jlens/cpu_job.py')
 for b in forecasts:
  ref(ROOT/'results/g_agreement/understand/e57/jlens'/f'{b}_INPUT_PLAN.json')
  ref(ROOT/'results/g_agreement/understand/e57/jlens'/f'{b}_results/ROW_LABELS.json')
 for n,h in read(HERE/'CODE_SEAL.json')['files'].items():assert sha(ref(ROOT/n))==h
 panels={'primary':[],'redaction_excluded_sensitivity':[]};excluded=[]
 for bank,f in forecasts.items():
  b='E73' if bank=='E73_CONTROLS' else bank
  if b=='E62_PLACEBO':
   for row in f['rows']:
    for reader in ['oracle','nla']:excluded.append(dict(bank=b,reader=reader,row=row['row'],reason='E62P NOT RUN / NO_FIT; 94a770cc(c)'))
   continue
  a=analyses[b];d=Path(p['analysis_bindings'][b]['results']).parent
  probe=read(d/'PROBE.json') if (d/'PROBE.json').exists() else a.get('probe')
  if b=='E56':rates=read(d/'NATIVE_RATES.json')
  else:rates=a.get('rates')
  for row in f['rows']:
   u=row['row']
   for reader in ['oracle','nla']:
    reason=None
    if b=='E62' and reader=='nla':reason='NLA NOT RUN; 402be5f0'
    elif b=='E62' and not a['R_L0'][u.split('_')[0]]:reason='R-L0: state fails probe >=0.90 at every rung'
    elif b=='E73' and u not in {x['state'] for x in a['primary']['probe_rows'] if x['probe_pass']}:reason='probe <0.90'
    elif b in ['E56','E57','E59'] and probe[u]<.90:reason='probe <0.90'
    if reason:excluded.append(dict(bank=b,reader=reader,row=u,reason=reason));continue
    for panel,rows in panels.items():
     stat=a[panel]['readers'][reader]['states'][u] if b=='E73' else rates[f'{reader}|{u}'+('|text' if b=='E56' else '')]
     truth='REPORTED' if stat['S']>=.20 and stat['CI95'][0]>0 else 'MISSED'
     rows.append(dict(model='Qwen3.6-27B',reader=reader,bank=b,row=u,truth=truth,S=stat['S'],S_CI95=stat['CI95'],j_prediction=row[reader+'_prediction'],j_label=row['label'],j_fraction=row['J_fraction'],j_null_median=null['median'],j_null_percentile975=null['percentile97_5'],forecast_source=bank))
 out=dict(panels=panels,excluded=excluded,source_sha256=refs,policy='All prospectively forecast eligible probe-gated binary units; E62 state gate; frozen S>=0.20 and CI lower>0. Primary and saved redaction sensitivity. Categories pending independent provenance receipt.',real_scorer_invoked=False)
 (HERE/'QWEN_BOUND_UNITS.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print({k:{r:sum(x['reader']==r for x in v) for r in ['oracle','nla']} for k,v in panels.items()})
if __name__=='__main__':bind()
