#!/usr/bin/env python3
"""Assert the gotcha contract: AGENTS.md trigger index <-> docs/gotchas/ parity.

The index in AGENTS.md is the always-loaded layer; the domain files under
docs/gotchas/ are lazy-loaded. This script asserts they cannot drift apart:

  1. AGENTS.md exists and carries a "## Environment gotchas" section.
  2. Every "### ... `docs/gotchas/<file>.md` ..." heading names a file that
     exists (under the configured gotchas directory, not just any path) AND
     carries a "when touching ..." trigger clause specific enough to route a
     task (a backticked path/glob, or at least three words).
  3. Every index bullet under a domain heading has an identical "## " title
     in that domain file. A bullet may carry a trailing "(annotation)" that
     the title does not; the exact form is tried first, then the stripped one.
  4. Every "## " title in a referenced domain file has an identical index bullet.
  5. No duplicate titles on either side, per domain; no domain declared twice.
  6. Every docs/gotchas/*.md on disk (except README.md) is referenced by a
     domain heading — no orphan files.
  7. No index bullet appears in the section before the first domain heading.
  8. Every docs/postmortems/<file>.md cited in a domain file exists.
  9. Every entry carries a YYYY-MM-DD date (disable with --no-require-dates
     while backfilling a legacy repository).
 10. Every copy of the skill's SKILL.md has the right name and a single-line
     description within budget, and all copies are byte-identical.
 11. Every domain file opens with front matter carrying `domain`, `triggers`
     and a YYYY-MM-DD `updated` date. scripts/gen-llms-txt.py reads it, so a
     missing header is a file the generated index cannot describe.
 12. Every entry states what it cost (only when the repository opts in via
     `[index] require_cost = true` or `--require-cost`).

Exit 0 when the contract holds, 1 with one line per violation otherwise.
`--selftest` builds a synthetic fixture, asserts it is clean, then applies
named mutations and asserts each one trips its check.

Paths, the index heading and the skill name can be overridden in gotcha.toml
at the repository root; every key is optional and defaults to the layout this
repository uses, so a repo without the file behaves exactly as before.

Stdlib only. Python 3.11+ (tomllib).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

SECTION_PREFIX = "## Environment gotchas"
SECTION_CLOSE_RE = re.compile(r"^#{1,2} ")
ANNOTATION_RE = re.compile(r"\s*\([^)]*\)$")
# A syntax heuristic, not proof of impact. Accept an explicit Cost: field,
# "cost a ..." / "cost 35 ...", or time spent/lost with a quantity and unit.
# Cost: unmeasured is intentional: never invent a number to satisfy a check.
_QUANTITY = r"(?:\d+(?:\.\d+)?|a|an|one|two|three)"
_DURATION = rf"{_QUANTITY}[ -](?:seconds?|minutes?|hours?|days?|weeks?)\b"
COST_RE = re.compile(
    rf"\bcost:\s*\S|\bcost(?:s)?\s+(?:{_QUANTITY}\b|\$\d+)"
    rf"|\b(?:took|spent|lost|wasted|delayed(?:\s+by)?)\s+{_DURATION}"
    rf"|\b{_DURATION}\s+(?:of\s+)?(?:investigation|detour|outage|downtime|rework|recovery|delay)\b",
    re.IGNORECASE,
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
POSTMORTEM_REF_RE = re.compile(r"docs/postmortems/[\w.-]+\.md")
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
BLOCK_SCALAR_RE = re.compile(r"^[>|][+-]?\s*$")
GOTCHAS_DIR = Path("docs/gotchas")

SKILL_NAME = "gotcha-distill"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# A deliberate always-loaded budget, not a vendor limit (Claude Code truncates
# description + when_to_use at 1,536 characters).
SKILL_DESC_MAX_CHARS = 512
SKILL_SEARCH_DIRS = (".agents/skills", ".claude/skills", ".opencode/skills", ".cursor/skills")
FRONTMATTER_KEYS = ("domain", "triggers", "updated")
CONFIG_FILE = "gotcha.toml"


@dataclass(frozen=True)
class Config:
    """Layout of the repository being checked. Defaults are this repo's layout."""

    name: str = ""  # empty means "use the directory name"
    contract: str = "AGENTS.md"
    gotchas: str = str(GOTCHAS_DIR)
    postmortems: str = "docs/postmortems"
    heading: str = SECTION_PREFIX
    skill_name: str = SKILL_NAME
    description_max_chars: int = SKILL_DESC_MAX_CHARS
    require_cost: bool = False  # assert every entry states what it cost

    @property
    def postmortem_ref_re(self) -> re.Pattern[str]:
        return re.compile(rf"{re.escape(self.postmortems)}/[\w.-]+\.md")


