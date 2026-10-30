"""E87 depth profile and descriptive classification (§200 E87 clarification 3, 4c3e9dca; reporting only, no rule change).
Extends 4bd32a3a's output with one figure and a table; uses the same pinned grid and join as e87_analysis.

Frozen choices (committed before the grouped grid seals):
- Figure layers {20, 28, 36, 44, 52, 60} exactly as listed; layer 56 (measured since clarification 1) is in the table only.
- S_layer per row and arm with an item-bootstrap 95% CI (2000 draws, seed 20261029); placebo S_layer beside it.
- Floor at each layer = max(0, E87 placebo S_layer at that layer, the row's E76 judged Oracle floor if E76 has the row,
  taken as max(0, S) over E76's random and shuffled pools). The 0 clamp is §200 E87 clarification 4 (ee7ec683). A layer "counts" when S_layer(real) - floor >= 0.20.
- Classes (on the six layers; earlier = 20/28/36, later = 52/60):
  persistent = counts at 44 and at >= 1 earlier layer; consumed = counts at an earlier layer, not at 44 or later;
  late = counts only after 44; never = counts nowhere. Patterns outside the four (44 only; earlier then later without
  44) are labelled explicitly, never forced into a class.
- First mention: median first_position among real-arm groups that state a value, per row and layer.
- E72 cells (blocks 36 and 40) are overlaid for shared rows and marked off-distribution; they never enter the class.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from .e87_analysis import grid, read, sha, require, MISSED, CONTROLS, SEED, DRAWS

FIG_LAYERS = (20, 28, 36, 44, 52, 60)
TABLE_LAYERS = (20, 28, 36, 44, 52, 56, 60)
EARLIER, LATER, BAR = (20, 28, 36), (52, 60), 0.20


def layer_stats(cells, row, arm, layer):
    c = cells.get((row, 'oracle', arm, layer), {});v = np.array([np.nan if x is None else x for _, x in sorted(c.items())], float)
    if not np.isfinite(v).any():return dict(S=None, ci95=None, n=int(np.isfinite(v).sum()))
    ix = np.random.default_rng(SEED).integers(0, len(v), (DRAWS, len(v)));z = v[ix];cnt = np.isfinite(z).sum(1)
    m = np.divide(np.nansum(z, 1), cnt, out=np.full(DRAWS, np.nan), where=cnt > 0);m = m[np.isfinite(m)]
    return dict(S=float(np.nanmean(v)), ci95=[float(np.quantile(m, .025)), float(np.quantile(m, .975))], n=int(np.isfinite(v).sum()))


def e76_floors(table):
    out = {}
    for r in table['rows']:
        o = r['readers'].get('oracle', {});vals = [p['judged_full']['S']['estimate'] for p in o.values() if p.get('judged_full', {}).get('S')]
        if vals:out[r['row']] = max(0.0, max(vals))
    return out


def classify(counts):
    at44 = counts[44];early = any(counts[L] for L in EARLIER);late = any(counts[L] for L in LATER)
    if at44 and early:return 'persistent'
    if early and not at44 and not late:return 'consumed'
    if late and not at44 and not early:return 'late'
    if not (at44 or early or late):return 'never'
    return 'outside the four (' + ('44 only' if at44 else 'earlier and later without 44') + ')'


def profile(cells, first, floors76):
    out = {}
    for row in MISSED+CONTROLS:
        real = {L: layer_stats(cells, row, 'real', L) for L in TABLE_LAYERS}
        plac = {L: layer_stats(cells, row, 'placebo', L) for L in TABLE_LAYERS}
        f76 = floors76.get(row)
        floor = {L: max([0.0]+[x for x in (plac[L]['S'], f76) if x is not None]) for L in FIG_LAYERS}  # clarification 4 (ee7ec683): floor >= 0
        counts = {L: real[L]['S'] is not None and real[L]['S'] - floor[L] >= BAR for L in FIG_LAYERS}
        out[row] = dict(real={str(L): v for L, v in real.items()}, placebo={str(L): v for L, v in plac.items()},
                        floor={str(L): v for L, v in floor.items()}, e76_floor=f76, counts={str(L): v for L, v in counts.items()},
                        **{'class': classify(counts)}, first_mention_median={str(L): (float(np.median(first[(row, L)])) if first.get((row, L)) else None) for L in FIG_LAYERS})
    return out


def first_by_layer(judgments, join):
    J = {x['id']: x for x in join};first = {}
    for c in judgments:
        j = J[c['id']]
        if j['reader'] == 'oracle' and j['arm'] == 'real' and c['category'] == 'states_value' and c.get('first_position') is not None:
            first.setdefault((j['row'], j['layer']), []).append(c['first_position'])
    return first


def figure(prof, e72, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = list(prof);fig, axes = plt.subplots(2, 5, figsize=(17, 6.6), sharey=True, constrained_layout=True)
    for ax, row in zip(axes.flat, rows):
        p = prof[row];xs = list(FIG_LAYERS)
        ys = [p['real'][str(L)]['S'] for L in xs];lo = [p['real'][str(L)]['ci95'][0] if p['real'][str(L)]['ci95'] else None for L in xs]
        hi = [p['real'][str(L)]['ci95'][1] if p['real'][str(L)]['ci95'] else None for L in xs]
        ok = [i for i, y in enumerate(ys) if y is not None]
        ax.fill_between([xs[i] for i in ok], [lo[i] for i in ok], [hi[i] for i in ok], color='#2a6fdb', alpha=.15, lw=0)
        ax.plot([xs[i] for i in ok], [ys[i] for i in ok], '-o', color='#2a6fdb', lw=2, ms=5, label='Oracle S_layer (95% CI)')
        ax.plot(xs, [p['placebo'][str(L)]['S'] for L in xs], '--', color='#8a8a8a', lw=1.5, label='placebo S_layer')
        ax.plot(xs, [p['floor'][str(L)] + BAR for L in xs], ':', color='#c0392b', lw=1.2, label='floor + 0.20')
        for b in (36, 40):
            c = e72.get(f'{row}:{b}')
            if c:ax.errorbar([b], [c['estimate']], yerr=[[c['estimate']-c['CI95'][0]], [c['CI95'][1]-c['estimate']]], fmt='D', color='#e67e22', ms=5, capsize=2, label='E72 cell (off-distribution)')
        ax.axhline(0, color='#cccccc', lw=.8);ax.set_title(f"{row}\n[{p['class']}]", fontsize=9);ax.set_xticks(xs)
    for ax in axes[1]:ax.set_xlabel('Oracle layer')
    for ax in axes[:, 0]:ax.set_ylabel('S (signed §172)')
    h, l = axes.flat[0].get_legend_handles_labels();seen = dict(zip(l, h))
    for ax in axes.flat:
        for hh, ll in zip(*ax.get_legend_handles_labels()):seen.setdefault(ll, hh)
    fig.legend(seen.values(), seen.keys(), loc='lower center', ncol=4, fontsize=9, bbox_to_anchor=(0.5, -0.06), frameon=False)
    fig.suptitle('E87 depth profile: Oracle S by layer, 8 MISSED rows + 2 controls (descriptive, §200 cl. 3)', fontsize=11)
    fig.savefig(path, dpi=160, bbox_inches='tight');plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec', type=Path, required=True);p.add_argument('--out', type=Path, required=True);a = p.parse_args()
    spec = read(a.spec)
    for path, digest in spec['pins'].items():require(sha(path) == digest, 'input pin: '+path)
    require(not a.out.exists(), 'once only');a.out.mkdir(parents=True)
    J, Jn = read(spec['judgments']), read(spec['private_join']);cells, _ = grid(J, Jn)
    prof = profile(cells, first_by_layer(J, Jn), e76_floors(read(spec['e76_floor_table'])))
    e72 = read(spec['e72_results'])['oracle']['rates']
    (a.out/'DEPTH_PROFILE.json').write_text(json.dumps(dict(experiment='E87', kind='DESCRIPTIVE depth profile (§200 cl. 3, 4c3e9dca)', rows=prof), indent=2, sort_keys=True)+'\n')
    figure(prof, e72, a.out/'E87_DEPTH_PROFILE.png')
    (a.out/'DEPTH_SEAL.json').write_text(json.dumps(dict(files={f.name: sha(f) for f in a.out.iterdir()}), indent=2, sort_keys=True)+'\n')
    print({r: v['class'] for r, v in prof.items()})


if __name__ == '__main__':main()
