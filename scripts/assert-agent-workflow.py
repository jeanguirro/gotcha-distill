#!/usr/bin/env python3
"""Assert the gotcha contract: AGENTS.md trigger index <-> docs/gotchas/ parity.

The index in AGENTS.md is the always-loaded layer; the domain files under
docs/gotchas/ are lazy-loaded. This script asserts they cannot drift apart:

  1. AGENTS.md exists and carries a "## Environment gotchas" section.
  2. Every "### ... `docs/gotchas/<file>.md` ..." heading names a file that exists.
  3. Every index bullet under a domain heading has an identical "## " title
     in that domain file.
  4. Every "## " title in a referenced domain file has an identical index bullet.
  5. No duplicate titles on either side, per domain.
  6. Every docs/gotchas/*.md on disk (except README.md) is referenced by a
     domain heading — no orphan files.
  7. No index bullet appears in the section before the first domain heading.
  8. The gotcha-distill SKILL.md frontmatter has the right name and a
     description within budget.

Exit 0 when the contract holds, 1 with one line per violation otherwise.
`--selftest` builds a synthetic fixture, asserts it is clean, then applies
named mutations and asserts each one trips its check.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable

SECTION_PREFIX = "## Environment gotchas"
SECTION_CLOSE_RE = re.compile(r"^#{1,2} ")
DOMAIN_H3_RE = re.compile(r"^### .*`docs/gotchas/([\w.-]+\.md)`")
ANNOTATION_RE = re.compile(r"\s*\([^)]*\)$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
BLOCK_SCALAR_RE = re.compile(r"^[>|][+-]?\s*$")
GOTCHAS_DIR = Path("docs/gotchas")

SKILL_NAME = "gotcha-distill"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_DESC_MAX_CHARS = 400
SKILL_SEARCH_DIRS = (".agents/skills", ".claude/skills", ".opencode/skills", ".cursor/skills")


# ---- parsing ---------------------------------------------------------------

def read_text(path: Path) -> str:
    """UTF-8 with an optional BOM, line endings normalised to LF."""
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def parse_index(text: str) -> tuple[dict[str, list[str]], list[str]]:
    """Return ({domain file: [bullet titles]}, errors) from AGENTS.md text.

    The section opens on a line starting with SECTION_PREFIX and closes at the
    next H1 or H2. Domain headings must backtick-quote the file path. A
    trailing "(annotation)" on a bullet is a hint, not part of the title.
    HTML comments are blanked (line count preserved) and fenced code blocks
    are skipped, so templates can carry examples without declaring domains.
    """
    index: dict[str, list[str]] = {}
    errors: list[str] = []
    in_section = False
    in_fence = False
    found_section = False
    current: str | None = None

    text = HTML_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    for lineno, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith(SECTION_PREFIX):
            in_section = True
            found_section = True
            continue
        if in_section and SECTION_CLOSE_RE.match(line):
            in_section = False
            current = None
        if not in_section:
            continue
        m = DOMAIN_H3_RE.match(line)
        if m:
            current = m.group(1)
            if current in index:
                errors.append(f"AGENTS.md:{lineno}: domain {GOTCHAS_DIR}/{current} is declared twice in the index")
            index.setdefault(current, [])
            continue
        if line.startswith("- "):
            title = ANNOTATION_RE.sub("", line[2:].strip())
            if current is None:
                errors.append(
                    f"AGENTS.md:{lineno}: index line appears before any domain heading: {title!r}"
                )
                continue
            index[current].append(title)

    if not found_section:
        errors.append(
            f"AGENTS.md must carry the gotcha trigger index (a section starting {SECTION_PREFIX!r})"
        )
    return index, errors


def parse_h2(text: str) -> list[str]:
    titles: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith("## "):
            titles.append(re.sub(r"^##\s+", "", line).strip())
    return titles


def parse_frontmatter(text: str) -> dict[str, str]:
    """Return top-level scalar keys from a YAML frontmatter block. Nested keys are ignored."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km:
            out[km.group(1)] = km.group(2).strip()
    return out


# ---- checks ----------------------------------------------------------------

def _dupes(items: list[str]) -> list[str]:
    return sorted({t for t in items if items.count(t) > 1})


