"""CPU-only analyses for exploratory E3/E4 (BRIEF_UNDERSTAND §§90–91).

Callers must verify the label-free capture seal before calling the labelled E3
functions. This module never reads a label file, chooses rows, or changes score
orientation. All paths/classes/row IDs are supplied from frozen W1 inputs.
"""
from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping, Sequence

import numpy as np

import common  # Make the pinned mats library importable, without network access.
from mats.metrics import auroc_labels, cluster_bootstrap

SEED = 20261024


def _matrix(x, name):
    x = np.asarray(x)
    if x.ndim != 2 or min(x.shape) == 0 or not np.isfinite(x).all():
        raise ValueError(f"{name} must be a nonempty finite matrix")
    return x


def _labels_groups(labels, groups, n):
    y, g = np.asarray(labels), np.asarray(groups)
    if y.ndim != 1 or g.ndim != 1 or len(y) != n or len(g) != n:
        raise ValueError("labels/groups must match the item axis")
    if set(y.tolist()) != {0, 1}:
        raise ValueError("labels must contain both 0 and 1; value A is 1")
    if any(v is None or str(v) == "" for v in g.tolist()):
        raise ValueError("every item must have a template cluster")
    return y.astype(int), g


def _ci(values, groups=None, *, n_boot=2000, seed=SEED):
    values = np.asarray(values, dtype=np.float64)
    if not len(values) or n_boot == 0:
        return None
    clusters = np.arange(len(values)) if groups is None else np.asarray(groups)
    if clusters.ndim != 1 or len(clusters) != len(values):
        raise ValueError("bootstrap groups must match items")
    return list(map(float, cluster_bootstrap(lambda i: float(values[i].mean()),
                                            clusters, n_boot=n_boot, seed=seed)))


def grouped_cv_probe(x, labels, groups, *, n_splits=5, seed=SEED, lam=1e-3,
                     n_boot=0):
    """W1's logistic fitter, on five disjoint template-grouped folds.

    Standardisation is fitted inside ``fit_logreg`` on each training fold only.
    The fixed score is the A-positive decision function, including below-chance
    results. CIs, if requested, resample clusters over fixed OOF predictions.
    """
    import torch
    from mats.probes import fit_logreg, group_folds

    x = _matrix(x, "residuals")
    y, g = _labels_groups(labels, groups, len(x))
    if n_splits < 2 or len(np.unique(g)) < n_splits:
        raise ValueError("need at least n_splits distinct template clusters")
    xt = torch.as_tensor(np.array(x, dtype=np.float32, copy=True), device="cpu")
    scores = np.full(len(y), np.nan)
    assignment = np.full(len(y), -1, dtype=int)
    folds = []
    for fold, test in enumerate(group_folds(g, k=n_splits, seed=seed)):
        train = np.setdiff1d(np.arange(len(y)), test)
        if set(y[train]) != {0, 1} or set(y[test]) != {0, 1}:
            raise ValueError("one-class train/test fold; do not silently change the grouping")
        if set(g[train]) & set(g[test]):
            raise AssertionError("template leakage")
        model = fit_logreg(xt[train], torch.as_tensor(y[train]), lam=lam)
        prediction = model.decision(xt[test]).detach().cpu().numpy()
        if not np.isfinite(prediction).all():
            raise ValueError("nonfinite held-out logistic score")
        scores[test] = prediction
        assignment[test] = fold
        folds.append({"fold": fold, "train_indices": train.tolist(), "test_indices": test.tolist(),
                      "train_clusters": sorted(set(g[train].tolist())),
                      "test_clusters": sorted(set(g[test].tolist())),
                      "n_train": len(train), "n_test": len(test)})
    if np.any(assignment < 0) or not np.isfinite(scores).all():
        raise AssertionError("incomplete held-out coverage")
    interval = None
    if n_boot:
        interval = list(map(float, cluster_bootstrap(
            lambda i: auroc_labels(scores[i], y[i]), g, n_boot=n_boot, seed=seed)))
    return {"auroc": float(auroc_labels(scores, y)), "ci95": interval,
            "n": len(y), "n_A": int(y.sum()), "n_B": int((1-y).sum()),
            "n_clusters": len(np.unique(g)), "n_splits": n_splits,
            "seed": seed, "lambda": lam, "positive_label": "value_A",
            "orientation_flipped": False, "standardisation": "training_fold_only",
            "oof_scores": scores.tolist(), "fold_assignment": assignment.tolist(), "folds": folds}


