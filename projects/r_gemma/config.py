"""Frozen constants for the Gemma stretch (BRIEF_RG.md §0, §2). Nothing here imports torch.

Verified against the HF API on 2026-10-18 (``HfApi.repo_info``): repo shas, the oracle's ``ao_config.json`` (special
token, prefix template, hook layer, activation layers 10/21/31), the Gemma Scope file layout (``params.npz`` per
``layer_L/width_W/average_l0_K``), gating (gemma-2-9b-it: manual; the SAE repos: open).
"""

from __future__ import annotations

from pathlib import Path

from projects.g_agreement.core import config as C

MODULE = "rg"

# ------------------------------------------------------------------ target (the oracle's own model; the SAE paper used its base)
TARGET_ID = "google/gemma-2-9b-it"
TARGET_SHA = "11c9b309abf73637e4b6f9a3fa1e92e615547819"   # HF API 2026-10-18 (gated: manual; the pod's HF_TOKEN must have access)
TARGET_DTYPE = "bfloat16"
ATTN_IMPL = "eager"           # Gemma-2 soft-caps attention logits; HF recommends eager
N_LAYERS = 42
D_MODEL = 3584
PAPER_MODEL_ID = "google/gemma-2-9b"   # Kantamneni et al.'s model (base); recorded, not loaded

# ------------------------------------------------------------------ the activation oracle (Karvonen et al., arXiv 2512.15674)
AO_REPO = "adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_gemma-2-9b-it"
AO_SHA = "44b5056006a4e14b9bb6fa99a98cf6e2bc86fcdf"       # HF API 2026-10-18; branch main only
AO_FILES = ["adapter_config.json", "adapter_model.safetensors", "ao_config.json", "README.md"]
AO_ADAPTER_NAME = "ao"
AO_SPECIAL = " ?"                                          # ao_config.json special_token; one token in the Gemma tokenizer (asserted)
AO_PREFIX = "Layer: {layer}\n{special} \n"                 # ao_config.json prefix_template with num_positions = 1
AO_HOOK_LAYER = 1                                          # ao_config.json hook_onto_layer: the OUTPUT of decoder block 1
AO_COEF = 1.0                                              # steering_coefficient of the repo's HF hook (add unit(v) * ||resid|| * coef)
AO_GRID = (10, 21, 31)                                     # ao_config.json act_layer_combinations (25 / 50 / 75 % of 42 blocks)
AO_FC_SUFFIX = ' Answer with exactly one of these two options and nothing else: "{pos}" or "{neg}".'
AO_YN_TEMPLATE = "Answer with 'Yes' or 'No' only. Is this statement about the text true: \"{statement}\"?"
AO_YES, AO_NO = "Yes", "No"

# ------------------------------------------------------------------ sites
LAYERS = (9, 10, 20, 21, 31, 41)          # captured: the paper's 9/20/31/41 + the oracle's 10/21/31 (block OUTPUT == resid_post)
SAE_LAYER = 20                            # the paper's site
AO_READ_LAYERS = {"chat": (21, 20, 10, 31), "raw": (21, 20)}   # BRIEF_RG §2.1: 21 on-grid primary, 20 the SAE site, 10/31 chat sweep
PRIMARY_LAYER = {"ao": 21, "ao_yn": 21, "logit_lens": 20, "probe": 20}
PRIMARY_RENDER = "chat"
RENDERS = ("chat", "raw")
MAX_TOKENS = 256                          # BRIEF_R's text truncation (the paper truncated at 1024 from the left; recorded)
CAPTURE_BATCH = 16
LO_BATCH = 32
SHUFFLE_SEED = 20261019
POOL_EVAL = 64                            # 32 per class: the quiver's labelled pool at the primary site
READERS = ("ao", "ao_yn")
POS_LAYERS = (10, 21, 31)                   # BRIEF_RG §11b: the oracle's grid (25 / 50 / 75 % depth)
ROT_SEEDS = tuple(range(10))                # BRIEF_RG §10: random orthogonal rotations of the block-20 state before the logit lens (E13 stand-in)

# ------------------------------------------------------------------ Gemma Scope SAEs (BRIEF_RG §2.1 table), all at block 20
GEMMA_SCOPE_PT = ("google/gemma-scope-9b-pt-res", "f9b689815814972562d28082f9f7d65d7e01fdc8")
GEMMA_SCOPE_IT = ("google/gemma-scope-9b-it-res", "e86af97a5b6fbbccca28ab654f2fda1b0768f770")
SAES = {
    "sae16": {"repo": GEMMA_SCOPE_PT[0], "sha": GEMMA_SCOPE_PT[1], "path": "layer_20/width_16k/average_l0_408",
              "role": "primary: the paper's fixed 16k SAE for scarcity / imbalance / noise / OOD", "lfs_sha256_prefix": "f2f96eedb5723180"},
    "sae131": {"repo": GEMMA_SCOPE_PT[0], "sha": GEMMA_SCOPE_PT[1], "path": "layer_20/width_131k/average_l0_276",
               "role": "the paper's fixed 131k SAE", "lfs_sha256_prefix": "7b2f522873b555e7"},
    "sae16c": {"repo": GEMMA_SCOPE_PT[0], "sha": GEMMA_SCOPE_PT[1], "path": "layer_20/width_16k/average_l0_68",
               "role": "SAELens canonical 16k", "lfs_sha256_prefix": "e429c4f6a3a65971"},
    "sae16it": {"repo": GEMMA_SCOPE_IT[0], "sha": GEMMA_SCOPE_IT[1], "path": "layer_20/width_16k/average_l0_189",
                "role": "IT-model SAE by the paper's rule (largest L0 at 16k)", "lfs_sha256_prefix": "192266adca5ee46d"},
}
SAE_PRIMARY = "sae16"
SAE_KS = (16, 128)
SAE_C_GRID = tuple(float(c) for c in (1e5, 7.74e3, 5.99e2, 4.64e1, 3.59, 2.78e-1, 2.15e-2, 1.67e-3, 1.29e-4, 1e-5))  # logspace(5, -5, 10)
SAE_FVE_FLAG = 0.3                        # BRIEF_RG §7.4: an SAE below this FVE is flagged (still run)

# ------------------------------------------------------------------ paths
RG_DIR = C.CACHE_DIR / "rg"
RESULTS = C.RESULTS_DIR / "rg"
LOG = RESULTS / "log.md"
FROZEN_RG = C.MANIFEST_DIR / "frozen_config_rg.json"
HERE = Path(__file__).resolve().parent


def rg_code_files() -> list[Path]:
    return sorted(p for p in HERE.glob("*.py") if p.exists())
