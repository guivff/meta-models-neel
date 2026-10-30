"""Qwen-Scope TopK SAE at layer 42 (BRIEF_Y §Y3): loading, TopK encode/decode, fraction of variance explained
(FVE) against a shuffled-decoder null, and the sparse LOO diff-in-means probe over latents that becomes the
"SAE probe" reader column if the transfer test passes.

Checkpoint (``Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50/layer42.sae.pt``): dict ``W_enc [81920, 5120]``,
``W_dec [5120, 81920]``, ``b_enc [81920]``, ``b_dec [5120]``; TopK k = 50; hook resid_post layer 42 (= our
block-42 output); trained on Qwen3.5-27B, so applying it to Qwen3.6-27B states is a transfer test.

Encode convention (recorded per row and in sae_fve.json):
  readme   z = topk(x @ W_encᵀ + b_enc, k)              (the README's ``get_feature_acts``; no b_dec subtraction)
  centred  z = topk((x − b_dec) @ W_encᵀ + b_enc, k)     (the standard TopK-SAE form; reported alongside)
Decode: x̂ = z @ W_decᵀ + b_dec.   FVE(X) = 1 − Σ‖x − x̂‖² / Σ‖x − mean(X)‖².
Null: the same codes decoded through W_dec with its columns permuted (seed 0) — same sparsity, no dictionary.

Sparse probe (fit on codes, never on raw states): for a held-out item the direction u is a diff-in-means over
the training codes (binary label: mean(z_pos) − mean(z_neg); identity label: class-mean(a) − class-mean(b));
only the ≤ 10 latents with the largest |u| are kept; score(h) = Σ_{l kept} sign(u_l) · z_l(h) (the sum of the
signed codes). X1: within-pair win (lo_A + lo_B > 0 with lo oriented toward the state's own answer, as in
x1_bank/analyze.py E1); X3: favours-actual (lo_actual > 0); X2: lo_own on read vectors with the direction
fitted on the X1 pairs of the family excluding the entry's own pair.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from projects.g_agreement.core import config as C

VARIANTS = ("readme", "centred")
PROBE_TEMPLATE = "sae_sparse_dim_probe"


# ------------------------------------------------------------------ model
@dataclass
class SAE:
    W_enc: Any  # [d_sae, d]
    W_dec: Any  # [d, d_sae]
    b_enc: Any  # [d_sae]
    b_dec: Any  # [d]
    k: int = C.SAE_K
    variant: str = C.SAE_ENCODE_VARIANT
    path: str | None = None

    @property
    def d(self) -> int:
        return int(self.W_enc.shape[1])

    @property
    def d_sae(self) -> int:
        return int(self.W_enc.shape[0])

    def with_variant(self, variant: str) -> "SAE":
        if variant not in VARIANTS:
            raise ValueError(f"unknown encode variant {variant!r}; expected {VARIANTS}")
        return SAE(self.W_enc, self.W_dec, self.b_enc, self.b_dec, self.k, variant, self.path)


def load_sae(path: str | Path, k: int = C.SAE_K, variant: str = C.SAE_ENCODE_VARIANT, device: str = "cpu") -> SAE:
    """torch.load the checkpoint dict, validate keys and shapes, cast to fp32."""
    import torch

    obj = torch.load(str(path), map_location="cpu", weights_only=False)
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: expected a dict checkpoint, got {type(obj).__name__}")
    missing = [k_ for k_ in ("W_enc", "W_dec", "b_enc", "b_dec") if k_ not in obj]
    if missing:
        raise ValueError(f"{path}: missing keys {missing}; has {sorted(obj)}")
    W_enc, W_dec, b_enc, b_dec = (obj[k_].to(device=device, dtype=torch.float32) for k_ in ("W_enc", "W_dec", "b_enc", "b_dec"))
    d_sae, d = W_enc.shape
    if tuple(W_dec.shape) != (d, d_sae) or tuple(b_enc.shape) != (d_sae,) or tuple(b_dec.shape) != (d,):
        raise ValueError(f"{path}: inconsistent shapes W_enc {tuple(W_enc.shape)} W_dec {tuple(W_dec.shape)} "
                         f"b_enc {tuple(b_enc.shape)} b_dec {tuple(b_dec.shape)}")
    if variant not in VARIANTS:
        raise ValueError(f"unknown encode variant {variant!r}")
    return SAE(W_enc, W_dec, b_enc, b_dec, int(k), variant, str(path))


def sae_meta(sae: SAE) -> dict[str, Any]:
    return {"d": sae.d, "d_sae": sae.d_sae, "k": sae.k, "variant": sae.variant, "path": sae.path,
            "repo": C.SAE_REPO, "sha": C.SAE_SHA, "file": C.SAE_FILE, "base_model": C.SAE_BASE_MODEL, "hook": C.SAE_HOOK}


# ------------------------------------------------------------------ encode / decode
def pre_acts(sae: SAE, X: Any) -> Any:
    import torch

    X = torch.as_tensor(X).to(sae.W_enc.device, torch.float32)
    if sae.variant == "centred":
        X = X - sae.b_dec
    return X @ sae.W_enc.T + sae.b_enc


def encode_sparse(sae: SAE, X: Any, chunk: int = 256) -> Tuple[Any, Any]:
    """TopK codes as (idx [N, k] long, vals [N, k] float): the k largest pre-activations per row."""
    import torch

    X = torch.as_tensor(X)
    if X.ndim == 1:
        X = X[None]
    idxs, vals = [], []
    for s in range(0, X.shape[0], chunk):
        pa = pre_acts(sae, X[s: s + chunk])
        v, i = torch.topk(pa, sae.k, dim=-1)
        idxs.append(i)
        vals.append(v)
    return torch.cat(idxs), torch.cat(vals)


def to_dense(idx: Any, vals: Any, d_sae: int) -> Any:
    import torch

    z = torch.zeros(idx.shape[0], d_sae, dtype=vals.dtype, device=vals.device)
    z.scatter_(-1, idx, vals)
    return z


def encode(sae: SAE, X: Any) -> Any:
    """Dense codes [N, d_sae] with exactly k non-zeros per row."""
    idx, vals = encode_sparse(sae, X)
    return to_dense(idx, vals, sae.d_sae)


def decode(sae: SAE, z: Any, W_dec: Any = None) -> Any:
    W = sae.W_dec if W_dec is None else W_dec
    return z @ W.T + sae.b_dec


def decode_sparse(sae: SAE, idx: Any, vals: Any, W_dec: Any = None) -> Any:
    """x̂ from sparse codes without materialising [N, d_sae]: Σ_j vals[:, j] · W_dec[:, idx[:, j]] + b_dec."""
    import torch

    W = sae.W_dec if W_dec is None else W_dec
    cols = W.T[idx]  # [N, k, d]
    return torch.einsum("nk,nkd->nd", vals.to(cols.dtype), cols) + sae.b_dec


def fve(X: Any, X_hat: Any) -> float:
    """1 − ‖X − X̂‖²_F / ‖X − mean(X)‖²_F (1.0 for a perfect reconstruction; can be negative)."""
    import torch

    X = torch.as_tensor(X).float()
    X_hat = torch.as_tensor(X_hat).float()
    if X.ndim == 1:
        X, X_hat = X[None], X_hat[None]
    res = float(((X - X_hat) ** 2).sum())
    tot = float(((X - X.mean(0, keepdim=True)) ** 2).sum())
    return float("nan") if tot <= 0 else 1.0 - res / tot


def shuffled_decoder(sae: SAE, seed: int = C.SAE_NULL_SEED) -> Any:
    """W_dec with its columns (latents) permuted by ``seed``: the null dictionary."""
    import torch

    g = torch.Generator(device="cpu").manual_seed(int(seed))
    perm = torch.randperm(sae.d_sae, generator=g).to(sae.W_dec.device)
    return sae.W_dec[:, perm]


def fve_report(sae: SAE, X: Any, seed: int = C.SAE_NULL_SEED, chunk: int = 256) -> dict[str, Any]:
    """FVE of the SAE on ``X`` [N, d] and of the shuffled-decoder null decoding the same codes."""
    import torch

    X = torch.as_tensor(X).float()
    idx, vals = encode_sparse(sae, X, chunk=chunk)
    W_null = shuffled_decoder(sae, seed)
    rec, rec_null = [], []
    for s in range(0, X.shape[0], chunk):
        rec.append(decode_sparse(sae, idx[s: s + chunk], vals[s: s + chunk]))
        rec_null.append(decode_sparse(sae, idx[s: s + chunk], vals[s: s + chunk], W_dec=W_null))
    X_hat, X_null = torch.cat(rec), torch.cat(rec_null)
    cos = torch.nn.functional.cosine_similarity(X, X_hat, dim=-1)
    return {"n": int(X.shape[0]), "variant": sae.variant, "k": sae.k, "fve": fve(X, X_hat), "fve_null": fve(X, X_null),
            "null": "W_dec columns permuted (same codes)", "null_seed": int(seed),
            "mean_cos_x_xhat": float(cos.mean()), "median_cos_x_xhat": float(cos.median()),
            "mean_norm_x": float(X.norm(dim=-1).mean()), "mean_norm_xhat": float(X_hat.norm(dim=-1).mean()),
            "mean_rel_l2": float(((X - X_hat).norm(dim=-1) / X.norm(dim=-1).clamp_min(1e-9)).mean()),
            "n_negative_codes": int((vals < 0).sum()), "frac_negative_codes": float((vals < 0).float().mean())}


# ------------------------------------------------------------------ sparse diff-in-means probe
def mean_code(idx: Any, vals: Any, d_sae: int) -> Any:
    """Dense mean [d_sae] of sparse codes (rows of idx/vals)."""
    import torch

    if idx.shape[0] == 0:
        return torch.zeros(d_sae, dtype=vals.dtype, device=vals.device)
    acc = torch.zeros(d_sae, dtype=vals.dtype, device=vals.device)
    acc.index_add_(0, idx.reshape(-1), vals.reshape(-1))
    return acc / idx.shape[0]


def sparse_direction(u: Any, max_latents: int = C.SAE_PROBE_MAX_LATENTS) -> Tuple[Any, Any]:
    """Keep the ≤ max_latents latents with the largest |u| (non-zero only). Returns (latents [m], signs [m])."""
    import torch

    m = min(int(max_latents), int((u != 0).sum()))
    if m == 0:
        return torch.zeros(0, dtype=torch.long, device=u.device), torch.zeros(0, dtype=u.dtype, device=u.device)
    _, lat = torch.topk(u.abs(), m)
    return lat, torch.sign(u[lat])


def score_codes(idx: Any, vals: Any, latents: Any, signs: Any, d_sae: int) -> Any:
    """Σ_{l kept} sign_l · z_l per row (the sum of the signed codes); [N]."""
    import torch

    w = torch.zeros(d_sae, dtype=vals.dtype, device=vals.device)
    if latents.numel():
        w[latents] = signs.to(vals.dtype)
    return (w[idx] * vals).sum(-1)


@dataclass
class Codes:
    """Sparse codes of a set of items, by id."""
    idx: Any  # [N, k]
    vals: Any  # [N, k]
    ids: List[str]
    d_sae: int

    def __post_init__(self) -> None:
        self.row = {iid: i for i, iid in enumerate(self.ids)}

    def rows(self, ids: Sequence[str]) -> Tuple[Any, Any]:
        import torch

        sel = torch.tensor([self.row[i] for i in ids], dtype=torch.long, device=self.idx.device)
        return self.idx[sel], self.vals[sel]

    def mean(self, ids: Sequence[str]) -> Any:
        i, v = self.rows(ids)
        return mean_code(i, v, self.d_sae)

    def score(self, ids: Sequence[str], latents: Any, signs: Any) -> List[float]:
        i, v = self.rows(ids)
        return [float(x) for x in score_codes(i, v, latents, signs, self.d_sae)]


def codes_for(sae: SAE, states: Mapping[str, Any]) -> Codes:
    """Encode a {item_id: fp32 [d]} dict (order = sorted ids)."""
    import torch

    ids = sorted(states)
    if not ids:
        return Codes(torch.zeros(0, sae.k, dtype=torch.long), torch.zeros(0, sae.k), [], sae.d_sae)
    X = torch.stack([torch.as_tensor(states[i]).float() for i in ids])
    idx, vals = encode_sparse(sae, X)
    return Codes(idx, vals, ids, sae.d_sae)


def _probe_rec(latents: Any, signs: Any, u: Any, label: str) -> dict[str, Any]:
    return {"type": label, "latents": [int(x) for x in latents], "signs": [int(x) for x in signs],
            "u_kept": [round(float(u[l]), 5) for l in latents], "n_kept": int(latents.numel()), "template": PROBE_TEMPLATE}


# ------------------------------------------------------------------ X1 rows (within-pair)
def x1_probe_rows(pairs: Sequence[dict], codes: Codes, probe_type: str, pos_version, max_latents: int = C.SAE_PROBE_MAX_LATENTS,
                  reader: str = "sae") -> List[dict]:
    """One row per state of every pair (x1_lo.jsonl schema; condition natural), LOO by pair.
    binary: u = mean over training pairs of (z_pos − z_neg); lo(state) = ±score (+ for the pos version).
    identity: u = (mean z | answer a) − (mean z | answer b) over training states, (a, b) = the pair's candidates;
    lo(A) = score(A), lo(B) = −score(B); pairs whose candidate never occurs in training are unscorable."""
    out: List[dict] = []
    usable = [p for p in pairs if all(p[v]["item_id"] in codes.row for v in "AB")]
    for p in usable:
        train = [q for q in usable if q["pair_id"] != p["pair_id"]]
        a, b = p["A"]["primary"]["candidates"]
        rec: Optional[dict] = None
        lo: Dict[str, Optional[float]] = {"A": None, "B": None}
        reason = None
        if not train:
            reason = "no training pairs"
        elif probe_type == "binary":
            pos = [q[pos_version(q)]["item_id"] for q in train]
            neg = [q["B" if pos_version(q) == "A" else "A"]["item_id"] for q in train]
            u = codes.mean(pos) - codes.mean(neg)
            lat, sg = sparse_direction(u, max_latents)
            s = dict(zip("AB", codes.score([p["A"]["item_id"], p["B"]["item_id"]], lat, sg)))
            pv = pos_version(p)
            lo = {v: (s[v] if v == pv else -s[v]) for v in "AB"}
            rec = _probe_rec(lat, sg, u, "binary_diff_in_means")
        else:
            by_val: Dict[str, List[str]] = {}
            for q in train:
                for v in "AB":
                    by_val.setdefault(q[v]["primary"]["answer"], []).append(q[v]["item_id"])
            if not by_val.get(a) or not by_val.get(b):
                reason = f"candidate {'A' if not by_val.get(a) else 'B'} never an answer in the training pairs"
            else:
                u = codes.mean(by_val[a]) - codes.mean(by_val[b])
                lat, sg = sparse_direction(u, max_latents)
                s = dict(zip("AB", codes.score([p["A"]["item_id"], p["B"]["item_id"]], lat, sg)))
                lo = {"A": s["A"], "B": -s["B"]}
                rec = _probe_rec(lat, sg, u, "identity_class_means")
        for v in "AB":
            it = p[v]
            own = it["primary"]["answer"]
            other = [c for c in it["primary"]["candidates"] if c != own][0]
            out.append({"key": f"{reader}|{it['item_id']}", "module": "y3", "reader": reader, "item_id": it["item_id"], "pair_id": p["pair_id"],
                        "family": it["family"], "split": it["split"], "version": v, "condition": "natural", "cand_A": own, "cand_B": other,
                        "lo": lo[v], "lp_A": None, "lp_B": None, "templates": [PROBE_TEMPLATE], "unscorable": lo[v] is None,
                        **({"reason": reason} if reason else {}), **({"probe": rec} if rec else {}), "n_train_pairs": len(train)})
    return out


def x1_mean_row(family: str, pairs: Sequence[dict], codes: Codes, reader: str = "sae") -> dict:
    """E3 placeholder: the probe's score has no nat scale, so the ±1-nat band is not applicable (recorded as such)."""
    ids = [p[v]["item_id"] for p in pairs for v in "AB" if p[v]["item_id"] in codes.row]
    return {"key": f"{reader}|mean|{family}", "module": "y3", "reader": reader, "family": family, "condition": "mean_state",
            "n_states_in_mean": len(ids), "state_item_ids": ids, "per_pair": [], "n_scorable": 0, "mean_lo": None, "mean_abs_lo": None,
            "within_band": None, "templates": [PROBE_TEMPLATE], "note": "E3 not applicable: probe score is not in nats"}


