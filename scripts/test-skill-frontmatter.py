#!/usr/bin/env python3
"""Validate shipped frontmatter using a real YAML loader (dev-only PyYAML)."""

from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class SkillFrontmatterTest(unittest.TestCase):
    def test_shipped_skill_loads(self):
        text = (ROOT / ".agents/skills/gotcha-distill/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        header = text.split("---\n", 2)[1]
        meta = yaml.safe_load(header)
        self.assertIsInstance(meta, dict)
        self.assertEqual(meta["name"], "gotcha-distill")
        self.assertIsInstance(meta["description"], str)
        self.assertTrue(meta["description"].strip())
        self.assertNotIn("\n", meta["description"])
        self.assertLessEqual(len(meta["description"]), 200)


if __name__ == "__main__":
    unittest.main()
