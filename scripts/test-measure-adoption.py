#!/usr/bin/env python3
"""Exercise fleet measurements against an isolated, configured repository."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "measure", Path(__file__).with_name("measure-adoption.py")
)
measure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(measure)


class MeasurementTest(unittest.TestCase):
    def test_custom_layout_and_prose_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            measure.contract._build_fixture(root)
            (root / "docs/gotchas").rename(root / "lessons")
            (root / "docs/postmortems").rename(root / "reviews")
            agents = root / "AGENTS.md"
            (root / "WORKFLOW.md").write_text(
                agents.read_text().replace("docs/gotchas", "lessons")
                .replace("## Environment gotchas", "## Lessons"), encoding="utf-8"
            )
            agents.unlink()
            (root / "gotcha.toml").write_text(
                '[paths]\ncontract = "WORKFLOW.md"\ngotchas = "lessons"\n'
                'postmortems = "reviews"\n[index]\nheading = "## Lessons"\n',
                encoding="utf-8",
            )
            domain = root / "lessons/infra.md"
            domain.write_text(
                domain.read_text().replace("docs/postmortems", "reviews")
                .replace("(2026-01-01): body", "(2026-01-01): Investigation took 35 minutes")
                .replace("(2026-01-02): body", "(2026-01-02): Prefer blue buttons every day")
                + "\n```markdown\n## Not an entry\n(2026-01-01) Cost: $20.\n```\n",
                encoding="utf-8",
            )
            result = measure.scan(root)
            self.assertEqual(result["canonical"], "hold")
            self.assertEqual(result["gotchas"], 3)
            self.assertEqual(result["dated"], 3)
            self.assertEqual(result["cost_signals"], 1)
            self.assertEqual(result["domain_files"], 1)
            self.assertEqual(result["postmortems"], 1)
            self.assertEqual(result["lazy_bytes"], len(domain.read_bytes()))
            self.assertGreater(result["index_bytes"], 0)
            self.assertEqual(result["ratio"], round(result["lazy_bytes"] / result["index_bytes"], 1))


if __name__ == "__main__":
    unittest.main()
