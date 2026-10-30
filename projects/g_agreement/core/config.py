"""Frozen constants for the G-experiments (G1–G4): asset ids and revisions, capture site,
sampling, caps, seeds, paths, the prompt-only template, and the freeze/guard logic of
INTERFACES §8. Nothing in here depends on torch; it is importable on the Mac.

Usage::

    from projects.g_agreement.core import config as C
    C.TARGET_MODEL_ID, C.LAYER, C.stable_seed("g1", "nla", "own-03A", 0)

``python -m projects.g_agreement.core.config --freeze`` writes ``manifest/frozen_config.json``;
``require_frozen("test")`` is what the collectors call before touching test items.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------ paths
HERE = Path(__file__).resolve().parent  # projects/g_agreement/core
PROJECT_DIR = HERE.parent  # projects/g_agreement
REPO_ROOT = PROJECT_DIR.parents[1]  # repo root: activation-readers (Mac) or /workspace/activation-readers (pod)
CACHE_DIR = REPO_ROOT / "cache" / "g_agreement"
STATES_DIR = CACHE_DIR / "states"
STATES_META = CACHE_DIR / "states_meta.jsonl"
GENS_DIR = CACHE_DIR / "gens"
BENCH_DIR = CACHE_DIR / "bench"
RESULTS_DIR = REPO_ROOT / "results" / "g_agreement"
COMPUTE_LEDGER = RESULTS_DIR / "compute.jsonl"
REPRO_DIR = RESULTS_DIR / "repro"
MANIFEST_DIR = PROJECT_DIR / "manifest"
FROZEN_CONFIG = MANIFEST_DIR / "frozen_config.json"
FROZEN_CONFIG_COLLECTION = MANIFEST_DIR / "frozen_config_collection.json"  # the collection-time freeze
FROZEN_CANDIDATES = (FROZEN_CONFIG, FROZEN_CONFIG_COLLECTION)
ASSETS_JSON = MANIFEST_DIR / "assets.json"
DATASET_DIR = PROJECT_DIR / "dataset"
ITEMS_JSON = DATASET_DIR / "items.json"
RUBRIC_MD = DATASET_DIR / "rubric.md"
DONORS_JSON = DATASET_DIR / "donors.json"
G4_PAIRS_JSON = DATASET_DIR / "g4_pairs.json"
THIRD_PARTY = REPO_ROOT / "third_party"
G_ASSETS_DIR = REPO_ROOT / "cache" / "g_assets"  # metadata-only mirror downloaded on the Mac

# third-party sources importable without installation (wsbench, jlens, nla)
THIRD_PARTY_SRC = [
    THIRD_PARTY / "workspace-bench" / "src",
    THIRD_PARTY / "jacobian-lens",
    THIRD_PARTY / "EasyNLA",
]


def add_third_party_to_path() -> None:
    for p in THIRD_PARTY_SRC:
        s = str(p)
        if p.is_dir() and s not in sys.path:
            sys.path.append(s)


# ------------------------------------------------------------------ target model and site
TARGET_MODEL_ID = "Qwen/Qwen3.6-27B"
TARGET_MODEL_SHA = "6a9e13bd6fc8f0983b9b99948120bc37f49c13e9"  # HF API verified 2026-10-07
TARGET_DTYPE = "bfloat16"
D_MODEL = 5120
N_LAYERS = 64
LAYER = 42  # decoder block index whose OUTPUT is captured (== hidden_states[43])
HOOK = "block_output"
HIDDEN_STATES_INDEX = LAYER + 1
DEV_EXTRA_LAYERS = (40, 44)  # dev items only: OLens off-grid sensitivity (on-grid neighbours of 42)
STATE_FREE_SAMPLES = 8  # state_free condition: mean dev activation, sample_idx 0..7 per verbalizer
JLENS_NULL_N = 20  # jlens_null: Gaussian vectors at the median dev-state norm (+ the mean vector)
JLENS_NULL_SEED = 20261007
ENABLE_THINKING = False  # chat render ends with "<think>\n\n</think>\n\n" (assistant onset)
RENDER = "chat"
CAPTURE_DTYPE = "bfloat16"
SAVE_DTYPE = "float32"

# ------------------------------------------------------------------ readers (assets)
JLENS_REPO = "neuronpedia/jacobian-lens"
JLENS_SHA = "b25d72a96b79c8e309d6625955a98751da47e67a"  # HF API HEAD 2026-10-07
JLENS_FILE = "qwen3.6-27b/jlens/Salesforce-wikitext/Qwen3.6-27B_jacobian_lens_n1000.pt"
JLENS_FILE_SHA256 = "1718c8c52dd8a9dad03738d4d625937c1fbba10be325b872ed446c7290fc11e1"
JLENS_TOP_K = 10

OLENS_REPO = "agu18dec/olens_and_ar"  # model repo (used here)
OLENS_SHA = "c95215d5d2f6250f20c305ae55c6e4d7569f92dc"  # HF API HEAD 2026-10-07
OLENS_SUBFOLDER = "olens_s3d_rl600"
OLENS_ADAPTER_SHA256 = "7d4b301e002246af3c3f2bb6e768f8fa62f8aac2c231a0bd02a8d4f9ecafd9aa"
OLENS_WSBENCH_LORA = (  # the dataset-repo path wsbench's OLens method uses by default
    "agu18dec/local-workspace:ckpts/ao/rl/s3d.ddp600.s0/iter_000600"
)
OLENS_WSBENCH_DATASET_SHA = "3f66b72cd40448c9278177c6bb56f07e0f74ae4f"  # dataset HEAD 2026-10-07
OLENS_ALPHA = 16000.0
OLENS_TRANSFORM = "unit"  # inject alpha * h/||h|| replacing the marker's input embedding
OLENS_PROMPT_KIND = "concepts_raw"
OLENS_PROMPT = (
    "An activation vector from layer {layer} of a language model is enclosed in activation "
    "tags: <activation>{char}</activation>. Produce distinct concepts that encode this "
    "activation, each as a '- ' bullet on its own line."
)
OLENS_MARKER_SCAN = (0x3200, 0x3400)  # enclosed-CJK block; wsbench scans it, README says ㈜ wins
OLENS_TRAINED_LAYERS = list(range(20, 61, 4))  # 42 is OFF this grid (compatibility note)

NLA_REPO = "ceselder/qwen3.6-27b-nla-rl"
NLA_SHA = "5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f"  # HF API HEAD 2026-10-07
NLA_BASE_SUBFOLDER = "av_base"
NLA_ADAPTER_SUBFOLDER = "av_rl_adapters/iter_000400"
NLA_ADAPTER_SHA256 = "b54e23e4e36dbd04023b307e3abfd4618b5db2b31b8e7c650a957ebb1c90c358"
NLA_META_FILE = "nla_meta.yaml"
NLA_EXAMPLES_FILE = "data/example_activations.parquet"
NLA_INJECTION_CHAR = "㈜"  # ㈜ (from nla_meta.yaml)
NLA_INJECTION_TOKEN_ID = 158983
NLA_LEFT_NEIGHBOR_ID = 29
NLA_RIGHT_NEIGHBOR_ID = 510
NLA_INJECT_LAYER_IDX = 1  # forward hook on the OUTPUT of decoder block 1 (Karvonen eq. 1)
NLA_INJECTION = "nla_add_normmatched_block1"  # h1 + ||h1|| * h/||h||
OLENS_INJECTION = "olens_replace_alpha16000_unit"
JLENS_INJECTION = "none"

# ------------------------------------------------------------------ Phase Y3: new reader families (BRIEF_Y §Y3; HF API verified 2026-10-08)
# Skip-lens ("agreelens") arms A and D: PEFT LoRA r64/alpha16 rsLoRA on the plain target base, the SAME
# marker/neighbours/injection as the NLA (㈜ 158983 between 29 and 510, Karvonen norm-matched ADD at the
# block-1 output), actor prompt from each repo's nla_meta.yaml, chat render with thinking off.
SKIPLENS_ARMS = ("a", "d")
SKIPLENS_REPOS = {"a": "ceselder/skip-lens-qwen36-27b-agreelens-a", "d": "ceselder/skip-lens-qwen36-27b-agreelens-d"}
SKIPLENS_SHAS = {"a": "adc5bc7e5c88581cf370c9fabf87e721c5256d94", "d": "128af7d319301f557067cc0d07c76c359cd29dc9"}  # repo HEADs
SKIPLENS_ADAPTER_SHA256 = {"a": "e21ce6a8f4beef421e1265128a64e3b31e1095ad3da72fa8532b1ead431698dc",  # LFS oid of adapter_model.safetensors
                           "d": "ae09113bf87dbc8af9acb9bbed2abe9d789a7921f88d5eb453d34ab9b35d8aac"}
SKIPLENS_ADAPTER_BYTES = 1867782664  # per arm
SKIPLENS_FILES = ["adapter_config.json", "adapter_model.safetensors", "nla_meta.yaml", "README.md"]  # NOT tokenizer.json (target's own)
SKIPLENS_META_FILE = "nla_meta.yaml"
SKIPLENS_READER_NAMES = {"a": "skip_a", "d": "skip_d"}  # reader.name == PEFT adapter_name on the target
SKIPLENS_INJECTION = "skiplens_add_normmatched_block1"  # h1 + ||h1|| * h/||h|| at the marker, prefill only (== NLA hook)
SKIPLENS_SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 0, "do_sample": True}  # README: temp 1.0, top-p 0.95 (no top-k)
SKIPLENS_LO_FORMS = ("{X}", " {X}")  # native LO: continuation right after the generation prompt, bare and leading-space forms
# Qwen-Scope TopK SAE (trained on Qwen3.5-27B; transfer to Qwen3.6-27B is the Y3 test)
SAE_REPO = "Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50"
SAE_SHA = "13d4221569f7ca5d3c1e605e3e3dc95117e4807c"
SAE_FILE = "layer42.sae.pt"  # dict {W_enc [81920, 5120], W_dec [5120, 81920], b_enc [81920], b_dec [5120]}
SAE_FILE_SHA256 = "a8d5253ba21f131337534c3efcb47e7b365fa5866221c40e66e4a493ee5d92b2"
SAE_FILE_BYTES = 3355793787
SAE_BASE_MODEL = "Qwen/Qwen3.5-27B"
SAE_K = 50
SAE_D_SAE = 81920
SAE_HOOK = "resid_post layer 42 == block-42 output (our capture site)"
SAE_ENCODE_VARIANT = "readme"  # README demo: z = topk(x @ W_enc^T + b_enc, k) (no b_dec subtraction); "centred" = topk((x - b_dec) @ W_enc^T + b_enc, k)
SAE_FVE_MIN = 0.5  # the SAE becomes a reader column only if FVE >= this (pooled X1 + X3 states)
SAE_PROBE_MAX_LATENTS = 10  # sparse LOO diff-in-means probe keeps <= 10 latents
SAE_NULL_SEED = 0  # shuffled-decoder null (W_dec columns permuted)
# R-lens (RelP Jacobian lens) from camilablank/workspace-lenses; same stacked-Jacobian dict as the J-lens
RLENS_REPO = "camilablank/workspace-lenses"
RLENS_SHA = "d740106d1e0f95456dc8718fba2895e9c8ffd6ef"
RLENS_FILE = "qwen3.6-27b/r-lens/lens.pt"
RLENS_FILE_SHA256 = "fe4d0b6a17318760e67e7a5ed417fc5dbb8e66129c6944656f506b2f10ce6192"
RLENS_FILE_BYTES = 3303028567
RLENS_NAME = "rlens"
# Y3 entry gate (E14): X1 E1 win >= 0.75 on ownership AND mapping (CI excluding 0.5) and E3 prior within +-1 nat
Y3_GATE_WIN = 0.75
Y3_E3_BAND = 1.0
Y3_READER_NAMES = ("skip_a", "skip_d", "sae", "rlens")

# ------------------------------------------------------------------ generation settings
SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "do_sample": True}
VERBALIZER_MAX_NEW_TOKENS = 256  # raised from 128 on 2026-10-07 after the dev run (NLA hit 128 on 8/8 dev states); = the bench setting
BENCH_MAX_NEW_TOKENS = 256  # the wsbench in-house setting, used only for the R0 reproduction
TARGET_MAX_NEW_TOKENS = 32  # greedy
PROMPT_ONLY_MAX_NEW_TOKENS = 128  # greedy
GREEDY = {"do_sample": False, "temperature": None, "top_p": None, "top_k": None}
SEED_NAMESPACE = "g_agreement-v1"

PROMPT_ONLY_TEMPLATE = (
    "You will read a short passage and answer one question about it.\n\n"
    "Passage:\n{prompt_text}\n\n"
    "Question: {question}\n"
    "Answer in a few words, then stop."
)
# Frozen 2026-10-07 before any test item was inspected. It contains only the item's prompt text
# and its primary question; never a reader output or a target answer. Do not tune on test items.


def stable_seed(module: str, method: str, item_id: str, sample_idx: int) -> int:
    """A reproducible per-call seed (31-bit) from the call's identity; recorded in every row."""
    key = f"{SEED_NAMESPACE}|{module}|{method}|{item_id}|{int(sample_idx)}"
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big") & 0x7FFFFFFF


