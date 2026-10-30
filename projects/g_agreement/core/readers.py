"""The three readers, with the semantics of ``wsbench.produce.methods`` (workspace-bench, MIT;
``third_party/workspace-bench/src/wsbench/produce/methods.py``) — copied with attribution rather
than imported, because wsbench's package pulls in judge dependencies and its ``bind`` methods
download from fixed repos. Every formula below is the wsbench one; the differences are
(1) pinned revisions, (2) per-call seeds, (3) raw output + parsed samples + accounting in the
result, (4) load-time assertions that an adapter is live and a marker is well formed.

  jlens  cosine readout  (W_U · J_L · h) / ‖J_Lᵀ W_U[t]‖, top-10               (JLens.read)
  olens  carrier prompt ``concepts_raw`` with layer integer; the marker's INPUT EMBEDDING is
         replaced by 16000 · h/‖h‖; LoRA on the probed model, off during capture (OLens.read)
  nla    av_base + RL adapter; actor prompt from nla_meta.yaml; at the output of decoder
         block 1 the marker row becomes h₁ + ‖h₁‖ · h/‖h‖                     (NLA.read)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as C
from . import model as M
from .generate import GenResult, generate_ids


# ------------------------------------------------------------------ result
@dataclass
class ReadResult:
    method: str
    raw_output: str | None
    native: dict[str, Any]
    input: dict[str, Any]
    n_prompt_tokens: int
    n_new_tokens: int
    finish_reason: str | None
    wall_s: float
    peak_mem_gb: float | None
    seed: int | None
    sampling: dict[str, Any]
    adapter: str
    model_sha: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def row(self) -> dict[str, Any]:
        return {
            "input": self.input, "sampling": self.sampling, "raw_output": self.raw_output,
            "native": self.native, "n_prompt_tokens": self.n_prompt_tokens,
            "n_new_tokens": self.n_new_tokens, "finish_reason": self.finish_reason,
            "wall_s": self.wall_s, "peak_mem_gb": self.peak_mem_gb, "seed": self.seed,
            "adapter": self.adapter, "model_sha": self.model_sha, **({"extra": self.extra} if self.extra else {}),
        }


# ------------------------------------------------------------------ marker helpers
def marker_well_formed(prompt_ids: list[int], inj_id: int, left_id: int, right_id: int) -> bool:
    """EasyNLA ``nla.injection.marker_well_formed`` (used if importable, else this verbatim
    reimplementation): exactly one marker, not at either end, with its canonical neighbours."""
    try:
        C.add_third_party_to_path()
        from nla.injection import marker_well_formed as _ref  # type: ignore

        return bool(_ref(list(prompt_ids), inj_id, left_id, right_id))
    except Exception:
        n = len(prompt_ids)
        positions = [i for i, t in enumerate(prompt_ids) if t == inj_id]
        if len(positions) != 1:
            return False
        p = positions[0]
        if p == 0 or p == n - 1:
            return False
        return prompt_ids[p - 1] == left_id and prompt_ids[p + 1] == right_id


def olens_carrier(tokenizer: Any, layer: int, prompt: str = C.OLENS_PROMPT,
                  scan: tuple[int, int] = C.OLENS_MARKER_SCAN) -> tuple[list[int], int, str, int]:
    """wsbench ``OLens._carrier``: the first enclosed-ideograph char in U+3200–U+33FF that is a
    single token alone AND appears exactly once in the full chat render (thinking off).
    Returns (ids, slot, char, char_id)."""
    for code in range(*scan):
        char = chr(code)
        ids = tokenizer(char, add_special_tokens=False)["input_ids"]
        if len(ids) != 1:
            continue
        rendered = M.chat_ids(tokenizer, [{"role": "user", "content": prompt.format(layer=layer, char=char)}])
        slots = [i for i, t in enumerate(rendered) if t == ids[0]]
        if len(slots) == 1:
            return rendered, slots[0], char, int(ids[0])
    raise ValueError("no enclosed ideograph survives as a single token in the carrier prompt")


def nla_prompt(tokenizer: Any, meta: dict[str, Any]) -> tuple[list[int], int, str]:
    """wsbench ``NLA.bind``: the actor template from nla_meta.yaml (``av`` or ``actor``) with the
    injection char, one user turn, chat render with thinking off. Returns (ids, marker, text)."""
    tmpl = meta["prompt_templates"].get("av") or meta["prompt_templates"]["actor"]
    text = tmpl.format(injection_char=meta["tokens"]["injection_char"])
    ids = M.chat_ids(tokenizer, [{"role": "user", "content": text}])
    marker_id = int(meta["tokens"]["injection_token_id"])
    left = int(meta["tokens"]["injection_left_neighbor_id"])
    right = int(meta["tokens"]["injection_right_neighbor_id"])
    if not marker_well_formed(ids, marker_id, left, right):
        hits = [i for i, t in enumerate(ids) if t == marker_id]
        raise RuntimeError(
            f"NLA marker not well formed: id {marker_id} at {hits}, neighbours expected ({left},{right}); "
            f"got {[(ids[i-1], ids[i+1]) for i in hits if 0 < i < len(ids)-1]}")
    (marker,) = [i for i, t in enumerate(ids) if t == marker_id]
    return ids, marker, text


def strip_explanation(text: str) -> str:
    """wsbench ``NLA.read`` post-processing (EasyNLA's EXPLANATION_RE semantics)."""
    return text.split("</explanation>")[0].removeprefix("<explanation>").strip()


_BULLET = re.compile(r"^\s*[-•*]\s+(.*\S)\s*$")


def olens_bullets(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = _BULLET.match(line)
        if m:
            out.append(m.group(1).strip())
    return out


# ------------------------------------------------------------------ adapter liveness
def adapter_key_report(peft_model: Any, adapter_dir: Path, adapter_name: str = "default") -> dict[str, Any]:
    """Every LoRA tensor in ``adapter_model.safetensors`` must land on a parameter of the
    wrapped model (an adapter that silently matches nothing looks exactly like a working one).
    ``adapter_name`` is the PEFT name the adapter was mounted under (several may coexist)."""
    from safetensors import safe_open

    f = adapter_dir / "adapter_model.safetensors"
    with safe_open(str(f), framework="pt") as sf:
        keys = list(sf.keys())
    names = {n for n, _ in peft_model.named_parameters() if f".{adapter_name}." in n or ".lora_" not in n}
    norm_names = {re.sub(r"\.(%s)\." % re.escape(adapter_name), ".", n) for n in names}

    def variants(k: str) -> list[str]:
        base = k
        out = [base, base.replace("lora_A.weight", f"lora_A.{adapter_name}.weight").replace("lora_B.weight", f"lora_B.{adapter_name}.weight")]
        # transformers-5 checkpoint prefix (model.language_model.* <-> model.*)
        out += [v.replace(".model.language_model.", ".model.") for v in list(out)]
        out += [v.replace(".model.layers.", ".model.language_model.layers.") for v in list(out)]
        return out

    matched = sum(1 for k in keys if any(v in names or v in norm_names for v in variants(k)))
    n_lora_modules = sum(1 for n, m in peft_model.named_modules() if hasattr(m, "lora_A"))
    return {"n_keys": len(keys), "n_matched": matched, "n_lora_modules": n_lora_modules,
            "all_matched": matched == len(keys) and len(keys) > 0}


def adapter_effect(peft_model: Any, ids: list[int]) -> float:
    """Max |Δlogit| at the last position with the adapter on vs off (0.0 == inert adapter)."""
    import torch

    dev = next(peft_model.parameters()).device
    x = torch.tensor([ids], device=dev)
    with torch.no_grad():
        on = peft_model(x, use_cache=False).logits[0, -1].float()
        with peft_model.disable_adapter():
            off = peft_model(x, use_cache=False).logits[0, -1].float()
    return float((on - off).abs().max())


def assert_adapter_live(peft_model: Any, adapter_dir: Path, probe_ids: list[int], min_effect: float = 1e-3,
                        adapter_name: str = "default") -> dict[str, Any]:
    """Key report + on/off effect of the ACTIVE adapter (callers activate ``adapter_name`` first)."""
    rep = adapter_key_report(peft_model, adapter_dir, adapter_name=adapter_name)
    rep["adapter_name"] = adapter_name
    rep["max_abs_logit_delta"] = adapter_effect(peft_model, probe_ids)
    if not rep["all_matched"]:
        raise RuntimeError(f"adapter {adapter_dir}: only {rep['n_matched']}/{rep['n_keys']} tensors matched a parameter")
    if rep["max_abs_logit_delta"] < min_effect:
        raise RuntimeError(f"adapter {adapter_dir} is inert (max |Δlogit| {rep['max_abs_logit_delta']:.2e})")
    return rep


def hf_dir(repo: str, revision: str, patterns: list[str], repo_type: str | None = None) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo, revision=revision, allow_patterns=patterns, repo_type=repo_type))


