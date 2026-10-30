"""Claim-level judge for free-text readouts (Oracle Lens bullets, NLA <explanation>).

Adapted from Michael Kenney's `nla-consistency/scripts/claim_judge.py` (NLA confabulation: a consistency
filter, and what NLAs read; unpacked read-only from nla-consistency-main.zip into `nla-consistency/`). His judge splits a
readout into <= 12 atomic claims and labels each against the source text with six labels (workspace,
background_true, misquote, contradicted, invented_content, unverifiable) using the OpenAI client against
`google/gemini-3.8-flash` on OpenRouter with a strict JSON schema, temperature 0, cached by item id.

What changed here (PREREG_WV Track C):
- Five labels: `input_true` / `input_false` (claims about the prompt text as written), `computation_true` /
  `computation_false` (claims about what the model is computing or about to answer, judged against the item's
  answer key and, where recorded, the model's actual greedy answer), `unverifiable`.
- The judge sees the prompt, the fact (question, candidates, key, aliases), the model's actual answer and the readout.
- Plain `requests` against OpenRouter (the repo's `common/judge.py` convention; the venv has no `openai`), the same
  strict `json_schema` response format, `reasoning.effort = minimal` for Gemini, usage/cost logged per model to
  `judge_usage.json`, concurrency <= 4, on-disk cache keyed by (judge model, gen_id).
- A second-judge "relabel" pass (claims fixed, labels re-assigned) for Cohen's kappa.

INPUT FORMATS (loader `load_readouts`)
1. Our gens files (`cache/g_agreement/gens/g*.jsonl`): rows with `gen_id, module, method, item_id/state_item_id,
   sample_idx, raw_output, family, split`. `method` is mapped to a reader name (olens -> Oracle, nla -> NLA); only
   `--readers` methods are kept. `--actual` may point at the same gens file: rows with `method == "target"` supply the
   model's greedy answer (`raw_output`) and the full chat prompt (`input.visible_prompt`).
2. S4 sample files written by the pod (one row per sample). REQUIRED keys:
       state_item_id   str   id of the state (matches the items file, or carries its own prompt_text)
       reader          str   "Oracle" | "NLA" (any string; used as the grouping key)
       sample_idx      int   0..7
       text            str   the free-text readout (Oracle bullets or NLA output, tags allowed)
   OPTIONAL keys (override the items file when present):
       candidates      list[str]   the candidate answers for the fact
       answer          str         the answer key (ground truth of the fact)
       actual_answer   str|null    the model's own greedy answer on this state (null if not recorded)
       prompt_text     str         the prompt as the model saw it (user turn or full chat string)
       question        str         what the fact is ("Who carries the lantern?")
       gen_id          str         default f"{reader}|{state_item_id}|s{sample_idx}"
       module, family, condition, direction, alpha  (carried through to the output)
   `--items` may then be a JSON list / dict / {"items": [...]} of {item_id|state_item_id, prompt_text, candidates,
   answer, question} or our G1 `dataset/items.json` (uses `primary`). `--actual none` when rows carry actual_answer.

OUTPUT: one JSON row per claim: claim_id (= gen_id#k), gen_id, module, reader, item_id, family, sample_idx,
claim_idx, claim_text, judge_label, claim_type (input|computation|unverifiable), truth (true|false|null), evidence,
judge_model, prompt_text, question, candidates, answer, actual_answer, actual_matches_key, n_claims_in_readout.

CLI
    .venv/bin/python -m projects.g_agreement.w_claims.judge \
        --readouts cache/g_agreement/gens/g1.jsonl --items projects/g_agreement/dataset/items.json \
        --actual cache/g_agreement/gens/g1.jsonl --split test --readers olens,nla \
        --out results/g_agreement/w/claims/claims_g1.jsonl
    ... --relabel <claims.jsonl> --judge anthropic/claude-sonnet-5.5 --subsample 100 --out <relabel.jsonl>
Run under `zsh -ic` so OPENROUTER_API_KEY is set; the key is never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests

REPO = Path(__file__).resolve().parents[3]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
JUDGE_MODEL = "google/gemini-3.8-flash"
SECOND_JUDGE_MODEL = "anthropic/claude-sonnet-5.5"
MAX_CLAIMS = 12
MAX_WORKERS = 4
LABELS = ["input_true", "input_false", "computation_true", "computation_false", "unverifiable"]
READER_NAMES = {"olens": "Oracle", "nla": "NLA", "oracle": "Oracle", "Oracle": "Oracle", "NLA": "NLA"}
DEFAULT_OUT_DIR = REPO / "results" / "g_agreement" / "w" / "claims"

SYSTEM = f"""You audit readouts from an interpretability tool. A language model was given the PROMPT (one chat
turn) and was about to write its reply. The tool, looking ONLY at the model's internal activation at the last
prompt token (it never sees the prompt text), produced the READOUT. You are told the FACT the model is known
to be computing at that point (a question with its candidate values and the answer key) and, where recorded,
the model's ACTUAL ANSWER (what it really wrote right after the prompt).

