"""Shared core of the G-experiments: frozen config, model loading/capture, state cache, readers
(jlens / olens / nla with wsbench semantics), generation with budgets, and compute accounting.
``scoring.py`` (claim extraction) is owned by the analysis track.

Import as ``from projects.g_agreement.core import config, model, states, readers, generate,
accounting`` with the repo root on ``PYTHONPATH``. Everything here is import-clean on a CPU-only
machine; GPU work happens only inside functions."""

from . import accounting, config  # noqa: F401  (torch-free)

__all__ = ["accounting", "config", "generate", "model", "readers", "states"]
