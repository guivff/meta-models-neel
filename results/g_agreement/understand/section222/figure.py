"""§222 evidence schematic from hash-verified sealed aggregate numbers only.
No raw outcomes, imports of analysis kernels, fits, bootstraps or new verdicts.
Run from any directory: python /absolute/path/to/section222/figure.py
"""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', '/tmp/wlens-section222-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BLUE = '#176f89'
INK = '#172936'
MUTED = '#526570'
ORANGE = '#a65a26'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    binding = json.loads((HERE / 'SOURCE_BINDINGS.json').read_text())
    data = {}
    for e, pin in binding['sources'].items():
        r, s = ROOT / pin['results'], ROOT / pin['seal']
        assert sha(r) == pin['results_sha256'], e + ' result changed'
        assert sha(s) == pin['seal_sha256'], e + ' seal changed'
        seal = json.loads(s.read_text())
        assert seal['status'] == 'COMPLETE_ONCE' and seal['files']['RESULTS.json'] == sha(r)
        data[e] = json.loads(r.read_text())
    return data


def estimate(m):
    lo, hi = m['CI95']
    return f"{m['estimate']:+.2f}  [{lo:+.2f}, {hi:+.2f}]"


def card(fig, box, color):
    ax = fig.add_axes(box)
    ax.set_axis_off()
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle='round,pad=0.0,rounding_size=0.025',
                              facecolor='white', edgecolor='#ccd7dc', linewidth=1.1,
                              transform=ax.transAxes))
    ax.plot([.045, .955], [.80, .80], color=color, lw=2, transform=ax.transAxes)
    return ax


def text(ax, x, y, value, size=11, color=INK, weight='normal', **kw):
    ax.text(x, y, value, fontsize=size, color=color, fontweight=weight,
            va='top', transform=ax.transAxes, **kw)


