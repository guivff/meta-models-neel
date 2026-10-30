"""Join independently supplied categories; do not run forecast comparisons."""
import json,hashlib,subprocess
from pathlib import Path
from datetime import datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a,cwd=ROOT):return subprocess.check_output(['git',*a],cwd=cwd,text=True).strip()
def main():
 u=read(HERE/'QWEN_BOUND_UNITS.json');p=read(HERE/'QWEN_PREFLIGHT_2026-10-28.json');catdir=ROOT/'results/g_agreement/understand/e58a';sources={};chronology=[]
 def ref(f):f=Path(f).resolve();sources[str(f)]=sha(f);return f
 # Analysis-seal commit dates are evidence timestamps; cached seal bytes must match.
 analysis_dates={}
 for b in ['E56','E57','E59','E62','E73']:
  repo=ROOT.parent/('wt-i2' if b=='E73' else 'wt-wmech')
  rel='results/g_agreement/i2/E73_ONCE_ANALYSIS_SEAL.json' if b=='E73' else f'results/g_agreement/understand/{b.lower()}/'+('analysis5968_once_2026-10-27' if b=='E59' else 'analysis402_once_2026-10-27')+'/ANALYSIS_SEAL.json'
  f=ref(repo/rel);assert sha(f)==p['analysis_bindings'][b]['analysis_seal_sha256']
  line=git('log','--diff-filter=A','--format=%H %cI','--',rel,cwd=repo).splitlines()[-1];commit,date=line.split()
  analysis_dates[b]=date;chronology.append(dict(bank=b,analysis_seal_commit=commit,analysis_seal_commit_time=date,path=str(f),sha256=sha(f)))
 cats={};prov={}
 for name in ['CATEGORIES.json','E57_AMENDMENT_CATEGORIES.json','E57_SENTIMENT_CATEGORY.json']:
  f=ref(catdir/name);rel=str(f.relative_to(ROOT));intro=git('log','--diff-filter=A','--format=%H %cI','--',rel).splitlines()[-1];commit,date=intro.split()
  assert git('show',commit+':'+rel)==f.read_text().strip()
  for r in read(f)['rows']:
   if r['bank'] not in ['E56','E57']:continue
   assert datetime.fromisoformat(date)<datetime.fromisoformat(analysis_dates[r['bank']])
   key=(r['bank'],r['row']);cats[key]=r['category'];prov[key]=dict(status='pre_outcome',path=str(f),commit=commit,commit_time=date,analysis_seal_commit_time=analysis_dates[r['bank']])
 aliases=read(ref(catdir/'E57_CONDITION_ALIASES.json'))['aliases']
 for row,parent in aliases.items():
  cats['E57',row]=cats['E57',parent];prov['E57',row]=dict(prov['E57',parent],canonical_row=parent)
 f=ref(ROOT/'results/g_agreement/understand/e52/r3b/E73_CONTROLS_FORECAST_BINDINGS.json');commit='91010ee05b29bf966d7193ee600c65c22abfc472';date=git('show','-s','--format=%cI',commit)
 assert subprocess.check_output(['git','show',commit+':'+str(f.relative_to(ROOT))],cwd=ROOT)==f.read_bytes()
 assert datetime.fromisoformat(date)<datetime.fromisoformat(analysis_dates['E73'])
 for row in ['W7','W8']:cats['E73',row]='content';prov['E73',row]=dict(status='pre_outcome',path=str(f),commit=commit,commit_time=date,analysis_seal_commit_time=analysis_dates['E73'])
 repo=ROOT.parent/'wt-wtext';rel='results/g_agreement/understand/e58a/e75_receipt/CATEGORY_RECEIPT.json';f=ref(repo/rel)
 # Require W-text's finished committed receipt, never consume its draft.
 assert subprocess.check_output(['git','show','HEAD:'+rel],cwd=repo)==f.read_bytes()
 commit=git('log','-1','--format=%H','--',rel,cwd=repo)
 for r in read(f)['rows']:
  assert not r['confirmatory_category_gap_eligible']
  key=r['bank'],r['row'];cats[key]=r['category'];prov[key]=dict(status='exploratory_mechanical',path=str(f),commit=commit,description=r['description'],derivation=r['derivation'])
 for rows in u['panels'].values():
  for r in rows:
   key=r['bank'],r['row'];r['category']=cats[key];r['category_provenance']=prov[key]['status'];r['category_binding']=prov[key]
 u['nonbinary_forecast_exclusions']={b:read(a['path']).get('exclusions',[]) for b,a in p['forecast_bindings'].items()}
 u['category_chronology']=chronology;u['policy']='All eligible forecast units retained for J BA. Pre-outcome categories alone in confirmatory category comparison; all-unit category comparison exploratory. Primary plus prespecified redaction sensitivity.'
 (HERE/'QWEN_BOUND_UNITS.json').write_text(json.dumps(u,indent=2,sort_keys=True)+'\n')
 p.update(status='READY_FOR_COMMITTED_ONCE_PLAN',category_contract='Direct user ruling 2026-10-28: provenance split; W-text mechanical receipt exploratory',missing_category_bindings={},real_E75_claim_consumed=False)
 (HERE/'QWEN_PREFLIGHT_2026-10-28.json').write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
 files=['bind_qwen.py','join_qwen_categories.py','run_qwen_once.py','QWEN_BOUND_UNITS.json','QWEN_PREFLIGHT_2026-10-28.json']
 plan=dict(command='/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python results/g_agreement/understand/e75/run_qwen_once.py',claim='cache/g_agreement/understand/e75/qwen_once/ONCE.json',never_reset=True,panels=['primary','redaction_excluded_sensitivity'],category_sources=sources,committed_files={str((HERE/n).relative_to(ROOT)):sha(HERE/n) for n in files},scope='Qwen E56 E57 E59 E62 E73; E62 placebo NOT RUN, E62 NLA NOT RUN; GLM separate',category_policy=u['policy'],no_source_analysis_rerun=True)
 (HERE/'QWEN_RUN_PLAN.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n')
 print('READY; no scorer invoked')
if __name__=='__main__':main()