# ================================================================== J-lens
class JLensReader:
    """wsbench ``JLens``: ``(h @ J_Lᵀ @ W_Uᵀ) / ‖W_U J_L‖_rows``, top-10, display tokens."""

    name = "jlens"
    adapter = "none"

    def __init__(self, k: int = C.JLENS_TOP_K):
        self.k = k
        self.J = None  # [n_src, d, d] fp32 on device, or a dict layer -> [d, d]
        self.w_u = None
        self.tokenizer = None
        self.device = None
        self.source_layers: list[int] = []
        self.n_prompts: int | None = None
        self.lens_path: str | None = None
        self._denom: dict[int, Any] = {}

    def bind(self, target: M.Target, lens_path: str | Path | None = None, layers_keep: list[int] | None = None) -> "JLensReader":
        """Load the pinned n1000 lens (fp16 on disk → fp32) and the model's unembedding."""
        import torch
        from huggingface_hub import hf_hub_download

        self.tokenizer, self.device = target.tokenizer, target.device
        path = str(lens_path) if lens_path else hf_hub_download(C.JLENS_REPO, C.JLENS_FILE, revision=C.JLENS_SHA)
        self.lens_path = path
        obj = torch.load(path, map_location="cpu", weights_only=False)
        jac = obj["J"] if "J" in obj else obj["jacobians"]
        if isinstance(jac, dict):
            layers = sorted(int(k) for k in jac)
            get = lambda L: (jac[L] if L in jac else jac[str(L)])  # noqa: E731
        else:
            layers = list(range(jac.shape[0]))
            get = lambda L: jac[L]  # noqa: E731
        self.source_layers = list(obj.get("source_layers", layers))
        self.n_prompts = obj.get("n_prompts")
        keep = layers_keep or [C.LAYER]
        self.J = {L: get(L).float().to(target.device) for L in keep if L in layers}
        self.w_u = M.unembed_weight(target.model).float()
        del obj, jac
        return self

    def bind_tensors(self, J: dict[int, Any], w_u: Any, tokenizer: Any, device: str = "cpu") -> "JLensReader":
        """MOCK/test entry: pre-built Jacobians and unembedding."""
        self.J, self.w_u, self.tokenizer, self.device = J, w_u.float(), tokenizer, device
        self.source_layers = sorted(J)
        return self

    def read(self, h: Any, layer: int | None = None, **_: Any) -> ReadResult:
        import torch

        layer = C.LAYER if layer is None else layer

        if layer not in self.J:
            raise ValueError(f"layer {layer} not loaded; lens source_layers={self.source_layers}")
        from .accounting import timed_call

        with timed_call() as st:
            J = self.J[layer]
            if layer not in self._denom:
                self._denom[layer] = (self.w_u @ J).norm(dim=1).clamp_min(1e-9)
            v = h.to(self.w_u.device).float()
            scores = ((v @ J.T) @ self.w_u.T) / self._denom[layer]
            vals, ids = torch.topk(scores, self.k)
        toks = M.display_tokens(self.tokenizer, ids.tolist())
        decoded = [self.tokenizer.decode([int(i)]) for i in ids.tolist()]  # real strings for the rubric
        return ReadResult(
            method=self.name, raw_output=None,
            native={"tokens": toks, "scores": [round(x, 4) for x in vals.tolist()], "token_ids": ids.tolist(),
                    "tokens_decoded": decoded},
            input={"fixed_instruction": None, "layer_in_prompt": None, "visible_prompt": None,
                   "prompt_ids_sha256": None, "injection": C.JLENS_INJECTION,
                   "activation_norm": round(float(h.norm()), 4), "lens_file": C.JLENS_FILE},
            n_prompt_tokens=0, n_new_tokens=0, finish_reason=None, wall_s=st.wall_s,
            peak_mem_gb=st.peak_mem_gb, seed=None, sampling={}, adapter=self.adapter,
        )