1. Split the readout into atomic claims (one checkable statement each). Drop pure filler, formatting and remarks
   the tool makes about its own output. Merge near-duplicates: a bullet repeated verbatim is one claim. At most
   {MAX_CLAIMS} claims.
2. Label each claim with exactly one of:
   - "input_true": a statement about the PROMPT TEXT AS WRITTEN (its language, what it asks, the task format and
     constraints such as "one word", the tense cue, the named people/objects/words and who holds or maps to what)
     that the prompt supports.
   - "input_false": a statement about the prompt text that the prompt shows false: wrong names, objects, words or
     relations; a wrong topic or scenario; wrong language named; quoted or near-quoted wording the prompt does not
     contain; an invented surrounding context (a preceding explanation, an "Answer:" header, a dataset or
     few-shot format) that the prompt does not have.
   - "computation_true": a statement about what the model is computing or about to answer (the answer word, the
     language or tense of the reply it will write, which name, the chain result, an example reply it writes out)
     that agrees with the model's ACTUAL ANSWER when one is recorded, otherwise with the answer key. An example
     reply counts as one computation claim about the fact it realises (e.g. a past-tense sentence => "past"); its
     incidental details are not input claims unless the readout asserts them about the prompt.
   - "computation_false": such a statement that names a wrong value (the other candidate, an invented word or
     name, the wrong language or tense), or an example reply that realises the wrong value.
   - "unverifiable": neither the prompt, the fact nor the actual answer can settle it (speculation about origin,
     audience, style; generic statements with no checkable content).
