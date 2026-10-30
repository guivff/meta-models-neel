"""Report-only reviewed E81 figure; reuse sealed values, CIs and bounds unchanged.
No analysis, bootstrap, private truth join, judging or source-bank run.
"""
import hashlib,json,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/i2-e81-reviewed-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'results/g_agreement/sealed/E81_RT1_ANALYSIS_V2'
OUT=ROOT/'results/g_agreement/sealed/E81_RT1_REVIEWED'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    seal=json.loads((SOURCE/'ANALYSIS_SEAL.json').read_text())
    for name,digest in seal['files'].items():assert sha(SOURCE/name)==digest
    assert not OUT.exists();OUT.mkdir()
    d=json.loads((SOURCE/'SUMMARY.json').read_text());rows=d['arms']['generic']['rows']
    order=sorted(rows,key=lambda x:(x['oracle_S'],x['key']))
    fig,axes=plt.subplots(1,2,figsize=(14,11),sharey=True)
    palette={'e49':'#3366a0','e57':'#3b8c72','e59':'#a36d24','e73':'#8d579b'}
    for ax,arm,title in zip(axes,('generic','oracle_wording'),('Generic instruction — PRIMARY','Oracle wording — secondary')):
        index={x['key']:x for x in d['arms'][arm]['rows']}
        for y,x in enumerate(order):
            z=index[x['key']];lo,hi=z['CI95'];ml,mh=z['S_missing_bounds'];color=palette[z['bank']]
            ax.plot([ml,mh],[y,y],color='#bec4cb',lw=5,alpha=.7,zorder=1)
            ax.plot([lo,hi],[y,y],color=color,lw=1.5,zorder=2)
            ax.scatter(z['S'],y,color=color,s=22,zorder=3)
            ax.scatter(z['oracle_S'],y,marker='|',color='#222222',s=90,zorder=4)
        ax.axvline(.1,color='#777777',ls='--',lw=.8);ax.axvline(.2,color='#777777',ls=':',lw=.8)
        ax.set_title(title,fontsize=12);ax.set_xlim(-.65,1.08);ax.set_xlabel('S = (correct-only − wrong-only) / kept judgments')
        ax.grid(axis='x',alpha=.15);ax.spines[['top','right']].set_visible(False)
    axes[0].set_yticks(range(len(order)),[x['key'] for x in order],fontsize=8)
    fig.suptitle('Text descriptions reproduce most Oracle misses',fontsize=17,x=.57,y=.98)
    fig.text(.57,.945,'Primary: 18/22 Oracle-missed rows stay missed; 8/13 Oracle-reported rows stay reported',ha='center',fontsize=10)
    fig.text(.57,.025,'Dots: text S; black ticks: frozen Oracle S; thin bars: 95% item bootstrap; gray bars: missingness bounds.\nR-T1 point rule MET; primary is sensitive to missingness and rubric. R-2 independently verified.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.93]);fig.savefig(OUT/'E81_RT1_ROWS.png',dpi=180);fig.savefig(OUT/'E81_RT1_ROWS.svg');plt.close(fig)
    svg=OUT/'E81_RT1_ROWS.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    notes=(SOURCE/'SLIDE_NOTES.md').read_text().replace('(provisional, R-2 review pending)','(independently reviewed)').replace('Independent R-2 review is pending; no reviewer-chat message was sent.','Independent R-2 review is complete at ea5d536ed3dad2d77001f19fe3b0d84a702133a2. The original sealed figure’s review-pending caption is historical; this report-only rendering supersedes that label.')
    notes+='\nReviewer addendum: all 222 row CIs reproduce exactly. Excluding the three authorized path-redacted records leaves every full-grid and matched-rubric R-T1 verdict and falsifier unchanged. This sensitivity is supplied by R-2; the sealed v2 scientific outputs remain unchanged. Both rubric sensitivity and worst-case missingness caveats remain mandatory. The matched-subset difference does not isolate a pure rubric-clause effect from fresh judge variation.\n'
    (OUT/'SLIDE_NOTES.md').write_text(notes)
    (OUT/'REPORT_SEAL.json').write_text(json.dumps(dict(status='R2_INDEPENDENTLY_REVIEWED_POINT_MET_WITH_SENSITIVITY_LIMITS',review_commit='ea5d536ed3dad2d77001f19fe3b0d84a702133a2',source_analysis_seal_sha256=sha(SOURCE/'ANALYSIS_SEAL.json'),source_summary_sha256=sha(SOURCE/'SUMMARY.json'),report_code_sha256=sha(Path(__file__)),no_analysis_or_bootstrap_rerun=True,only_figure_caption_review_status_changed=True,files={p.name:sha(p) for p in OUT.iterdir()}),indent=2)+'\n')
if __name__=='__main__':main()
