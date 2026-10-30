"""BRIEF_RP §52 PTS: is reader success "poised to say" rather than "linearly present"?

Inputs (one JSONL row per item): ``exp``, ``item_id``, ``cluster`` (the experiment's item / prompt unit), ``base`` [repo, sha], ``adapter``
[repo, sha] or null, ``messages`` (the frozen prompt as chat messages, rendered with the generation prompt) or ``text`` (a raw string),
``target``. Reader scores (one CSV per experiment): ``exp, reader, item_id, success`` (+ optional ``probe_margin`` per item in the inputs).

    python -m projects.r_panel.pts build50 --answers <taboo_answers.csv> --diff <diff_scores.json> --out <dir>    # Mac, §50 (EXPLORATORY)
    python -m projects.r_panel.pts sample --inputs <inputs.jsonl> --out <rows.jsonl> [--limit N]                 # pod
    python -m projects.r_panel.pts analyze --rows <rows.jsonl> --scores <scores.csv> [...] --out <dir>            # Mac
P_soon: 8 samples at T = 1 (no top-p / top-k), 24 new tokens, seed 0 per item; the fraction whose continuation contains the target
(case-insensitive substring). LP_next: log P(first token of the target | frozen prompt), the log-sum over the two first-token spellings
(with and without a leading space), since the experiments do not fix which one the model would use.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

N_SAMPLES, MAX_NEW, SEED = 8, 24, 0
STATUS = {"§50": "EXPLORATORY", "§42": "EXPLORATORY", "§47": "PRE-REGISTERED", "§35": "PRE-REGISTERED", "§43": "PRE-REGISTERED"}


def build50(answers: Path, diff: Path, out: Path) -> None:
    import numpy as np
    import pandas as pd

    from projects.r_panel import taboo_ao as T

    a = pd.read_csv(answers)
    prompts = sorted(a.prompt.unique(), key=list(a.prompt.unique()).index)
    pid = {p: i for i, p in enumerate(prompts)}
    rows = [{"exp": "§50", "item_id": f"{w}|{pid[p]}", "cluster": f"prompt{pid[p]}", "base": list(T.BASE),
             "adapter": [f"bcywinski/gemma-2-9b-it-taboo-{w}", T.TABOO_SHA[w]], "messages": [{"role": "user", "content": p}], "target": w}
            for w in T.WORDS for p in prompts]
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "inputs_s50.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    sc = []
    qname = {T.PREFIX + q: f"ao_q{i + 1}" for i, q in enumerate(T.QUESTIONS)}
    for r in a.itertuples():
        sc.append({"exp": "§50", "reader": qname[r.question], "item_id": f"{r.word}|{pid[r.prompt]}", "success": float(r.correct)})
    d = json.loads(diff.read_text())
    for r in d["rows"]:
        s = np.array([r["scores"][w] for w in T.WORDS])
        rank = int((s > r["scores"][r["word"]]).sum())             # 0 = top-1
        sc.append({"exp": "§50", "reader": "diff_top1", "item_id": f"{r['word']}|{pid[r['prompt']]}", "success": float(rank == 0)})
        sc.append({"exp": "§50", "reader": "diff_rank", "item_id": f"{r['word']}|{pid[r['prompt']]}", "success": float(-rank)})
    pd.DataFrame(sc).to_csv(out / "scores_s50.csv", index=False)
    print(f"§50: {len(rows)} items, {len(sc)} reader scores", flush=True)


def sample(inputs: Path, out: Path, limit: int | None = None, batch: int = 8) -> int:
    import time

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    rows = [json.loads(l) for l in open(inputs) if l.strip()]
    if limit:   # smoke: the first `limit` items of each (base, adapter) group, two groups at most
        seen, keep = {}, []
        for r in rows:
            k = (tuple(r["base"]), tuple(r["adapter"] or ()))
            if len(seen) >= 2 and k not in seen:
                continue
            seen.setdefault(k, 0)
            if seen[k] < limit:
                keep.append(r)
                seen[k] += 1
        rows = keep
    done = {json.loads(l)["item_id"] + "|" + json.loads(l)["exp"] for l in open(out)} if out.exists() else set()
    torch.set_grad_enabled(False)
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((tuple(r["base"]), tuple(r["adapter"] or ())), []).append(r)
    model = tok = cur_base = None
    t0 = time.time()
    with open(out, "a") as fo:
        for (base, adapter), items in groups.items():
            if cur_base != base:
                tok = AutoTokenizer.from_pretrained(base[0], revision=base[1])
                model = AutoModelForCausalLM.from_pretrained(base[0], revision=base[1], torch_dtype=torch.bfloat16, device_map="cuda",
                                                             attn_implementation="eager")
                model.eval()
                cur_base = base
            if adapter:
                model.load_adapter(adapter[0], revision=adapter[1], adapter_name="tgt")
                model.set_adapter("tgt")
            for r in items:
                if r["item_id"] + "|" + r["exp"] in done:
                    continue
                text = (tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True) if r.get("messages") else r["text"])
                ids = tok(text, return_tensors="pt", add_special_tokens=False).input_ids.to(model.device)
                logp = torch.log_softmax(model(ids).logits[0, -1].float(), -1)
                firsts = {tok.encode(v, add_special_tokens=False)[0] for v in (r["target"], " " + r["target"]) if tok.encode(v, add_special_tokens=False)}
                lp_next = float(torch.logsumexp(logp[list(firsts)], 0))
                torch.manual_seed(SEED)
                outs = model.generate(ids.repeat(N_SAMPLES, 1), do_sample=True, temperature=1.0, top_p=1.0, top_k=0, max_new_tokens=MAX_NEW,
                                      pad_token_id=tok.pad_token_id or tok.eos_token_id)
                conts = tok.batch_decode(outs[:, ids.shape[1]:], skip_special_tokens=True)
                p_soon = sum(r["target"].lower() in c.lower() for c in conts) / N_SAMPLES
                fo.write(json.dumps({"exp": r["exp"], "item_id": r["item_id"], "cluster": r["cluster"], "target": r["target"],
                                     "p_soon": p_soon, "lp_next": lp_next, "first_tokens": sorted(firsts), "continuations": conts}) + "\n")
                fo.flush()
            if adapter:
                model.delete_adapter("tgt")
    print("PTS_TIMING " + json.dumps({"items": len(rows), "groups": len(groups), "wall_s": time.time() - t0}), flush=True)
    return 0


def spearman_partial(df, x: str, y: str, z: str | None):
    import numpy as np
    from scipy.stats import rankdata

    rx, ry = rankdata(df[x]), rankdata(df[y])
    rho = float(np.corrcoef(rx, ry)[0, 1])
    if z is None:
        return rho, None
    rz = rankdata(df[z])
    ex = rx - np.polyval(np.polyfit(rz, rx, 1), rz)
    ey = ry - np.polyval(np.polyfit(rz, ry, 1), rz)
    return rho, float(np.corrcoef(ex, ey)[0, 1])


def analyze(rows_path: Path, score_paths: list[Path], out: Path, n_boot: int = 2000):
    import numpy as np
    import pandas as pd

    rows = pd.DataFrame([json.loads(l) for l in open(rows_path) if l.strip()]).drop(columns=["continuations"], errors="ignore")
    sc = pd.concat([pd.read_csv(p) for p in score_paths], ignore_index=True)
    res = []
    for (exp, reader), g in sc.groupby(["exp", "reader"]):
        m = g.merge(rows[rows.exp == exp], on=["exp", "item_id"])
        has_probe = "probe_margin" in m and m["probe_margin"].notna().all() and len(m)
        for poised in ("p_soon", "lp_next"):
            cell = {"exp": exp, "status": STATUS.get(exp, "EXPLORATORY"), "reader": reader, "poised": poised, "n": len(m)}
            if len(m) < 30:
                res.append({**cell, "verdict": "MISSING", "reason": f"{len(m)} items with both quantities (< 30)"})
                continue
            if m[poised].nunique() < 2 or m["success"].nunique() < 2:
                which = "reader success" if m["success"].nunique() < 2 else "the poised score"
                res.append({**cell, "verdict": "NO VARIANCE (uninformative)", "reason": f"no variation in {which}"})
                continue
            rho, prho = spearman_partial(m, "success", poised, "probe_margin" if has_probe else None)
            cl = m.cluster.unique()
            idx = {c: np.where(m.cluster.to_numpy() == c)[0] for c in cl}
            rng = np.random.default_rng(0)
            br, bp = [], []
            for _ in range(n_boot):
                take = np.concatenate([idx[c] for c in rng.choice(cl, len(cl))])
                b = m.iloc[take]
                if b["success"].nunique() < 2 or b[poised].nunique() < 2:
                    continue
                r1, r2 = spearman_partial(b, "success", poised, "probe_margin" if has_probe else None)
                br.append(r1)
                if r2 is not None:
                    bp.append(r2)
            ci = [float(np.nanquantile(br, .025)), float(np.nanquantile(br, .975))]
            pci = [float(np.nanquantile(bp, .025)), float(np.nanquantile(bp, .975))] if bp else [None, None]
            rho_ok = rho > 0.3 and (ci[0] > 0 or ci[1] < 0)
            if not has_probe:
                v = "PARTIAL-ONLY (ρ clause " + ("met" if rho_ok else "not met") + "; no probe margin)"
            elif rho_ok and prho > 0.2:
                v = "SUPPORTS"
            elif pci[0] is not None and pci[0] > -0.1 and pci[1] < 0.1:
                v = "AGAINST"
            else:
                v = "INCONCLUSIVE"
            res.append({**cell, "rho": rho, "rho_ci95": ci, "partial_rho": prho, "partial_ci95": pci, "clusters": len(cl), "verdict": v})
    df = pd.DataFrame(res)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "pts.csv", index=False)
    return df


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build50", "sample", "analyze"])
    ap.add_argument("--answers", type=Path)
    ap.add_argument("--diff", type=Path)
    ap.add_argument("--inputs", type=Path)
    ap.add_argument("--rows", type=Path)
    ap.add_argument("--scores", type=Path, nargs="*")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)
    if a.cmd == "build50":
        build50(a.answers, a.diff, a.out)
    elif a.cmd == "sample":
        return sample(a.inputs, a.out, a.limit)
    else:
        print(analyze(a.rows, a.scores, a.out).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
