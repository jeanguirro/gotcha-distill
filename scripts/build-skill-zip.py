#!/usr/bin/env python3
"""Build or check the dedicated Claude web upload ZIP (stdlib only).

Usage:
    python3 scripts/build-skill-zip.py
    python3 scripts/build-skill-zip.py --check dist/gotcha-distill.zip

This packages the procedure and license. Repository installation and its
validation scripts are distributed separately through the source checkout.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path, PurePosixPath
import stat
import sys
from zipfile import BadZipFile, ZIP_STORED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "gotcha-distill/SKILL.md": ".agents/skills/gotcha-distill/SKILL.md",
    "gotcha-distill/LICENSE": "LICENSE",
}


def payload(root: Path) -> dict[str, bytes]:
    """Use an explicit manifest, never a recursive archive of the repository."""
    result = {}
    for member, relative in FILES.items():
        source = root
        for part in Path(relative).parts:
            source = source / part
            if source.is_symlink():
                raise ValueError(f"package source is a symlink: {relative}")
        result[member] = source.read_bytes()
    return result


def validate(archive: ZipFile, expected: dict[str, bytes]) -> None:
    """Check the finished artifact, including Unix file types and payload bytes."""
    entries = archive.infolist()
    if any(stat.S_ISLNK(entry.external_attr >> 16) for entry in entries):
        raise ValueError("archive contains a symlink")
    skills = [entry for entry in entries
              if PurePosixPath(entry.filename).name == "SKILL.md"]
    if len(skills) != 1:
        raise ValueError(f"expected exactly one SKILL.md; found {len(skills)}")
    names = [entry.filename for entry in entries]
    if len(names) != len(set(names)):
        raise ValueError("archive contains duplicate member names")
    if set(names) != set(expected):
        raise ValueError("archive must contain only gotcha-distill/SKILL.md and gotcha-distill/LICENSE")
    for entry in entries:
        if not stat.S_ISREG(entry.external_attr >> 16):
            raise ValueError(f"archive member is not a regular file: {entry.filename}")
        if archive.read(entry) != expected[entry.filename]:
            raise ValueError(f"archive member differs from source: {entry.filename}")


def build(root: Path, output: Path) -> None:
    expected = payload(root)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
        for name, content in sorted(expected.items()):
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3  # Unix, independent of the build host.
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, content)
    buffer.seek(0)
    with ZipFile(buffer) as archive:
        validate(archive, expected)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(buffer.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--output", type=Path, default=ROOT / "dist/gotcha-distill.zip")
    mode.add_argument("--check", type=Path, metavar="ZIP", help="validate an existing ZIP against this checkout")
    args = parser.parse_args()
    try:
        if args.check:
            with ZipFile(args.check) as archive:
                validate(archive, payload(ROOT))
            print(f"validated {args.check}")
        else:
            build(ROOT, args.output)
            print(f"built and validated {args.output}")
    except (OSError, ValueError, BadZipFile) as error:
        print(f"skill package failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
