"""Report-only §226 arithmetic from sealed aggregates. No original analysis imports."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def verify(p,seal):
 for f,h in read(p/seal)['files'].items():assert sha(p/f)==h,f
p94=ROOT/'results/g_agreement/understand/e94/analysis_once_20261028'
p98=ROOT/'results/g_agreement/understand/e98/analysis_once'
verify(p94,'PUBLICATION_SEAL.json');verify(p98,'ANALYSIS_SEAL.json')
d=read(p94/'SUMMARY.json');m=d['pooled_value_grounded'];rs=m['readers'];best=max(rs,key=lambda r:rs[r]['precision']['rate'])
correct=sum(rs[r]['marginal_accuracy']['k'] for r in rs);denom=sum(rs[r]['marginal_accuracy']['n'] for r in rs)
rows=[r for r in read(p98/'RESULTS.json')['rows'] if r['binary']]
n=len(rows);missed=sum(r['native_label']=='MISSED' for r in rows);agree=sum(r['J_agrees'] for r in rows)
assert (n,missed,agree)==(23,20,18)
result={'status':'SEALED_AGGREGATE_REPORT_ONLY','no_analysis_replay':True,'E94':{'scope':d['pooling'],'paired_items':m['n'],'agreement_precision':m['ensemble']['precision'],'agreement_coverage':m['ensemble']['coverage'],'better_single_reader_by_precision':best,'better_single_precision':rs[best]['precision'],'single_readers':rs,'base_rate_correct_readouts':{'k':correct,'n':denom,'rate':correct/denom,'definition':'both reader readouts on common-parseable paired value-grounded items; no-mention/wrong are not correct'},'precision_gain_over_better_single':m['ensemble']['precision']['rate']-rs[best]['precision']['rate']},'E98':{'J_agreement':{'k':agree,'n':n,'rate':agree/n},'always_MISSED':{'k':missed,'n':n,'rate':missed/n},'J_minus_constant':(agree-missed)/n,'forecast_claim_on_Qwen3_4B':False,'decision':'§226: constant baseline >= 18/23; do not make forecast claim','scope':'23 binary rows only; 3 nonbinary excluded consistently','mandatory_caveat':'R5 64130637 independently verified numerical results; complete final typed-count/dual-input/old-rubric adapter finalized after terminal judging, so literal §217(6) pre-bank-seal custody NOT MET for complete final adapter. Historical pre-judging binary kernel and final-plan-before-claim verified; descriptive only.'},'sources':{str(p.relative_to(ROOT)):sha(p) for p in [p94/'PUBLICATION_SEAL.json',p94/'SUMMARY.json',p98/'ANALYSIS_SEAL.json',p98/'RESULTS.json']}}
(HERE/'BASELINES.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
report=f'''# §226 trust-slide baselines — sealed aggregate projection

E94 pooled value-grounded common-parseable items: {m['n']:,} paired items. E67's incompatible claim rubric and unavailable E62/E76 are outside this pool, exactly as in the original sealed analysis.

| Measure | Numerator / denominator | Rate |
|---|---:|---:|
| Agreement precision (decisive same-value agreement) | 943 / 1001 | 94.21% |
| Better single-reader precision: NLA | 1389 / 1596 | 87.03% |
| Oracle single-reader precision | 1442 / 1731 | 83.30% |
| Base rate of correct readouts, both readers | {correct} / {denom} | {100*correct/denom:.2f}% |
| Oracle base rate (marginal accuracy) | 1442 / 4313 | 33.43% |
| NLA base rate (marginal accuracy) | 1389 / 4313 | 32.20% |
| Agreement coverage | 1001 / 4313 | 23.21% |

Agreement precision exceeds the better single reader's precision by 7.18 percentage points descriptively. Precision denominators are stated-value readouts (single reader) or decisive same-value agreements (ensemble); base-rate denominators also include no-mention readouts. These are different selections/coverages, not a matched-coverage causal gain. Both-no-mention agreements are excluded from precision. No new confidence intervals, tests or source analysis were run; original Wilson intervals are copied in BASELINES.json. Better reader is selected by precision, not marginal accuracy; the original H-A1 comparison to marginal accuracy is preserved historically and is not reused as the precision comparison.

E98: J/native agreement **18/23 (78.26%)**; constant **always MISSED 20/23 (86.96%)**. J is 2 rows / 8.70 percentage points lower. Under §226, **no Qwen3-4B forecast claim is made**. All 23 binary rows included; 3 original nonbinary rows excluded from both denominators. This is a same-family transfer result, not a second model family.

Mandatory E98 caveat: R5 64130637 independently verified all numerical results, but the complete final typed-count/dual-input/old-rubric adapter was finalized after terminal judging: literal §217(6) pre-bank-seal custody NOT MET for complete final adapter. Historical pre-judging binary kernel and final plan before exclusive claim verified. Descriptive only; do not rerun to remove chronology.

Source seals and exact aggregate hashes: BASELINES.json. This is new presentation arithmetic from sealed summaries; all original results/claims remain untouched.
'''
(HERE/'NOTES.md').write_text(report)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
fig=plt.figure(figsize=(16,9),facecolor='#f6f8fb')
fig.text(.055,.91,'When does agreement deserve trust?',fontsize=29,weight='bold',color='#173449')
fig.text(.055,.855,'Sealed-data baselines · §226 · descriptive',fontsize=14,color='#526775')
a=fig.add_axes([.055,.28,.43,.49]);a.set_facecolor('#f6f8fb')
vals=[.942057942,.870300752,correct/denom]
a.barh([2,1,0],vals,color=['#187d89','#6f849b','#c6ced8'],height=.56)
for y,v,label in zip([2,1,0],vals,['943 / 1,001','1,389 / 1,596',f'{correct:,} / {denom:,}']):a.text(v+.015,y,f'{v:.1%}  ({label})',va='center',fontsize=13)
a.set_yticks([]);a.set_ylim(-.45,2.55);a.set_xlim(0,1.36);a.set_xticks([])
for y,label in zip([2,1,0],['Agreement precision','Better single: NLA','Correct-readout base rate']):a.text(0,y+.34,label,fontsize=12,va='bottom')
for s in a.spines.values():s.set_visible(False)
a.set_title('E94 · agreement selects a more precise subset',loc='left',fontsize=16,pad=18,weight='bold')
fig.text(.56,.73,'E98 · Qwen3-4B',fontsize=20,weight='bold',color='#173449')
fig.text(.56,.60,'18/23',fontsize=46,weight='bold',color='#187d89');fig.text(.77,.61,'J/native agreement\n78.3%',fontsize=16,color='#173449')
fig.text(.56,.43,'20/23',fontsize=46,weight='bold',color='#6f849b');fig.text(.77,.44,'Always MISSED\n87.0%',fontsize=16,color='#173449')
fig.text(.56,.29,'No Qwen3-4B forecast claim (§226)',fontsize=18,weight='bold',color='#963f32')
fig.text(.055,.20,'E94: agreement coverage 23.2%; precision and base rate use different denominators. NLA is the better single by precision.',fontsize=11,color='#526775')
fig.text(.055,.13,'E98: numerically verified by R5; final adapter amended after judging, so complete-adapter pre-bank-seal custody NOT MET.\nDescriptive only. Full denominator definitions, source seals and limitations: NOTES.md.',fontsize=11,color='#526775',linespacing=1.6)
fig.savefig(HERE/'TRUST_BASELINES.png',dpi=160);fig.savefig(HERE/'TRUST_BASELINES.svg');plt.close(fig)
(HERE/'PUBLICATION_SEAL.json').write_text(json.dumps({'status':'COMPLETE_REPORT_ONLY','files':{f:sha(HERE/f) for f in ['BASELINES.json','NOTES.md','TRUST_BASELINES.png','TRUST_BASELINES.svg','build.py']}},indent=2,sort_keys=True)+'\n')
print('Sealed aggregate baselines and PNG/SVG saved; no analysis replay.')
