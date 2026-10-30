"""§103 E14: does GLM-5.3's Oracle lens state or enact text-structure state? CPU only.

Frozen rules: see BRIEF_UNDERSTAND.md §103 (commit ae6ffef7). Input: parquet files of
ceselder/glm-5.3-olens-wild-rollouts (rows with left_ctx, token, next16, rl_*/sft_* readouts).
Usage: python -m projects.g_agreement.understand.e14.run --data DIR_OR_PARQUET... --out OUTDIR
"""
from __future__ import annotations
import argparse, glob, hashlib, json, math, os, re
import numpy as np

SEED = 20261024
N_BOOT = 2000
RL = ['rl_greedy', 'rl_s1', 'rl_s2', 'rl_s3', 'rl_s4']
SFT = ['sft_greedy', 'sft_s1', 'sft_s2', 'sft_s3', 'sft_s4']
STATES = ['paren', 'quote', 'code', 'table', 'list']
LIST_MARK = re.compile(r'^\s*([-*+]|\d+[.)])\s')

# ---- state labels from the text up to and including the read token ----
def label(prefix: str) -> dict:
    depth = 0
    for ch in prefix:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
    line = prefix.rsplit('\n', 1)[-1]
    return {
        'paren': depth > 0,
        'quote': line.count('"') % 2 == 1,
        'code': prefix.count('```') % 2 == 1,
        'table': line.lstrip().startswith('|'),
        'list': bool(LIST_MARK.match(line)),
    }

# ---- readout codes ----
STATE_RX = {
    'paren': re.compile(r'parenthe|bracket', re.I),
    'quote': re.compile(r'quot|string literal|inside (a|the) string', re.I),
    'code': re.compile(r'code block|code fence|inside (the )?code', re.I),
    'table': re.compile(r'\btable\b|\bcolumn|\bcell\b', re.I),
    'list': re.compile(r'\blist\b|bullet', re.I),
}

def enacts(state: str, text: str) -> bool:
    if state == 'paren':
        c, o = text.find(')'), text.find('(')
        return c >= 0 and (o < 0 or c < o)
    if state == 'quote':
        q, n = text.find('"'), text.find('\n')
        return q >= 0 and (n < 0 or q < n)
    if state == 'code':
        return '```' in text
    if state == 'table':
        return '|' in text
    if state == 'list':
        return any(LIST_MARK.match(l) for l in text.split('\n'))
    raise KeyError(state)

def states(state: str, text: str) -> bool:
    return bool(STATE_RX[state].search(text))

# ---- stats ----
def wilson(k: float, n: int) -> list:
    if n == 0:
        return [float('nan')] * 3
    p, z = k / n, 1.959963984540054
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [p, c - h, c + h]

def boot_diff(on: np.ndarray, off: np.ndarray, rng) -> list:
    if len(on) == 0 or len(off) == 0:
        return [float('nan')] * 3
    d = np.empty(N_BOOT)
    for b in range(N_BOOT):
        d[b] = on[rng.integers(0, len(on), len(on))].mean() - off[rng.integers(0, len(off), len(off))].mean()
    return [float(on.mean() - off.mean()), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]

# ---- io ----
def load(paths: list):
    import pyarrow.parquet as pq
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, '**', '*.parquet'), recursive=True)) if os.path.isdir(p) else [p]
    need = {'left_ctx', 'token', 'next16', *RL, *SFT}
    rows, used = [], []
    for f in files:
        t = pq.read_table(f)
        if not need <= set(t.column_names):
            continue
        used.append({'file': f, 'sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest(), 'rows': t.num_rows})
        rows += t.select(sorted(need | ({'pos', 'tid'} & set(t.column_names)))).to_pylist()
    if not rows:
        raise SystemExit('no parquet file with the required columns')
    return rows, used

def analyse(rows: list, rng=None) -> dict:
    rng = rng or np.random.default_rng(SEED)
    lab = [label((r['left_ctx'] or '') + (r['token'] or '')) for r in rows]
    out = {'n_positions': len(rows), 'state_counts': {s: int(sum(l[s] for l in lab)) for s in STATES}, 'results': {}}
    versions = {'rl': RL, 'sft': SFT, 'next16': ['next16']}
    for s in STATES:
        on_mask = np.array([l[s] for l in lab])
        for v, cols in versions.items():
            for code, fn in (('states', states), ('enacts', enacts)):
                per = np.array([np.mean([fn(s, r[c] or '') for c in cols]) for r in rows])
                k_on = float(per[on_mask].sum() * len(cols)); n_on = int(on_mask.sum()) * len(cols)
                k_off = float(per[~on_mask].sum() * len(cols)); n_off = int((~on_mask).sum()) * len(cols)
                out['results'][f'{s}/{v}/{code}'] = {
                    'rate_on': wilson(round(k_on), n_on), 'rate_off': wilson(round(k_off), n_off),
                    'diff_on_minus_off': boot_diff(per[on_mask], per[~on_mask], rng),
                    'n_on_positions': int(on_mask.sum()), 'n_off_positions': int((~on_mask).sum())}
    return out, lab

def examples(rows, lab, rng) -> dict:
    ex = {}
    for s in STATES:
        idx = [i for i, l in enumerate(lab) if l[s]]
        pick = rng.choice(idx, size=min(2, len(idx)), replace=False).tolist() if idx else []
        ex[s] = [{k: rows[i].get(k) for k in ['tid', 'pos', 'left_ctx', 'token', 'next16', *RL, *SFT]} for i in pick]
    return ex

def hand_check(rows, lab, rng) -> list:
    out = []
    for s in STATES:
        for code, fn in (('states', states), ('enacts', enacts)):
            hits = [(i, c) for i, r in enumerate(rows) for c in RL + SFT if fn(s, r[c] or '')]
            for j in (rng.choice(len(hits), size=min(50, len(hits)), replace=False) if hits else []):
                i, c = hits[j]
                out.append({'state': s, 'code': code, 'column': c, 'state_true': lab[i][s],
                            'left_ctx_tail': (rows[i]['left_ctx'] or '')[-160:], 'token': rows[i]['token'], 'readout': rows[i][c]})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=False)
    rows, used = load(a.data)
    rng = np.random.default_rng(SEED)
    lab = [label((r['left_ctx'] or '') + (r['token'] or '')) for r in rows]
    ex = examples(rows, lab, rng)  # selected before any rate is computed
    json.dump(ex, open(os.path.join(a.out, 'EXAMPLES.json'), 'w'), indent=1, ensure_ascii=False)
    res, _ = analyse(rows, np.random.default_rng(SEED + 1))
    res['inputs'] = used
    res['brief'] = 'BRIEF_UNDERSTAND.md §103 @ ae6ffef7'
    json.dump(res, open(os.path.join(a.out, 'RESULTS.json'), 'w'), indent=1)
    with open(os.path.join(a.out, 'HAND_CHECK.jsonl'), 'w') as f:
        for h in hand_check(rows, lab, np.random.default_rng(SEED + 2)):
            f.write(json.dumps(h, ensure_ascii=False) + '\n')
    print(json.dumps({k: v['diff_on_minus_off'] for k, v in res['results'].items()}, indent=1))

if __name__ == '__main__':
    main()
