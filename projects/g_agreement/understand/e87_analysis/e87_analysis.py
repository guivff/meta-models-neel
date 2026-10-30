"""E87 once-only analysis: R-L1 (BRIEF_UNDERSTAND §200 E87, clarifications 1 and 2; 47cf57c2). Integrator-authored per Guiv
2026-10-28; committed before the grouped E87 judgment grid is sealed or opened.

Frozen choices:
- One grouped judgment per (item, reader, arm, layer) (funded_queue E87 bank). Signed §172 score per group: +1 if exactly
  one value is stated and it is the item's target, -1 if exactly one value is stated and it is the other value, 0
  otherwise (both values, property only, exhibits, silent). UNPARSEABLE is missing, never 0.
- S_layer(row, arm) = mean signed score over the row's items at that Oracle layer (layers {20,28,36,44,52,56,60}).
  S_max(row, arm) = max over layers. D(row) = S_max(real) - S_max(placebo). Item bootstrap (2000 draws,
  seed 20261029) resamples items jointly over layers and arms; D's CI is reported.
- Rows: 8 MISSED rows; controls topic_twin and loop_direction (REPORTED).
- R-L1 MET iff D <= 0.10 on >= 6 of 8 MISSED rows AND both controls have D >= 0.30.
  Control gate first: if either control fails (D < 0.30), R-L1 and its falsifier are NOT EVALUABLE. Only with both
  controls passing: FALSIFIED ("single-site blind spot") iff D >= 0.20 on >= 4 of 8 MISSED rows; otherwise MET as
  above, else NOT MET. (Order fixed pre-output per R-Q 257a4bec5; §200 E87 operational note.)
- Clarification 2: holder_after_handovers stays in the registered 8-row verdict; a 7-row sensitivity line (scaled
  thresholds: >= 5 of 7 for MET, >= 4 of 7 for the falsifier) is reported beside it, never as the verdict.
- Reported: S by layer, first-mention position (median first_position among states_value groups), the NLA analogue
  (block 42, real only, no placebo arm exists), UNPARSEABLE counts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ORACLE_LAYERS = (20, 28, 36, 44, 52, 56, 60)
MISSED = ('container_after_move', 'holder_after_handovers', 'branch_taken', 'var_type_at_use', 'user_expertise',
          'unit_system', 'nesting_depth', 'indent_level')
CONTROLS = ('topic_twin', 'loop_direction')
SENSITIVITY_DROP = 'holder_after_handovers'
DRAWS, SEED = 2000, 20261029


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def require(ok, msg):
    if not ok:raise ValueError(msg)


def signed(code, target):
    if code['category'] == 'UNPARSEABLE':return None
    vals = code.get('values') or []
    if code['category'] != 'states_value' or len(vals) != 1:return 0
    return 1 if vals[0] == target else -1


def grid(judgments, join):
    """{(row, reader, arm, layer): {item: score or None}} plus first-mention positions."""
    J = {x['id']: x for x in join};out = {};first = {}
    require({j['id'] for j in judgments} == set(J), 'complete grouped grid and join')
    for code in judgments:
        j = J[code['id']];key = (j['row'], j['reader'], j['arm'], j['layer'])
        cell = out.setdefault(key, {});require(j['public_item_id'] not in cell, 'one group per item per cell')
        cell[j['public_item_id']] = signed(code, j['target'])
        if code['category'] == 'states_value' and code.get('first_position') is not None:
            first.setdefault((j['row'], j['reader']), []).append(code['first_position'])
    return out, first


def row_stat(cells, row):
    """S_layer and S_max per arm, D and its item-bootstrap CI."""
    items = sorted(set().union(*[set(cells.get((row, 'oracle', a, L), {})) for a in ('real', 'placebo') for L in ORACLE_LAYERS]))
    require(items, 'row has items: '+row)
    M = {a: np.array([[np.nan if cells.get((row, 'oracle', a, L), {}).get(i) is None else cells[(row, 'oracle', a, L)][i]
                       for L in ORACLE_LAYERS] for i in items], dtype=float) for a in ('real', 'placebo')}

    def smax(m, ix=None):
        z = m if ix is None else m[ix];cnt = np.isfinite(z).sum(axis=-2)
        mean = np.divide(np.nansum(z, axis=-2), cnt, out=np.full(cnt.shape, np.nan), where=cnt > 0)
        return np.nanmax(mean, axis=-1) if np.isfinite(mean).any() else np.nan, mean

    real, s_real = smax(M['real']);plac, s_plac = smax(M['placebo'])
    rng = np.random.default_rng(SEED);ix = rng.integers(0, len(items), (DRAWS, len(items)))
    dr = []
    for b in ix:
        r, _ = smax(M['real'], b);p, _ = smax(M['placebo'], b);dr.append(r-p)
    dr = np.array(dr, dtype=float);ok = np.isfinite(dr)
    ci = [float(np.quantile(dr[ok], .025)), float(np.quantile(dr[ok], .975))] if ok.any() else None
    return dict(n_items=len(items), S_layer_real=dict(zip(map(str, ORACLE_LAYERS), map(float, s_real))),
                S_layer_placebo=dict(zip(map(str, ORACLE_LAYERS), map(float, s_plac))), S_max_real=float(real),
                S_max_placebo=float(plac), D=float(real-plac), D_ci95=ci,
                unparseable=dict(real=int(np.isnan(M['real']).sum()), placebo=int(np.isnan(M['placebo']).sum())))


def verdict(per_row, missed):
    D = {r: per_row[r]['D'] for r in missed}
    n = len(missed);need_met = 6 if n == 8 else 5;need_fals = 4
    low = sum(d <= 0.10 for d in D.values());high = sum(d >= 0.20 for d in D.values())
    controls_ok = all(per_row[c]['D'] >= 0.30 for c in CONTROLS)
    # Control gate first (registered: "If either control fails, R-L1 is NOT EVALUABLE"); the falsifier is only read
    # once both controls pass (§200 E87 operational note, R-Q 257a4bec5).
    if not controls_ok:status = 'NOT EVALUABLE (a positive control failed)'
    elif high >= need_fals:status = 'FALSIFIED (single-site blind spot)'
    elif low >= need_met:status = 'MET'
    else:status = 'NOT MET'
    return dict(status=status, rows=n, rows_D_le_0_10=low, rows_D_ge_0_20=high, need_met=need_met, need_falsifier=need_fals,
                controls={c: per_row[c]['D'] for c in CONTROLS}, controls_ok=controls_ok)


def analyze(spec):
    for path, digest in spec['pins'].items():require(sha(path) == digest, 'input pin: '+path)
    cells, first = grid(read(spec['judgments']), read(spec['private_join']))
    per_row = {r: row_stat(cells, r) for r in MISSED+CONTROLS}
    nla = {}
    for r in MISSED+CONTROLS:
        c = cells.get((r, 'nla', 'real', 42), {});v = [x for x in c.values() if x is not None]
        nla[r] = dict(n=len(c), unparseable=sum(x is None for x in c.values()), S=(float(np.mean(v)) if v else None))
    fm = {f'{r}:{rd}': dict(n=len(v), median=float(np.median(v))) for (r, rd), v in first.items()}
    return dict(experiment='E87', registration='§200 E87 + clarifications 1/2 (47cf57c2)', per_row=per_row,
                R_L1=verdict(per_row, MISSED), sensitivity_7_rows_excluding_holder=verdict(per_row, tuple(r for r in MISSED if r != SENSITIVITY_DROP)),
                nla_descriptive=nla, first_mention_position=fm)


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec', type=Path, required=True);a = p.parse_args()
    spec = read(a.spec);guard = Path(spec['guard']);out = Path(spec['out'])
    require(not guard.exists() and not out.exists(), 'once only: guard or output exists')
    result = analyze(spec)
    guard.parent.mkdir(parents=True, exist_ok=True);guard.write_text(json.dumps(dict(spec_sha256=sha(a.spec)))+'\n')
    out.mkdir(parents=True);(out/'RESULTS.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    (out/'ANALYSIS_SEAL.json').write_text(json.dumps(dict(experiment='E87', status='COMPLETE_ONCE', spec_sha256=sha(a.spec),
        files={f.name: sha(f) for f in out.iterdir()}), indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(R_L1=result['R_L1'], sensitivity=result['sensitivity_7_rows_excluding_holder']['status']), sort_keys=True))


if __name__ == '__main__':main()
