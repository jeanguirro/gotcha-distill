#!/usr/bin/env python3
"""Measure gotcha-distill adoption and health across a fleet of repositories.

Read-only: it never writes to the repositories it inspects. For each sibling
directory under --fleet-root that carries the canonical contract
(scripts/assert-agent-workflow.py), it reports volume, contract health, token
economics, provenance and skill drift, as a table or --json.

Two contract results are reported per repo, because the fleet is not uniform:

  self      the repo's own copy of the contract, run by the repo itself
  canonical the fleet-canonical contract (this repo's copy) run against it —
            this is the one that shows a repo still on an older format

"canonical" failing on photos_backup is expected: it is the originating repo
and still uses the pre-date/pre-front-matter format its own older contract
copy accepts.

Stdlib only. Python 3.11+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent  # the gotcha-distill repository (fleet canonical)
CANONICAL_ASSERT = HERE / "assert-agent-workflow.py"
CANONICAL_SKILL = REPO / ".agents" / "skills" / "gotcha-distill" / "SKILL.md"
CONTRACT_NAME = "assert-agent-workflow.py"

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MONTH_RE = re.compile(r"\b(\d{4}-\d{2})-\d{2}\b")
COST_RE = re.compile(r"\b(cost|minute|hour|day|outage|downtime)\b|\$\d+", re.IGNORECASE)
GOTCHAS_DIR = Path("docs/gotchas")
POSTMORTEMS_DIR = Path("docs/postmortems")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def skill_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8] if path.is_file() else "-"


def gotcha_index_bytes(agents_path: Path) -> int:
    """Bytes of the always-loaded gotcha trigger index in AGENTS.md."""
    out: list[str] = []
    in_section = False
    for line in read_text(agents_path).splitlines():
        if line.startswith("## Environment gotchas"):
            in_section = True
            continue
        if in_section and re.match(r"^## ", line):
            break
        if in_section:
            out.append(line)
    return len("\n".join(out).encode("utf-8"))


def contract_result(script: Path, repo: Path) -> str:
    if not script.is_file():
        return "no-script"
    proc = subprocess.run(
        [sys.executable, str(script), "--root", str(repo)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode == 0:
        return "hold"
    m = re.search(r"VIOLATED \((\d+)\)", proc.stderr)
    return f"violate-{m.group(1)}" if m else f"fail({proc.returncode})"


def scan(repo: Path) -> dict:
    agents = repo / "AGENTS.md"
    gotchas = repo / GOTCHAS_DIR
    postmortems = repo / POSTMORTEMS_DIR

    entries: list[tuple[str, str]] = []  # (title, body)
    domain_files = 0
    lazy_bytes = 0
    months: dict[str, int] = {}
    for f in sorted(gotchas.glob("*.md")):
        if f.name == "README.md":
            continue
        domain_files += 1
        text = read_text(f)
        lazy_bytes += len(text.encode("utf-8"))
        current: str | None = None
        body: list[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                if current is not None:
                    entries.append((current, "\n".join(body)))
                current = line[3:].strip()
                body = []
            elif current is not None:
                body.append(line)
        if current is not None:
            entries.append((current, "\n".join(body)))
        for m in MONTH_RE.finditer(text):
            months[m.group(1)] = months.get(m.group(1), 0) + 1

    dated = sum(1 for _, body in entries if DATE_RE.search(body))
    costed = sum(1 for _, body in entries if COST_RE.search(body))
    reinc = read_text(agents).count("do not re-investigate")
    index_bytes = gotcha_index_bytes(agents)
    ratio = round(lazy_bytes / index_bytes, 1) if index_bytes else 0.0

    skill = repo / ".agents" / "skills" / "gotcha-distill" / "SKILL.md"
    if not skill.is_file():
        for alt in (".claude", ".opencode"):
            candidate = repo / alt / "skills" / "gotcha-distill" / "SKILL.md"
            if candidate.is_file():
                skill = candidate
                break
    canonical_md5 = skill_md5(CANONICAL_SKILL)

    postmortem_count = (
        len([p for p in postmortems.glob("*.md") if p.name != "README.md"])
        if postmortems.is_dir() else 0
    )

    return {
        "name": repo.name,
        "gotchas": len(entries),
        "domain_files": domain_files,
        "postmortems": postmortem_count,
        "index_bytes": index_bytes,
        "index_tokens": index_bytes // 4,
        "lazy_bytes": lazy_bytes,
        "ratio": ratio,
        "dated": dated,
        "costed": costed,
        "do_not_reinvestigate": reinc,
        "skill_md5": skill_md5(skill),
        "skill_drift": skill_md5(skill) != canonical_md5,
        "self": contract_result(repo / "scripts" / CONTRACT_NAME, repo),
        "canonical": contract_result(CANONICAL_ASSERT, repo),
        "months": dict(sorted(months.items())),
    }


def render_table(rows: list[dict]) -> str:
    head = (
        "repo               gotchas domains pm  index   idxTok lazy    ratio "
        "dated costed rinv  skill   self       canonical"
    )
    out = [head, "-" * len(head)]
    for r in rows:
        out.append(
            f"{r['name']:<18} {r['gotchas']:>7} {r['domain_files']:>6} {r['postmortems']:>3} "
            f"{r['index_bytes']:>5}B {r['index_tokens']:>5} {r['lazy_bytes']:>5}B "
            f"{r['ratio']:>6} {r['dated']:>5} {r['costed']:>6} {r['do_not_reinvestigate']:>4} "
            f"{r['skill_md5']:>8} {r['self']:<10} {r['canonical']}"
        )
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fleet-root", type=Path, default=REPO.parent,
                        help="directory of repositories to scan (default: the gotcha-distill repo's parent)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit a single JSON document instead of a table")
    args = parser.parse_args()

    fleet = args.fleet_root.resolve()
    rows: list[dict] = []
    for child in sorted(fleet.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "scripts" / CONTRACT_NAME).is_file():
            continue
        if not (child / "AGENTS.md").is_file():
            continue
        rows.append(scan(child))

    if args.as_json:
        print(json.dumps(rows, indent=2))
        return 0

    if not rows:
        print(f"no canonical repos found under {fleet}", file=sys.stderr)
        return 1
    print(render_table(rows))
    print()
    drift = [r["name"] for r in rows if r["skill_drift"]]
    noncanon = [r["name"] for r in rows if r["canonical"] != "hold"]
    print(f"{len(rows)} repos; skill drift: {', '.join(drift) or 'none'}; "
          f"non-canonical format: {', '.join(noncanon) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