def gen_id(module: str, method: str, item_id: str, sample_idx: int) -> str:
    return f"{module}|{method}|{item_id}|s{int(sample_idx)}"


# ------------------------------------------------------------------ hashing helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path | str) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_ids(ids: list[int]) -> str:
    """sha256 of the token-id list in a canonical textual form."""
    return sha256_bytes(",".join(str(int(i)) for i in ids).encode("ascii"))


def sha256_tree(paths: list[Path]) -> str:
    """One sha over several files (name + content), for the code snapshot."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def core_code_files() -> list[Path]:
    files = sorted(HERE.glob("*.py"))
    # core/*.py already covers scoring.py and analysis_utils.py; the module globs cover every
    # collect.py and analyze.py (g1..g4), so the freeze sha spans collection AND analysis code.
    for sub in ("g1_agreement", "g2_relations", "g3_activation_dependence", "g4_repeats", "repro"):
        files += sorted((PROJECT_DIR / sub).glob("*.py"))
    return files


# ------------------------------------------------------------------ dataset access
def load_items(split: str = "all", limit: int = 0, path: Path | None = None) -> list[dict[str, Any]]:
    """Items from dataset/items.json (INTERFACES §1). ``split`` in {dev, test, all}."""
    p = path or ITEMS_JSON
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run dataset/build_dataset.py first")
    d = json.loads(p.read_text(encoding="utf-8"))
    items = d["items"]
    if split != "all":
        items = [it for it in items if it["split"] == split]
    if limit:
        items = items[:limit]
    return items


def dataset_meta(path: Path | None = None) -> dict[str, Any]:
    p = path or ITEMS_JSON
    return json.loads(p.read_text(encoding="utf-8")).get("meta", {}) if p.exists() else {}


# ------------------------------------------------------------------ frozen config (§8)
def snapshot(frozen: bool) -> dict[str, Any]:
    """Everything the freeze records. Shas of files that do not exist yet are null."""
    git_sha = None
    try:
        git_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5
        ).stdout.strip() or None
    except Exception:  # not a git repo on the Mac copy
        git_sha = None
    return {
        "frozen": frozen,
        "frozen_at": datetime.now(UTC).isoformat(),
        "assets": {
            "target": {"id": TARGET_MODEL_ID, "sha": TARGET_MODEL_SHA, "dtype": TARGET_DTYPE},
            "jlens": {"repo": JLENS_REPO, "sha": JLENS_SHA, "file": JLENS_FILE, "file_sha256": JLENS_FILE_SHA256},
            "olens": {"repo": OLENS_REPO, "sha": OLENS_SHA, "subfolder": OLENS_SUBFOLDER,
                      "adapter_sha256": OLENS_ADAPTER_SHA256, "wsbench_lora": OLENS_WSBENCH_LORA},
            "nla": {"repo": NLA_REPO, "sha": NLA_SHA, "base": NLA_BASE_SUBFOLDER,
                    "adapter": NLA_ADAPTER_SUBFOLDER, "adapter_sha256": NLA_ADAPTER_SHA256},
        },
        "site": {"layer": LAYER, "hook": HOOK, "hidden_states_index": HIDDEN_STATES_INDEX,
                 "render": RENDER, "enable_thinking": ENABLE_THINKING, "position": "last prompt token"},
        "sampling": dict(SAMPLING),
        "caps": {"verbalizer": VERBALIZER_MAX_NEW_TOKENS, "target": TARGET_MAX_NEW_TOKENS,
                 "prompt_only": PROMPT_ONLY_MAX_NEW_TOKENS, "bench": BENCH_MAX_NEW_TOKENS},
        "seed_namespace": SEED_NAMESPACE,
        "prompt_only_template_sha256": sha256_bytes(PROMPT_ONLY_TEMPLATE.encode()),
        "dataset_sha256": sha256_file(ITEMS_JSON),
        "dataset_meta_sha256_items": dataset_meta().get("sha256_items"),
        "rubric_sha256": sha256_file(RUBRIC_MD),
        "donors_sha256": sha256_file(DONORS_JSON),
        "g4_selection_sha256": sha256_file(G4_PAIRS_JSON),
        "code_sha256": sha256_tree(core_code_files()),
        "git_sha": git_sha,
        "python": platform.python_version(),
    }


def freeze(force: bool = False) -> Path:
    if FROZEN_CONFIG.exists() and not force:
        prev = json.loads(FROZEN_CONFIG.read_text())
        if prev.get("frozen"):
            raise RuntimeError(f"{FROZEN_CONFIG} is already frozen; pass --force to re-freeze "
                               "(and add a dated Deviations note to BRIEF.md)")
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    FROZEN_CONFIG.write_text(json.dumps(snapshot(frozen=True), indent=1, ensure_ascii=False) + "\n")
    return FROZEN_CONFIG


CHECKED_KEYS = (
    "dataset_sha256", "rubric_sha256", "donors_sha256", "g4_selection_sha256",
    "prompt_only_template_sha256", "code_sha256",
)


def frozen_status(strict_code: bool = True, path: Path | None = None) -> tuple[bool, list[str]]:
    """(ok, problems). ok iff a frozen manifest exists (``frozen_config.json`` or, failing that,
    ``frozen_config_collection.json``), is frozen, and every recorded sha still matches disk.
    ``strict_code=False`` turns a changed ``code_sha256`` into a note (the follow-up collectors
    G5/G6 add code after the freeze and record both shas in their rows)."""
    cands = [path] if path else [p for p in FROZEN_CANDIDATES if p.exists()]
    if not cands:
        return False, ["frozen_config.json / frozen_config_collection.json missing (run core/config.py --freeze)"]
    all_problems: list[str] = []
    now = snapshot(frozen=True)
    for cand in cands:
        fz = json.loads(cand.read_text())
        problems = []
        if not fz.get("frozen"):
            problems.append("frozen is false")
        for k in CHECKED_KEYS:
            if fz.get(k) != now.get(k):
                msg = f"{k} changed since freeze ({str(fz.get(k))[:12]} -> {str(now.get(k))[:12]})"
                if k == "code_sha256" and not strict_code:
                    print(f"[config] note ({cand.name}): {msg}; accepted (strict_code=False)")
                    continue
                problems.append(msg)
        for a in ("target", "jlens", "olens", "nla"):
            if fz["assets"].get(a) != now["assets"].get(a):
                problems.append(f"asset {a} changed since freeze")
        if fz.get("sampling") != now["sampling"] or fz.get("caps") != now["caps"]:
            problems.append("sampling/caps changed since freeze")
        if not problems:
            return True, []
        all_problems += [f"{cand.name}: {x}" for x in problems]
    return False, all_problems


def frozen_shas() -> dict[str, Any]:
    """What the follow-up collectors record per row: the manifest used, its code sha, the current one."""
    out: dict[str, Any] = {"manifest": None, "frozen_code_sha256": None,
                           "current_code_sha256": sha256_tree(core_code_files())}
    for p in FROZEN_CANDIDATES:
        if p.exists():
            out["manifest"], out["frozen_code_sha256"] = p.name, json.loads(p.read_text()).get("code_sha256")
            break
    return out


def require_frozen(split: str, allow_unfrozen_dev: bool = True, strict_code: bool = True) -> None:
    """Collectors call this. Test items need a valid freeze; dev items may run unfrozen."""
    if split == "dev" and allow_unfrozen_dev:
        return
    ok, problems = frozen_status(strict_code=strict_code)
    if not ok:
        raise SystemExit("refusing to collect on split=%s: %s" % (split, "; ".join(problems)))


def env_summary() -> dict[str, Any]:
    out: dict[str, Any] = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("torch", "transformers", "peft", "huggingface_hub"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:
            out[mod] = None
    try:
        import torch

        out["cuda"] = torch.cuda.is_available()
        out["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        out["cuda"] = False
    out["HF_HOME"] = os.environ.get("HF_HOME")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--freeze", action="store_true", help="write manifest/frozen_config.json")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", action="store_true", help="check the freeze against disk")
    ap.add_argument("--show", action="store_true", help="print the current snapshot")
    ap.add_argument("--relax-code", action="store_true", help="--status: code sha mismatch is a note only")
    a = ap.parse_args(argv)
    if a.freeze:
        print(f"wrote {freeze(force=a.force)}")
    if a.status:
        ok, problems = frozen_status(strict_code=not getattr(a, "relax_code", False))
        print("frozen OK" if ok else "NOT frozen / mismatch: " + "; ".join(problems))
    if a.show or not (a.freeze or a.status):
        print(json.dumps(snapshot(frozen=False), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
