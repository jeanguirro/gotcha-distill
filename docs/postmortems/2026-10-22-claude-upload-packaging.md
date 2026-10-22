# Release review: source archives rejected by Claude web uploads

**Recorded:** 2026-10-22; the upload attempt times were not recorded.
**Trigger:** the owner attempted to upload the v0.2.0 and v0.2.1 source ZIPs
through Claude's web UI.
**Outcome:** both release-source uploads were reported rejected; the corrected
candidate was subsequently uploaded successfully, confirmed by the owner on
2026-10-22. Cost: unmeasured; no duration, affected-user count, or operational
savings are established.

## What happened

The published GitHub release metadata and actual source ZIPs were inspected
on the recording date. Neither release contained an attached upload asset.

| Release | Source revision | Archive inspection | Upload evidence |
|---|---|---|---|
| [v0.2.0](https://github.com/jeanguirro/gotcha-distill/releases/tag/v0.2.0) | `21ef202` | One `SKILL.md`, two symlinks | Owner reported failure; the following release's notes identify a symlink rejection |
| [v0.2.1](https://github.com/jeanguirro/gotcha-distill/releases/tag/v0.2.1) | `2b7607a` | Two `SKILL.md` files, no symlinks | Owner reported rejection because two skill entrypoints were present |

The release timestamps were 2026-10-21 at 22:42 and 22:55 UTC, respectively
(2026-10-22 in the owner's local timezone). v0.2.1 replaced the symlink from
`.claude/skills` to `.agents/skills` with a byte-identical file copy and changed
`CLAUDE.md` into a plain import file. That preserved repository discovery, but
put both discovery copies into GitHub's source ZIP.

## The trigger: repository layout mistaken for an upload package

Repository installation and web upload have different artifact requirements.
The source tree carries agent discovery paths and the project's examples,
tests, and documentation. Claude's uploader needs one skill folder. Removing
symlinks did not turn the entire source tree into that folder.

Anthropic's [packaging guidance](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
describes a ZIP containing a skill-named root folder. The owner supplied the
additional observed constraint that the ZIP contain exactly one `SKILL.md`.
The raw downloaded archives were inspected outside the repository; committed
regression fixtures synthesize these layouts and contain no captured output.

## Blind spots

**Verification covered the repository, not the deliverable.** Contract,
frontmatter, and installer checks could all pass while the source ZIP remained
unsuitable for uploading. v0.2.1 checked the first reported symptom without
validating the complete package or recording a successful UI upload.

**The fix overstated completion.** The v0.2.1 notes accurately describe removing
symlinks, but framing that change as the upload fix implied a working path
that had not been demonstrated. `AGENTS.md` also retained an obsolete reference
to a `CLAUDE.md` symlink, contrary to the repository's documentation rule.

## What changed as a result

`scripts/build-skill-zip.py` now packages an explicit manifest into
`gotcha-distill/SKILL.md` and `gotcha-distill/LICENSE`. It validates the completed
archive, and regression tests cover both failing source layouts. CI builds and
saves the upload ZIP separately from GitHub's automatic source archives.
Installation docs identify the correct artifact and explain that repository
tooling is installed separately. The skill now handles unavailable repository
access explicitly, and its discovery description fits a 200-character local
budget. The fix, this review, the indexed lesson, and generated documentation
are delivered together in the same commit. Release delivery uses v0.2.2 with
the dedicated asset and dated corrections to the v0.2.0/v0.2.1 notes, as specified
in `docs/releases.md`; the prior tags and original change lists are preserved.

## Upload verification

On 2026-10-22, after receiving the corrected `dist/gotcha-distill.zip`, the owner
confirmed that the upload worked. The supplied screenshot shows `gotcha-distill`
enabled in Claude's Skills settings, with `SKILL.md` and `LICENSE` listed and
the revised repository-access guidance visible. This establishes successful
upload and enablement for the tested candidate. It does not show a chat invoking
the skill or completing a distillation task. The screenshot remains outside
the repository; this review records the observation rather than copying UI
output into source.

## Portfolio assessment

This is a bounded release-engineering failure. It does not invalidate the
parser fixes or structural tests in v0.2.0. The evidence supports a portable
repository knowledge layout, executable invariants, regression cases, and one
confirmed Claude web upload. It does not establish reliable skill invocation,
avoided incidents, or time saved. The existing usage report already
distinguishes adoption and byte ratios from those unmeasured outcomes.

Preserve the published tags and commits. Correct the release notes visibly,
then ship the dedicated artifact in a patch release with the upload result and
the limits of that verification stated explicitly.
Deleting or retagging the failed releases would obscure the evidence without
improving reliability. An honest failure review and regression check demonstrate
the same learning loop this project offers; they do not erase the failed uploads.

## Still open

- Exercise a representative distillation prompt with the enabled skill. Record
  the actual outcome before claiming invocation or task-level effectiveness.
- Task-level effectiveness and operational savings remain unmeasured; this
  packaging repair supplies no evidence for those claims.
