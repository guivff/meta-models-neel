"""Description-only category receipt. Never opens results, probes, or reader files."""
import json,hashlib,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
BASE=ROOT/'results/g_agreement/understand'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def history(repo,path):
 raw=subprocess.check_output(['git','-C',str(repo),'log','--all','--diff-filter=A','--format=%H|%aI|%cI','--',path],text=True).strip().splitlines()
 return [dict(zip(['commit','author_time','committer_time'],x.split('|'))) for x in raw]
def ref(repo,path):
 p=repo/path
 return {'repo':str(repo),'path':path,'sha256':sha(p),'introduction_history':history(repo,path)}
def main():
 source=json.loads((BASE/'e58a/CATEGORIES.json').read_text())
 cat={(r['bank'],r['row']):r for r in source['rows']}
 defs=json.loads((BASE/'e62/RUNG_DEFINITIONS.json').read_text())
 rows=[]
 def add(bank,row,category,desc,origin):
  rows.append({'bank':bank,'row':row,'category':category,'description':desc,'derivation':origin,'category_prediction':'REPORTED' if category in ('content','plan') else 'MISSED','category_baseline_group':'content_or_plan' if category in ('content','plan') else 'other','within_category_group':category,'assignment_status':'EXPLORATORY_POST_OUTCOME_BINDING','confirmatory_category_gap_eligible':False,'J_forecast_eligibility':'UNCHANGED: determined independently by W-lens from prospective J forecast and gates'})
 for row in ['format_plan','language_plan','stance_plan','length_plan','hedge_plan','decline_plan']:
  add('E59',row,'plan','Instruction fixes '+row.removesuffix('_plan')+' of the forthcoming answer.','E59 rows59.py explicitly returns RowSpec kind=plan for every row; no dedicated E58a category supplement found. New E75 binding is exploratory despite pre-outcome plan typing.')
 for state,d in defs['states'].items():
  c=cat[(d['bank'],d['row'])]
  for rung in ['L0','L1','L2','L3','L4']:
   add('E62',state+'_'+rung,c['category'],d['property'],{'source_bank':d['bank'],'source_row':d['row'],'source_category':c['category'],'rule':'Inherit the target state category across rungs; asking/reporting/decision framing does not change the target. This bank-level inheritance is first explicitly bound now, hence exploratory.'})
 for row,c,d in [('W1','delimiter','Inside an unclosed Python string literal versus not'),('W2','bookkeeping','Exactly one versus at least three unclosed brackets'),('W3','bookkeeping','At most four versus at least twelve leading indentation spaces'),('W4','syntactic','Inside call arguments versus at statement level'),('W5','bookkeeping','Current line length at most fifteen versus at least fifty-five characters')]:
  add('E73',row,c,d,'Mechanical frozen E58a distinction: delimiter state; numeric depth/width/length bookkeeping; grammatical call-argument position syntactic. First explicit E75 assignment now; exploratory.')
 sources=[ref(ROOT,'results/g_agreement/understand/'+p) for p in ['e58a/CATEGORIES.json','e58a/HANDOFF_2026-10-27.md','e59/rows59.py','e59/BANK_SEAL.json','e62/RUNG_DEFINITIONS.json','e62/BANK_SEAL.json','e52/r3b/CATEGORY_COMPARISON_2026-10-27.md','e52/r3b/category_comparison.py']]
 authorities=[]
 for c in ['6aacc13d','f21ed03e']:
  h,a,t=subprocess.check_output(['git','show','-s','--format=%H|%aI|%cI',c],text=True).strip().split('|');authorities.append({'commit':h,'author_time':a,'committer_time':t,'role':'Registers category comparison policy; not a row-category supplement'})
 seals=[]
 mech=ROOT.parent/'wt-wmech'
 for b,p in [('E59','e59/analysis5968_once_2026-10-27/ANALYSIS_SEAL.json'),('E62','e62/analysis402_once_2026-10-27/ANALYSIS_SEAL.json')]:
  r=ref(mech,'results/g_agreement/understand/'+p);meta=json.loads((mech/r['path']).read_text());r.update(bank=b,status=meta['status'],outcome_members_opened=False);seals.append(r)
 receipt={'date':'2026-10-28','scope':'E59 six rows, E62 S1–S5 × L0–L4, E73 W1–W5 only','rows':rows,'sources':sources,'registration_commits':authorities,'analysis_seals':seals,'chronology_conclusion':'Historical definitions precede E59/E62 analysis-seal commits, but no dedicated pre-outcome category binding for these bank units was recovered. All 36 receipt assignments are exploratory; do not count them in confirmatory category-gap or confirmatory within-category subsets. Do not remove these units from J-only BA solely for missing category provenance.','E73_chronology':'No completed E73 ANALYSIS_SEAL.json located in checked local wcensus/wlens/i2 E73 paths. Incoming owner message reports sealed outcomes. No pre-outcome structural category binding recovered; do not infer pre-outcome eligibility from missing seal metadata.','E73_W7_W8':'Outside requested structural receipt. Keep W-lens existing pre-GO content tags and provenance unchanged.','search_scope':'Current origin/r/blindspot e58a catalog and E59/E62 J forecast category keys; no dedicated bank supplement or category keys found. Not a claim about unavailable histories.','outcomes_opened':False,'scores_computed':False}
 (HERE/'CATEGORY_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (HERE/'RECEIPT_SEAL.json').write_text(json.dumps({'files':{p.name:sha(p) for p in [HERE/'CATEGORY_RECEIPT.json',Path(__file__)]}},indent=2)+'\n')
 assert len(rows)==36 and len({(r['bank'],r['row']) for r in rows})==36
 assert all(not r['confirmatory_category_gap_eligible'] for r in rows)
 print('36 unique exploratory assignments; source/seal provenance recorded; no scores computed')
if __name__=='__main__':main()
