# Preparing a release

GitHub's automatic **Source code (zip)** is a repository snapshot. Claude web
uploads use the separate **gotcha-distill.zip** asset, containing exactly:

```text
gotcha-distill/
├── SKILL.md
└── LICENSE
```

The web package teaches the distillation procedure. Repository installation
provides the contract scripts and scaffolding; it remains a separate path.

## Validation and delivery

1. Run the validation commands in `AGENTS.md`, including the YAML test and
   packaging regression suite. Generate `llms.txt` if its inputs changed.
2. Build with `python3 scripts/build-skill-zip.py`, then run
   `python3 scripts/build-skill-zip.py --check dist/gotcha-distill.zip`.
   The checker verifies layout, file types, unique membership, and bytes against
   the checkout. It does not simulate Claude's upload service.
3. Upload that exact ZIP to Claude web and enable the skill. Try a prompt such as
   “This repository bug is fixed; use the supplied diff and incident evidence to
   draft a reusable lesson and its trigger index.” Check that it uses supplied
   facts, and reports unavailable repository checks as pending. Record the date,
   artifact SHA-256, and observed result; do not claim success from local checks.
4. Keep the code, gotcha, index, and generated docs in one commit. Tag the reviewed
   revision only when release publication is authorized. Build the release ZIP
   from that revision, verify its bytes match the tested candidate, and attach
   it as `gotcha-distill.zip` with release notes describing the actual verification.

CI saves the ZIP in an Actions artifact named `claude-skill-package`. GitHub
wraps Actions downloads in another ZIP: extract that wrapper and use the inner
`gotcha-distill.zip`. Neither the wrapper nor **Source code (zip)** is the upload
asset. CI does not publish a release automatically.

## v0.2.2 release notes

Fix Claude web packaging by providing a dedicated `gotcha-distill.zip` with
one skill entrypoint and no symlinks. Download this asset for web uploads;
use the repository source for coding-agent installation.

The package builder, archive regression tests, and CI artifact cover the
two failures observed in v0.2.0/v0.2.1. The skill clarifies how to draft changes
when repository access is unavailable. Its description now fits a
200-character budget.

Verification: local structural checks passed. On 2026-10-22, the owner confirmed
successful Claude web upload of the candidate and supplied a screenshot showing
the skill enabled with `SKILL.md` and `LICENSE`. Invocation behavior remains
untested; upload acceptance alone does not establish task effectiveness. See the
[release review](postmortems/2026-10-22-claude-upload-packaging.md).

## Historical release corrections

Preserve the original change lists and tags. Append the following corrections
dated 2026-10-22, linking to the dedicated asset in
[v0.2.2](https://github.com/jeanguirro/gotcha-distill/releases/tag/v0.2.2).

**v0.2.0:** The automatic source ZIP is not a Claude web upload package: it
contains symlinks and the repository layout. No dedicated web-upload asset was
attached to this release. Repository installation and web upload are separate
distribution paths.

**v0.2.1:** This release removed symlinks but did not complete the Claude web
upload fix. Its source ZIP contains two `SKILL.md` files and was reported
rejected. No dedicated upload asset was attached, and a successful web upload
was not verified for this release. Use the dedicated `gotcha-distill.zip` asset
from v0.2.2, whose upload and enablement the owner confirmed.