def analyze_e3_cell(residuals, labels, groups, *, reader, row, row_class,
                    layers=None, positions=("injection", "preanswer"),
                    asked_auroc=None, expected_n=168, n_splits=5, seed=SEED,
                    n_boot=0):
    """Analyze [items,layers,positions,hidden] capture; retain every cell.

    The side-by-side W1 asked AUROC is a descriptive test-only comparator,
    whereas the internal probe CV uses dev+test. No paired difference CI is
    manufactured for those distinct estimands.
    """
    h = np.asarray(residuals)
    if h.ndim != 4 or len(h) != expected_n:
        raise ValueError(f"need [{expected_n},layers,positions,hidden] residuals")
    layers = list(range(h.shape[1])) if layers is None else list(layers)
    if len(layers) != h.shape[1] or len(positions) != h.shape[2]:
        raise ValueError("layer/position metadata does not match capture")
    if len(set(layers)) != len(layers) or len(set(positions)) != len(positions):
        raise ValueError("duplicate layer or position")
    if asked_auroc is not None and not 0 <= asked_auroc <= 1:
        raise ValueError("invalid W1 asked AUROC")
    _labels_groups(labels, groups, len(h))
    result = []
    for layer_i, layer in enumerate(layers):
        for position_i, position in enumerate(positions):
            cell = {"reader": reader, "row": row, "class": row_class,
                    "layer": layer, "position": position,
                    "w1_asked_auroc": asked_auroc,
                    "probe_population": "W1 dev+test", "asked_population": "W1 test"}
            try:
                cell.update(grouped_cv_probe(h[:, layer_i, position_i, :], labels, groups,
                            n_splits=n_splits, seed=seed, n_boot=n_boot))
                cell["status"] = "COMPLETE"
            except (ValueError, RuntimeError) as error:
                # A failed cell stays in the result grid and appears masked in the plot.
                cell.update(status="NOT_EVALUABLE", reason=str(error), auroc=None)
            result.append(cell)
    return result


def random_unit_directions(d, n=200, *, seed=SEED):
    if d < 1 or n < 1:
        raise ValueError("positive direction dimension/count required")
    z = np.random.default_rng(seed).normal(size=(n, d))
    return z / np.linalg.norm(z, axis=1, keepdims=True)


def summarize_gradients(gradients, direction, *, groups=None, seed=SEED,
                        n_random=200, n_boot=2000):
    """Per-row gradient alignment and matched isotropic-direction baseline.

    Exactly-zero gradients contribute zero to both reported means; their cosine
    is mathematically undefined, so the count and nonzero-only mean are also
    supplied. The baseline holds the *same* 200 seeded random directions across
    items and reports their dispersion as well as a paired item/cluster CI.
    """
    g = np.asarray(_matrix(gradients, "gradients"), dtype=np.float64)
    u = np.asarray(direction, dtype=np.float64)
    if u.shape != (g.shape[1],) or not np.isfinite(u).all() or np.linalg.norm(u) == 0:
        raise ValueError("direction must be finite, nonzero and match gradient width")
    u = u / np.linalg.norm(u)
    norms = np.linalg.norm(g, axis=1)
    normalized = np.divide(g, norms[:, None], out=np.zeros_like(g), where=norms[:, None] != 0)
    align = np.abs(normalized @ u)
    random = random_unit_directions(g.shape[1], n_random, seed=seed)
    baseline_matrix = np.abs(normalized @ random.T)
    baseline_per_item = baseline_matrix.mean(axis=1)
    baseline_per_direction = baseline_matrix.mean(axis=0)
    nonzero = norms > 0
    return {"n": len(g), "hidden_size": g.shape[1], "zero_gradient_n": int((~nonzero).sum()),
            "zero_gradient_convention": "zero in both means; cosine undefined; nonzero-only mean also reported",
            "mean_abs_cos": float(align.mean()),
            "mean_abs_cos_nonzero": float(align[nonzero].mean()) if nonzero.any() else None,
            "mean_abs_cos_ci95": _ci(align, groups, n_boot=n_boot, seed=seed),
            "random_mean_abs_cos": float(baseline_per_item.mean()),
            "random_mean_abs_cos_ci95": _ci(baseline_per_item, groups, n_boot=n_boot, seed=seed),
            "alignment_minus_random": float((align-baseline_per_item).mean()),
            "alignment_minus_random_ci95": _ci(align-baseline_per_item, groups, n_boot=n_boot, seed=seed),
            "random_direction_mean_interval95": np.quantile(baseline_per_direction, [.025, .975]).tolist(),
            "random_direction_means": baseline_per_direction.tolist(), "random_directions": n_random,
            "seed": seed, "bootstrap_unit": "template_cluster" if groups is not None else "item",
            "gradient_norm_mean": float(norms.mean()), "gradient_norm_max": float(norms.max()),
            "item_abs_cos": align.tolist(), "item_random_mean_abs_cos": baseline_per_item.tolist(),
            "item_gradient_norm": norms.tolist()}


