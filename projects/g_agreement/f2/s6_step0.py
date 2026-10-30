"""S6 step zero: do the third-party Qwen3-4B readers read the G1 keys? (BRIEF_S.md "S6 step zero"). GPU, pod.

    python -m projects.g_agreement.f2.s6_step0 [--smoke]

Target Qwen/Qwen3-4B; G1 test items (32 states); last-token states at blocks 22/24/26. Readers: J-lens (neuronpedia
qwen3-4b), Oracle LoRA (neuronpedia qwen3-4b/oracle; marker U+320E forced), NLA substitute anicka/nla-qwen3-4b-universal-av
(LoRA on the target; input embedding of the marker := 150 * unit(h); depth tag 63% for block 24). Native LO (G1 conventions)
and one free-text sample per state and text reader (G1 sampling, 256 tokens). Outputs cache/g_agreement/s6/.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, now_iso
from projects.g_agreement.core.generate import generate_ids

OUT = C.CACHE_DIR / "s6"
TARGET = "Qwen/Qwen3-4B"
LAYERS = (22, 24, 26)
JL_REPO, JL_FILE = "neuronpedia/jacobian-lens", "qwen3-4b/jlens/Salesforce-wikitext/Qwen3-4B_jacobian_lens.pt"
OL_SUB = "qwen3-4b/oracle"
MARKER_CHAR, MARKER_ID, MARKER_NB = "㈎", 149705, (29, 522)
NLA_REPO = "anicka/nla-qwen3-4b-universal-av"
NLA_NORM = 150.0
NLA_DEPTHS = (4, 10, 17, 25, 32, 40, 47, 55, 63, 71, 80, 90, 96)


def depth_pct(layer: int, n_layers: int = 36) -> int:
    x = layer * 100 / n_layers
    return min(NLA_DEPTHS, key=lambda d: abs(d - x))


class OLens4B(R.OLensReader):
    """Our OLens reader with the 4B lens's fixed marker (U+320E) instead of the scanned one."""

    def carrier(self, layer: int):
        if layer not in self._carriers:
            ids, slot, char, cid = R.olens_carrier(self.target.tokenizer, layer, self.prompt, scan=(0x320E, 0x320F))
            if cid != MARKER_ID or (ids[slot - 1], ids[slot + 1]) != MARKER_NB:
                raise RuntimeError(f"4B Oracle marker mismatch: id {cid}, neighbours {(ids[slot - 1], ids[slot + 1])}")
            self._carriers[layer] = (ids, slot, char, cid)
        return self._carriers[layer]


class NLA4B:
    """anicka universal AV: LoRA on the target, marker input embedding := NLA_NORM * unit(h)."""

    name = "nla"

    def __init__(self, target: M.Target, adapter_dir: Path, meta: dict[str, Any], layer: int):
        from peft import PeftModel

        self.target = target
        if isinstance(target.model, PeftModel):
            target.model = target.model.unload()
        target.model = PeftModel.from_pretrained(target.model, str(adapter_dir))
        target.model.eval()
        text = meta["prompt_templates"]["av"].format(depth_pct=depth_pct(layer), injection_char=meta["tokens"]["injection_char"])
        self.ids = M.chat_ids(target.tokenizer, [{"role": "user", "content": text}])
        hits = [i for i, t in enumerate(self.ids) if t == int(meta["tokens"]["injection_token_id"])]
        if len(hits) != 1:
            raise RuntimeError(f"NLA marker found {len(hits)} times")
        self.slot, self.prompt_text = hits[0], text
        self.liveness = R.assert_adapter_live(target.model, Path(adapter_dir), self.ids)

    def embeds(self, ids_t: Any, vecs: list[Any]) -> Any:
        import torch

        emb = self.target.model.get_input_embeddings()
        with torch.no_grad():
            e = emb(ids_t).clone()
            for r, v in enumerate(vecs):
                v = v.to(e.device).float()
                e[r, self.slot, :] = (NLA_NORM * v / v.norm().clamp_min(1e-9)).to(e.dtype)
        return e

    def read(self, h: Any, seed: int) -> Any:
        import torch

        dev = next(self.target.model.parameters()).device
        e = self.embeds(torch.tensor([self.ids], device=dev), [h])
        return generate_ids(self.target.model, self.target.tokenizer, self.ids, max_new_tokens=C.VERBALIZER_MAX_NEW_TOKENS,
                            sampling=C.SAMPLING, seed=seed, inputs_embeds=e, adapter_enabled=True)

    def lo(self, H: Any, cands: list[tuple[str, str]], family: str) -> list[dict[str, Any]]:
        tok = self.target.tokenizer
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        dev = next(self.target.model.parameters()).device
        temps = LO.templates_for(family)
        out = []
        for i, (a, b) in enumerate(cands):
            per = []
            for tmpl in temps:
                rows = [list(self.ids) + LO.encode(tok, tmpl.format(X=c)) for c in (a, b)]
                lps = LO._summed_logprobs(self.target.model, rows, len(self.ids), pad, dev,
                                          embed_fn=lambda ids_t, v=H[i]: self.embeds(ids_t, [v, v]))
                per.append(lps[0] - lps[1])
            out.append({"lo": sum(per) / len(per), "per_template": per})
        return out