# ------------------------------------------------------------------ X3 rows (favours actual)
def x3_probe_rows(items: Mapping[str, dict], codes: Codes, sets: Sequence[str], family: str, max_latents: int = C.SAE_PROBE_MAX_LATENTS,
                  reader: str = "sae") -> List[dict]:
    """LOO over the items of ``sets`` (one union). puzzle: identity over symbols (class means of the ACTUAL answer),
    u = d_actual − d_other, lo_actual = score. choice: binary label 'actual == first-listed option', midpoint
    threshold, lo_actual = ±(score − thr) oriented toward the actual answer (the E9 construct on codes)."""
    ids = sorted(i for i, it in items.items() if it["set"] in sets and it["family"] == family and i in codes.row)
    out: List[dict] = []
    for iid in ids:
        it = items[iid]
        actual, other = it["primary"]["candidates"]
        train = [j for j in ids if j != iid]
        lo_actual: Optional[float] = None
        rec = None
        reason = None
        if family == "puzzle":
            by_val: Dict[str, List[str]] = {}
            for j in train:
                by_val.setdefault(items[j]["primary"]["answer"], []).append(j)
            if not by_val.get(actual) or not by_val.get(other):
                reason = "actual or other symbol never the actual answer in the training items"
            else:
                u = codes.mean(by_val[actual]) - codes.mean(by_val[other])
                lat, sg = sparse_direction(u, max_latents)
                lo_actual = codes.score([iid], lat, sg)[0]
                rec = _probe_rec(lat, sg, u, "identity_class_means")
        else:
            def first(j: str) -> Optional[int]:
                fl = (items[j].get("source") or {}).get("first_listed")
                return None if fl is None else int(items[j]["primary"]["answer"] == fl)

            y = {j: first(j) for j in train}
            pos = [j for j in train if y[j] == 1]
            neg = [j for j in train if y[j] == 0]
            yi = first(iid)
            if yi is None or not pos or not neg:
                reason = "no first-listed label or a class is empty in the training items"
            else:
                mp, mn = codes.mean(pos), codes.mean(neg)
                u = mp - mn
                lat, sg = sparse_direction(u, max_latents)
                thr = float((sg * ((mp + mn) / 2)[lat]).sum()) if lat.numel() else 0.0
                s = codes.score([iid], lat, sg)[0] - thr
                lo_actual = s if yi == 1 else -s
                rec = _probe_rec(lat, sg, u, "binary_first_listed_midpoint")
        out.append({"key": f"{reader}|{iid}", "reader": reader, "item_id": iid, "family": family, "set": it["set"], "cand_actual": actual,
                    "cand_other": other, "text_key": it.get("text_key"), "lo_actual": lo_actual, "lp_actual": None, "lp_other": None,
                    "favours_actual": (lo_actual > 0) if lo_actual is not None else None, "templates": [PROBE_TEMPLATE],
                    "unscorable": lo_actual is None, "layer": C.LAYER, "format": "probe", **({"reason": reason} if reason else {}),
                    **({"probe": rec} if rec else {}), "n_train_items": len(train)})
    return out