def receptive_subspace(gradients, directions: Mapping[str, np.ndarray], *,
                        ks=(16, 64, 256), seed=SEED, n_random=200, basis_out=None):
    """Exact *uncentered*, unnormalised pooled-gradient SVD, in raw input space.

    Do not complete a deficient matrix with arbitrary null-space singular
    vectors. For requested k beyond its numerical rank, report effective k and
    project only onto the available gradient span. Directions are normalised;
    gradient magnitudes are deliberately preserved.
    """
    raw = _matrix(gradients, "pooled gradients")
    dtype_eps = np.finfo(raw.dtype).eps if np.issubdtype(raw.dtype, np.floating) else np.finfo(float).eps
    g = np.asarray(raw, dtype=np.float64)
    ks = tuple(ks)
    if not ks or any(not isinstance(k, (int, np.integer)) or k < 1 for k in ks):
        raise ValueError("k must contain positive integers")
    if len(set(ks)) != len(ks):
        raise ValueError("duplicate k")
    if not directions:
        raise ValueError("at least one probe direction required")
    named = []
    for name, direction in directions.items():
        u = np.asarray(direction, dtype=np.float64)
        if u.shape != (g.shape[1],) or not np.isfinite(u).all() or np.linalg.norm(u) == 0:
            raise ValueError(f"invalid direction for {name}")
        named.append((name, u/np.linalg.norm(u)))
    _, singular, vt = np.linalg.svd(g, full_matrices=False)
    tolerance = float(max(g.shape)*dtype_eps*singular[0]) if len(singular) else 0.0
    rank = int(np.count_nonzero(singular > tolerance))
    if basis_out is not None:
        path = Path(basis_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError("refusing to replace existing receptive basis")
        with path.open("xb") as handle:
            np.savez_compressed(handle, right_singular_vectors=vt[:min(max(ks), rank)].astype(np.float32),
                                singular_values=singular, numerical_rank=rank, rank_tolerance=tolerance)
    random = random_unit_directions(g.shape[1], n_random, seed=seed)
    rows = []
    for k in ks:
        effective = min(k, rank)
        basis = vt[:effective]
        random_fraction = np.sum((random @ basis.T)**2, axis=1)
        for name, u in named:
            fraction = float(np.clip(np.sum((basis @ u)**2), 0, 1))
            rows.append({"row": name, "k_requested": int(k), "k_effective": effective,
                         "rank_limited": effective < k, "fraction_inside": fraction,
                         "random_mean_fraction": float(random_fraction.mean()),
                         "random_fraction_interval95": np.quantile(random_fraction, [.025, .975]).tolist(),
                         "isotropic_expected_fraction": effective/g.shape[1]})
    return {"n_gradients": len(g), "hidden_size": g.shape[1], "centered": False,
            "gradients_normalized": False, "svd": "exact_numpy_float64",
            "numerical_rank": rank, "rank_tolerance": tolerance,
            "basis_file": str(basis_out) if basis_out is not None else None,
            "rank_tolerance_epsilon": float(dtype_eps),
            "zero_gradient_n": int(np.count_nonzero(np.linalg.norm(g, axis=1) == 0)),
            "singular_values": singular.tolist(), "seed": seed,
            "random_directions": n_random, "rows": rows}


def plot_e3(cells: Sequence[dict], out_dir):
    """Per-reader layer×row heatmaps for both sites and class summary curves.

    Missing/failed cells remain grey; a separate W1 asked column uses the same
    fixed 0–1 colour scale. Curves average rows equally within frozen classes.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for reader in sorted({c["reader"] for c in cells}):
        reader_cells = [c for c in cells if c["reader"] == reader]
        rows = sorted({(c["class"], c["row"]) for c in reader_cells})
        layers = sorted({c["layer"] for c in reader_cells}, key=lambda x: (isinstance(x,str),x))
        positions = sorted({c["position"] for c in reader_cells})
        for position in positions:
            subset = [c for c in reader_cells if c["position"] == position]
            keyed = {(c["row"], c["layer"]): c for c in subset}
            if len(keyed) != len(subset):
                raise ValueError("duplicate E3 result cell")
            values = np.full((len(rows),len(layers)), np.nan)
            asked = np.full((len(rows),1),np.nan)
            for r, (_, row) in enumerate(rows):
                for l, layer in enumerate(layers):
                    cell = keyed.get((row,layer), {})
                    value = cell.get("auroc")
                    if value is not None:
                        values[r,l] = value
                    if cell.get("w1_asked_auroc") is not None:
                        asked[r,0] = cell["w1_asked_auroc"]
            fig, axes = plt.subplots(1,2,figsize=(max(8,len(layers)*.17), max(4,len(rows)*.26)),
                                     gridspec_kw={"width_ratios":[max(3,len(layers)),2]}, sharey=True)
            cmap = plt.get_cmap("viridis").with_extremes(bad="#c9c9c9")
            image = axes[0].imshow(np.ma.masked_invalid(values),aspect="auto",vmin=0,vmax=1,cmap=cmap)
            axes[1].imshow(np.ma.masked_invalid(asked),aspect="auto",vmin=0,vmax=1,cmap=cmap)
            axes[0].set_yticks(range(len(rows)),[f"{row} [{cls}]" for cls,row in rows],fontsize=7)
            tick = np.unique(np.linspace(0,len(layers)-1,min(12,len(layers))).astype(int))
            axes[0].set_xticks(tick,[str(layers[i]) for i in tick],rotation=45,fontsize=7)
            axes[0].set_xlabel("Reader layer / native stage")
            axes[1].set_xticks([0],["W1 asked\n(test only)"],fontsize=8)
            fig.suptitle(f"E3 exploratory · {reader} · {position}\nGrouped-CV probe AUROC (dev + test; A positive)")
            fig.colorbar(image,ax=axes.tolist(),label="AUROC",fraction=.025,pad=.02)
            path = out/f"{reader}_{position}_heatmap.png"
            fig.savefig(path,dpi=170,bbox_inches="tight"); plt.close(fig); files.append(str(path))
            fig,ax=plt.subplots(figsize=(8,4))
            for cls in sorted({cls for cls,_ in rows}):
                indices=[i for i,(c,_) in enumerate(rows) if c==cls]
                means=[]
                for j in range(len(layers)):
                    valid=values[indices,j]; valid=valid[np.isfinite(valid)]
                    means.append(float(valid.mean()) if len(valid) else np.nan)
                line,=ax.plot(range(len(layers)),means,label=f"{cls} probe")
                comparator=asked[indices,0]; comparator=comparator[np.isfinite(comparator)]
                if len(comparator):
                    ax.axhline(comparator.mean(),color=line.get_color(),linestyle=":",alpha=.8,
                               label=f"{cls} W1 asked (test)")
            ax.axhline(.5,color="grey",linestyle="--",linewidth=1)
            ax.set(ylim=(0,1.03),ylabel="Mean row AUROC",xlabel="Reader layer / native stage",
                   title=f"E3 exploratory · {reader} · {position}")
            ax.set_xticks(tick,[str(layers[i]) for i in tick],rotation=45,fontsize=7)
            ax.legend(fontsize=7); fig.tight_layout()
            path=out/f"{reader}_{position}_class_curves.png"
            fig.savefig(path,dpi=170);plt.close(fig);files.append(str(path))
    return files
