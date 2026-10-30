"""E58b projection primitives; no labels, row metadata or CPU join."""
import numpy as np
from common58 import require


def check_basis(q, dim=5120, rank=384):
    q = np.asarray(q)
    require(q.shape == (dim, rank) and np.isfinite(q).all(), 'Wrong or nonfinite basis')
    error = float(np.max(np.abs(q.astype(np.float64).T @ q.astype(np.float64) - np.eye(rank))))
    require(error < 1e-5, 'Basis is not orthonormal')
    return error


def random_basis(seed, dim=5120, rank=384):
    # Haar subspaces from an explicitly seeded, independent Gaussian QR.
    q, r = np.linalg.qr(np.random.default_rng(seed).standard_normal((dim, rank)), mode='reduced')
    q *= np.where(np.diag(r) < 0, -1., 1.)
    q = q.astype(np.float32)
    check_basis(q, dim, rank)
    return q


def projection_hook(q, prompt_lengths, prompt_starts=None):
    """Block output only; candidate and padding positions stay byte-identical."""
    import torch
    lengths = torch.as_tensor(prompt_lengths, device=q.device)
    starts = torch.zeros_like(lengths) if prompt_starts is None else torch.as_tensor(prompt_starts, device=q.device)
    require(lengths.ndim == 1 and bool((lengths > 0).all()), 'Positive prompt lengths required')
    require(starts.shape == lengths.shape and bool((starts >= 0).all()), 'Valid prompt starts required')

    def hook(_module, _inputs, output):
        h = output[0] if isinstance(output, tuple) else output
        require(h.ndim == 3 and h.shape[0] == len(lengths) and h.shape[2] == q.shape[0],
                'Projection hook shape mismatch')
        positions = torch.arange(h.shape[1], device=h.device)[None, :]
        mask = (positions >= starts[:, None]) & (positions < (starts + lengths)[:, None])
        raw = h.float()
        edited = (raw - (raw @ q) @ q.T).to(h.dtype)
        value = torch.where(mask[:, :, None], edited, h)
        return (value,) + output[1:] if isinstance(output, tuple) else value
    return hook


class PCAMoments:
    def __init__(self, dim=5120, device='cuda'):
        import torch
        self.n = 0
        self.sum = torch.zeros(dim, dtype=torch.float64, device=device)
        self.cross = torch.zeros((dim, dim), dtype=torch.float64, device=device)

    def add(self, vectors):
        import torch
        x = vectors.detach().to(device=self.sum.device, dtype=torch.float64)
        require(x.ndim == 2 and x.shape[1] == len(self.sum) and bool(torch.isfinite(x).all()),
                'Finite raw dev activation matrix required')
        self.n += len(x)
        self.sum += x.sum(0)
        self.cross += x.T @ x

    def basis(self, rank=384):
        import torch
        require(self.n > rank, 'Insufficient dev samples for registered PCA rank; no padding')
        covariance = self.cross - self.sum[:, None] @ self.sum[None, :] / self.n
        covariance = (covariance + covariance.T) / 2
        eigenvalues, vectors = torch.linalg.eigh(covariance)
        require(float(eigenvalues[-rank]) > max(1e-10, float(eigenvalues[-1]) * 1e-12),
                'Dev PCA has insufficient numerical rank; no random completion')
        q = vectors[:, -rank:].flip(1).float()
        return q, eigenvalues[-rank:].flip(0).cpu().tolist()


