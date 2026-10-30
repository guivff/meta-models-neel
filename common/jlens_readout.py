"""J-lens readouts: top-k tokens, clustered view, and a blind-judge prompt.

Depends on the Anthropic reference implementation (`pip install -e third_party/jacobian-lens`, package `jlens`).
The exact API below follows the repo README as of 2026-10-02; if a call fails, open
third_party/jacobian-lens/README.md and adjust — the lens file is a dict with keys J (layer -> tensor),
n_prompts, source_layers, d_model, so a manual transport `J[layer] @ h` always works.

    from common.jlens_readout import JLens
    jl = JLens.from_neuronpedia(model, tok, "olmo-3-7b")     # or JLens.fit(model, tok, prompts)
    top = jl.topk(h, layer=16, k=50)                          # [(token, prob)]
    clusters = jl.clustered(h, layer=16, n_clusters=8, per=6) # [[(token, prob), ...], ...]
    print(jl.judge_prompt(top, clusters))                      # paste to an LLM judge, or use common.judge

Clustered view = k-means on the unembedding rows of the top-M tokens (M=200 by default), so clusters are
groups of tokens with similar output embeddings, each shown with its highest-probability members.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import torch

try:
    import jlens  # type: ignore
except Exception:  # pragma: no cover
    jlens = None


class JLens:
    def __init__(self, model, tok, lens):
        self.model, self.tok, self.lens = model, tok, lens
        self.W_U = model.get_output_embeddings().weight.detach()      # (V, d)
        self.final_norm = _find_final_norm(model)

    @classmethod
    def from_neuronpedia(cls, model, tok, model_slug: str):
        assert jlens is not None, "pip install -e third_party/jacobian-lens"
        lens = jlens.JacobianLens.from_pretrained("neuronpedia/jacobian-lens", filename=f"{model_slug}/lens.pt")
        return cls(model, tok, lens)

    @classmethod
    def from_file(cls, model, tok, path: str):
        assert jlens is not None
        lens = jlens.JacobianLens.load(path)
        return cls(model, tok, lens)

    @classmethod
    def fit(cls, model, tok, prompts: Sequence[str], save_path: Optional[str] = None):
        """Fit a J-lens on ~1k web-text prompts (≈ minutes on a 7B). Use per OLMo stage if the released lens's
        source checkpoint is unclear."""
        assert jlens is not None
        wrapped = jlens.from_hf(model, tok)
        lens = jlens.fit(wrapped, prompts=list(prompts), checkpoint_path=save_path)
        if save_path:
            lens.save(save_path)
        return cls(model, tok, lens)

    # --- core ---
    @torch.no_grad()
    def logits(self, h: torch.Tensor, layer: int) -> torch.Tensor:
        """h: (d,) residual at `layer` → (V,) logits via J_ℓ, final norm, W_U."""
        h = h.to(self.W_U.device, self.W_U.dtype)
        try:
            t = self.lens.transport(h[None, :], layer)[0]
        except Exception:
            J = self.lens.J[layer].to(h.device, h.dtype)
            t = J @ h
        t = self.final_norm(t[None, None, :])[0, 0] if self.final_norm is not None else t
        return (self.W_U @ t).float()

    def topk(self, h: torch.Tensor, layer: int, k: int = 50) -> List[Tuple[str, float]]:
        p = torch.softmax(self.logits(h, layer), -1)
        v, i = p.topk(k)
        return [(self.tok.decode([int(ix)]), float(pv)) for pv, ix in zip(v, i)]

    def clustered(self, h: torch.Tensor, layer: int, n_clusters: int = 8, per: int = 6, M: int = 200,
                  seed: int = 0) -> List[List[Tuple[str, float]]]:
        from sklearn.cluster import KMeans
        p = torch.softmax(self.logits(h, layer), -1)
        v, i = p.topk(M)
        E = self.W_U[i].float().cpu().numpy()
        E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-8)
        lab = KMeans(n_clusters=n_clusters, n_init=4, random_state=seed).fit_predict(E)
        out = []
        for c in range(n_clusters):
            members = [(self.tok.decode([int(i[j])]), float(v[j])) for j in range(M) if lab[j] == c]
            members.sort(key=lambda x: -x[1])
            out.append(members[:per])
        out.sort(key=lambda cl: -sum(pv for _, pv in cl))
        return out

    @staticmethod
    def judge_prompt(top: Optional[List[Tuple[str, float]]], clusters: Optional[List[List[Tuple[str, float]]]]) -> str:
        """Blind-judge prompt: the judge sees ONE of the two views and must name the concept + confidence 0–1,
        or answer NONE if the tokens look unrelated/random. Used for P3's top-k vs clustered comparison."""
        body = ""
        if top is not None:
            body += "Top tokens (token: prob):\n" + ", ".join(f"{t!r}:{p:.3f}" for t, p in top) + "\n"
        if clusters is not None:
            body += "Token clusters:\n" + "\n".join(f"- " + ", ".join(f"{t!r}" for t, _ in cl) for cl in clusters) + "\n"
        return ("You are shown the readout of a direction in a language model's residual stream. "
                "Name the single concept this direction most likely encodes (≤ 6 words), then a confidence in [0,1]. "
                "If the tokens look like noise or unrelated, answer exactly: NONE 0.0\n\n" + body +
                "\nAnswer format: <concept> | <confidence>")


def _find_final_norm(model):
    for attr in ("model.norm", "transformer.ln_f", "gpt_neox.final_layer_norm"):
        obj = model
        ok = True
        for a in attr.split("."):
            if hasattr(obj, a):
                obj = getattr(obj, a)
            else:
                ok = False
                break
        if ok:
            return obj
    return None
