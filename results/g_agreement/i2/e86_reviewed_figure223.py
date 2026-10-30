"""Render independently reviewed E86 sealed aggregate values; no analysis replay."""
from pathlib import Path
import json,hashlib,datetime
R=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 src=R.parent/'wt-wmech2/results/g_agreement/understand/e86/analysis_once';seal=json.loads((src/'ANALYSIS_SEAL.json').read_text());assert sha(src/'ANALYSIS_SEAL.json')=='f8c8af780fb7cbb31705f900a69d3b6e8cb53eed2ce1c6053c52ac721ddca43f'
 for n,h in seal['files'].items():assert sha(src/n)==h
 d=json.loads((src/'RESULTS.json').read_text());assert d['R_K1']=='NOT EVALUABLE' and d['falsifier']=='NOT EVALUABLE'
 out=R/'results/g_agreement/sealed/E86_REVIEWED_FIGURE223';out.mkdir(exist_ok=False)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 rows=[(reader,arm,d['R_K2_descriptive'][reader][arm])for reader in ['oracle','nla']for arm in ['honest','role']]
 fig,(a,b)=plt.subplots(1,2,figsize=(13,6),gridspec_kw={'width_ratios':[1.3,1]});fig.subplots_adjust(left=.13,right=.97,top=.76,bottom=.25,wspace=.40)
 colors=['#238b8d','#e79b42','#8063ad','#d8dee4'];keys=['truth_only','wrong_only','both','neither'];labels=['Truth only','Wrong only','Both','Neither']
 for y,(reader,arm,x)in enumerate(rows):
  assert x['kept']==200 and x['missing']==0 and sum(x[k]for k in keys)==200
  left=0
  for k,c in zip(keys,colors):
   value=x[k]/200;a.barh(y,value,left=left,color=c,height=.58,edgecolor='white')
   if x[k]>=15:a.text(left+value/2,y,str(x[k]),ha='center',va='center',fontsize=10,color='white'if k!='neither'else'#263238')
   left+=value
  point=x['conditional_wrong_minus_truth'];den=x['naming_either_value']
  if den:
   est=point['estimate'];lo,hi=point['CI95'];b.errorbar(est,y,xerr=[[est-lo],[hi-est]],fmt='o',color='#334c62',capsize=4,markersize=7)
   b.text(.98,y-.22,f'named {den}/200',ha='right',fontsize=9,color='#52616b')
  else:b.text(-.05,y,'Not evaluable: names neither value',ha='center',va='center',fontsize=9,color='#52616b')
 a.set_yticks(range(4),[f'{"NLA" if reader=="nla" else "Oracle"} · {arm}'for reader,arm,x in rows]);a.invert_yaxis();b.set_ylim(a.get_ylim());b.set_yticks([])
 a.set_xlim(0,1);a.set_xticks([0,.25,.5,.75,1],['0%','25%','50%','75%','100%']);a.set_xlabel('Share of 200 kept readouts per row');a.set_title('What the released readouts name',loc='left',fontsize=12,pad=14)
 b.axvline(0,color='#bcc6cf',lw=1);b.set_xlim(-1.06,1.03);b.set_xticks([-1,-.5,0,.5,1]);b.set_xlabel('Conditional P(wrong) − P(truth)');b.set_title('Descriptive contrasts · sealed 95% CIs',loc='left',fontsize=12,pad=14)
 for ax in [a,b]:
  ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='both',length=0);ax.grid(axis='x',alpha=.12);ax.set_axisbelow(True)
 from matplotlib.patches import Patch
 fig.legend([Patch(facecolor=c)for c in colors],labels,loc='lower center',bbox_to_anchor=(.5,.13),ncol=4,frameon=False)
 fig.suptitle('E86 · Released honest and role readouts',x=.13,y=.95,ha='left',fontsize=19,weight='bold')
 fig.text(.13,.86,'R-K1 and falsifier: NOT EVALUABLE — lie BOW gate failed; open cohort underpowered.',fontsize=11,color='#8c3b35')
 fig.text(.13,.075,'Role results are descriptive. Oracle Δ = 0.095 [0, 0.19]; NLA conditional rates are undefined (named n = 0).',fontsize=10)
 fig.text(.13,.04,'Both-valued readouts count toward both probabilities. All 800 primary judgments kept; original-rubric sensitivity remains separate.',fontsize=9,color='#52616b')
 fig.text(.13,.01,'Copied from sealed E86 analysis ca7d45c9; R-2 d444692d9 reproduced all 54 CIs. Figure rendering adds no statistics.',fontsize=8,color='#52616b')
 for ext in ['png','svg']:fig.savefig(out/('E86_released_readouts.'+ext),dpi=170,facecolor='white')
 svg=out/'E86_released_readouts.svg';svg.write_text('\n'.join(l.rstrip()for l in svg.read_text().splitlines())+'\n')
 plt.close(fig)
 first=out/'E86_released_readouts.png';record=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),experiment='E86',status='FIGURE_RENDERED_FROM_REVIEWED_AGGREGATES_FIGURE_REVIEW_PENDING',analysis_seal_sha256=sha(src/'ANALYSIS_SEAL.json'),results_sha256=sha(src/'RESULTS.json'),review_commit='d444692d9',no_analysis_or_bootstrap_replay=True,first_output_evidence=dict(member=first.name,mtime_ns=first.stat().st_mtime_ns,sha256=sha(first)),files={p.name:sha(p)for p in out.iterdir()if p.is_file()})
 (out/'FIGURE_SEAL.json').write_text(json.dumps(record,indent=2)+'\n');print(out)
if __name__=='__main__':main()