def check(root: Path) -> list[str]:
    errors: list[str] = []

    agents_path = root / "AGENTS.md"
    if not agents_path.is_file():
        return ["AGENTS.md must exist at the repository root (the canonical agent contract)"]

    index, index_errors = parse_index(read_text(agents_path))
    errors.extend(index_errors)

    for fname, bullets in index.items():
        gpath = root / GOTCHAS_DIR / fname
        if not gpath.is_file():
            errors.append(f"{GOTCHAS_DIR}/{fname} is missing but referenced by the AGENTS.md index")
            continue
        h2 = parse_h2(read_text(gpath))
        for title in bullets:
            if title not in h2:
                errors.append(f"gotcha index line has NO H2 in {GOTCHAS_DIR}/{fname}: {title!r}")
        for title in h2:
            if title not in bullets:
                errors.append(f"{GOTCHAS_DIR}/{fname} H2 has NO index line in AGENTS.md: {title!r}")
        for title in _dupes(bullets):
            errors.append(f"gotcha index lines for {fname} must be unique; duplicate: {title!r}")
        for title in _dupes(h2):
            errors.append(f"H2 titles in {GOTCHAS_DIR}/{fname} must be unique; duplicate: {title!r}")

    gdir = root / GOTCHAS_DIR
    if gdir.is_dir():
        for path in sorted(gdir.glob("*.md")):
            if path.name != "README.md" and path.name not in index:
                errors.append(
                    f"{GOTCHAS_DIR}/{path.name} exists but is not referenced by any domain heading in AGENTS.md"
                )

    errors.extend(_check_skill(root))
    return errors


def _check_skill(root: Path) -> list[str]:
    skill_path = next(
        (p for d in SKILL_SEARCH_DIRS if (p := root / d / SKILL_NAME / "SKILL.md").is_file()),
        None,
    )
    if skill_path is None:
        return [f"{SKILL_NAME}/SKILL.md not found under any of: {', '.join(SKILL_SEARCH_DIRS)}"]

    fm = parse_frontmatter(read_text(skill_path))
    rel = skill_path.relative_to(root)
    errors: list[str] = []
    name = fm.get("name", "")
    if name != SKILL_NAME or not SKILL_NAME_RE.match(name):
        errors.append(f"{rel}: frontmatter name must be {SKILL_NAME!r}, got {name!r}")
    desc = fm.get("description", "")
    if not desc:
        errors.append(f"{rel}: frontmatter description is missing")
    elif BLOCK_SCALAR_RE.match(desc):
        errors.append(f"{rel}: frontmatter description must be a single line, not a YAML block scalar")
    elif len(desc) > SKILL_DESC_MAX_CHARS:
        errors.append(
            f"{rel}: frontmatter description is {len(desc)} chars; max {SKILL_DESC_MAX_CHARS}"
        )
    return errors


# ---- selftest --------------------------------------------------------------

_FIXTURE_AGENTS = """# AGENTS.md

## Agent rules

**1.** Rule one.

## Environment gotchas — trigger index (full text lazy-loaded in `docs/gotchas/`)

Intro paragraph. The count is hand-kept; parity is asserted.

<!-- A commented-out example must be ignored by the parser:
### Example — read `docs/gotchas/example.md` when touching `example/`
- Example lesson
-->

```markdown
### Fenced — read `docs/gotchas/fenced.md` when touching `fenced/`
- Fenced lesson
```

### Infra — read `docs/gotchas/infra.md` when touching `infra/`
- First lesson
- Second lesson (do not re-investigate)

# An H1 closes the section too
- Not an index line

## Documentation map

- `docs/gotchas/` — lessons.
"""

_FIXTURE_GOTCHA = """# Gotchas — infra

Preamble.

```markdown
## A fenced heading is not an entry
```

## First lesson

**First lesson** (2026-01-01): body.

## Second lesson

**Second lesson** (2026-01-02): body.
"""

_FIXTURE_SKILL = """---
name: gotcha-distill
description: Distill a bug into a gotcha. Use after fixing anything non-trivial.
license: MIT
---

# Body
"""