def main():
    d = load()
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    fig = plt.figure(figsize=(15, 12.8), facecolor='#f3f6f7')
    fig.text(.06, .965, 'What the reader reports vs what the model uses', fontsize=24,
             weight='bold', color=INK, va='top')
    fig.text(.06, .926, '§222  •  Oracle reader  •  sealed estimates and existing 95% intervals',
             fontsize=12, color=MUTED, va='top')
    fig.text(.535, .881, 'MODEL USES IT?', ha='center', fontsize=12, weight='bold', color=INK)
    fig.text(.307, .851, 'YES — behaviour flips', ha='center', fontsize=16, weight='bold', color=BLUE)
    fig.text(.756, .851, 'NO STRICT FLIPS — E105', ha='center', fontsize=16, weight='bold', color=BLUE)
    fig.text(.024, .545, 'STATE PRESENT AT THE READ SITE?', rotation=90,
             ha='center', va='center', fontsize=12, weight='bold', color=INK)

    tl = card(fig, [.07, .51, .435, .312], BLUE)
    tr = card(fig, [.53, .51, .435, .312], BLUE)
    bl = card(fig, [.07, .17, .435, .312], ORANGE)
    br = card(fig, [.53, .17, .435, .312], ORANGE)

    text(tl,.045,.95,'PRESENT / DIRECTLY STEERED',10,BLUE,'bold')
    text(tl,.045,.895,'E101 · write at the read site',16,INK,'bold')
    text(tl,.045,.755,'Row',11,MUTED,'bold');text(tl,.44,.755,'Reader S [95% CI]',11,MUTED,'bold')
    for y,row,label in [(.67,'fact_recall','Fact recall'),(.46,'language_plan','Language plan')]:
        z=d['e101']['rows'][row]['oracle']
        text(tl,.045,y,label,12,INK,'bold')
        text(tl,.44,y,estimate(z['S_target'])+'*',11)
        text(tl,.045,y-.07,f"Behaviour flips: {z['flipped_n']}/84",10,MUTED)
        text(tl,.045,y-.125,'ΔS vs random: '+estimate(z['difference']),11,BLUE)
    text(tl,.045,.14,'S targets the steered value; behaviour-flipped cohort.',10,MUTED)
    text(tl,.045,.075,'Only 2/14 cells reach a dose; E101 rules NOT EVALUABLE.',9.5,MUTED)

    text(tr,.045,.95,'PRESENT / TRANSPLANTED',10,BLUE,'bold')
    text(tr,.045,.895,'E100 reader · E105 behaviour',16,INK,'bold')
    text(tr,.045,.755,'E100 transplant row',11,MUTED,'bold');text(tr,.44,.755,'Donor S [95% CI]',11,MUTED,'bold')
    for y,row,label in zip([.67,.575,.48,.385,.29],
            ['fact_recall','format_plan','language_continuation','language_plan','tense_implicit'],
            ['Fact recall','Format plan','Language continuation','Language plan','Tense']):
        z=d['e100']['rows'][row]['oracle']['transplant']
        text(tr,.045,y,label,11);text(tr,.44,y,estimate(z)+('*' if z['over_5_percent'] else ''),11)
    controls=d['e105']['rows']
    assert all(z['flip_T']['estimate']==0 and z['flip_S']['estimate']==0 for z in controls.values())
    text(tr,.045,.17,'E100 R-PC: 5/5. E105: 0/84 flips in every run row.',10,BLUE,'bold')
    text(tr,.045,.105,'E105 rows: fact, format, language plan, nesting, page-range.',10,MUTED)
    text(tr,.045,.05,'Indent level NOT RUN; continuous changes can be nonzero.',9.5,MUTED)

    text(bl,.045,.95,'WRITTEN ELSEWHERE · ARRIVAL UNRESOLVED',10,ORANGE,'bold')
    text(bl,.045,.895,'E104 · eight earlier positions',16,INK,'bold')
    text(bl,.045,.755,'Arm U row',11,MUTED,'bold');text(bl,.44,.755,'Reader S [95% CI]',11,MUTED,'bold')
    for y,row,label in [(.67,'fact_recall','Fact recall'),(.46,'language_plan','Language plan')]:
        z=d['e104']['arms']['U'][row]
        text(bl,.045,y,label,12,INK,'bold')
        text(bl,.44,y,estimate(z['S_target'])+('*' if z['missing']['steered']['cohort_over5percent'] else ''),11)
        text(bl,.045,y-.07,f"Behaviour flips: {z['flipped_n']}/84",10,MUTED)
        text(bl,.045,y-.125,'ΔS vs random: '+estimate(z['difference']),11,ORANGE)
    text(bl,.045,.14,'S targets the steered value; behaviour-flipped cohort.',10,MUTED)
    text(bl,.045,.075,'Written elsewhere does not prove absence at the read site.',9.5,ORANGE)

    text(br,.045,.95,'PROBE-PRESENT, YET NOT REPORTED',10,ORANGE,'bold')
    text(br,.045,.895,'E100 · missed bookkeeping rows',16,INK,'bold')
    text(br,.045,.755,'Transplant row',11,MUTED,'bold');text(br,.44,.755,'Donor S [95% CI]',11,MUTED,'bold')
    for y,row,label in [(.66,'nesting_depth','Nesting depth'),(.55,'indent_level','Indent level'),(.44,'page_range_digit','Page-range digit')]:
        z=d['e100']['rows'][row]['oracle']['transplant']
        text(br,.045,y,label,11);text(br,.44,y,estimate(z),11)
    text(br,.045,.30,'State present by probe ≥ 0.90 (§222).',11,ORANGE,'bold')
    text(br,.045,.215,'E105: 0 strict flips for nesting depth / page-range digit.',10,MUTED)
    text(br,.045,.15,'Indent level was not run in E105.',10,MUTED)
    text(br,.045,.11,'This is an exception to presence ⇒ reader reporting,',9.5,ORANGE)
    text(br,.045,.055,'not a demonstrated absent-state cell.',9.5,ORANGE)

    fig.text(.07,.127,'Evidence schematic, not a completed 2 × 2 factorial: bottom cells do not establish state absence.',
             fontsize=11, color=INK, weight='bold')
    fig.text(.07,.101,'S = signed judged report (correct minus wrong). E101/E104: steered-value target; E100: donor-value target.',
             fontsize=10,color=MUTED)
    fig.text(.07,.079,'ΔS is the sealed steered-minus-random contrast. * >5% terminal missing judgments; retained as missing, never zero.',
             fontsize=10,color=MUTED)
    fig.text(.07,.057,'All displayed estimates / intervals are copied from COMPLETE_ONCE results. No pooling, fitting, bootstrap or new verdict.',
             fontsize=10,color=MUTED)
    fig.text(.07,.035,'Sources: E100, E101, E104, E105 analysis_once/RESULTS.json + ANALYSIS_SEAL.json; exact hashes in SOURCE_BINDINGS.json.',
             fontsize=9,color=MUTED)
    fig.savefig(HERE/'SITE_LOCAL_2X2.png', dpi=180, facecolor=fig.get_facecolor())
    fig.savefig(HERE/'SITE_LOCAL_2X2.svg', facecolor=fig.get_facecolor(), metadata={'Date':None})
    plt.close(fig)
    outputs={p.name:sha(p) for p in [HERE/'figure.py',HERE/'SOURCE_BINDINGS.json',HERE/'SITE_LOCAL_2X2.png',HERE/'SITE_LOCAL_2X2.svg']}
    (HERE/'FIGURE_SEAL.json').write_text(json.dumps({'status':'FIGURE_ONLY','scope':'§222 sealed aggregate display; no statistical rerun','files':outputs},indent=2)+'\n')


if __name__ == '__main__':
    main()