# ================================================================== OLens
class OLensReader:
    """wsbench ``OLens`` on the probed model (PEFT LoRA mounted on it; capture must disable it)."""

    name = "olens"

    def __init__(self, alpha: float = C.OLENS_ALPHA, prompt: str = C.OLENS_PROMPT,
                 max_new_tokens: int = C.VERBALIZER_MAX_NEW_TOKENS, sampling: dict[str, Any] | None = None):
        self.alpha, self.prompt = alpha, prompt
        self.max_new_tokens = max_new_tokens
        self.sampling = dict(sampling or C.SAMPLING)
        self.target: M.Target | None = None
        self.adapter = C.OLENS_SUBFOLDER
        self.adapter_dir: Path | None = None
        self.liveness: dict[str, Any] | None = None
        self._carriers: dict[int, tuple[list[int], int, str, int]] = {}

    def bind(self, target: M.Target, adapter_dir: str | Path | None = None, check: bool = True) -> "OLensReader":
        from peft import PeftModel

        if adapter_dir is None:
            local = hf_dir(C.OLENS_REPO, C.OLENS_SHA, [f"{C.OLENS_SUBFOLDER}/*"])
            adapter_dir = local / C.OLENS_SUBFOLDER
        self.adapter_dir = Path(adapter_dir)
        if isinstance(target.model, PeftModel):
            target.model = target.model.unload()
        target.model = PeftModel.from_pretrained(target.model, str(self.adapter_dir))
        target.model.eval()
        self.target = target
        if check:
            ids, _slot, _c, _cid = self.carrier(C.LAYER)
            self.liveness = assert_adapter_live(target.model, self.adapter_dir, ids)
        return self

    def carrier(self, layer: int) -> tuple[list[int], int, str, int]:
        if layer not in self._carriers:
            assert self.target is not None
            self._carriers[layer] = olens_carrier(self.target.tokenizer, layer, self.prompt)
        return self._carriers[layer]

    def read(self, h: Any, layer: int | None = None, seed: int | None = None, max_new_tokens: int | None = None) -> ReadResult:
        import torch

        layer = C.LAYER if layer is None else layer
        t = self.target
        assert t is not None
        ids, slot, char, char_id = self.carrier(layer)
        cap = max_new_tokens or self.max_new_tokens
        embed = t.model.get_input_embeddings()
        dev = next(t.model.parameters()).device
        with torch.no_grad():
            e = embed(torch.tensor([ids], device=dev)).clone()
            v = h.to(dev).float()
            e[0, slot, :] = (self.alpha * v / v.norm().clamp_min(1e-9)).to(e.dtype)
        res: GenResult = generate_ids(t.model, t.tokenizer, ids, max_new_tokens=cap,
                                      sampling=self.sampling, seed=seed, inputs_embeds=e, adapter_enabled=True)
        text = res.raw_output.strip()
        bullets = olens_bullets(text)
        return ReadResult(
            method=self.name, raw_output=res.raw_output,
            native={"samples": [text], "bullets": bullets},
            input={"fixed_instruction": self.prompt.format(layer=layer, char=char),
                   "layer_in_prompt": layer, "visible_prompt": None,
                   "prompt_ids_sha256": C.sha256_ids(ids), "marker_index": slot,
                   "marker_char": char, "marker_id": char_id,
                   "injection": C.OLENS_INJECTION, "alpha": self.alpha,
                   "activation_norm": round(float(h.norm()), 4), "n_prompt_tokens": len(ids)},
            n_prompt_tokens=res.n_prompt_tokens, n_new_tokens=res.n_new_tokens,
            finish_reason=res.finish_reason, wall_s=res.wall_s, peak_mem_gb=res.peak_mem_gb,
            seed=seed, sampling=res.sampling, adapter=self.adapter,
        )