def _build_fixture(root: Path, crlf: bool = False, bom: bool = False) -> None:
    def write(path: Path, text: str) -> None:
        if crlf:
            text = text.replace("\n", "\r\n")
        path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))

    write(root / "AGENTS.md", _FIXTURE_AGENTS)
    (root / GOTCHAS_DIR).mkdir(parents=True)
    write(root / GOTCHAS_DIR / "infra.md", _FIXTURE_GOTCHA)
    write(root / GOTCHAS_DIR / "README.md", "# Gotchas\n")
    skill_dir = root / ".agents/skills" / SKILL_NAME
    skill_dir.mkdir(parents=True)
    write(skill_dir / "SKILL.md", _FIXTURE_SKILL)


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"selftest fixture drift: {old!r} not in {path.name}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


Mutation = tuple[str, Callable[[Path], None], str]

_MUTATIONS: list[Mutation] = [
    ("gotcha-index-drift",
     lambda r: _replace(r / "AGENTS.md", "- First lesson\n", "- First lesson\n- A gotcha that exists in no file\n"),
     "NO H2"),
    ("gotcha-file-drift",
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "## Second lesson", "## Second lesson renamed"),
     "NO index line"),
    ("missing-domain-file",
     lambda r: (r / GOTCHAS_DIR / "infra.md").unlink(),
     "missing"),
    ("orphan-file",
     lambda r: (r / GOTCHAS_DIR / "orphan.md").write_text("# Orphan\n\n## Lost lesson\n", encoding="utf-8"),
     "not referenced"),
    ("dupe-index-bullet",
     lambda r: _replace(r / "AGENTS.md", "- First lesson\n", "- First lesson\n- First lesson\n"),
     "unique"),
    ("dupe-h2",
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "## Second lesson\n", "## Second lesson\n\nbody\n\n## Second lesson\n"),
     "unique"),
    ("undomained-bullet",
     lambda r: _replace(r / "AGENTS.md", "parity is asserted.\n", "parity is asserted.\n- Stray line\n"),
     "before any"),
    ("dupe-domain-heading",
     lambda r: _replace(r / "AGENTS.md", "- Second lesson (do not re-investigate)\n",
                        "- Second lesson (do not re-investigate)\n### Infra again — read `docs/gotchas/infra.md` when touching `infra/`\n"),
     "declared twice"),
    ("folded-description",
     lambda r: _replace(r / ".agents/skills" / SKILL_NAME / "SKILL.md",
                        "description: Distill a bug into a gotcha. Use after fixing anything non-trivial.",
                        "description: >\n  Distill a bug into a gotcha. Use after fixing anything non-trivial."),
     "single line"),
    ("missing-section",
     lambda r: _replace(r / "AGENTS.md", "## Environment gotchas", "## Gotchas"),
     "trigger index"),
    ("skill-name-mismatch",
     lambda r: _replace(r / ".agents/skills" / SKILL_NAME / "SKILL.md", "name: gotcha-distill", "name: gotcha_distill_x"),
     "name"),
    ("skill-desc-bloat",
     lambda r: _replace(r / ".agents/skills" / SKILL_NAME / "SKILL.md", "non-trivial.", "non-trivial. " + "x" * SKILL_DESC_MAX_CHARS),
     "description"),
    ("skill-missing",
     lambda r: shutil.rmtree(r / ".agents"),
     "not found"),
]


def selftest() -> int:
    failures: list[str] = []

    for label, kwargs in (("clean", {}), ("crlf", {"crlf": True}), ("bom", {"bom": True})):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_fixture(root, **kwargs)
            clean = check(root)
            if clean:
                failures.append(f"{label} fixture reported errors: " + "; ".join(clean))

    for name, mutate, expected in _MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_fixture(root)
            mutate(root)
            errors = check(root)
            if not any(expected in e for e in errors):
                failures.append(f"{name}: expected an error containing {expected!r}, got {errors!r}")

    if failures:
        print(f"selftest FAILED ({len(failures)}):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"selftest OK ({len(_MUTATIONS)} mutations each trip their check).")
    return 0


# ---- cli -------------------------------------------------------------------

def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "AGENTS.md").is_file():
            return candidate
    return start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None,
                        help="repository root (default: nearest ancestor of cwd containing AGENTS.md)")
    parser.add_argument("--selftest", action="store_true",
                        help="run the fixture-mutation selftest instead of checking a repository")
    parser.add_argument("--quiet", action="store_true", help="print nothing on success")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    root = (args.root or find_root(Path.cwd())).resolve()
    errors = check(root)
    if errors:
        print(f"agent-workflow contract VIOLATED ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"agent-workflow contract holds ({root}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