def load_config(root: Path) -> Config:
    """Read gotcha.toml if present. Absent file, or absent key, means the default."""
    path = root / CONFIG_FILE
    if not path.is_file():
        return Config()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    project = raw.get("project", {})
    paths = raw.get("paths", {})
    index = raw.get("index", {})
    skill = raw.get("skill", {})
    base = Config()
    return Config(
        name=project.get("name", base.name),
        contract=paths.get("contract", base.contract),
        gotchas=paths.get("gotchas", base.gotchas),
        postmortems=paths.get("postmortems", base.postmortems),
        heading=index.get("heading", base.heading),
        require_cost=index.get("require_cost", base.require_cost),
        skill_name=skill.get("name", base.skill_name),
        description_max_chars=skill.get("description_max_chars", base.description_max_chars),
    )


# ---- parsing ---------------------------------------------------------------

def read_text(path: Path) -> str:
    """UTF-8 with an optional BOM, line endings normalised to LF."""
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def unfenced_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield (lineno, line) for lines outside fenced code blocks.

    A fence closes only on the same delimiter character that opened it, so a
    ``` block may contain a ~~~ line and vice versa.
    """
    fence: str | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = FENCE_RE.match(line)
        if m:
            token = m.group(1)[0]
            if fence is None:
                fence = token
            elif fence == token:
                fence = None
            continue
        if fence is None:
            yield lineno, line


def domain_h3_re(gotchas: str) -> re.Pattern[str]:
    """Match a domain heading, capturing the literal path and the file name.

    Match the routing target immediately after "read", never a later trigger
    path. parse_index rejects every H3 that does not match this shape.
    """
    return re.compile(rf"^### [^`]*?\bread\s+`({re.escape(gotchas)}/([\w.-]+\.md))`(?=\s|$)")


def trigger_clause_error(line: str) -> str | None:
    """Validate the "when touching ..." clause routes to something concrete.

    Returns an error message, or None when the clause is specific enough. A
    clause is accepted when it names a complete backticked path/glob, or when
    it has at least three words. This is a syntax floor, not a semantic test
    that the trigger will match the right tasks.
    """
    m = re.search(r"\bwhen touching\s+(.+)$", line)
    if not m:
        return ('domain heading has no "when touching ..." trigger clause; '
                "an index nobody can match to a task routes nothing")
    clause = m.group(1)
    tokens = re.findall(r"(?<!`)`([^`\s]+)`(?!`)", clause)
    paths = [t for t in tokens if re.search(r"[\w]", t) and (
        re.search(r"[/.*?\[\]]", t) or t in {"Dockerfile", "Makefile", "LICENSE"}
    )]
    if paths or len(re.findall(r"\b[\w]+(?:-[\w]+)*\b", clause)) >= 3:
        return None
    return (f"trigger clause is too vague to route a task: {clause!r} "
            "(name a backticked path/glob, or use at least three words)")