# ================================================================== NLA
class NLAReader:
    """wsbench ``NLA``: a separate reader model (av_base + RL adapter) with a forward hook on the
    output of its decoder block 1 that adds ‖h₁‖·unit(h) at the marker position (prefill only).
    ``_vec["v"]`` may be ``[d]`` (generation) or ``[B, d]`` (one vector per batch row, scoring)."""

    name = "nla"

    def __init__(self, max_new_tokens: int = C.VERBALIZER_MAX_NEW_TOKENS, sampling: dict[str, Any] | None = None,
                 inject_layer_idx: int = C.NLA_INJECT_LAYER_IDX):
        self.max_new_tokens = max_new_tokens
        self.sampling = dict(sampling or C.SAMPLING)
        self.inject_layer_idx = inject_layer_idx
        self.adapter = C.NLA_ADAPTER_SUBFOLDER
        self.model = None
        self.tokenizer = None
        self.meta: dict[str, Any] = {}
        self.ids: list[int] = []
        self.marker = -1
        self.prompt_text = ""
        self.device = None
        self._vec: dict[str, Any] = {"v": None}
        self.liveness: dict[str, Any] | None = None
        self.n_hook_calls = 0
        self.base_dir: Path | None = None
        self.adapter_dir: Path | None = None

    # ---- loading
    def bind(self, device: str = "cuda", base_dir: str | Path | None = None, adapter_dir: str | Path | None = None,
             check: bool = True, dtype: str = "bfloat16") -> "NLAReader":
        import torch
        import yaml
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if base_dir is None:
            local = hf_dir(C.NLA_REPO, C.NLA_SHA, [f"{C.NLA_BASE_SUBFOLDER}/*", C.NLA_META_FILE])
            base_dir = local / C.NLA_BASE_SUBFOLDER
        if adapter_dir is None:
            local = hf_dir(C.NLA_REPO, C.NLA_SHA, [f"{C.NLA_ADAPTER_SUBFOLDER}/*"])
            adapter_dir = local / C.NLA_ADAPTER_SUBFOLDER
        self.base_dir, self.adapter_dir = Path(base_dir), Path(adapter_dir)
        meta = yaml.safe_load((self.base_dir / "nla_meta.yaml").read_text(encoding="utf-8"))
        tok = AutoTokenizer.from_pretrained(str(self.base_dir))
        model = AutoModelForCausalLM.from_pretrained(str(self.base_dir), dtype=getattr(torch, dtype), device_map=device)
        if self.adapter and self.adapter != "none":
            model = PeftModel.from_pretrained(model, str(self.adapter_dir), torch_dtype=getattr(torch, dtype))
        model.eval()
        self.attach(model, tok, meta, device)
        if check and self.adapter != "none":
            self.liveness = assert_adapter_live(self.model, self.adapter_dir, self.ids)
        return self

    def attach(self, model: Any, tokenizer: Any, meta: dict[str, Any], device: str = "cpu") -> "NLAReader":
        """Attach to an already-loaded reader (also the MOCK/test entry). Checks the marker and
        registers the injection hook on block ``inject_layer_idx``."""
        self.model, self.tokenizer, self.meta, self.device = model, tokenizer, meta, device
        self.ids, self.marker, self.prompt_text = nla_prompt(tokenizer, meta)
        for k, want in (("injection_token_id", C.NLA_INJECTION_TOKEN_ID),
                        ("injection_left_neighbor_id", C.NLA_LEFT_NEIGHBOR_ID),
                        ("injection_right_neighbor_id", C.NLA_RIGHT_NEIGHBOR_ID)):
            if int(meta["tokens"][k]) != want and not meta.get("_mock"):
                raise RuntimeError(f"nla_meta.yaml {k}={meta['tokens'][k]} != frozen {want}")
        blks = M.blocks(model)
        block = blks[self.inject_layer_idx]
        mp = self.marker
        vec = self._vec
        reader = self

        def hook(_mod, _inp, out):
            h = out[0] if isinstance(out, tuple) else out
            v = vec.get("v")
            if v is None or h.shape[1] <= mp:  # decode steps (seq_len 1) never re-inject
                return out
            reader.n_hook_calls += 1
            hp = h[:, mp, :]
            v = v.to(h.device)
            if v.ndim == 2:  # one vector per batch row (teacher-forced scoring): row i gets v[i]
                if v.shape[0] != h.shape[0]:
                    raise RuntimeError(f"NLA hook: {v.shape[0]} vectors for a batch of {h.shape[0]}")
                vu = v.to(h.dtype) / (v.norm(dim=-1, keepdim=True).to(h.dtype) + 1e-9)
            else:
                vu = v.to(h.dtype) / (v.norm().to(h.dtype) + 1e-9)
            h[:, mp, :] = hp + hp.norm(dim=-1, keepdim=True) * vu
            return out

        self._handle = block.register_forward_hook(hook)
        return self

    # ---- reading
    def read(self, h: Any, layer: int | None = None, seed: int | None = None, max_new_tokens: int | None = None) -> ReadResult:
        assert self.model is not None
        cap = max_new_tokens or self.max_new_tokens
        self._vec["v"] = h.float()
        calls0 = self.n_hook_calls
        try:
            res: GenResult = generate_ids(self.model, self.tokenizer, self.ids, max_new_tokens=cap,
                                          sampling=self.sampling, seed=seed)
        finally:
            self._vec["v"] = None
        n_inj = self.n_hook_calls - calls0
        if n_inj < 1:
            raise RuntimeError("NLA injection hook did not fire during the prefill")
        text = res.raw_output
        return ReadResult(
            method=self.name, raw_output=text,
            native={"samples": [strip_explanation(text)], "explanation_closed": "</explanation>" in text},
            input={"fixed_instruction": self.prompt_text, "layer_in_prompt": None, "visible_prompt": None,
                   "prompt_ids_sha256": C.sha256_ids(self.ids), "marker_index": self.marker,
                   "marker_id": int(self.meta["tokens"]["injection_token_id"]),
                   "neighbours": [int(self.meta["tokens"]["injection_left_neighbor_id"]),
                                  int(self.meta["tokens"]["injection_right_neighbor_id"])],
                   "injection": C.NLA_INJECTION, "inject_block": self.inject_layer_idx,
                   "activation_norm": round(float(h.norm()), 4), "n_prompt_tokens": len(self.ids)},
            n_prompt_tokens=res.n_prompt_tokens, n_new_tokens=res.n_new_tokens,
            finish_reason=res.finish_reason, wall_s=res.wall_s, peak_mem_gb=res.peak_mem_gb,
            seed=seed, sampling=res.sampling, adapter=self.adapter, extra={"n_hook_injections": n_inj},
        )

    def unload(self) -> None:
        try:
            self._handle.remove()
        except Exception:
            pass
        M.unload(self)


