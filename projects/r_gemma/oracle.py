"""The released Gemma-2-9B-it activation oracle (Karvonen et al.) as a natively scored reader (BRIEF_RG §2.1).

Recipe (from the repo's ``ao_config.json``, ``dataset_utils.create_training_datapoint`` and the HF steering hook):
  prompt   user turn = "Layer: {L}\\n ? \\n" + question; chat template with the generation prompt; the answer is the
           assistant turn
  inject   at the OUTPUT of decoder block 1, at the ` ?` position: resid <- resid + unit(v) * ||resid|| * 1.0
  layers   the oracle was trained on block outputs 10 / 21 / 31 of the target ("Layer: 21" in the prompt)
Two native forms (both candidates of a state in the same forward; left padding, positions shifted by the pad):
  ao      candidate form: question + 'Answer with exactly one of these two options and nothing else: "pos" or "neg".',
          s_X = Σ lp(tokens of X) teacher-forced as the assistant turn; LO = s_pos − s_neg
  ao_yn   training-native yes/no form: 'Answer with 'Yes' or 'No' only. Is this statement about the text true: "T(X)"?',
          s_X = lp(Yes) − lp(No) at the assistant onset; LO = s_pos − s_neg
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from projects.g_agreement.core import model as M
from projects.r_gemma import config as G
from projects.r_gemma import gemma as GM


def hf_adapter_dir(repo: str = G.AO_REPO, revision: str = G.AO_SHA, files: list[str] = G.AO_FILES) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo, revision=revision, allow_patterns=files))


class AOReader:
    """Mounts the oracle LoRA on the probed model (PEFT, adapter name ``ao``); capture must run adapter-off
    (``core.model.disable_adapter_ctx``). ``name`` selects the form: ``ao`` or ``ao_yn``."""

    def __init__(self, form: str = "ao", coef: float = G.AO_COEF, hook_layer: int = G.AO_HOOK_LAYER):
        if form not in G.READERS:
            raise ValueError(form)
        self.name = form
        self.base_name = "ao"
        self.coef = coef
        self.hook_layer = hook_layer
        self.target: M.Target | None = None
        self.adapter_dir: Path | None = None
        self.ao_config: dict[str, Any] = {}
        self.special_id: int | None = None
        self.yes_id: int | None = None
        self.no_id: int | None = None
        self._vec: dict[str, Any] = {"v": None, "pos": None}
        self.n_hook_calls = 0
        self._handle = None
        self._carrier: dict[tuple[int, str], tuple[list[int], int]] = {}
        self.liveness: dict[str, Any] = {}

    # ---------------------------------------------------------------- mounting
    def bind(self, target: M.Target, adapter_dir: str | Path | None = None, check: bool = True) -> "AOReader":
        from peft import PeftModel

        self.target = target
        self.adapter_dir = Path(adapter_dir) if adapter_dir else hf_adapter_dir()
        cfg_path = self.adapter_dir / "ao_config.json"
        if cfg_path.exists():
            self.ao_config = json.loads(cfg_path.read_text())
            if check:
                self._check_config()
        model = target.model
        if hasattr(model, "peft_config"):
            if G.AO_ADAPTER_NAME not in model.peft_config:
                model.load_adapter(str(self.adapter_dir), adapter_name=G.AO_ADAPTER_NAME, is_trainable=False)
        else:
            model = PeftModel.from_pretrained(model, str(self.adapter_dir), adapter_name=G.AO_ADAPTER_NAME, is_trainable=False)
            target.model = model
        model.set_adapter(G.AO_ADAPTER_NAME)
        model.eval()
        return self.attach(target)

    def attach(self, target: M.Target) -> "AOReader":
        """Tokens and the hook (separate from ``bind`` so a mock can attach without PEFT files)."""
        self.target = target
        tok = target.tokenizer
        sp = GM.encode(tok, G.AO_SPECIAL)
        if len(sp) != 1:
            raise RuntimeError(f"the oracle's special token {G.AO_SPECIAL!r} is {len(sp)} tokens, expected 1")
        self.special_id = int(sp[0])
        self.yes_id = int(GM.encode(tok, G.AO_YES)[0])
        self.no_id = int(GM.encode(tok, G.AO_NO)[0])
        if self.yes_id == self.no_id:
            raise RuntimeError("Yes / No share their first token")
        self._install_hook()
        return self

    def _check_config(self) -> None:
        c = self.ao_config
        if c.get("special_token") not in (None, G.AO_SPECIAL):
            raise RuntimeError(f"ao_config special_token {c.get('special_token')!r} != {G.AO_SPECIAL!r}")
        if c.get("hook_onto_layer") not in (None, G.AO_HOOK_LAYER):
            raise RuntimeError(f"ao_config hook_onto_layer {c.get('hook_onto_layer')} != {G.AO_HOOK_LAYER}")
        if c.get("model_name") not in (None, G.TARGET_ID):
            raise RuntimeError(f"ao_config model_name {c.get('model_name')} != {G.TARGET_ID}")
        grid = tuple(sorted({L for combo in c.get("act_layer_combinations", []) for L in combo}))
        if grid and grid != G.AO_GRID:
            raise RuntimeError(f"ao_config act layers {grid} != {G.AO_GRID}")

    def _install_hook(self) -> None:
        import torch

        if self._handle is not None:
            self._handle.remove()
        blk = M.blocks(self.target.model)[self.hook_layer]
        reader = self

        def hook(_mod, _inp, out):
            v, pos = reader._vec["v"], reader._vec["pos"]
            if v is None:
                return None
            h = out[0] if isinstance(out, tuple) else out
            if h.shape[1] <= 1:   # not a prefill forward
                return None
            reader.n_hook_calls += 1
            h = h.clone()
            b_idx = torch.arange(h.shape[0], device=h.device)
            p_idx = torch.as_tensor(pos, device=h.device)
            orig = h[b_idx, p_idx, :]
            vv = v.to(h.device).float()
            unit = vv / vv.norm(dim=-1, keepdim=True).clamp_min(1e-9)
            steered = unit * orig.float().norm(dim=-1, keepdim=True) * reader.coef
            h[b_idx, p_idx, :] = (steered + orig.float()).to(h.dtype)
            return (h,) + tuple(out[1:]) if isinstance(out, tuple) else h

        self._handle = blk.register_forward_hook(hook)

    def unload(self) -> None:
        if self._handle is not None:
            self._handle.remove()
            self._handle = None

    # ---------------------------------------------------------------- prompts
    def prefix(self, layer: int) -> str:
        return G.AO_PREFIX.format(layer=layer, special=G.AO_SPECIAL)

    def carrier(self, layer: int, question: str) -> tuple[list[int], int]:
        """(head ids, special position) for the oracle prompt ``prefix(layer) + question`` (cached per layer × question)."""
        key = (layer, question)
        if key not in self._carrier:
            head, _ = GM.chat_ids(self.target.tokenizer, self.prefix(layer) + question)
            pos = [i for i, t in enumerate(head) if t == self.special_id]
            if len(pos) != 1:
                raise RuntimeError(f"expected exactly one special token in the oracle prompt, found {len(pos)}")
            self._carrier[key] = (head, pos[0])
        return self._carrier[key]

    @staticmethod
    def fc_question(question: str, pos: str, neg: str) -> str:
        return question + G.AO_FC_SUFFIX.format(pos=pos, neg=neg)

    @staticmethod
    def yn_question(statement: str) -> str:
        return G.AO_YN_TEMPLATE.format(statement=statement)

    # ---------------------------------------------------------------- scoring
    def _arm(self, vecs: list[Any], positions: list[int]):
        """Set the vectors; the positions are shifted by the left-pad offsets right before the forward."""
        import torch

        V = torch.stack([torch.as_tensor(v).float() for v in vecs])
        base = list(positions)

        def before(offsets: list[int]) -> None:
            self._vec["v"] = V
            self._vec["pos"] = [p + o for p, o in zip(base, offsets)]

        return before

    def _disarm(self) -> None:
        self._vec["v"] = None
        self._vec["pos"] = None

    def lo_candidates(self, H: Any, pairs: list[tuple[str, str]], question: str, layer: int, batch: int = G.LO_BATCH) -> list[dict[str, Any]]:
        """Candidate form: both candidates of a state share the forward batch; s_X = Σ lp(tokens of X)."""
        tok = self.target.tokenizer
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        model = self.target.model
        dev = next(model.parameters()).device
        per = max(1, batch // 2)
        out: list[dict[str, Any]] = []
        for s in range(0, H.shape[0], per):
            hs, prs = H[s: s + per], pairs[s: s + per]
            rows, heads, vecs, poss = [], [], [], []
            for i, (a, b) in enumerate(prs):
                q = self.fc_question(question, a, b)
                head, p = self.carrier(layer, q)
                for c in (a, b):
                    rows.append(head + GM.encode(tok, c))
                    heads.append(len(head))
                    vecs.append(hs[i])
                    poss.append(p)
            calls0 = self.n_hook_calls
            try:
                lps = GM.teacher_forced_lp(model, rows, heads, pad, dev, before_forward=self._arm(vecs, poss))
            finally:
                self._disarm()
            if self.n_hook_calls == calls0:
                raise RuntimeError("the oracle hook did not fire")
            for i, (a, b) in enumerate(prs):
                la, lb = lps[2 * i], lps[2 * i + 1]
                out.append({"reader": "ao", "lo": la - lb, "lp_A": la, "lp_B": lb, "templates": [G.AO_FC_SUFFIX], "format": "candidate",
                            "n_tokens_A": len(rows[2 * i]) - heads[2 * i], "n_tokens_B": len(rows[2 * i + 1]) - heads[2 * i + 1],
                            "layer_in_prompt": layer, "marker_index": poss[2 * i], "unscorable": False})
        return out

    def lo_yesno(self, H: Any, pairs: list[tuple[str, str]], template: str, layer: int, batch: int = G.LO_BATCH) -> list[dict[str, Any]]:
        """Yes/no form: one row per candidate statement; s_X = lp(Yes) − lp(No) at the assistant onset."""
        tok = self.target.tokenizer
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        model = self.target.model
        dev = next(model.parameters()).device
        per = max(1, batch // 2)
        out: list[dict[str, Any]] = []
        for s in range(0, H.shape[0], per):
            hs, prs = H[s: s + per], pairs[s: s + per]
            rows, vecs, poss = [], [], []
            for i, (a, b) in enumerate(prs):
                for c in (a, b):
                    head, p = self.carrier(layer, self.yn_question(template.format(X=c)))
                    rows.append(head)
                    vecs.append(hs[i])
                    poss.append(p)
            calls0 = self.n_hook_calls
            try:
                lps = GM.next_token_lp(model, rows, pad, dev, [self.yes_id, self.no_id], before_forward=self._arm(vecs, poss))
            finally:
                self._disarm()
            if self.n_hook_calls == calls0:
                raise RuntimeError("the oracle hook did not fire")
            for i, (a, b) in enumerate(prs):
                sa = lps[2 * i][0] - lps[2 * i][1]
                sb = lps[2 * i + 1][0] - lps[2 * i + 1][1]
                out.append({"reader": "ao_yn", "lo": sa - sb, "lp_A": sa, "lp_B": sb, "templates": [template, G.AO_YN_TEMPLATE],
                            "format": "yesno", "lp_yes_A": lps[2 * i][0], "lp_no_A": lps[2 * i][1], "lp_yes_B": lps[2 * i + 1][0],
                            "lp_no_B": lps[2 * i + 1][1], "layer_in_prompt": layer, "marker_index": poss[2 * i], "unscorable": False})
        return out

    def score(self, H: Any, pairs: list[tuple[str, str]], primary: dict[str, Any], layer: int, batch: int = G.LO_BATCH) -> list[dict[str, Any]]:
        """Dispatch on the form; ``primary`` is the item's spec (question, template)."""
        import torch

        H = torch.as_tensor(H).float()
        if H.ndim == 1:
            H = H[None]
        if H.shape[0] != len(pairs):
            raise ValueError(f"{H.shape[0]} states but {len(pairs)} pairs")
        if self.name == "ao":
            rows = self.lo_candidates(H, pairs, primary["question"], layer, batch)
        else:
            rows = self.lo_yesno(H, pairs, primary["template"], layer, batch)
        for r, (a, b) in zip(rows, pairs):
            r["cand_A"], r["cand_B"] = a, b
        return rows

    # ---------------------------------------------------------------- no-activation arm (BRIEF_RG §10; the Li control)
    def noact_user(self, layer: int, text: str, question: str) -> str:
        """The oracle prompt with the TEXT where the activation placeholder would be, so the oracle answers from text alone."""
        return G.AO_PREFIX.replace("{special}", "{text}").format(layer=layer, text=text) + question

    def score_noact(self, texts: list[str], pairs: list[tuple[str, str]], primary: dict[str, Any], layer: int, batch: int = G.LO_BATCH) -> list[dict[str, Any]]:
        """Both forms without any injection (``_vec`` stays None, so the hook is a no-op); reader names ``ao_noact`` / ``ao_yn_noact``."""
        tok = self.target.tokenizer
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        model = self.target.model
        dev = next(model.parameters()).device
        self._disarm()
        out: list[dict[str, Any]] = []
        per = max(1, batch // 2)
        for s in range(0, len(texts), per):
            tx, prs = texts[s: s + per], pairs[s: s + per]
            if self.name == "ao":
                rows, heads = [], []
                for t, (a, b) in zip(tx, prs):
                    head, _ = GM.chat_ids(tok, self.noact_user(layer, GM.truncate_text(tok, t), self.fc_question(primary["question"], a, b)))
                    for c in (a, b):
                        rows.append(head + GM.encode(tok, c))
                        heads.append(len(head))
                lps = GM.teacher_forced_lp(model, rows, heads, pad, dev)
                for i, (a, b) in enumerate(prs):
                    out.append({"reader": "ao_noact", "lo": lps[2 * i] - lps[2 * i + 1], "lp_A": lps[2 * i], "lp_B": lps[2 * i + 1],
                                "templates": [G.AO_FC_SUFFIX], "format": "candidate_noact", "layer_in_prompt": layer, "marker_index": None,
                                "unscorable": False, "cand_A": a, "cand_B": b})
            else:
                rows = []
                for t, (a, b) in zip(tx, prs):
                    for c in (a, b):
                        rows.append(GM.chat_ids(tok, self.noact_user(layer, GM.truncate_text(tok, t), self.yn_question(primary["template"].format(X=c))))[0])
                lps = GM.next_token_lp(model, rows, pad, dev, [self.yes_id, self.no_id])
                for i, (a, b) in enumerate(prs):
                    sa, sb = lps[2 * i][0] - lps[2 * i][1], lps[2 * i + 1][0] - lps[2 * i + 1][1]
                    out.append({"reader": "ao_yn_noact", "lo": sa - sb, "lp_A": sa, "lp_B": sb, "templates": [primary["template"], G.AO_YN_TEMPLATE],
                                "format": "yesno_noact", "layer_in_prompt": layer, "marker_index": None, "unscorable": False, "cand_A": a, "cand_B": b})
        return out

    # ---------------------------------------------------------------- text + activation arm (BRIEF_RG §11a)
    def textact_user(self, layer: int, text: str, question: str) -> str:
        """The oracle prompt WITH the placeholder (activation injected) AND the item's text after the prefix."""
        return self.prefix(layer) + text + "\n" + question

    def score_textact(self, H: Any, texts: list[str], pairs: list[tuple[str, str]], primary: dict[str, Any], layer: int, batch: int = G.LO_BATCH) -> list[dict[str, Any]]:
        """Both forms with the activation at the placeholder and the text in the prompt; reader names ``ao_textact`` / ``ao_yn_textact``."""
        import torch

        tok = self.target.tokenizer
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        model = self.target.model
        dev = next(model.parameters()).device
        H = torch.as_tensor(H).float()
        out: list[dict[str, Any]] = []
        per = max(1, batch // 2)
        for s in range(0, len(texts), per):
            tx, prs, hs = texts[s: s + per], pairs[s: s + per], H[s: s + per]
            rows, heads, vecs, poss = [], [], [], []
            if self.name == "ao":
                for i, (t, (a, b)) in enumerate(zip(tx, prs)):
                    user = self.textact_user(layer, GM.truncate_text(tok, t), self.fc_question(primary["question"], a, b))
                    head, _ = GM.chat_ids(tok, user)
                    p = [j for j, tid in enumerate(head) if tid == self.special_id]
                    if not p:
                        raise RuntimeError("text+activation prompt: no placeholder token")
                    # the prefix's placeholder is the FIRST one; a ' ?' inside the text (BRIEF_RG §9 note 2026-10-19) is ordinary text
                    for c in (a, b):
                        rows.append(head + GM.encode(tok, c)); heads.append(len(head)); vecs.append(hs[i]); poss.append(p[0])
                calls0 = self.n_hook_calls
                try:
                    lps = GM.teacher_forced_lp(model, rows, heads, pad, dev, before_forward=self._arm(vecs, poss))
                finally:
                    self._disarm()
                if self.n_hook_calls == calls0:
                    raise RuntimeError("the oracle hook did not fire")
                for i, (a, b) in enumerate(prs):
                    out.append({"reader": "ao_textact", "lo": lps[2 * i] - lps[2 * i + 1], "lp_A": lps[2 * i], "lp_B": lps[2 * i + 1],
                                "templates": [G.AO_FC_SUFFIX], "format": "candidate_textact", "layer_in_prompt": layer, "marker_index": poss[2 * i],
                                "unscorable": False, "cand_A": a, "cand_B": b})
            else:
                for i, (t, (a, b)) in enumerate(zip(tx, prs)):
                    for c in (a, b):
                        user = self.textact_user(layer, GM.truncate_text(tok, t), self.yn_question(primary["template"].format(X=c)))
                        head, _ = GM.chat_ids(tok, user)
                        p = [j for j, tid in enumerate(head) if tid == self.special_id]
                        if not p:
                            raise RuntimeError("text+activation prompt: no placeholder token")
                        rows.append(head); vecs.append(hs[i]); poss.append(p[0])
                calls0 = self.n_hook_calls
                try:
                    lps = GM.next_token_lp(model, rows, pad, dev, [self.yes_id, self.no_id], before_forward=self._arm(vecs, poss))
                finally:
                    self._disarm()
                if self.n_hook_calls == calls0:
                    raise RuntimeError("the oracle hook did not fire")
                for i, (a, b) in enumerate(prs):
                    sa, sb = lps[2 * i][0] - lps[2 * i][1], lps[2 * i + 1][0] - lps[2 * i + 1][1]
                    out.append({"reader": "ao_yn_textact", "lo": sa - sb, "lp_A": sa, "lp_B": sb, "templates": [primary["template"], G.AO_YN_TEMPLATE],
                                "format": "yesno_textact", "layer_in_prompt": layer, "marker_index": poss[2 * i], "unscorable": False, "cand_A": a, "cand_B": b})
        return out

    # ---------------------------------------------------------------- liveness (BRIEF_RG §7.3)
    def adapter_effect(self, ids: list[int]) -> float:
        """Max |Δ logit| at the last position between adapter on and off (no injection)."""
        import torch

        model = self.target.model
        dev = next(model.parameters()).device
        x = torch.tensor([ids], device=dev)
        with torch.no_grad():
            on = model(x, use_cache=False).logits[0, -1].float()
            with M.disable_adapter_ctx(model):
                off = model(x, use_cache=False).logits[0, -1].float()
        return float((on - off).abs().max())