def parse_index(
    text: str,
    heading: str = SECTION_PREFIX,
    gotchas: str = "docs/gotchas",
) -> tuple[dict[str, list[str]], list[str]]:
    """Return ({domain file: [raw bullet titles]}, errors) from AGENTS.md text.

    The section opens on a line starting with SECTION_PREFIX and closes at the
    next H1 or H2. Domain headings must backtick-quote the file path and carry
    a "when touching ..." trigger clause. HTML comments are blanked (line count
    preserved) and fenced code blocks are skipped, so templates can carry
    examples without declaring domains.
    """
    index: dict[str, list[str]] = {}
    errors: list[str] = []
    in_section = False
    found_section = False
    current: str | None = None

    text = HTML_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    h3 = domain_h3_re(gotchas)
    for lineno, line in unfenced_lines(text):
        if line.startswith(heading):
            in_section = True
            found_section = True
            current = None
            continue
        if in_section and SECTION_CLOSE_RE.match(line):
            in_section = False
            current = None
        if not in_section:
            continue
        m = h3.match(line)
        if m:
            current = m.group(2)
            if current in index:
                errors.append(f"AGENTS.md:{lineno}: domain {gotchas}/{current} is declared twice in the index")
            trigger_err = trigger_clause_error(line)
            if trigger_err:
                errors.append(f"AGENTS.md:{lineno}: {trigger_err}")
            index.setdefault(current, [])
            continue
        if line.startswith("### "):
            current = None
            errors.append(
                f"AGENTS.md:{lineno}: invalid domain heading; expected "
                f"read `{gotchas}/<file>.md` when touching <triggers>"
            )
            continue
        if line.startswith("- "):
            title = line[2:].strip()
            if current is None:
                errors.append(
                    f"AGENTS.md:{lineno}: index line appears before any domain heading: {title!r}"
                )
                continue
            index[current].append(title)

    if not found_section:
        errors.append(
            f"AGENTS.md must carry the gotcha trigger index (a section starting {heading!r})"
        )
    return index, errors


def parse_entries(text: str) -> list[tuple[str, str]]:
    """Return [(H2 title, body text)] for a domain file, ignoring fenced blocks."""
    entries: list[tuple[str, list[str]]] = []
    for _, line in unfenced_lines(text):
        if line.startswith("## "):
            entries.append((re.sub(r"^##\s+", "", line).strip(), []))
        elif entries:
            entries[-1][1].append(line)
    return [(title, "\n".join(body)) for title, body in entries]


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


def check(
    root: Path,
    *,
    require_dates: bool = True,
    skill_name: str | None = None,
    require_cost: bool | None = None,
    config: Config | None = None,
) -> list[str]:
    cfg = config or Config()
    if skill_name is not None:
        cfg = Config(**{**cfg.__dict__, "skill_name": skill_name})
    if require_cost is not None:
        cfg = Config(**{**cfg.__dict__, "require_cost": require_cost})
    errors: list[str] = []

    agents_path = root / cfg.contract
    if not agents_path.is_file():
        return [f"{cfg.contract} must exist at the repository root (the canonical agent contract)"]

    index, index_errors = parse_index(read_text(agents_path), cfg.heading, cfg.gotchas)
    errors.extend(index_errors)

    for fname, bullets in index.items():
        gpath = root / cfg.gotchas / fname
        rel = f"{cfg.gotchas}/{fname}"
        if not gpath.is_file():
            errors.append(f"{rel} is missing but referenced by the {cfg.contract} index")
            continue
        text = read_text(gpath)
        entries = parse_entries(text)
        h2 = [title for title, _ in entries]
        stripped = {ANNOTATION_RE.sub("", b) for b in bullets}
        accepted = set(bullets) | stripped

        meta = parse_frontmatter(text)
        missing = [k for k in FRONTMATTER_KEYS if not meta.get(k)]
        if missing:
            errors.append(
                f"{rel}: front matter is missing {', '.join(missing)} "
                f"— gen-llms-txt.py has nothing to describe the file with"
            )
        elif not DATE_RE.fullmatch(meta["updated"]):
            errors.append(f"{rel}: front matter 'updated' must be YYYY-MM-DD, got {meta['updated']!r}")

        for b in bullets:
            if b not in h2 and ANNOTATION_RE.sub("", b) not in h2:
                errors.append(f"gotcha index line has NO H2 in {rel}: {b!r}")
        for title in h2:
            if title not in accepted:
                errors.append(f"{rel} H2 has NO index line in {cfg.contract}: {title!r}")
        for title in _dupes(bullets):
            errors.append(f"gotcha index lines for {fname} must be unique; duplicate: {title!r}")
        for title in _dupes(h2):
            errors.append(f"H2 titles in {rel} must be unique; duplicate: {title!r}")

        for ref in sorted(set(cfg.postmortem_ref_re.findall(text))):
            if not (root / ref).is_file():
                errors.append(f"{rel} cites a postmortem that does not exist: {ref}")

        if require_dates:
            for title, body in entries:
                if not DATE_RE.search(body):
                    errors.append(f"{rel}: entry has no YYYY-MM-DD date: {title!r}")

        if cfg.require_cost:
            for title, body in entries:
                if not COST_RE.search(body):
                    errors.append(
                        f"{rel}: entry has no stated cost: {title!r} "
                        "(use Cost: <impact>, cost a <consequence>, or took <quantity> <time unit>)"
                    )

    gdir = root / cfg.gotchas
    if gdir.is_dir():
        for path in sorted(gdir.glob("*.md")):
            if path.name != "README.md" and path.name not in index:
                errors.append(
                    f"{cfg.gotchas}/{path.name} exists but is not referenced by "
                    f"any domain heading in {cfg.contract}"
                )

    errors.extend(_check_skill(root, cfg.skill_name, cfg.description_max_chars))
    return errors