# ================================================================== Skip-lens (Phase Y3)
def install_marker_add_hook(model: Any, block_idx: int, marker: int, vec: dict[str, Any], counter: Any) -> Any:
    """The NLA injection hook (same formula as ``NLAReader.attach``), registered on the output of
    decoder block ``block_idx`` of ``model``: at the marker position the row becomes
    h₁ + ‖h₁‖ · v/‖v‖ (prefill only; decode steps with seq_len ≤ marker are untouched).
    ``vec["v"]`` is ``None`` (hook inert), ``[d]`` (one vector) or ``[B, d]`` (one per batch row).
    ``counter.n_hook_calls`` is incremented per injection. Returns the hook handle."""
    block = M.blocks(model)[block_idx]

    def hook(_mod, _inp, out):
        h = out[0] if isinstance(out, tuple) else out
        v = vec.get("v")
        if v is None or h.shape[1] <= marker:
            return out
        counter.n_hook_calls += 1
        hp = h[:, marker, :]
        v = v.to(h.device)
        if v.ndim == 2:
            if v.shape[0] != h.shape[0]:
                raise RuntimeError(f"marker hook: {v.shape[0]} vectors for a batch of {h.shape[0]}")
            vu = v.to(h.dtype) / (v.norm(dim=-1, keepdim=True).to(h.dtype) + 1e-9)
        else:
            vu = v.to(h.dtype) / (v.norm().to(h.dtype) + 1e-9)
        h[:, marker, :] = hp + hp.norm(dim=-1, keepdim=True) * vu
        return out

    return block.register_forward_hook(hook)


