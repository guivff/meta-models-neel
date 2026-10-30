"""E130 CPU probes: project-owned port of Suraj exp24, source23d5a972."""
from dataclasses import dataclass
import numpy as np
import torch
from sklearn.metrics import roc_auc_score

@dataclass(frozen=True)
class LogReg:
    w: torch.Tensor  # [d] in standardised space
    b: float
    mu: torch.Tensor
    sd: torch.Tensor

    def decision(self, X: torch.Tensor) -> torch.Tensor:
        return ((X.float() - self.mu) / self.sd) @ self.w + self.b

    def direction(self) -> torch.Tensor:
        """Unit probe direction in raw activation space (w / sd)."""
        v = self.w / self.sd
        return v / v.norm()

def fit_logreg(X: torch.Tensor, y: torch.Tensor, lam: float = 1e-3, iters: int = 200) -> LogReg:
    X = X.float()
    mu, sd = X.mean(0), X.std(0).clamp_min(1e-4)
    Z = (X - mu) / sd
    yt = torch.as_tensor(y, dtype=torch.float32, device=X.device)
    w = torch.zeros(X.shape[1], device=X.device, requires_grad=True)
    b = torch.zeros(1, device=X.device, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], lr=1, max_iter=iters, history_size=20,
                            line_search_fn="strong_wolfe")

    def closure() -> torch.Tensor:
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b, yt) + lam * (w**2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    return LogReg(w.detach(), float(b.detach()), mu, sd)

def group_folds(groups: np.ndarray, k: int = 5, seed: int = 0) -> list[np.ndarray]:
    """k test-index arrays; each group lands in exactly one fold."""
    ug = np.unique(groups)
    rng = np.random.default_rng(seed)
    rng.shuffle(ug)
    return [np.flatnonzero(np.isin(groups, part)) for part in np.array_split(ug, k)]

FACTORS = ('addressed', 'genre')
BOOT_SEED = 20261031


def require(ok, message):
    if not ok:
        raise ValueError(message)


def score(model, x):
    x = np.asarray(x)
    require(x.ndim == 2 and x.shape[1] == len(model.w) and np.isfinite(x).all(), 'finite compatible CPU matrix')
    return model.decision(torch.as_tensor(x.copy(), dtype=torch.float32)).numpy()


def fit(x, y):
    x, y = np.asarray(x), np.asarray(y)
    require(x.ndim == 2 and len(x) == len(y) and np.isfinite(x).all() and set(y) == {0, 1}, 'finite matrix and both fixed classes')
    return fit_logreg(torch.as_tensor(x.copy(), dtype=torch.float32), torch.as_tensor(y))


def cv(x, y, groups):
    """Exact exp24 group_folds k5/seed0; fold-local sample standardization."""
    y, groups = np.asarray(y), np.asarray(groups)
    require(len(groups) == len(y) == len(x) and len(np.unique(groups)) >= 5, 'at least five original groups')
    pred = np.full(len(y), np.nan)
    folds = group_folds(groups, 5, 0)
    for te in folds:
        tr = np.setdiff1d(np.arange(len(y)), te)
        require(len(te) > 0 and set(y[tr]) == {0, 1}, 'nonempty fold and two-class training')
        pred[te] = score(fit(x[tr], y[tr]), x[te])
    require(np.isfinite(pred).all(), 'complete out-of-fold predictions')
    return pred, [te.tolist() for te in folds]


def summary(y, predictions, draws=2000, seed=BOOT_SEED):
    """Paired item bootstrap, fixed predictions; never refits or selects polarity."""
    y = np.asarray(y)
    p = {k: np.asarray(v) for k, v in predictions.items()}
    require(set(y) == {0, 1} and all(v.shape == y.shape and np.isfinite(v).all() for v in p.values()), 'complete binary scores')
    point = {k: float(roc_auc_score(y, v)) for k, v in p.items()}
    samples = {k: [] for k in p}; delta = []; invalid = 0
    rng = np.random.default_rng(seed)
    for _ in range(draws):
        ix = rng.integers(0, len(y), len(y))
        if len(np.unique(y[ix])) < 2:
            invalid += 1
            continue
        a = {k: float(roc_auc_score(y[ix], v[ix])) for k, v in p.items()}
        for k in p:
            samples[k].append(a[k])
        if 'intact' in p and 'shuffled' in p:
            delta.append(a['intact'] - a['shuffled'])
    def ci(v):
        return [float(z) for z in np.quantile(v, [.025, .975])] if v else None
    result = dict(scores={k: dict(AUROC=point[k], CI95=ci(samples[k])) for k in p},
                  bootstrap=dict(unit='item', draws=draws, seed=seed, undefined_single_class=invalid,
                                 valid=draws-invalid, paired_conditions=True, refits=0))
    if 'intact' in p and 'shuffled' in p:
        result['intact_minus_shuffle'] = dict(delta=point['intact']-point['shuffled'], CI95=ci(delta))
    return result


def reading(control, result):
    """§237 fixed addressed-positive interpretation; no E125 inference."""
    if control < .80:
        return 'UNINFORMATIVE_TRUE_SPAN_CONTROL_BELOW_0.80'
    v = result['scores']['intact']
    if v['AUROC'] >= .70 and v['CI95'] is not None and v['CI95'][0] > .60 and result['intact_minus_shuffle']['delta'] >= .10-1e-12:
        return 'CARRIED_IN_READOUT_ARRANGEMENT'
    if v['AUROC'] <= .60:
        return 'NOT_CARRIED_UNDER_E130_PROTOCOL'
    return 'INCONCLUSIVE'


def label_binding(order, labels):
    require(set(order) == {'dev', 'test'} and len(labels) == 600, 'original E85 roster')
    by = {r['public_id']: r for r in labels}
    require(len(by) == 600, 'unique original public IDs')
    result = {}; seen = []; splitgroups = {}; allgroups = {}
    for split, n in [('dev', 200), ('test', 400)]:
        ids = order[split]
        require(len(ids) == len(set(ids)) == n and set(ids) <= set(by), 'complete original ordered split')
        rows = [by[i] for i in ids]
        require(all(r['split'] == split and type(r['genre']) is int and type(r['addressed']) is int
                    and r['genre'] in (0, 1) and r['addressed'] in (0, 1) for r in rows), 'fixed original split/factors')
        result[split] = {f: np.array([r[f] for r in rows]) for f in FACTORS}
        # Keep original matched-set values: no recoding, random groups, or split-by-cell.
        result[split]['groups'] = np.array([r['matched_set'] for r in rows])
        splitgroups[split] = {r['matched_set'] for r in rows}
        seen += ids
        for r in rows:
            allgroups.setdefault(r['matched_set'], []).append(r)
    require(len(set(seen)) == 600 and set(seen) == set(by) and splitgroups['dev'].isdisjoint(splitgroups['test']), 'split-disjoint groups')
    require(len(splitgroups['dev']) == 50 and len(splitgroups['test']) == 100, '50 DEV/100 TEST matched quartets')
    require(all(len(v) == 4 and {(r['genre'], r['addressed']) for r in v} == {(0,0),(0,1),(1,0),(1,1)} for v in allgroups.values()), 'complete original matched quartets')
    return result
