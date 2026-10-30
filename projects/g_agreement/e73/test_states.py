"""Independent expected labels: 50 hand-checkable examples per state."""
import json
import unittest
from collections import Counter
from pathlib import Path

from .fixtures import examples
from .sample import topic_for_title
from .states import extract_states


class HandCheckableFixtures(unittest.TestCase):
    def test_all_400(self):
        rows = examples()
        self.assertEqual(Counter(r["state"] for r in rows), {f"W{i}": 50 for i in range(1, 9)})
        for row in rows:
            with self.subTest(id=row["id"], reason=row["reason"]):
                topic = row.get("topic")
                if row["state"] == "W8":
                    frozen = json.loads(Path(__file__).with_name("sports_science_titles.json").read_text())
                    topic = topic_for_title(row["title"], frozen)
                    self.assertEqual(topic, row["topic"])
                actual = extract_states(row["text"], row["language"], [row["offset"]],
                                        title=row.get("title", ""), topic=topic)
                self.assertEqual(actual[row["state"]], [row["expected"]])

    def test_frozen_fixtures_match_source(self):
        self.assertEqual(json.loads(Path(__file__).with_name("hand_examples.json").read_text()), examples())


if __name__ == "__main__":
    unittest.main()