class SkipLensReader:
    """Skip-lens ("agreelens") arm A or D (BRIEF_Y §Y3): a PEFT LoRA on the PLAIN TARGET BASE, so it is
    mounted on the probed model as a NAMED adapter (``skip_a`` / ``skip_d``) beside the Oracle lens's
    ``default`` adapter; ``active()`` makes it the active adapter for a read and restores the previous
    one afterwards, and the target's own decodes keep using ``disable_adapter`` (``model.capture`` /
    ``generate_ids(adapter_enabled=False)``). Injection = the NLA hook at the block-1 output (per-row
    vectors), marker ㈜ 158983 between (29, 510), actor prompt from the repo's ``nla_meta.yaml``, chat
    render with thinking off. Free-text ``read()`` samples at T = 1, top-p 0.95 (the README setting);
    teacher-forced LO lives in ``scoring_lo.lo_skiplens``.

    Mount order: bind the Oracle lens FIRST (``OLensReader.bind`` unloads any mounted adapter), then
    the skip-lens arms (``load_adapter`` on the existing PeftModel)."""

    def __init__(self, arm: str = "a", max_new_tokens: int = C.VERBALIZER_MAX_NEW_TOKENS, sampling: dict[str, Any] | None = None,
                 inject_layer_idx: int = C.NLA_INJECT_LAYER_IDX):
        if arm not in C.SKIPLENS_ARMS:
            raise ValueError(f"unknown skip-lens arm {arm!r}; expected one of {C.SKIPLENS_ARMS}")
        self.arm = arm
        self.name = C.SKIPLENS_READER_NAMES[arm]
        self.adapter_name = self.name
        self.adapter = f"{C.SKIPLENS_REPOS[arm]}@{C.SKIPLENS_SHAS[arm][:8]}"
        self.max_new_tokens = max_new_tokens
        self.sampling = dict(sampling or C.SKIPLENS_SAMPLING)
        self.inject_layer_idx = inject_layer_idx
        self.target: M.Target | None = None
        self.tokenizer = None
        self.device = None
        self.meta: dict[str, Any] = {}
        self.ids: list[int] = []
        self.marker = -1
        self.prompt_text = ""
        self._vec: dict[str, Any] = {"v": None}
        self._handle = None
        self.n_hook_calls = 0
        self.liveness: dict[str, Any] | None = None
        self.adapter_dir: Path | None = None

    @property
    def model(self) -> Any:
        return None if self.target is None else self.target.model

    # ---- loading
    def bind(self, target: M.Target, adapter_dir: str | Path | None = None, check: bool = True) -> "SkipLensReader":
        import yaml
        from peft import PeftModel

        if adapter_dir is None:
            adapter_dir = hf_dir(C.SKIPLENS_REPOS[self.arm], C.SKIPLENS_SHAS[self.arm], list(C.SKIPLENS_FILES))
        self.adapter_dir = Path(adapter_dir)
        meta = yaml.safe_load((self.adapter_dir / C.SKIPLENS_META_FILE).read_text(encoding="utf-8"))
        if isinstance(target.model, PeftModel):
            if self.adapter_name not in target.model.peft_config:
                target.model.load_adapter(str(self.adapter_dir), adapter_name=self.adapter_name)
        else:
            target.model = PeftModel.from_pretrained(target.model, str(self.adapter_dir), adapter_name=self.adapter_name)
        target.model.eval()
        self.attach(target, meta)
        if check:
            with self.active():
                self.liveness = assert_adapter_live(target.model, self.adapter_dir, self.ids, adapter_name=self.adapter_name)
        return self

    def attach(self, target: M.Target, meta: dict[str, Any]) -> "SkipLensReader":
        """Attach to a target whose model already carries the adapter (also the MOCK/test entry):
        marker check against the frozen NLA ids, hook on the block-``inject_layer_idx`` output."""
        self.target, self.tokenizer, self.meta, self.device = target, target.tokenizer, meta, target.device
        self.ids, self.marker, self.prompt_text = nla_prompt(target.tokenizer, meta)
        for k, want in (("injection_token_id", C.NLA_INJECTION_TOKEN_ID),
                        ("injection_left_neighbor_id", C.NLA_LEFT_NEIGHBOR_ID),
                        ("injection_right_neighbor_id", C.NLA_RIGHT_NEIGHBOR_ID)):
            if int(meta["tokens"][k]) != want and not meta.get("_mock"):
                raise RuntimeError(f"skip-lens {self.arm} nla_meta.yaml {k}={meta['tokens'][k]} != frozen {want}")
        if self._handle is not None:
            self._handle.remove()
        self._handle = install_marker_add_hook(target.model, self.inject_layer_idx, self.marker, self._vec, self)
        return self

    # ---- adapter switching
    def active(self):
        """Context: this arm is the active PEFT adapter; the previously active one is restored on exit."""
        reader = self

        class _Ctx:
            def __enter__(self_):
                m = reader.model
                self_.prev = None
                if hasattr(m, "set_adapter") and hasattr(m, "peft_config"):
                    act = getattr(m, "active_adapters", None) or [getattr(m, "active_adapter", None)]
                    self_.prev = [a for a in act if a] or None
                    if reader.adapter_name not in m.peft_config:
                        raise RuntimeError(f"adapter {reader.adapter_name} is not mounted on the target")
                    m.set_adapter(reader.adapter_name)
                return reader

            def __exit__(self_, *a):
                m = reader.model
                if self_.prev and hasattr(m, "set_adapter"):
                    prev = self_.prev[0] if len(self_.prev) == 1 else self_.prev
                    if all(p in m.peft_config for p in self_.prev):
                        m.set_adapter(prev)
                return False

        return _Ctx()

    # ---- reading
    def read(self, h: Any, layer: int | None = None, seed: int | None = None, max_new_tokens: int | None = None) -> ReadResult:
        assert self.target is not None
        cap = max_new_tokens or self.max_new_tokens
        calls0 = self.n_hook_calls
        with self.active():
            self._vec["v"] = h.float()
            try:
                res: GenResult = generate_ids(self.target.model, self.tokenizer, self.ids, max_new_tokens=cap,
                                              sampling=self.sampling, seed=seed, adapter_enabled=True)
            finally:
                self._vec["v"] = None
        n_inj = self.n_hook_calls - calls0
        if n_inj < 1:
            raise RuntimeError(f"skip-lens {self.arm} injection hook did not fire during the prefill")
        text = res.raw_output
        return ReadResult(
            method=self.name, raw_output=text, native={"samples": [text.strip()]},
            input={"fixed_instruction": self.prompt_text, "layer_in_prompt": None, "visible_prompt": None,
                   "prompt_ids_sha256": C.sha256_ids(self.ids), "marker_index": self.marker,
                   "marker_id": int(self.meta["tokens"]["injection_token_id"]),
                   "neighbours": [int(self.meta["tokens"]["injection_left_neighbor_id"]), int(self.meta["tokens"]["injection_right_neighbor_id"])],
                   "injection": C.SKIPLENS_INJECTION, "inject_block": self.inject_layer_idx, "arm": self.arm,
                   "adapter_name": self.adapter_name, "activation_norm": round(float(h.norm()), 4), "n_prompt_tokens": len(self.ids)},
            n_prompt_tokens=res.n_prompt_tokens, n_new_tokens=res.n_new_tokens, finish_reason=res.finish_reason,
            wall_s=res.wall_s, peak_mem_gb=res.peak_mem_gb, seed=seed, sampling=res.sampling, adapter=self.adapter,
            extra={"n_hook_injections": n_inj},
        )

    def unload(self) -> None:
        """Remove the hook and the adapter from the target (the target itself stays loaded)."""
        try:
            self._handle.remove()
        except Exception:
            pass
        m = self.model
        if m is not None and hasattr(m, "delete_adapter") and self.adapter_name in getattr(m, "peft_config", {}):
            others = [a for a in m.peft_config if a != self.adapter_name]
            if others:
                m.set_adapter(others[0])
                m.delete_adapter(self.adapter_name)
        self.target = None


