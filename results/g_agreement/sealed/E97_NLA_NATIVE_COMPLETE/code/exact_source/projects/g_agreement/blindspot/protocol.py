"""Plain-Python input/score seals and an integrator-owned compute gate."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
BRIEF = "projects/g_agreement/BRIEF_BLINDSPOT.md"
SEED = 20261023
CAP_SECONDS = {"W1": 7200, "W5": 1800, "W1b": 3600}
RUNTIME = {"batch": 32, "oracle_pair_native_batch": 32}
DECODING = {
    "samples": [
        {"temperature": 0.0, "top_p": 1.0, "top_k": 0, "max_new_tokens": 128},
        {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "max_new_tokens": 128},
    ],
    "seeds": [SEED, SEED + 1],
    "baseline_top_k": 10,
    "baseline_repeats": "deterministic_identical_not_independent_generations",
}



# Descriptive J/logit baselines need native single-token labels, not a tokenwise
# average over decoder sentences. First pair is the existing feature token pair;
# this second authored pair keeps the same A-minus-B orientation. All variants
# are tested using the pinned upstream token_variants and real Qwen tokenizer.
BASELINE_SYNONYMS = {
    "prose_sentence": ("initial", "final"),
    "prose_words": ("fewer", "more"),
    "prose_budget": ("more", "less"),
    "prose_column": ("brief", "extended"),
    "prose_paren": ("open", "closed"),
    "prose_quote": ("open", "closed"),
    "prose_topic": ("plants", "sea"),
    "prose_sentiment": ("happy", "sad"),
    "python_line": ("initial", "final"),
    "python_argument": ("initial", "subsequent"),
    "python_depth": ("flat", "nested"),
    "python_indent": ("outer", "inner"),
    "python_string": ("open", "closed"),
    "python_comment": ("annotation", "executable"),
    "python_effect": ("modify", "duplicate"),
    "python_error": ("exception", "returning"),
    "latex_section": ("initial", "final"),
    "latex_item": ("initial", "subsequent"),
    "latex_math": ("mathematical", "prose"),
    "latex_brace": ("single", "triple"),
    "latex_environment": ("formula", "quotation"),
    "latex_fraction": ("top", "bottom"),
    "latex_subject": ("symbolic", "geometric"),
    "latex_role": ("proposition", "illustration"),
    "json_field": ("initial", "subsequent"),
    "json_depth": ("flat", "nested"),
    "json_type": ("textual", "numeric"),
    "json_status": ("accepted", "denied"),
    "table_column": ("initial", "subsequent"),
    "table_row": ("initial", "final"),
    "table_role": ("heading", "entry"),
    "table_status": ("accepted", "denied"),
    "list_index": ("initial", "subsequent"),
    "list_depth": ("outer", "inner"),
    "list_completed": ("fewer", "more"),
    "list_words": ("fewer", "more"),
    "list_ordered": ("numbered", "unordered"),
    "list_task": ("complete", "incomplete"),
    "list_priority": ("immediate", "ordinary"),
    "list_topic": ("tourism", "learning"),
    "table_column_ordinal": ("subsequent", "initial"),
    "python_depth_ordinal": ("nested", "flat"),
}


def baseline_pairs(feature, spec):
    pairs = [tuple(spec.tokens), BASELINE_SYNONYMS[feature]]
    if len(set(pairs)) != 2 or any(a == b for a, b in pairs):
        raise ValueError("baseline pairs must be distinct, oriented contrasts")
    if any(not term or len(term.split()) != 1 for pair in pairs for term in pair):
        raise ValueError("baseline terms must be individual words")
    return pairs


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def jsonl(path, values):
    with Path(path).open("x") as f:
        for row in values:
            f.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def seal(directory, names, kind):
    directory = Path(directory)
    result = {"status": kind, "files": {n: sha(directory/n) for n in names}}
    dump(directory/("SCORE_SEAL.json" if kind.startswith("SCORES") else "INPUT_SEAL.json"), result)
    return result


def verify(directory, seal_name):
    directory = Path(directory)
    result = json.loads((directory/seal_name).read_text())
    for name, expected in result["files"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts or sha(directory/name) != expected:
            raise ValueError("seal mismatch: " + name)
    return result


def write_bank(directory, items, lengths, tokenizer, *, experiment="W1", selection_receipt=None, seed=SEED):
    """Freeze label-free inputs and hash the separate, local-only ground truth.

    The full bank stays in cache; manifest.json and INPUT_SEAL.json are committed
    before capture. Cluster is a template family, pair_id is a matched instance.
    """
    from .items import FEATURES, ORDINAL_FEATURES
    registry = {**FEATURES, **ORDINAL_FEATURES}
    if experiment not in {"W1", "W1b"}:
        raise ValueError("bank experiment must be W1 or W1b")
    if experiment == "W1b" and not selection_receipt:
        raise ValueError("W1b requires committed screen candidates before item construction")
    tokenizer_file = Path(tokenizer)/"tokenizer.json"
    tokenizer_sha256 = sha(tokenizer_file) if tokenizer_file.is_file() else None
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    pairs = {}
    for it in items:
        if it["feature"] in FEATURES:
            pairs.setdefault((it["feature"], it["meta"]["pair_id"]), []).append(it)
    donors = {}
    for pair in pairs.values():
        if (len(pair) != 2 or pair[0]["value"] == pair[1]["value"]
                or len(pair[0]["ids"]) != len(pair[1]["ids"])
                or pair[0]["cluster"] != pair[1]["cluster"]
                or pair[0]["domain"] != pair[1]["domain"]
                or pair[0]["split"] != pair[1]["split"]):
            raise ValueError("invalid matched opposite-value pair")
        donors[pair[0]["id"]] = pair[1]["id"]
        donors[pair[1]["id"]] = pair[0]["id"]
    jsonl(directory/"items.input.jsonl", [{"id": it["id"], "feature": it["feature"], "ids": it["ids"], "donor_id": donors.get(it["id"])} for it in items])
    jsonl(directory/"labels.DO_NOT_STAGE.jsonl", [{k: it[k] for k in ("id", "feature", "class", "domain", "value", "split", "cluster")} for it in items])
    jsonl(directory/"items.DO_NOT_STAGE.jsonl", items)
    causal = []
    for feature in sorted({it['feature'] for it in items}):
        eligible = sorted((pair for (f, _), pair in pairs.items() if f == feature and pair[0]['split'] == 'test'), key=lambda pair: pair[0]['meta']['pair_id'])
        causal.extend(it['id'] for pair in eligible for it in pair)
    dump(directory/"causal.input.json", causal)
    dump(directory/"lengths.json", lengths)
    definitions = {}
    for feature in sorted({i["feature"] for i in items}):
        spec = registry[feature]
        definitions[feature] = {"olens": spec.pairs("olens"), "nla": spec.pairs("nla"),
            "jlens": baseline_pairs(feature, spec), "logit": baseline_pairs(feature, spec),
            "values": list(spec.values), "class": spec.kind, "domain": spec.domain,
            "kind": "binary" if feature in FEATURES else "ordinal",
            "score_orientation": "value_A_positive" if feature in FEATURES else "increasing_level_positive"}
    dump(directory/"templates.json", definitions)
    dump(directory/"sweep.input.json", [it['id'] for it in items if it['split'] == 'test' and it['feature'] in FEATURES])
    dump(directory/"decoding.json", DECODING)
    dump(directory/"runtime.json", RUNTIME)
    dump(directory/"provenance.json", {"seed": seed, "experiment": experiment,
        "tokenizer": str(tokenizer), "labels_sha256": sha(directory/"labels.DO_NOT_STAGE.jsonl"),
        "tokenizer_sha256": tokenizer_sha256,
        "items": len(items), "features": len(definitions), "brief": BRIEF, "brief_sha256": sha(ROOT/BRIEF)})
    names = ["items.input.jsonl", "templates.json", "provenance.json", "lengths.json", "causal.input.json", "sweep.input.json", "decoding.json", "runtime.json"]
    from collections import Counter
    summary = {}
    for feature, spec in definitions.items():
        subset = [it for it in items if it['feature'] == feature]
        summary[feature] = {**spec, "n": len(subset), "clusters": len({it['cluster'] for it in subset}),
            "split_counts": dict(Counter(it['split'] for it in subset)),
            "value_counts": dict(Counter(str(it['value']) for it in subset))}
    dump(directory/"manifest.json", {"schema": "blindspot-w1-v2", "experiment": experiment,
        "seed": seed, "brief": BRIEF, "brief_sha256": sha(ROOT/BRIEF),
        "source_files": code_hashes(), "tokenizer": str(tokenizer), "rows": summary,
        "tokenizer_sha256": tokenizer_sha256,
        "files": {n: sha(directory/n) for n in names + ["labels.DO_NOT_STAGE.jsonl", "items.DO_NOT_STAGE.jsonl"]},
        "selection_receipt": selection_receipt,
        "capture_sites": [42, 44], "sweep_sites": [20, 28, 36, 44, 52, 60],
        "caps_gpu_seconds": CAP_SECONDS, "bootstrap_replicates": 2000,
        "split_unit": "template family; six dev and six test families",
        "read_position": "last token of raw prefix, no chat template",
        "ground_truth": "generator-defined excerpt after unrelated preamble delimiter"})
    return seal(directory, names + ["manifest.json"], "INPUTS_FROZEN")


def code_hashes(root=ROOT):
    root = Path(root)
    paths = [root/"common/__init__.py", root/"common/stats.py", root/BRIEF,
             root/"projects/g_agreement/manifest/assets.json",
             root/"projects/g_agreement/blindspot/pod_run.sh"]
    # W-mechanism edits ar_tests.py concurrently; it is not executed by W-core.
    paths += [root/"projects/g_agreement/blindspot"/n for n in
              ("__init__.py", "items.py", "w1_templates.py", "run.py", "protocol.py", "analysis.py", "stage.py", "recall.py")]
    paths += sorted((root/"external/mats-nla-workspace/src").rglob("*.py"))
    return {str(p.relative_to(root)): sha(p) for p in paths if p.is_file()}


def admit(assignment, root=ROOT, now=None, pod_id=None, *, experiment=None, bank=None):
    """The integrator attests publication/registration and assigns this exact pod/source.

    This receipt does not allocate a pod, grant a budget, or replace the integrator's
    independent provider hardstop and retrieval supervision. No implicit local override.
    """
    root = Path(root)
    a = json.loads(Path(assignment).read_text())
    now = time.time() if now is None else now
    pod_id = os.environ.get("RUNPOD_POD_ID") if pod_id is None else pod_id
    if not pod_id or a.get("pod_id") != pod_id or a.get("issuer") != "integrator":
        raise ValueError("requires integrator assignment for this RunPod pod")
    if a.get("brief_registered") is not True or a.get("brief_pushed") is not True:
        raise ValueError("BRIEF_BLINDSPOT must be registered and pushed first")
    for field in ("source_commit", "brief_commit"):
        v = a.get(field, "")
        if len(v) != 40 or any(c not in "0123456789abcdef" for c in v):
            raise ValueError("missing pinned " + field)
    if not (root/BRIEF).is_file() or a.get("brief_sha256") != sha(root/BRIEF):
        raise ValueError("BRIEF_BLINDSPOT bytes differ from registration")
    if a.get("source_files") != code_hashes(root):
        raise ValueError("assigned source differs from worker bytes")
    created, deadline = float(a["provider_created_epoch"]), float(a["deadline_epoch"])
    budget = float(a["allocated_gpu_seconds"])
    experiment = experiment or a.get("experiment")
    if experiment not in CAP_SECONDS or a.get("experiment") != experiment:
        raise ValueError("assignment must name the requested registered experiment")
    previous = float(a["previous_gpu_seconds"])
    if (not all(math.isfinite(v) for v in (created, deadline, budget, previous, now))
            or previous < 0 or budget <= 0 or previous + budget > CAP_SECONDS[experiment]):
        raise ValueError("cumulative allocation exceeds registered GPU cap")
    if bank is not None:
        verify(bank, "INPUT_SEAL.json")
        if a.get("manifest_sha256") != sha(Path(bank)/"manifest.json"):
            raise ValueError("assignment bank manifest differs")
        commit = a.get("manifest_commit", "")
        if a.get("manifest_committed") is not True or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            raise ValueError("manifest must be committed before capture")
        manifest = json.loads((Path(bank)/"manifest.json").read_text())
        if manifest.get("source_files") != code_hashes(root):
            raise ValueError("bank was frozen against different source bytes")
        pins = json.loads((root/"projects/g_agreement/manifest/assets.json").read_text())
        if manifest.get("tokenizer_sha256") != pins["target"]["files_needed"]["tokenizer.json_sha256"]:
            raise ValueError("bank did not use the pinned Qwen tokenizer")
    if not 0 < deadline-created <= budget or not created <= now < deadline-180:
        raise ValueError("allocation expired or retrieval reserve reached")
    if not a.get("external_hardstop_verified"):
        raise ValueError("integrator hardstop evidence required")
    return a


@contextmanager
def compute_window(a):
    """Bound the process as well as checking admission between production stages."""
    def stop(_signum, _frame):
        raise TimeoutError("integrator allocation retrieval reserve reached")
    previous = signal.signal(signal.SIGALRM, stop)
    signal.setitimer(signal.ITIMER_REAL, max(.01, a["deadline_epoch"]-180-time.time()))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@contextmanager
def logged(stage, root=ROOT, gpu=False, extra=None):
    start = time.perf_counter()
    stamp = datetime.now(timezone.utc).isoformat()
    status = "FAILED"
    try:
        yield
        status = "COMPLETE"
    finally:
        elapsed = time.perf_counter()-start
        directory = Path(root)/"results/g_agreement"
        directory.mkdir(parents=True, exist_ok=True)
        record = {"module": "blindspot", "step": stage, "started": stamp, "wall_s": elapsed, "gpu_hours": elapsed/3600 if gpu else 0, "gpu": "integrator-assigned" if gpu else "cpu", "accounting_scope": "worker process, do not add to provider custody charge" if gpu else "CPU only", "seed": SEED, "status": status, "command": sys.argv, "extra": extra or {}}
        with (directory/"compute.jsonl").open("a") as f:
            f.write(json.dumps(record, sort_keys=True)+"\n")
        with (directory/"log.md").open("a") as f:
            f.write(f"\n- {stamp} blindspot `{stage}`; seed {SEED}; {elapsed:.3f}s; {status}; GPU-h {record['gpu_hours']:.6f}.\n")
