#!/usr/bin/env python3
"""Regression checks for the upload artifact, using synthesized fixtures."""

import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZipInfo


SPEC = importlib.util.spec_from_file_location("package", Path(__file__).with_name("build-skill-zip.py"))
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)

SKILL = b"---\nname: gotcha-distill\ndescription: Synthetic package fixture.\n---\n"
EXPECTED = {"gotcha-distill/SKILL.md": SKILL, "gotcha-distill/LICENSE": b"Synthetic license\n"}


class SkillPackageTest(unittest.TestCase):
    def archive(self, entries):
        buffer = io.BytesIO()
        with ZipFile(buffer, "w") as archive:
            for name, content, mode in entries:
                info = ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, content)
        buffer.seek(0)
        return ZipFile(buffer)

    def entries(self):
        return [(name, content, stat.S_IFREG | 0o644) for name, content in EXPECTED.items()]

    def test_build_is_reproducible_and_ignores_repository_copies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for member, relative in package.FILES.items():
                source = root / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(EXPECTED[member])
            bridge = root / ".claude/skills/gotcha-distill/SKILL.md"
            bridge.parent.mkdir(parents=True)
            bridge.write_bytes(SKILL)
            (root / "private.txt").write_text("Synthetic unrelated file")
            first, second = root / "dist/first.zip", root / "dist/second.zip"
            package.build(root, first)
            package.build(root, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with ZipFile(first) as archive:
                self.assertEqual(set(archive.namelist()), set(EXPECTED))
                package.validate(archive, EXPECTED)

    def test_source_archive_layouts_are_rejected(self):
        # Synthetic reproductions of the two distinct release failures.
        layouts = [
            ([('source/.agents/skills/gotcha-distill/SKILL.md', SKILL, stat.S_IFREG | 0o644),
              ('source/.claude/skills', b'../.agents/skills', stat.S_IFLNK | 0o777)], 'symlink'),
            ([('source/.agents/skills/gotcha-distill/SKILL.md', SKILL, stat.S_IFREG | 0o644),
              ('source/.claude/skills/gotcha-distill/SKILL.md', SKILL, stat.S_IFREG | 0o644)], 'exactly one'),
        ]
        for entries, reason in layouts:
            with self.subTest(reason=reason), self.archive(entries) as archive:
                with self.assertRaisesRegex(ValueError, reason):
                    package.validate(archive, EXPECTED)

    def test_missing_duplicate_extra_and_stale_members_are_rejected(self):
        cases = [
            (self.entries()[1:], 'exactly one'),
            (self.entries() + [self.entries()[0]], 'exactly one'),
            (self.entries() + [self.entries()[1]], 'duplicate member'),
            (self.entries() + [('gotcha-distill/extra.txt', b'extra', stat.S_IFREG | 0o644)], 'contain only'),
            ([(name, b'stale' if name.endswith('SKILL.md') else content, mode)
              for name, content, mode in self.entries()], 'differs from source'),
            ([(name, content, stat.S_IFLNK | 0o777) for name, content, _ in self.entries()], 'symlink'),
        ]
        for entries, reason in cases:
            with self.subTest(reason=reason), warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)  # Deliberate duplicate ZIP members.
                with self.archive(entries) as archive:
                    with self.assertRaisesRegex(ValueError, reason):
                        package.validate(archive, EXPECTED)

    def test_wrong_roots_and_nonregular_members_are_rejected(self):
        for prefix in ('', 'source/gotcha-distill/', '../gotcha-distill/'):
            entries = [(prefix + name.rsplit('/', 1)[1], content, mode)
                       for name, content, mode in self.entries()]
            with self.subTest(prefix=prefix), self.archive(entries) as archive:
                with self.assertRaisesRegex(ValueError, 'contain only'):
                    package.validate(archive, EXPECTED)
        entries = [(name, content, stat.S_IFIFO | 0o644) for name, content, _ in self.entries()]
        with self.archive(entries) as archive:
            with self.assertRaisesRegex(ValueError, 'regular file'):
                package.validate(archive, EXPECTED)

    def test_symlinked_source_file_or_directory_is_rejected(self):
        for directory in (False, True):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                actual = root / "actual"
                actual.mkdir()
                (actual / "SKILL.md").write_bytes(SKILL)
                source = root / ".agents/skills/gotcha-distill"
                source.parent.mkdir(parents=True)
                if directory:
                    source.symlink_to(actual, target_is_directory=True)
                else:
                    source.mkdir()
                    (source / "SKILL.md").symlink_to(actual / "SKILL.md")
                with self.assertRaisesRegex(ValueError, 'source is a symlink'):
                    package.build(root, root / 'output.zip')
                self.assertFalse((root / 'output.zip').exists())


if __name__ == "__main__":
    unittest.main()