def main() -> int:
    import torch
    from huggingface_hub import hf_hub_download, snapshot_download

    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--items", default=None, help="items file (default: G1 test items)")
    ap.add_argument("--out", default=None, help="output dir under cache/g_agreement (default s6)")
    a = ap.parse_args()
    global OUT
    if a.out:
        OUT = C.CACHE_DIR / a.out
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = lambda s: print(f"[s6] {s} ({(time.time() - t0) / 60:.1f} min)", flush=True)  # noqa: E731
    C.N_LAYERS = 36  # load_target checks the block count against the 27B constant
    target = M.load_target(TARGET, revision=None)
    tok = target.tokenizer
    items = C.load_items("test", 0, path=Path(a.items) if a.items else None)[: 4 if a.smoke else None]
    log(f"loaded {TARGET} ({target.n_layers} blocks); {len(items)} items")
    H: dict[str, dict[int, Any]] = {}
    for it in items:
        ids = M.render_item(tok, it["prompt_text"], it.get("system"))
        cap = M.capture(target.model, ids, list(LAYERS), [len(ids) - 1])
        H[it["item_id"]] = {L: cap[L][0].float() for L in LAYERS}
        g = generate_ids(target.model, tok, ids, max_new_tokens=C.TARGET_MAX_NEW_TOKENS, sampling=None, seed=None)
        append_jsonl(OUT / "targets.jsonl", {"item_id": it["item_id"], "answer_text": g.raw_output, "n_tokens": len(ids)})
    torch.save(H, OUT / "states.pt")
    cands = {it["item_id"]: (str(it["primary"]["answer"]), [c for c in it["primary"]["candidates"] if c != it["primary"]["answer"]][0])
             for it in items}
    fam = {it["item_id"]: it["family"] for it in items}
    by_fam: dict[str, list[str]] = {}
    for it in items:
        by_fam.setdefault(it["family"], []).append(it["item_id"])
    gens, lop = OUT / "gens.jsonl", OUT / "lo.jsonl"
    # J-lens
    jl = R.JLensReader().bind(target, lens_path=hf_hub_download(JL_REPO, JL_FILE), layers_keep=list(LAYERS))
    for L in LAYERS:
        for f, iids in by_fam.items():
            res = LO.lo_jlens(jl, torch.stack([H[i][L] for i in iids]), [cands[i] for i in iids], layer=L)
            for i, r in zip(iids, res):
                append_jsonl(lop, {"reader": "jlens", "layer": L, "item_id": i, "family": f, "lo": r.get("lo"), "unscorable": r["unscorable"]})
        for i in H:
            rr = jl.read(H[i][L], L)
            append_jsonl(gens, {"reader": "jlens", "layer": L, "item_id": i, "method": "jlens", "native": rr.native})
    del jl
    torch.cuda.empty_cache()
    log("J-lens done")
    # Oracle
    od = Path(snapshot_download(JL_REPO, allow_patterns=[f"{OL_SUB}/*"])) / OL_SUB
    ol = OLens4B().bind(target, adapter_dir=od)
    for L in LAYERS:
        for f, iids in by_fam.items():
            res = LO.lo_olens(ol, torch.stack([H[i][L] for i in iids]), [cands[i] for i in iids], layer=L)
            for i, r in zip(iids, res):
                append_jsonl(lop, {"reader": "olens", "layer": L, "item_id": i, "family": f, "lo": r["lo"], "unscorable": False})
        for i in H:
            rr = ol.read(H[i][L], L, seed=C.stable_seed("s6", "olens", i, L))
            append_jsonl(gens, {"reader": "olens", "layer": L, "item_id": i, "method": "olens", "native": rr.native,
                                "finish_reason": rr.finish_reason, "marker": rr.input.get("marker_char")})
    log(f"Oracle done (liveness max |dlogit| {ol.liveness.get('max_abs_logit_delta') if ol.liveness else None})")
    # NLA substitute (block 24 only; the adapter is universal, the depth tag follows the layer)
    nd = Path(snapshot_download(NLA_REPO))
    import yaml

    meta = yaml.safe_load((nd / "nla_meta.yaml").read_text())
    for L in (24,):
        nla = NLA4B(target, nd, meta, L)
        for f, iids in by_fam.items():
            res = nla.lo(torch.stack([H[i][L] for i in iids]), [cands[i] for i in iids], f)
            for i, r in zip(iids, res):
                append_jsonl(lop, {"reader": "nla", "layer": L, "item_id": i, "family": f, "lo": r["lo"], "per_template": r["per_template"], "unscorable": False})
        for i in H:
            g = nla.read(H[i][L], seed=C.stable_seed("s6", "nla", i, L))
            append_jsonl(gens, {"reader": "nla", "layer": L, "item_id": i, "method": "nla",
                                "native": {"samples": [R.strip_explanation(g.raw_output)]}, "raw_output": g.raw_output,
                                "finish_reason": g.finish_reason, "depth_pct": depth_pct(L)})
    log("NLA done")
    (OUT / "done.json").write_text(json.dumps({"done_at": now_iso(), "wall_min": (time.time() - t0) / 60, "n_items": len(items),
                                               "nla_liveness": nla.liveness.get("max_abs_logit_delta"), "nla_prompt": nla.prompt_text}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