Return JSON {{"claims": [{{"claim": "...", "label": "...", "evidence": "<10 words"}}]}}."""

RELABEL_SYSTEM = SYSTEM.split("1. Split", 1)[0] + (
    "The readout has ALREADY been split into numbered claims. Label each claim with exactly one of:\n"
    + SYSTEM.split("2. Label each claim with exactly one of:", 1)[1].rsplit("Return JSON", 1)[0]
    + 'Return JSON {"labels": [{"i": <claim number>, "label": "..."}]} with one entry per claim, in order.'
)

SCHEMA = {
    "name": "claims", "strict": True,
    "schema": {"type": "object", "properties": {"claims": {"type": "array", "items": {
        "type": "object",
        "properties": {"claim": {"type": "string"}, "label": {"type": "string", "enum": LABELS},
                       "evidence": {"type": "string"}},
        "required": ["claim", "label", "evidence"], "additionalProperties": False}}},
        "required": ["claims"], "additionalProperties": False},
}
RELABEL_SCHEMA = {
    "name": "labels", "strict": True,
    "schema": {"type": "object", "properties": {"labels": {"type": "array", "items": {
        "type": "object", "properties": {"i": {"type": "integer"}, "label": {"type": "string", "enum": LABELS}},
        "required": ["i", "label"], "additionalProperties": False}}},
        "required": ["labels"], "additionalProperties": False},
}


# ----------------------------------------------------------------------------------------------- text helpers
def clean_readout(text: str) -> str:
    """Strip NLA wrapper tags and stray HTML; keep bullets and line structure."""
    t = text or ""
    t = re.sub(r"</?explanation>", "", t)
    t = re.sub(r"</?br/?>", "\n", t)
    return t.strip()


def label_type(label: str) -> str:
    return label.split("_", 1)[0] if label != "unverifiable" else "unverifiable"


def label_truth(label: str) -> Optional[bool]:
    return None if label == "unverifiable" else label.endswith("_true")


def parse_json_content(content: str) -> Any:
    """Parse the judge's JSON; tolerate code fences and leading prose."""
    s = (content or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if start < 0 or end <= start:
            raise
        return json.loads(s[start:end + 1])


# ----------------------------------------------------------------------------------------------- loaders
def _read_jsonl(path: Path) -> List[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def load_items(path: Optional[Path]) -> Dict[str, dict]:
    """item id -> {prompt_text, question, candidates, answer, aliases, family, regex}. Accepts G1 items.json
    ({"items": [...]} with `primary`), a flat list, or a dict keyed by id."""
    if path is None or str(path).lower() == "none":
        return {}
    raw = json.loads(Path(path).read_text())
    rows = raw.get("items", raw) if isinstance(raw, dict) else raw
    if isinstance(rows, dict):
        rows = [dict(v, item_id=v.get("item_id", v.get("state_item_id", k))) for k, v in rows.items()]
    out = {}
    for it in rows:
        iid = it.get("state_item_id") or it.get("item_id")
        p = it.get("primary") or {}
        out[iid] = {
            "prompt_text": it.get("prompt_text") or it.get("prompt") or "",
            "question": it.get("question") or p.get("question"),
            "candidates": it.get("candidates") or p.get("candidates") or [],
            "answer": it.get("answer") if it.get("answer") is not None else p.get("answer"),
            "aliases": it.get("answer_aliases") or p.get("answer_aliases") or [],
            "family": it.get("family"),
            "regex": it.get("target_answer_regex"),
        }
    return out


def load_actual(path: Optional[Path]) -> Dict[str, dict]:
    """item id -> {actual_answer, visible_prompt}. Accepts our gens file (method == 'target' rows) or generic rows
    with state_item_id|item_id and actual_answer|raw_output."""
    if path is None or str(path).lower() == "none":
        return {}
    out = {}
    for r in _read_jsonl(Path(path)):
        if "method" in r and r["method"] != "target":
            continue
        iid = r.get("state_item_id") or r.get("item_id")
        ans = r.get("actual_answer", r.get("raw_output"))
        vis = (r.get("input") or {}).get("visible_prompt") if isinstance(r.get("input"), dict) else r.get("prompt_text")
        out[iid] = {"actual_answer": ans, "visible_prompt": vis}
    return out


def load_readouts(path: Path, readers: Iterable[str] = ("olens", "nla"), split: Optional[str] = None,
                  condition: Optional[str] = None) -> List[dict]:
    """Normalise gens rows or S4 rows to: gen_id, reader, state_item_id, sample_idx, text (+ optional fields)."""
    readers = {READER_NAMES.get(r, r) for r in readers} if readers else None
    out = []
    for r in _read_jsonl(Path(path)):
        if "raw_output" in r and "method" in r:                      # our gens format
            reader = READER_NAMES.get(r["method"], r["method"])
            if split and r.get("split") != split:
                continue
            if condition and r.get("condition") != condition:
                continue
            row = {"gen_id": r["gen_id"], "reader": reader, "state_item_id": r.get("state_item_id") or r["item_id"],
                   "sample_idx": r.get("sample_idx", 0), "text": r["raw_output"], "module": r.get("module"),
                   "family": r.get("family"), "condition": r.get("condition")}
        else:                                                         # S4 format
            reader = READER_NAMES.get(r["reader"], r["reader"])
            sidx = int(r.get("sample_idx", 0))
            row = {"gen_id": r.get("gen_id") or f"{reader}|{r['state_item_id']}|s{sidx}", "reader": reader,
                   "state_item_id": r["state_item_id"], "sample_idx": sidx, "text": r["text"],
                   "module": r.get("module", "s4"), "family": r.get("family"), "condition": r.get("condition")}
            for k in ("candidates", "answer", "actual_answer", "prompt_text", "question", "direction", "alpha"):
                if k in r:
                    row[k] = r[k]
        if readers and row["reader"] not in readers:
            continue
        out.append(row)
    return out


def resolve_context(row: dict, items: Dict[str, dict], actual: Dict[str, dict]) -> dict:
    """Merge row-level fields over the items/actual files into the judge's context."""
    it = items.get(row["state_item_id"], {})
    ac = actual.get(row["state_item_id"], {})
    prompt = row.get("prompt_text") or ac.get("visible_prompt") or it.get("prompt_text") or ""
    ctx = {"prompt_text": prompt, "question": row.get("question") or it.get("question"),
           "candidates": row.get("candidates", it.get("candidates", [])),
           "answer": row.get("answer", it.get("answer")), "aliases": it.get("aliases", []),
           "actual_answer": row.get("actual_answer", ac.get("actual_answer")),
           "family": row.get("family") or it.get("family")}
    rx = it.get("regex")
    ctx["actual_matches_key"] = (bool(re.search(rx, ctx["actual_answer"])) if rx and ctx["actual_answer"] else None)
    return ctx


def user_prompt(ctx: dict, readout: str) -> str:
    fact = {"question": ctx.get("question"), "candidates": ctx.get("candidates"), "answer_key": ctx.get("answer"),
            "key_aliases": ctx.get("aliases") or []}
    act = ctx.get("actual_answer")
    act_s = json.dumps(act, ensure_ascii=False) if act is not None else "not recorded"
    return (f"PROMPT (exactly as the model saw it; the readout was taken at its last token, before any reply):\n"
            f"<<<{ctx.get('prompt_text', '')}>>>\n\nFACT: {json.dumps(fact, ensure_ascii=False)}\n"
            f"MODEL'S ACTUAL ANSWER (greedy reply to this prompt): {act_s}\n\nREADOUT:\n{clean_readout(readout)}")


def relabel_prompt(ctx: dict, claims: List[str]) -> str:
    base = user_prompt(ctx, "").rsplit("READOUT:", 1)[0]
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
    return base + f"CLAIMS extracted from the readout:\n{numbered}"


# ----------------------------------------------------------------------------------------------- API + cache
class Usage:
    def __init__(self, path: Path):
        self.path, self.lock = Path(path), threading.Lock()
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def add(self, model: str, usage: dict) -> None:
        with self.lock:
            d = self.data.setdefault(model, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0})
            d["calls"] += 1
            d["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
            d["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
            d["cost_usd"] = round(d["cost_usd"] + float(usage.get("cost", 0.0) or 0.0), 6)
            self.data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=1))


def _post(payload: dict, timeout: int = 120) -> dict:
    key = os.environ["OPENROUTER_API_KEY"]
    r = requests.post(OPENROUTER_URL, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"openrouter {r.status_code}: {r.text[:300]}")
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"openrouter error: {str(j['error'])[:300]}")
    return j