# ------------------------------------------------------------------ X2 rows (read vectors)
def x2_probe_rows(beh_rows: Sequence[dict], readvec_codes: Codes, x1_pairs_by_family: Mapping[str, Sequence[dict]], x1_codes: Codes,
                  probe_type: Mapping[str, str], pos_version, max_latents: int = C.SAE_PROBE_MAX_LATENTS, reader: str = "sae") -> List[dict]:
    """lo_own / lo_toward_other for every behaviour row whose read vector is encoded: the direction is fitted on the
    X1 pairs of the entry's family EXCLUDING the entry's own pair (binary: ± by the source state's pos-ness;
    identity: u = d_candA − d_candB). x2_lo.jsonl schema."""
    out: List[dict] = []
    cache: Dict[Tuple[str, str, str, str], Any] = {}
    for b in beh_rows:
        if b["key"] not in readvec_codes.row:
            continue
        fam = b["family"]
        pairs = [p for p in x1_pairs_by_family.get(fam, []) if all(p[v]["item_id"] in x1_codes.row for v in "AB")]
        train = [p for p in pairs if p["pair_id"] != b["pair_id"]]
        own = [p for p in pairs if p["pair_id"] == b["pair_id"]]
        lo_own: Optional[float] = None
        reason = None
        rec = None
        if not train:
            reason = "no X1 training pairs for the family"
        elif probe_type.get(fam) == "binary":
            ck = (fam, b["pair_id"], "binary", "")
            if ck not in cache:
                pos = [q[pos_version(q)]["item_id"] for q in train]
                neg = [q["B" if pos_version(q) == "A" else "A"]["item_id"] for q in train]
                u = x1_codes.mean(pos) - x1_codes.mean(neg)
                cache[ck] = (u,) + sparse_direction(u, max_latents)
            u, lat, sg = cache[ck]
            s = readvec_codes.score([b["key"]], lat, sg)[0]
            if own:
                lo_own = s if pos_version(own[0]) == b["source"] else -s
            else:
                reason = "source pair not among the X1 pairs (orientation undefined)"
            rec = _probe_rec(lat, sg, u, "binary_diff_in_means")
        else:
            a, bb = b["cand_A"], b["cand_B"]
            ck = (fam, b["pair_id"], a, bb)
            if ck not in cache:
                by_val: Dict[str, List[str]] = {}
                for q in train:
                    for v in "AB":
                        by_val.setdefault(q[v]["primary"]["answer"], []).append(q[v]["item_id"])
                if by_val.get(a) and by_val.get(bb):
                    u = x1_codes.mean(by_val[a]) - x1_codes.mean(by_val[bb])
                    cache[ck] = (u,) + sparse_direction(u, max_latents)
                else:
                    cache[ck] = None
            if cache[ck] is None:
                reason = "a candidate never an answer in the training pairs"
            else:
                u, lat, sg = cache[ck]
                lo_own = readvec_codes.score([b["key"]], lat, sg)[0]
                rec = _probe_rec(lat, sg, u, "identity_class_means")
        row = {"key": f"{reader}|{b['key']}", "entry_key": b["key"], "reader": reader,
               **{k: b.get(k) for k in ("pair_id", "family", "source", "state_item_id", "site", "edit_layer", "positions_kind", "alpha",
                                         "condition", "null_k", "sign", "other_pair_id", "cand_A", "cand_B", "dose_abs", "lo_model",
                                         "flipped_to_other", "coherent")},
               "lo_own": lo_own, "lo_toward_other": (None if lo_own is None else -lo_own), "lp_A": None, "lp_B": None,
               "templates": [PROBE_TEMPLATE], "unscorable": lo_own is None, **({"reason": reason} if reason else {}),
               **({"probe": rec} if rec else {}), "n_train_pairs": len(train)}
        out.append(row)
    return out
