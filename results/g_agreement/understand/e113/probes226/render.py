"""Render sealed E113 AUROC table only; no fitting or metric recomputation."""
import json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent/'analysis_once'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((P/'ANALYSIS_SEAL.json').read_text())
for f,h in s['files'].items():assert sha(P/f)==h
r=json.loads((P/'RESULTS.json').read_text());rows=['nesting_depth','indent_level','page_range_digit','fact_recall','format_plan','language_plan'];positions=['injected_activation','first_generated_token']
plt.rcParams.update({'svg.fonttype':'none','font.family':'DejaVu Sans'})
fig,axes=plt.subplots(2,3,figsize=(15,8),sharex=True,sharey=True)
for ax,row in zip(axes.flat,rows):
 for pos,c in zip(positions,['#167b88','#b16a35']):ax.plot(range(64),[r['rows'][row][str(i)][pos] for i in range(64)],label=pos.replace('_',' '),color=c,lw=1.8)
 ax.axhline(.90,color='#56616b',ls='--',lw=.8);ax.axhline(.65,color='#9ca3a8',ls=':',lw=.8)
 ax.set_title(row,loc='left',weight='bold');ax.set_ylim(0,1.025);ax.set_xlim(0,63);ax.grid(alpha=.12)
 ax.set_xlabel('Oracle decoder block output');ax.set_ylabel('Test AUROC')
axes.flat[0].legend(loc='lower right',fontsize=9)
fig.suptitle('E113 · Does state enter the Oracle reader?',fontsize=21,weight='bold')
fig.text(.04,.02,'84 dev / 84 test per row · 5-fold dev-only selection · all 768 test cells once · final binder after capture, before CPU claim',fontsize=10)
fig.tight_layout(rect=[0,.05,1,.94]);fig.savefig(P/'AUROC_BY_LAYER.png',dpi=160);fig.savefig(P/'AUROC_BY_LAYER.svg');plt.close(fig)
(P/'FIGURE_SEAL.json').write_text(json.dumps({'status':'SEALED_RESULT_RENDER_ONLY','analysis_seal_sha256':sha(P/'ANALYSIS_SEAL.json'),'files':{f:sha(P/f) for f in ['AUROC_BY_LAYER.png','AUROC_BY_LAYER.svg']},'render_source_sha256':sha(Path(__file__))},indent=2,sort_keys=True)+'\n')