# ================================================================== R-lens (Phase Y3)
class RLensReader(JLensReader):
    """RelP Jacobian lens (camilablank/workspace-lenses ``qwen3.6-27b/r-lens/lens.pt``): the J-lens cosine
    readout on a different stacked-Jacobian dictionary. ``bind`` inspects the checkpoint at run time and
    uses it only if ``J`` is ``[n_src, d, d]`` (or a dict of ``[d, d]``) with d == D_MODEL and the capture
    layer among ``source_layers``; otherwise ``self.usable`` is False and ``self.skip_reason`` says why."""

    name = C.RLENS_NAME
    adapter = "none"

    def __init__(self, k: int = C.JLENS_TOP_K):
        super().__init__(k=k)
        self.usable = False
        self.skip_reason: str | None = None
        self.format: dict[str, Any] = {}

    def bind(self, target: M.Target, lens_path: str | Path | None = None, layers_keep: list[int] | None = None) -> "RLensReader":
        import torch
        from huggingface_hub import hf_hub_download

        self.tokenizer, self.device = target.tokenizer, target.device
        path = str(lens_path) if lens_path else hf_hub_download(C.RLENS_REPO, C.RLENS_FILE, revision=C.RLENS_SHA)
        self.lens_path = path
        obj = torch.load(path, map_location="cpu", weights_only=False)
        fmt = self.inspect(obj)
        self.format = fmt
        if not fmt["compatible"]:
            self.usable, self.skip_reason = False, fmt["reason"]
            del obj
            return self
        jac = obj["J"] if "J" in obj else obj["jacobians"]
        src = fmt["source_layers"]
        keep = layers_keep or [C.LAYER]
        if isinstance(jac, dict):
            get = lambda L: (jac[L] if L in jac else jac[str(L)])  # noqa: E731
        else:
            index = {int(L): i for i, L in enumerate(src)}
            get = lambda L: jac[index[L]]  # noqa: E731
        self.source_layers = list(src)
        self.n_prompts = obj.get("n_prompts")
        self.J = {L: get(L).float().to(target.device) for L in keep if L in self.source_layers}
        self.w_u = M.unembed_weight(target.model).float()
        self.usable = bool(self.J)
        self.skip_reason = None if self.usable else f"layers {keep} not in source_layers {self.source_layers[:3]}..{self.source_layers[-3:]}"
        del obj, jac
        return self

    @staticmethod
    def inspect(obj: Any, d_model: int | None = None, layer: int | None = None) -> dict[str, Any]:
        """Shape/key report of a lens checkpoint: compatible iff J is d×d per layer and ``layer`` is covered."""
        d_model = C.D_MODEL if d_model is None else d_model
        layer = C.LAYER if layer is None else layer
        rep: dict[str, Any] = {"compatible": False, "reason": None, "keys": None, "source_layers": None, "shape": None}
        if not isinstance(obj, dict):
            rep["reason"] = f"checkpoint is a {type(obj).__name__}, not a dict"
            return rep
        rep["keys"] = sorted(str(k) for k in obj)
        jac = obj.get("J", obj.get("jacobians"))
        if jac is None:
            rep["reason"] = "no 'J' / 'jacobians' entry"
            return rep
        if isinstance(jac, dict):
            layers = sorted(int(k) for k in jac)
            shapes = {tuple(jac[k].shape) for k in jac}
            rep["source_layers"] = layers
            rep["shape"] = f"dict of {len(layers)} x {sorted(shapes)}"
            if shapes != {(d_model, d_model)}:
                rep["reason"] = f"per-layer matrices are {sorted(shapes)}, not ({d_model}, {d_model})"
                return rep
        else:
            shape = tuple(getattr(jac, "shape", ()))
            rep["shape"] = list(shape)
            if len(shape) != 3 or shape[1:] != (d_model, d_model):
                rep["reason"] = f"J has shape {shape}, expected [n_src, {d_model}, {d_model}]"
                return rep
            src = obj.get("source_layers")
            layers = [int(x) for x in src] if src is not None else list(range(shape[0]))
            if len(layers) != shape[0]:
                rep["reason"] = f"source_layers has {len(layers)} entries for {shape[0]} matrices"
                return rep
            rep["source_layers"] = layers
        if layer not in rep["source_layers"]:
            rep["reason"] = f"layer {layer} not among source_layers"
            return rep
        rep["compatible"] = True
        prov = obj.get("provenance")
        if isinstance(prov, dict):
            rep["provenance"] = {k: (v if isinstance(v, (str, int, float, bool)) else str(v)[:200]) for k, v in prov.items()}
        rep["n_prompts"] = obj.get("n_prompts")
        return rep

    def read(self, h: Any, layer: int | None = None, **kw: Any) -> ReadResult:
        if not self.usable:
            raise RuntimeError(f"R-lens not usable: {self.skip_reason}")
        res = super().read(h, layer, **kw)
        res.method = self.name
        res.input["lens_file"] = C.RLENS_FILE
        return res


