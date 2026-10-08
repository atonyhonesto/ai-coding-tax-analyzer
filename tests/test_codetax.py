import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codetax import metrics
from codetax.__main__ import analyse
from codetax.history import Change, Commit
from sample_repo import build

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def commit(day, msg, *changes):
    return Commit("x", T0 + timedelta(days=day), "dev", msg, [Change(*c) for c in changes])


class MarkerTests(unittest.TestCase):
    def test_detects_common_trailers(self):
        for msg in ("Fix\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
                    "Add\n\nCo-authored-by: GitHub Copilot <copilot@github.com>",
                    "Refactor\n\nGenerated with Cursor"):
            self.assertTrue(commit(0, msg).ai_assisted, msg)

    def test_ignores_human_coauthors(self):
        self.assertFalse(commit(0, "Pair\n\nCo-authored-by: Sam <sam@example.com>").ai_assisted)


class ReworkTests(unittest.TestCase):
    def test_deletions_inside_window_are_charged_to_the_adder(self):
        cs = [commit(0, "x\n\nCo-Authored-By: Claude", ("a.py", 100, 0)),
              commit(5, "fix", ("a.py", 10, 40)),
              commit(40, "late", ("a.py", 0, 30))]          # outside the 21-day window
        g = metrics.rework(cs, 21)
        self.assertEqual(g["ai-assisted"].reworked_lines, 40)
        self.assertAlmostEqual(g["ai-assisted"].rework_rate, 0.4)

    def test_rework_capped_at_lines_added(self):
        cs = [commit(0, "small", ("a.py", 5, 0)), commit(1, "big delete", ("a.py", 0, 50))]
        self.assertEqual(metrics.rework(cs)["other"].reworked_lines, 5)


class StaticTests(unittest.TestCase):
    def test_complexity_counts_branches(self):
        self.assertEqual(metrics.complexity("x = 1\n"), 1)
        self.assertEqual(metrics.complexity("if a and b:\n    pass\nfor i in x:\n    pass\n"), 4)

    def test_duplication_finds_pasted_block(self):
        block = "\n".join(f"total = total + {i}" for i in range(8))
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.py").write_text("x = 1\n" + block)
            Path(d, "b.py").write_text(block + "\ny = 2\n")
            Path(d, "c.py").write_text("\n".join(f"z{i} = {i}" for i in range(8)))
            share, pairs = metrics.duplication(d, ["a.py", "b.py", "c.py"])
        self.assertEqual(pairs[0][:2], ("a.py", "b.py"))
        self.assertAlmostEqual(share, 16 / 26)


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = analyse(build())

    def test_history_read(self):
        self.assertEqual(self.r["commits"], 30)
        self.assertAlmostEqual(self.r["ai_assisted_share"], 1 / 3)

    def test_ai_code_reworked_more(self):
        rw = self.r["rework"]
        self.assertGreater(rw["ai-assisted"]["rework_rate"], 2 * rw["other"]["rework_rate"])

    def test_pasted_helper_is_found(self):
        self.assertGreater(self.r["duplication"], 0.02)
        self.assertTrue(self.r["duplicate_pairs"])

    def test_hotspots_ranked(self):
        scores = [h[3] for h in self.r["hotspots"]]
        self.assertEqual(scores, sorted(scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
