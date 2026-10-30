"""Check every frozen label and post a fixed five-example sample per state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .states import extract_states
from .sample import topic_for_title


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fixture = Path(__file__).with_name("hand_examples.json")
    rows = json.loads(fixture.read_text())
    report = {"experiment": "E73", "track": "C", "human_review": "PENDING_GUIV",
              "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(), "states": {}}
    page = ["# E73: five hand-checkable examples per state", "",
            "These are unit fixtures, not corpus samples. Labels were authored independently of the extractor.",
            "`⟦READ⟧` marks the exclusive character endpoint after the read text; subsequent text is shown for checking.",
            "A = 0; B = 1. Selection was fixed to examples 1, 6, 11, 16, 21 per state before running tests.",
            "Guiv's eyeball review is pending. W8 also checks each fixture title against the frozen lists under clarification 2.", ""]
    failures = []
    for state in [f"W{i}" for i in range(1, 9)]:
        subset = [r for r in rows if r["state"] == state]
        assert len(subset) == 50
        passed = 0
        for row in subset:
            topic = row.get("topic")
            if state == "W8":
                topic = topic_for_title(row["title"], json.loads(Path(__file__).with_name("sports_science_titles.json").read_text()))
            observed = extract_states(row["text"], row["language"], [row["offset"]],
                                      title=row.get("title", ""), topic=topic)[state][0]
            if observed == row["expected"]:
                passed += 1
            else:
                failures.append({"id": row["id"], "expected": row["expected"], "observed": observed})
        report["states"][state] = {"n": 50, "passed": passed, "failed": 50-passed}
        page.extend([f"## {state}", ""])
        for index in [0, 5, 10, 15, 20]:
            row = subset[index]
            text = row["text"][:row["offset"]] + "⟦READ⟧" + row["text"][row["offset"]:]
            if state == "W8":
                text = f"Article title: {row['title']}\n\n" + text
            page.extend([f"**{row['id']} — {'A' if row['expected']==0 else 'B'}.** {row['reason']}", "",
                         "````text", text.rstrip("\n"), "````", ""])
    report["failures"] = failures
    report["status"] = "PASS" if not failures else "FAIL"
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "EXTRACTOR_VALIDATION.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "EYEBALL_EXAMPLES.md").write_text("\n".join(page))
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
