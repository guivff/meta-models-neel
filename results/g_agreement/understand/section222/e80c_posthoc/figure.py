"""Render already-computed post hoc aggregates; no scientific calculation."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
H=Path(__file__).resolve().parent
r=json.loads((H/'RESULTS.json').read_text()); o=r['readers']['oracle']; c=o['original_complete_case_pass_none_cohort']['conditions']; full=o['all_sealed_items']['conditions']
keys=['J_ablated','random_ablated','PCA_ablated'];names=['J-space','Random rank-384','Top-384 PCA'];colors=['#2166ac','#737b86','#b66a28']
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','font.size':14})
f=plt.figure(figsize=(16,9),facecolor='#fafaf7')
f.text(.055,.925,'E80c | How much variance did each ablation remove?',fontsize=25,weight='bold',color='#152b40')
f.text(.055,.88,'POST HOC · DESCRIPTIVE     Oracle / block 44     Paired item bootstrap, 2,000 draws',fontsize=14,color='#526273')
axes=[f.add_axes([.16,.42,.29,.32]),f.add_axes([.63,.42,.30,.32])]
for ax,metric,ci,title,scale in [(axes[0],'variance_removed_share','variance_removed_ci95','Read-site variance removed',100),(axes[1],'fall_per_variance_share','fall_per_variance_share_ci95','Pass-rate fall / variance removed',1)]:
 for y,(k,col) in enumerate(zip(keys,colors)):
  row=c[k];v=row[metric]*scale;lo,hi=[z*scale for z in row[ci]]
  ax.errorbar(v,y,xerr=[[v-lo],[hi-v]],fmt='o',color=col,markersize=10,capsize=5,lw=2)
  if scale==100:
   ax.scatter(full[k][metric]*100,y,marker='D',s=42,facecolor='white',edgecolor=col,zorder=4)
  ax.text(.98,y-.22,f'{v:.2f}'+('%' if scale==100 else '')+f'  [{lo:.2f}, {hi:.2f}]',transform=ax.get_yaxis_transform(),ha='right',va='center',fontsize=12,color=col)
 ax.set_yticks(range(3),names if scale==100 else ['','','']);ax.set_ylim(2.6,-.65)
 ax.set_title(title,loc='left',fontsize=18,pad=20,weight='bold');ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0,pad=12);ax.grid(axis='x',alpha=.16);ax.set_facecolor('#fafaf7')
 ax.set_xlim(-2 if scale==100 else 0,106 if scale==100 else 4.25)
 ax.set_xlabel('Share of centered activation variance (%)' if scale==100 else 'Pass-rate fall (pp) / variance removed (pp)',fontsize=12,labelpad=12)
f.text(.09,.29,'● Original pass-under-none cohort: 184 items, 0 missing exclusions',fontsize=12,color='#33495b')
f.text(.09,.255,'◇ All 518 sealed items: J 14.31% · random 7.72% · PCA 99.80%',fontsize=12,color='#526273')
f.text(.59,.29,'Pass-rate falls: J 57.61 pp · random 9.78 pp · PCA 96.74 pp',fontsize=12,color='#33495b')
f.text(.055,.19,'J has the largest fall per unit of removed variance in this post hoc comparison.',fontsize=19,weight='bold',color='#152b40')
f.text(.055,.14,'Normalization uses the same 184 items for fall and variance. Bases stay fixed in the bootstrap; no PCA refit.',fontsize=12,color='#526273')
f.text(.055,.105,'This ratio is not a variance-matched intervention or a causal slope. R-X3 remains NOT MET.',fontsize=12,color='#526273')
f.text(.055,.055,'§223 item 2 · Companion to the §222 2×2 · Sealed E80/E80c vectors and terminal judgments only · CPU, no model calls',fontsize=10,color='#687886')
f.savefig(H/'E80C_VARIANCE_POSTHOC.png',dpi=225,facecolor=f.get_facecolor());f.savefig(H/'E80C_VARIANCE_POSTHOC.svg',facecolor=f.get_facecolor())
