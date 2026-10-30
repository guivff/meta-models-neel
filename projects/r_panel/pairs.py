"""Pinned (target, oracle) pairs of the standard-reader panel (BRIEF_RP §1, §3.2, §13). Nothing here imports torch.

Every value was read from the HF API / the repos' ``ao_config.json`` on 2026-10-19 (BRIEF_RP §1 table) and from the training
code (adamkarvonen/activation_oracles ``main``; Bauer et al.'s multi-layer prefix from ceselder/cot-oracle @ 5208ece,
``AObench/utils/dataset_utils.get_introspection_prefix``: one ``"Layer: {L}\\n ?" + " \\n"`` block per layer).
"""

from __future__ import annotations

from typing import Any

QWEN3_8B = ("Qwen/Qwen3-8B", "b968826d9c46dd6066d109eabc6255188de91218")
QWEN3_32B = ("Qwen/Qwen3-32B", "9216db5781bf21249d130ec9da846c4624c16137")
QWEN36_27B = ("Qwen/Qwen3.6-27B", "6a9e13bd6fc8f0983b9b99948120bc37f49c13e9")

Q8B_LAYERS = (21, 22, 23, 24, 25)
Q8B_VIRTUAL = 2125          # the layer id under which Q8B's five-block read is keyed (no such block; ≥ N_LAYERS)

PAIRS: dict[str, dict[str, Any]] = {
    "Q8": {
        "target": QWEN3_8B, "n_layers": 36, "d_model": 4096,
        "ao": ("adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3-8B", "6e3c7e9d7157f1b09b1915175eb23a4a88830c08"),
        "ao_model_name": "Qwen/Qwen3-8B", "grid": (9, 18, 27), "primary": 18,
        # captured: the grid, Q8B's 21–25 (same target), the last block
        "layers": (9, 18, 21, 22, 23, 24, 25, 27, 35),
        "ao_read": {"chat": (18, 9, 27), "raw": (18,)},
        "pos_layers": (9, 18, 21, 22, 23, 24, 25, 27),      # captured once for Q8 and Q8B
        "pos_ao": (9, 18, 27), "pos_probe": (9, 18, 23, 27),   # Q8's AO on its grid; probes on the grid + Q8B's probe block
        "probe": 18, "states_from": None,
    },
    "Q8B": {
        "target": QWEN3_8B, "n_layers": 36, "d_model": 4096,
        "ao": ("ceselder/qwen3-8b-ao-v3-best", "a7344ac8f21ed848c9f0593893e94137c4cb38cb"),
        "ao_model_name": "Qwen/Qwen3-8B", "grid": Q8B_LAYERS, "primary": Q8B_VIRTUAL, "multi": Q8B_LAYERS,
        "layers": (9, 18, 21, 22, 23, 24, 25, 27, 35),
        "ao_read": {"chat": (Q8B_VIRTUAL,), "raw": (Q8B_VIRTUAL,)},
        "pos_layers": (Q8B_VIRTUAL,),
        "probe": 23, "states_from": "Q8",
    },
    "Q32": {
        "target": QWEN3_32B, "n_layers": 64, "d_model": 5120,
        "ao": ("adamkarvonen/checkpoints_cls_latentqa_past_lens_Qwen3-32B", "08c733f35a12ab245f30192878eb9050736865f7"),
        "ao_model_name": "Qwen/Qwen3-32B", "grid": (16, 32, 48), "primary": 32,
        "layers": (16, 32, 48, 63),
        "ao_read": {"chat": (32, 16, 48), "raw": (32,)},
        "pos_layers": (16, 32, 48),
        "probe": 32, "states_from": None,
    },
    "Q27": {
        "target": QWEN36_27B, "n_layers": 64, "d_model": 5120,
        "ao": ("adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B", "891bef83dfd5dd5d01bf1f4dc6bed99f68ad6743"),
        "ao_model_name": "Qwen/Qwen3.6-27B", "grid": (16, 32, 48), "primary": 32,
        "layers": (16, 32, 48),
        "ao_read": {"chat": (32, 16, 48), "raw": (32,)},
        "pos_layers": (16, 32, 48),
        "probe": 32, "states_from": None,
    },
}

AO_FILES = ["adapter_config.json", "adapter_model.safetensors", "ao_config.json", "README.md"]


def multi_prefix(layers: tuple[int, ...], special: str = " ?") -> str:
    """Bauer et al.'s ``get_introspection_prefix(layers, 1)`` with the "Layer: {layer}" template."""
    return "".join(f"Layer: {L}\n{special} \n" for L in layers)


def multi_noact_prefix(layers: tuple[int, ...], text: str) -> str:
    """Text-only arm for a multi-layer oracle (BRIEF_RP §12, 2026-10-19 implementation note): the layer lines, then the
    text once where the slot block would start."""
    return "".join(f"Layer: {L}\n" for L in layers) + f"{text} \n"
