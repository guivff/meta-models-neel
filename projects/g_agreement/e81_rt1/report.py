"""Render and arithmetically audit the sealed E81 summary; never call analysis.

No outcome recomputation, external API, new truth join, or source-bank rerun.
"""
import csv, hashlib, json, os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/i2-e81-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/g_agreement/sealed/E81_RT1_ANALYSIS_V2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def main():
    seal=json.loads((OUT/'ANALYSIS_SEAL.json').read_text())
    for n,d in seal['files'].items():assert sha(OUT/n)==d
    d=json.loads((OUT/'SUMMARY.json').read_text());base=json.loads((OUT/'ORACLE_BASELINES.json').read_text())
    rows=d['arms']['generic']['rows'];r=d['arms']['generic']['rule']
    assert len(rows)==37 and sum(x['N_planned'] for x in rows)==3688
    assert sum(x['missing'] for x in rows)==131
    assert sum(x['missing'] for x in d['arms']['oracle_wording']['rows'])==72
    assert r['text_misses_in_oracle_missed']==18 and r['oracle_missed_rows']==22
    assert r['text_reports_in_oracle_reported']==8 and r['oracle_reported_rows']==13
    assert r['text_missed_all_rows']==21 and not r['channel_insensitive_falsifier']
    # Baseline uncertainty shown separately; primary text bounds hold the
    # original source-analysis Oracle S cohorts fixed, as preregistered.
    uncertainty=[]
    for x in rows:
        b=base[x['key']];n=b['N'];m=b['missing'];total=b['S']*n
        bounds=[(total-m)/(n+m),(total+m)/(n+m)]
        uncertainty.append(dict(key=x['key'],oracle_S=b['S'],kept=n,missing=m,bounds=bounds,
            cohort_missed_can_flip=(bounds[0]<=.1<=bounds[1]) if m else False,
            cohort_reported_can_flip=(bounds[0]<=.2<=bounds[1]) if m else False))
    dump(OUT/'BASELINE_MISSINGNESS_DIAGNOSTIC.json',dict(scope='Diagnostic only; original Oracle cohorts remain fixed, no E73/source-bank analysis rerun',rows=uncertainty))
    with (OUT/'ROWS.csv').open('x',newline='') as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(['arm','bank','row','Oracle_S','text_S','CI95_low','CI95_high','planned','kept','missing','missing_low','missing_high'])
        for arm in ('generic','oracle_wording'):
            for x in d['arms'][arm]['rows']:
                w.writerow([arm,x['bank'],x['row'],x['oracle_S'],x['S'],*x['CI95'],x['N_planned'],x['kept'],x['missing'],*x['S_missing_bounds']])
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
    fig.text(.57,.025,'Dots: text S; black ticks: frozen Oracle S; thin bars: 95% item bootstrap; gray bars: missingness bounds.\nR-T1 point rule MET; primary is sensitive to missingness and rubric. R-2 review pending.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.93]);fig.savefig(OUT/'E81_RT1_ROWS.png',dpi=180);fig.savefig(OUT/'E81_RT1_ROWS.svg');plt.close(fig)
    svg=OUT/'E81_RT1_ROWS.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    notes='''# E81 — text-only baseline (provisional, R-2 review pending)

Judging completed 2026-10-28 23:12:16Z (2026-10-29 00:12:16 CET). Actual cost **$4.10268275** under the **$33 total cap**; no further judging is required.

The registered generic-arm R-T1 point rule is **MET**: descriptions also miss **18/22 (81.8%)** Oracle-missed rows (threshold ≥80%), and report **8/13 (61.5%)** Oracle-reported rows (threshold ≥50%). Two Oracle rows between 0.10 and 0.20 remain in the all-row falsifier denominator but neither stratum. The channel-insensitivity falsifier is **not triggered**: text S≤0.10 on **21/37 (56.8%)**, below 90%.

Oracle wording is secondary and cannot alter the primary verdict: **20/22 (90.9%)** and **8/13 (61.5%)**; point rule MET.

**Slide caveat:** the primary point verdict is **not robust to worst-case missing judgments**. Generic has 131/3,688 missing (3.55%; four rows >5%); secondary 72/3,688 (1.95%; two rows >5%). Missing records are excluded from S and explicitly bounded as all correct/all wrong, never zero-coded. The secondary rule survives these text-judgment bounds. These bounds hold the original Oracle cohorts fixed; separate source-baseline missingness diagnostics are included.

**Rubric sensitivity:** on the same frozen 25% subset, the amended rubric meets R-T1 but the original rubric does not (17/22=77.3% miss agreement, below 80%, in both instruction arms). This is a matched-subset sensitivity, not an original-rubric result on the whole grid. Report the dependency, not an unconditional robust confirmation.

**Interpretation:** most states missed by Oracle are also absent from ordinary text descriptions. The registered rule is named “reader-specific,” but its expected first condition is shared absence; meeting it does not establish a uniquely reader-specific mechanism. Row-level informative exceptions: text reports / Oracle misses: E49 arith_carry, unit_system, user_expertise. Reverse: E57 loop_direction, subject_number; E59 stance_plan.

All 37 registered rows retained. Six probe-passing E49 rows omitted by its old additional base-text gate are scored here solely as an E81 baseline supplement, using the unchanged sealed E49 regex and already acquired native readouts. Original E49 and E73 analyses are neither rerun nor mutated.

Implementation audit: v1 had an E73 A/B polarity error and is explicitly INVALIDATED, with original intent/code/output preserved. Corrected code binds every E73 item to its original sealed private key (0=A,1=B); other banks retain 1=A,0=B. The regression suite has 13 passing synthetic tests. Code was committed before the one corrective recomputation. No new API/GPU calls, rubric edits, row selection or threshold changes.

Artifacts: SUMMARY.json, ROWS.csv, E81_RT1_ROWS.png/svg, ORACLE_BASELINES.json, PROVENANCE.json and source analysis seals. Private labels/joins remain local. Independent R-2 review is pending; no reviewer-chat message was sent.
'''
    (OUT/'SLIDE_NOTES.md').write_text(notes)
    request=ROOT/'results/g_agreement/i2/E81_R2_REVIEW_REQUEST.md'
    request.write_text('''# E81 R-2 review request — FILE publication only

Please review `results/g_agreement/sealed/E81_RT1_ANALYSIS_V2` and committed `projects/g_agreement/e81_rt1`. Primary point rule MET; primary missingness/rubric sensitivity must be reported. Review all37 source-probe-selected rows, six E49 supplemental baseline rows, exact packet/source-key A/B polarity including E73 inversion, kept-only S and full-N bounds, generic-primary precedence, 80%/50%/90% inclusive thresholds, informative exceptions, 2000 item-bootstrap draws/seed20261027, and matched old-rubric sensitivity. The failed v1 remains sealed and explicitly INVALIDATED; v2 is the single source-bound implementation correction. No paid judging rerun or source-bank analysis rerun. Independent review has NOT been performed by the operator.
''')
    dump(OUT/'REPORT_SEAL.json',dict(status='RENDERED_REVIEW_PENDING',analysis_seal_sha256=sha(OUT/'ANALYSIS_SEAL.json'),report_code_sha256=sha(__file__),files={f.name:sha(f) for f in OUT.iterdir() if f.name!='REPORT_SEAL.json'}))
    print(str(OUT/'SLIDE_NOTES.md'))
if __name__=='__main__':main()