def call_judge(system: str, user: str, schema: dict, model: str, usage: Optional[Usage] = None,
               post: Callable[[dict], dict] = None, retries: int = 4) -> Any:
    """One structured call; falls back to free-form JSON parsing if the schema is rejected."""
    post = post or _post
    payload = {"model": model, "temperature": 0, "max_tokens": 2000,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "response_format": {"type": "json_schema", "json_schema": schema}, "usage": {"include": True}}
    if model.startswith("google/"):
        payload["reasoning"] = {"effort": "minimal"}
    err: Exception = RuntimeError("no attempt")
    for attempt in range(retries):
        try:
            j = post(payload)
            if usage is not None:
                usage.add(model, j.get("usage") or {})
            return parse_json_content(j["choices"][0]["message"]["content"])
        except Exception as e:  # noqa: BLE001 - retry transient failures, drop the schema on a 400
            err = e
            if "400" in str(e) and "response_format" in payload:
                payload.pop("response_format")
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"judge failed after {retries} attempts: {err!r}")


class Cache:
    """Append-only JSONL cache of raw judge responses keyed by (model, key)."""

    def __init__(self, path: Path):
        self.path, self.lock = Path(path), threading.Lock()
        self.d: Dict[str, Any] = {}
        if self.path.exists():
            for r in _read_jsonl(self.path):
                self.d[r["key"]] = r["response"]

    @staticmethod
    def key(model: str, k: str) -> str:
        return f"{model}::{k}"

    def get(self, model: str, k: str):
        return self.d.get(self.key(model, k))

    def put(self, model: str, k: str, resp: Any) -> None:
        with self.lock:
            self.d[self.key(model, k)] = resp
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as fh:
                fh.write(json.dumps({"key": self.key(model, k), "response": resp}, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------------------------- pipeline
def judge_readouts(rows: List[dict], items: Dict[str, dict], actual: Dict[str, dict], model: str = JUDGE_MODEL,
                   cache: Optional[Cache] = None, usage: Optional[Usage] = None, post: Callable = None,
                   workers: int = MAX_WORKERS, log=print) -> List[dict]:
    """Split + label every readout; returns flat per-claim rows."""
    cache = cache or Cache(DEFAULT_OUT_DIR / "cache" / "judge_cache.jsonl")
    ctxs = {r["gen_id"]: resolve_context(r, items, actual) for r in rows}

    def one(r: dict):
        hit = cache.get(model, r["gen_id"])
        if hit is not None:
            return hit
        resp = call_judge(SYSTEM, user_prompt(ctxs[r["gen_id"]], r["text"]), SCHEMA, model, usage, post)
        claims = [c for c in resp.get("claims", []) if c.get("label") in LABELS and c.get("claim")][:MAX_CLAIMS]
        cache.put(model, r["gen_id"], {"claims": claims})
        return {"claims": claims}

    todo = [r for r in rows if cache.get(model, r["gen_id"]) is None]
    log(f"[judge] {len(rows)} readouts, {len(todo)} uncached, model={model}, workers={min(workers, MAX_WORKERS)}")
    with ThreadPoolExecutor(min(workers, MAX_WORKERS)) as ex:
        results = list(ex.map(one, rows))
    out = []
    for r, res in zip(rows, results):
        ctx = ctxs[r["gen_id"]]
        claims = res["claims"]
        for k, c in enumerate(claims):
            out.append({"claim_id": f"{r['gen_id']}#{k}", "gen_id": r["gen_id"], "module": r.get("module"),
                        "reader": r["reader"], "item_id": r["state_item_id"], "family": ctx.get("family"),
                        "sample_idx": r.get("sample_idx", 0), "condition": r.get("condition"),
                        "claim_idx": k, "claim_text": c["claim"], "judge_label": c["label"],
                        "claim_type": label_type(c["label"]), "truth": label_truth(c["label"]),
                        "evidence": c.get("evidence", ""), "judge_model": model,
                        "prompt_text": ctx["prompt_text"], "question": ctx.get("question"),
                        "candidates": ctx.get("candidates"), "answer": ctx.get("answer"),
                        "actual_answer": ctx.get("actual_answer"), "actual_matches_key": ctx.get("actual_matches_key"),
                        "n_claims_in_readout": len(claims)})
        if not claims:
            out.append({"claim_id": f"{r['gen_id']}#none", "gen_id": r["gen_id"], "module": r.get("module"),
                        "reader": r["reader"], "item_id": r["state_item_id"], "family": ctx.get("family"),
                        "sample_idx": r.get("sample_idx", 0), "condition": r.get("condition"), "claim_idx": None,
                        "claim_text": None, "judge_label": None, "claim_type": None, "truth": None, "evidence": "",
                        "judge_model": model, "prompt_text": ctx["prompt_text"], "question": ctx.get("question"),
                        "candidates": ctx.get("candidates"), "answer": ctx.get("answer"),
                        "actual_answer": ctx.get("actual_answer"), "actual_matches_key": ctx.get("actual_matches_key"),
                        "n_claims_in_readout": 0})
    return out


def subsample_claims(claims: List[dict], n: int, seed: int = 0, claim_type: str = "computation") -> List[dict]:
    pool = [c for c in claims if c.get("claim_type") == claim_type]
    if len(pool) <= n:
        return pool
    rng = random.Random(seed)
    return sorted(rng.sample(pool, n), key=lambda c: (c["gen_id"], c["claim_idx"]))


def relabel_claims(claims: List[dict], model: str = SECOND_JUDGE_MODEL, cache: Optional[Cache] = None,
                   usage: Optional[Usage] = None, post: Callable = None, workers: int = MAX_WORKERS,
                   log=print) -> List[dict]:
    """Second judge: same context, claims fixed (grouped per readout), labels re-assigned."""
    cache = cache or Cache(DEFAULT_OUT_DIR / "cache" / "judge_cache.jsonl")
    groups: Dict[str, List[dict]] = {}
    for c in claims:
        groups.setdefault(c["gen_id"], []).append(c)
    gids = sorted(groups)

    def one(gid: str):
        cs = groups[gid]
        texts = [c["claim_text"] for c in cs]
        key = f"{gid}#relabel#{hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()[:16]}"
        hit = cache.get(model, key)
        if hit is not None:
            return hit
        ctx = {k: cs[0].get(k) for k in ("prompt_text", "question", "candidates", "answer", "actual_answer")}
        ctx["aliases"] = []
        resp = call_judge(RELABEL_SYSTEM, relabel_prompt(ctx, texts), RELABEL_SCHEMA, model, usage, post)
        labels = {}
        for e in resp.get("labels", []):
            try:
                labels[int(e["i"]) - 1] = e["label"] if e["label"] in LABELS else None
            except (KeyError, TypeError, ValueError):
                continue
        res = {"labels": [labels.get(i) for i in range(len(texts))]}
        cache.put(model, key, res)
        return res

    log(f"[relabel] {len(claims)} claims in {len(gids)} readouts, model={model}")
    with ThreadPoolExecutor(min(workers, MAX_WORKERS)) as ex:
        results = list(ex.map(one, gids))
    out = []
    for gid, res in zip(gids, results):
        for c, lab in zip(groups[gid], res["labels"]):
            out.append({"claim_id": c["claim_id"], "gen_id": gid, "reader": c["reader"], "item_id": c["item_id"],
                        "claim_text": c["claim_text"], "judge1_model": c["judge_model"],
                        "judge1_label": c["judge_label"], "judge2_model": model, "judge2_label": lab})
    return out


def write_jsonl(path: Path, rows: List[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--readouts", type=Path, help="gens jsonl or S4 sample jsonl")
    ap.add_argument("--items", type=Path, default=None, help="items json (G1 format or flat) or 'none'")
    ap.add_argument("--actual", type=Path, default=None, help="jsonl with the model's actual answers, or 'none'")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--readers", default="olens,nla")
    ap.add_argument("--split", default=None, help="gens format only: keep this split (e.g. test)")
    ap.add_argument("--condition", default=None, help="gens format only: keep this condition")
    ap.add_argument("--judge", default=None, help=f"OpenRouter model id (default {JUDGE_MODEL}; relabel default "
                                                  f"{SECOND_JUDGE_MODEL})")
    ap.add_argument("--relabel", type=Path, default=None, help="claims jsonl to re-label with a second judge")
    ap.add_argument("--subsample", type=int, default=100, help="relabel: computation-claim subsample size")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    ap.add_argument("--usage", type=Path, default=DEFAULT_OUT_DIR / "judge_usage.json")
    ap.add_argument("--cache", type=Path, default=DEFAULT_OUT_DIR / "cache" / "judge_cache.jsonl")
    a = ap.parse_args(argv)
    usage, cache = Usage(a.usage), Cache(a.cache)
    if a.relabel:
        claims = [c for c in _read_jsonl(a.relabel) if c.get("claim_text")]
        sub = subsample_claims(claims, a.subsample, a.seed)
        rows = relabel_claims(sub, a.judge or SECOND_JUDGE_MODEL, cache, usage, workers=a.workers)
    else:
        if a.readouts is None:
            ap.error("--readouts is required unless --relabel is given")
        rows_in = load_readouts(a.readouts, a.readers.split(","), a.split, a.condition)
        rows = judge_readouts(rows_in, load_items(a.items), load_actual(a.actual), a.judge or JUDGE_MODEL,
                              cache, usage, workers=a.workers)
    write_jsonl(a.out, rows)
    print(f"wrote {len(rows)} rows -> {a.out}; usage -> {a.usage}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
