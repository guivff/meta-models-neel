"""CPU-only E23 source gate. Never correct a registered hash implicitly."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

REVISION = "a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb"
AUTHORITY = "e347b86a"
# These abbreviated SHA256 pins are verbatim from section 117, clarification 1.
# Git blobs were independently fetched at REVISION; they do not override SHA pins.
FILES = (
    ("experiments/13_new_rows/results/gen_ol_tb_tablecol.json", "2e8738d0…79b9d", "fc77a4edd2b368704b5f5d0de3cdda0cd72b4e99", "tb_tablecol"),
    ("experiments/13_new_rows/results/gen_ol_tb_paren.json", "10bf31c7…a6b51", "8347a1ad0c3f9a04ad6c3290cf8fe268186b7ecc", "tb_paren"),
    ("experiments/handoff_inputs/07_template_mining/gen_ol_bk_listidx.json", "ef289fa3…be50ba", "ba8d5e8bfd1c4622958118f951f5945da744cb28", "bk_listidx"),
    ("experiments/13_new_rows/feature_spec.py", "b0dd043f…7effe43", "5835f00c6717e09f4871a550d30555345dfc4a81", None),
    ("experiments/13_new_rows/templates_frozen.json", "d9046206…837d16", "e24976286c1b344de0350b00b1b0b70ee17c73b3", None),
    ("experiments/07_template_mining/templates_frozen.json", "09156722b059edb99d01e919c29b2ff660e37cba3152f2d3ce67f3272d3e923b", "fe84815ad09e14b8d926eaf319258ff55e5b3c67", None),
)
PARITY_FILES = (
    ("experiments/handoff_inputs/13_new_rows/acts_tb_tablecol.pt", "40d8a9e22e58ebe5bfed09f02b27c0029ccd264d"),
    ("experiments/handoff_inputs/13_new_rows/acts_tb_paren.pt", "27875d2a740a34e8444021c0a7a464466258ac1f"),
    ("experiments/handoff_inputs/07_template_mining/acts_bk_listidx.pt", "95a69c2dc22e54559afdb7ae37142865ce0b1811"),
)


def digests(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


def matches_pin(actual: str, registered: str) -> bool:
    if "…" not in registered:
        return actual == registered
    prefix, suffix = registered.split("…")
    return bool(prefix and suffix) and actual.startswith(prefix) and actual.endswith(suffix)


def item_metadata(document: dict, feature: str) -> dict:
    # Deliberately do not inspect ol_gens or other previous reader outputs.
    items = document["items"]
    if len(items) != 200:
        raise ValueError("expected exactly 200 Suraj items")
    for field in ("id", "cluster"):
        if len({r[field] for r in items}) != 200:
            raise ValueError(f"expected one unique {field} per item")
    if any(r["feature"] != feature for r in items):
        raise ValueError("wrong feature")
    split_counts = Counter(r["split"] for r in items)
    if split_counts != {"mine": 40, "select": 160}:
        raise ValueError("mine/select split differs from registration")
    values = sorted({r["value"] for r in items})
    counts = {s: dict(sorted(Counter(r["value"] for r in items if r["split"] == s).items()))
              for s in ("mine", "select")}
    if len(values) != 2 or sorted(counts["mine"].values()) != [20, 20]:
        raise ValueError("mine must contain 20 items per value")
    if any(not r["ids"] or not all(isinstance(t, int) and t >= 0 for t in r["ids"]) for r in items):
        raise ValueError("invalid token prefix")
    return {"feature": feature, "items": 200, "unique_clusters": 200,
            "split_counts": dict(split_counts), "value_counts": counts,
            "token_lengths": {"min": min(len(r["ids"]) for r in items),
                              "max": max(len(r["ids"]) for r in items)},
            "mine_role": "dev/probe training", "select_role": "test",
            "M2_population": "all 200 items, grouped five-fold",
            "M1_T_population": "train mine 40, test select 160"}


def audit(root: Path) -> dict:
    files, errors = [], []
    for path, pin, blob, feature in FILES:
        entry = {"path": path, "registered_sha256_abbreviation": pin, "expected_git_blob": blob,
                 "url": f"https://github.com/Jarus77/mats-nla-workspace/blob/{REVISION}/{path}"}
        try:
            data = (root / path).read_bytes()
            entry.update(digests(data))
            entry["registered_sha256_matches"] = matches_pin(entry["sha256"], pin)
            entry["pinned_git_blob_matches"] = entry["git_blob"] == blob
            if not entry["registered_sha256_matches"]:
                errors.append({"path": path, "reason": "registered SHA256 mismatch"})
            if not entry["pinned_git_blob_matches"]:
                errors.append({"path": path, "reason": "pinned Git blob mismatch"})
            if feature:
                entry["item_metadata"] = item_metadata(json.loads(data), feature)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({"path": path, "reason": str(exc)})
        files.append(entry)
    parity = []
    for path, blob in PARITY_FILES:
        entry = {"path": path, "expected_git_blob": blob, "use": "parity only; never scientific input"}
        try:
            entry.update(digests((root / path).read_bytes()))
            entry["pinned_git_blob_matches"] = entry["git_blob"] == blob
            if not entry["pinned_git_blob_matches"]:
                errors.append({"path": path, "reason": "parity Git blob mismatch"})
        except OSError as exc:
            errors.append({"path": path, "reason": str(exc)})
        parity.append(entry)
    return {"schema": "E23_SOURCE_AUDIT_V1", "authority_commit": AUTHORITY,
            "repository": "Jarus77/mats-nla-workspace", "revision": REVISION,
            "status": "PASS" if not errors else "BLOCKED_SOURCE_GATE",
            "launch_allowed": not errors, "files": files, "parity_files": parity,
            "errors": errors, "activation_parity": {"status": "NOT_RUN", "minimum_cosine": 0.999,
                "required_layers": [40, 42, 44], "required_items_per_row": 200,
                "fresh_capture": "E23 own hooks; compare every item before scores"},
            "transport": {"text": "GitHub pinned individual UTF-8 files, exact bytes",
                "parity": "individual files from existing local checkout; Git blobs checked against pinned GitHub directory metadata",
                "repository_cloned": False}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "errors": result["errors"]}))
    return 0 if result["launch_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
