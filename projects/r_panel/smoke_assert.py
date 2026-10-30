"""PODS.md rule 5(a): after the smoke, every pre-registered arm × condition of BRIEF_RP for this pair has ≥ 1 row, on every
smoke dataset; otherwise print ``SMOKE FAILED: missing <arm/condition>`` lines and exit 1 (the chain then launches no full run).

    python -m projects.r_panel.smoke_assert <pair> <smoke_cache_dir> <dataset> [<dataset> …]

Arms (BRIEF_RP §3.3–§3.6, §13): AO and AO-yn natural + shuffled at every read site (chat grid, raw primary); pool-eval rows at
the primary chat site; state-free rows per form × site; the text arm with the question (both forms); text + activation (both
forms, chat and raw states); the position sweep (AO rows at every sweep block × offset; LR probe cells, except Q8B which uses
Q8's); the training-native pool rows (both offsets); prompt-only; the logit lens; Q27's ``ao_base``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from projects.r_panel import pairs as PR


def rows(path: Path) -> list[dict]:
    out = []
    for f in sorted(path.parent.glob(path.name)):
        out += [json.loads(l) for l in open(f) if l.strip()]
    return out


def main(argv: list[str]) -> int:
    pair, root, datasets = argv[0], Path(argv[1]), argv[2:]
    p = PR.PAIRS[pair]
    L0 = p["primary"]
    expect: list[tuple[str, str, callable]] = []
    lo = rows(root / "reader_lo*.jsonl")
    lo = [r for r in lo if "_textact" not in r["reader"]]
    have = Counter((r["dataset"], r["reader"], r["layer"], r["render"], r["condition"], r["split"]) for r in lo)
    for ds in datasets:
        for form in ("ao", "ao_yn"):
            for render, layers in p["ao_read"].items():
                for L in layers:
                    for cond in ("natural", "shuf"):
                        expect.append((f"{ds} {form} L{L} {render} {cond} test", have[(ds, form, L, render, cond, "test")]))
            expect.append((f"{ds} {form} L{L0} chat pool_eval", have[(ds, form, L0, "chat", "natural", "pool")]))
            expect.append((f"{ds} {form}_noact L{L0} chat test", have[(ds, f"{form}_noact", L0, "chat", "natural", "test")]))
        if pair == "Q27":
            expect.append((f"{ds} ao_base L32 chat test", have[(ds, "ao_base", 32, "chat", "natural", "test")]))
    sf = Counter((r["dataset"], r["reader"], r["layer"], r["render"]) for r in rows(root / "state_free*.jsonl"))
    ta = Counter((r["dataset"], r["reader"], r["render"]) for r in rows(root / "reader_lo_textact*.jsonl"))
    pos = Counter((r["dataset"], r["layer"]) for r in rows(root / "reader_lo_pos*.jsonl"))
    pos_k = Counter((r["dataset"], r["layer"], r["offset"]) for r in rows(root / "reader_lo_pos*.jsonl"))
    pp = Counter((r["dataset"], r["layer"]) for r in rows(root / "pos_probe*.jsonl"))
    nat = Counter((r["dataset"], r["offset_name"]) for r in rows(root / "reader_lo_native*.jsonl"))
    po = Counter(r["dataset"] for r in rows(root / "prompt_only*.jsonl"))
    ll = Counter(r["dataset"] for r in rows(root / "logit_lens*.jsonl"))
    pos_ao = p.get("pos_ao", p["pos_layers"])
    for ds in datasets:
        for form in ("ao", "ao_yn"):
            for render, layers in p["ao_read"].items():
                for L in layers:
                    expect.append((f"{ds} state_free {form} L{L} {render}", sf[(ds, form, L, render)]))
            for render in ("chat", "raw"):
                expect.append((f"{ds} {form}_textact {render}", ta[(ds, f"{form}_textact", render)]))
        for L in pos_ao:
            expect.append((f"{ds} position sweep AO L{L}", pos[(ds, L)]))
            n_off = len({k for (d, l, k) in pos_k if d == ds and l == L})
            expect.append((f"{ds} position sweep AO L{L} ≥ 2 offsets", int(n_off >= 2)))
        for L in p.get("pos_probe", () if p.get("states_from") else p["pos_layers"]):
            expect.append((f"{ds} position probe L{L}", pp[(ds, L)]))
        for name in ("im_end", "nl"):
            expect.append((f"{ds} native pool rows {name}", nat[(ds, name)]))
        if not p.get("states_from"):
            expect.append((f"{ds} prompt_only", po[ds]))
            expect.append((f"{ds} logit_lens", ll[ds]))
    missing = [name for name, n in expect if not n]
    for name, n in expect:
        print(f"{'ok ' if n else 'MISSING'} {name}: {n}")
    for name in missing:
        print(f"SMOKE FAILED: missing {name}")
    print(f"SMOKE {'FAILED' if missing else 'PASSED'}: {len(expect) - len(missing)}/{len(expect)} arm × condition cells have rows")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
