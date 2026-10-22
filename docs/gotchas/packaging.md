---
domain: Skill packaging
triggers: scripts/build-skill-zip.py, .github/workflows/, release upload instructions
updated: 2026-10-22
---

# Gotchas — skill packaging

## Validate the upload ZIP separately from the repository source archive

**Validate the upload ZIP separately from the repository source archive**
(2026-10-22, recording date). Cost: unmeasured; the owner reported failed
Claude web uploads for v0.2.0 and v0.2.1. Inspection of the published source
archives confirmed two symlinks in v0.2.0 and two `SKILL.md` files in v0.2.1:
replacing the Claude Code bridge with a file cleared one restriction while
violating another. Neither release had a dedicated upload asset. Build from
an explicit manifest with `scripts/build-skill-zip.py`; check the resulting ZIP
for one skill at the expected root, regular files, exact membership and source
bytes. Keep repository discovery copies out of the upload artifact, and
distinguish structural checks from an actual UI smoke test. The owner later
confirmed successful upload and enablement of the corrected candidate;
invocation behavior remains untested. See
`docs/postmortems/2026-10-22-claude-upload-packaging.md`.