def _check_skill(root: Path, skill_name: str, desc_max: int = SKILL_DESC_MAX_CHARS) -> list[str]:
    copies = [p for d in SKILL_SEARCH_DIRS if (p := root / d / skill_name / "SKILL.md").is_file()]
    if not copies:
        return [f"{skill_name}/SKILL.md not found under any of: {', '.join(SKILL_SEARCH_DIRS)}"]

    canonical = copies[0]
    rel = canonical.relative_to(root)
    errors: list[str] = []
    fm = parse_frontmatter(read_text(canonical))
    name = fm.get("name", "")
    if name != skill_name or not SKILL_NAME_RE.match(name):
        errors.append(f"{rel}: frontmatter name must be {skill_name!r}, got {name!r}")
    desc = fm.get("description", "")
    if not desc:
        errors.append(f"{rel}: frontmatter description is missing")
    elif BLOCK_SCALAR_RE.match(desc):
        errors.append(f"{rel}: frontmatter description must be a single line, not a YAML block scalar")
    elif not desc.startswith(("'", '"')) and re.search(r":\s", desc):
        errors.append(f"{rel}: quote the description: an unquoted colon followed by whitespace is invalid YAML")
    elif len(desc) > desc_max:
        errors.append(
            f"{rel}: frontmatter description is {len(desc)} chars; max {desc_max}"
        )

    canonical_bytes = canonical.read_bytes()
    for other in copies[1:]:
        if other.read_bytes() != canonical_bytes:
            errors.append(
                f"{other.relative_to(root)} differs from {rel} (every copy of the skill must be identical)"
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
~~~
### Still fenced — read `docs/gotchas/still.md` when touching `still/`
```

### Infra — read `docs/gotchas/infra.md` when touching `infra/`
- First lesson
- Second lesson (do not re-investigate)
- Third lesson (staging only)

# An H1 closes the section too
- Not an index line

## Documentation map

- `docs/gotchas/` — lessons.
"""

_FIXTURE_GOTCHA = """---
domain: Infra
triggers: infra/, deploy workflows
updated: 2026-01-01
---

# Gotchas — infra

Preamble.

```markdown
## A fenced heading is not an entry
```

## First lesson

**First lesson** (2026-01-01): body. See
`docs/postmortems/2026-01-01-example.md`.

## Second lesson

**Second lesson** (2026-01-02): body.

## Third lesson (staging only)

**Third lesson** (2026-01-03): a title may legitimately end in a parenthetical.
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
    (root / "docs/postmortems").mkdir(parents=True)
    write(root / "docs/postmortems/2026-01-01-example.md", "# Post-mortem\n")
    skill_dir = root / ".agents/skills" / SKILL_NAME
    skill_dir.mkdir(parents=True)
    write(skill_dir / "SKILL.md", _FIXTURE_SKILL)


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"selftest fixture drift: {old!r} not in {path.name}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _copy_skill_with_drift(root: Path) -> None:
    dst = root / ".claude/skills" / SKILL_NAME
    dst.mkdir(parents=True)
    (dst / "SKILL.md").write_text(_FIXTURE_SKILL + "\nAn extra line.\n", encoding="utf-8")


Mutation = tuple[str, Callable[[Path], None], str]
_SKILL_MD = Path(".agents/skills") / SKILL_NAME / "SKILL.md"

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
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "## Second lesson\n", "## Second lesson\n\nbody (2026-01-02)\n\n## Second lesson\n"),
     "unique"),
    ("undomained-bullet",
     lambda r: _replace(r / "AGENTS.md", "parity is asserted.\n", "parity is asserted.\n- Stray line\n"),
     "before any"),
    ("dupe-domain-heading",
     lambda r: _replace(r / "AGENTS.md", "- Third lesson (staging only)\n",
                        "- Third lesson (staging only)\n### Infra again — read `docs/gotchas/infra.md` when touching `infra/`\n"),
     "declared twice"),
    ("no-trigger-clause",
     lambda r: _replace(r / "AGENTS.md", "### Infra — read `docs/gotchas/infra.md` when touching `infra/`",
                        "### Infra — read `docs/gotchas/infra.md`"),
     "trigger clause"),
    ("vague-trigger",
     lambda r: _replace(r / "AGENTS.md", "when touching `infra/`", "when touching stuff"),
     "too vague"),
    ("unmatched-trigger-backtick",
     lambda r: _replace(r / "AGENTS.md", "when touching `infra/`", "when touching stuff`"),
     "too vague"),
    ("empty-trigger-token",
     lambda r: _replace(r / "AGENTS.md", "when touching `infra/`", "when touching ``"),
     "too vague"),
    ("nonpath-trigger-token",
     lambda r: _replace(r / "AGENTS.md", "when touching `infra/`", "when touching `stuff`"),
     "too vague"),
    ("stale-heading-after-valid-heading",
     lambda r: _replace(r / "AGENTS.md", "- Second lesson",
                        "### Stale — read `elsewhere/missing.md` when touching `infra/`\n- Second lesson"),
     "invalid domain heading"),
    ("missing-section",
     lambda r: _replace(r / "AGENTS.md", "## Environment gotchas", "## Gotchas"),
     "trigger index"),
    ("missing-frontmatter",
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "---\ndomain: Infra\ntriggers: infra/, deploy workflows\nupdated: 2026-01-01\n---\n\n", ""),
     "front matter is missing"),
    ("bad-frontmatter-date",
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "updated: 2026-01-01", "updated: last Tuesday"),
     "must be YYYY-MM-DD"),
    ("dangling-postmortem",
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "2026-01-01-example.md", "2026-01-01-missing.md"),
     "postmortem that does not exist"),
    ("undated-entry",
     lambda r: _replace(r / GOTCHAS_DIR / "infra.md", "(2026-01-02)", "(long ago)"),
     "no YYYY-MM-DD"),
    ("skill-name-mismatch",
     lambda r: _replace(r / _SKILL_MD, "name: gotcha-distill", "name: gotcha_distill_x"),
     "frontmatter name must be"),
    ("skill-desc-bloat",
     lambda r: _replace(r / _SKILL_MD, "non-trivial.", "non-trivial. " + "x" * SKILL_DESC_MAX_CHARS),
     "description"),
    ("folded-description",
     lambda r: _replace(r / _SKILL_MD,
                        "description: Distill a bug into a gotcha. Use after fixing anything non-trivial.",
                        "description: >\n  Distill a bug into a gotcha. Use after fixing anything non-trivial."),
     "single line"),
    ("unquoted-description-colon",
     lambda r: _replace(r / _SKILL_MD, "description: Distill", "description: Incident: Distill"),
     "invalid YAML"),
    ("skill-copy-drift",
     _copy_skill_with_drift,
     "differs"),
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

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_fixture(root)
        _replace(root / GOTCHAS_DIR / "infra.md", "(2026-01-02)", "(long ago)")
        if check(root, require_dates=False):
            failures.append("--no-require-dates did not disable the date check")

    # require_cost: a stated cost is asserted only when the repo opts in.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_fixture(root)
        if not check(root, require_cost=True):
            failures.append("require_cost=True did not flag a costless entry")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_fixture(root)
        for old, new in (
            ("(2026-01-01): body", "(2026-01-01): body, cost a 5-minute detour"),
            ("(2026-01-02): body", "(2026-01-02): body, cost a 2-hour outage"),
            ("(2026-01-03): a title", "(2026-01-03): cost a day of rework; a title"),
        ):
            _replace(root / GOTCHAS_DIR / "infra.md", old, new)
        if check(root, require_cost=True):
            failures.append("require_cost=True flagged entries that state a cost")

    # configurable gotchas path: an honest heading passes, a lying one fails.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_fixture(root)
        shutil.move(str(root / GOTCHAS_DIR), str(root / "lessons"))
        cfg = Config(gotchas="lessons")
        if not check(root, config=cfg):
            failures.append("configurable path: a docs/gotchas heading should fail once gotchas=lessons")
        _replace(root / "AGENTS.md", "`docs/gotchas/infra.md`", "`lessons/infra.md`")
        if check(root, config=cfg):
            failures.append("configurable path: an honest lessons/ heading should pass")
        _replace(root / "AGENTS.md", "- Second lesson",
                 "### Stale — read `docs/gotchas/missing.md` when touching `infra/`\n- Second lesson")
        parsed, errors = parse_index(read_text(root / "AGENTS.md"), gotchas="lessons")
        if not any("invalid domain heading" in e for e in errors):
            failures.append("configurable path: stale heading after valid heading was accepted")
        if parsed.get("infra.md") != ["First lesson"]:
            failures.append("configurable path: stale heading leaked bullets into previous domain")

    for clause in ("`src/`", "`*.py`", "`gotcha.toml`", "`Dockerfile`", "cross-account IAM policies"):
        if trigger_clause_error(f"### Infra — read `docs/gotchas/infra.md` when touching {clause}"):
            failures.append(f"valid trigger rejected: {clause}")

    # Exercise the whole entry check, including ordinary plurals and incidental
    # time words. These samples are synthetic prose, not live system output.
    cost_cases = [
        ("Investigation took 35 minutes.", True),
        ("Recovery took 2 hours.", True),
        ("We lost one day.", True),
        ("A 35-minute detour.", True),
        ("Cost: $12 in wasted compute.", True),
        ("Cost: unmeasured; prevented a failed deploy.", True),
        ("Prefer blue buttons every day.", False),
        ("Read whatever file is current that day.", False),
        ("Rotate keys every 2 hours.", False),
        ("Discuss cost optimization and outage handling.", False),
        ("Cost:   ", False),
    ]
    for body, accepted in cost_cases:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _build_fixture(root)
            path = root / GOTCHAS_DIR / "infra.md"
            preamble = _FIXTURE_GOTCHA.split("## First lesson")[0]
            path.write_text(preamble + "\n".join(
                f"## {title}\n\n(2026-01-01): {body}\n"
                for title in ("First lesson", "Second lesson", "Third lesson (staging only)")
            ), encoding="utf-8")
            errors = check(root, require_cost=True)
            if (not errors) != accepted:
                failures.append(f"cost form {body!r}: expected accepted={accepted}, got {errors!r}")

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
        if (candidate / "AGENTS.md").is_file() or (candidate / CONFIG_FILE).is_file():
            return candidate
    return start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=None,
                        help="repository root (default: nearest ancestor of cwd containing AGENTS.md)")
    parser.add_argument("--skill-name", default=None,
                        help=f"override the skill directory name (default: {CONFIG_FILE} or {SKILL_NAME})")
    parser.add_argument("--no-require-dates", dest="require_dates", action="store_false",
                        help="do not require a YYYY-MM-DD date in every entry (for backfilling legacy repos)")
    parser.add_argument("--require-cost", dest="require_cost", action="store_true", default=None,
                        help="require every entry to state what it cost (overrides [index] require_cost)")
    parser.add_argument("--selftest", action="store_true",
                        help="run the fixture-mutation selftest instead of checking a repository")
    parser.add_argument("--quiet", action="store_true", help="print nothing on success")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    root = (args.root or find_root(Path.cwd())).resolve()
    cfg = load_config(root)
    errors = check(root, require_dates=args.require_dates, skill_name=args.skill_name,
                   require_cost=args.require_cost, config=cfg)
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