READERS = {"jlens": JLensReader, "olens": OLensReader, "nla": NLAReader}
SKIPLENS_READERS = {"skip_a": lambda **kw: SkipLensReader("a", **kw), "skip_d": lambda **kw: SkipLensReader("d", **kw)}


def input_dump(reader: Any, h: Any, tokenizer: Any | None = None) -> dict[str, Any]:
    """The COMPLETE input a reader receives for one activation (R0 check e)."""
    if isinstance(reader, OLensReader):
        ids, slot, char, cid = reader.carrier(C.LAYER)
        tok = reader.target.tokenizer
        return {"method": "olens", "prompt_text": tok.decode(ids, skip_special_tokens=False),
                "fixed_instruction": reader.prompt.format(layer=C.LAYER, char=char),
                "token_ids": ids, "tokens": [tok.decode([i]) for i in ids], "marker_index": slot,
                "marker_char": char, "marker_id": cid, "layer_in_prompt": C.LAYER,
                "injection": "input_embedding[marker] := alpha * h / ||h||", "alpha": reader.alpha,
                "activation_norm": float(h.norm()), "injected_row_norm": reader.alpha,
                "sampling": {**reader.sampling, "max_new_tokens": reader.max_new_tokens},
                "adapter": str(reader.adapter_dir), "adapter_liveness": reader.liveness}
    if isinstance(reader, NLAReader):
        tok = reader.tokenizer
        return {"method": "nla", "prompt_text": tok.decode(reader.ids, skip_special_tokens=False),
                "fixed_instruction": reader.prompt_text, "token_ids": reader.ids,
                "tokens": [tok.decode([i]) for i in reader.ids], "marker_index": reader.marker,
                "marker_id": int(reader.meta["tokens"]["injection_token_id"]),
                "neighbours": [reader.ids[reader.marker - 1], reader.ids[reader.marker + 1]],
                "injection": "block1_output[marker] := h1 + ||h1|| * h / ||h||  (prefill only)",
                "activation_norm": float(h.norm()),
                "sampling": {**reader.sampling, "max_new_tokens": reader.max_new_tokens},
                "base": str(reader.base_dir), "adapter": str(reader.adapter_dir), "adapter_liveness": reader.liveness}
    if isinstance(reader, JLensReader):  # J-lens and the R-lens subclass
        return {"method": reader.name, "lens_file": reader.lens_path, "source_layers": reader.source_layers,
                "n_prompts": reader.n_prompts, "layer": C.LAYER,
                "readout": "scores[t] = (h @ J_L^T @ W_U^T)[t] / ||W_U[t] @ J_L||; top-10",
                "activation_norm": float(h.norm()), "k": reader.k}
    if isinstance(reader, SkipLensReader):
        tok = reader.tokenizer
        return {"method": reader.name, "arm": reader.arm, "prompt_text": tok.decode(reader.ids, skip_special_tokens=False),
                "fixed_instruction": reader.prompt_text, "token_ids": reader.ids,
                "tokens": [tok.decode([i]) for i in reader.ids], "marker_index": reader.marker,
                "marker_id": int(reader.meta["tokens"]["injection_token_id"]),
                "neighbours": [reader.ids[reader.marker - 1], reader.ids[reader.marker + 1]],
                "injection": "block1_output[marker] := h1 + ||h1|| * h / ||h||  (prefill only; LoRA on the target, adapter %s active)" % reader.adapter_name,
                "activation_norm": float(h.norm()),
                "sampling": {**reader.sampling, "max_new_tokens": reader.max_new_tokens},
                "adapter": str(reader.adapter_dir), "adapter_liveness": reader.liveness,
                "lo_forms": list(C.SKIPLENS_LO_FORMS)}
    raise TypeError(type(reader))


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)
