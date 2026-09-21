# AGENTS.md — agent contract

<!-- Replace this paragraph with two or three lines on what this repository
     is and the commands an agent needs (build, test, deploy). Keep the two
     sections below: the rules and the gotcha trigger index are what the
     gotcha-distill skill and scripts/assert-agent-workflow.py depend on. -->

This file is read by every coding agent at session start, regardless of
vendor (Claude Code reads it via the `CLAUDE.md` symlink; Cursor, Codex and
OpenCode read `AGENTS.md` directly). It is the always-loaded layer. Keep it
short; the full lessons live in `docs/gotchas/` and load lazily.

If commands, architecture or gotchas changed, update THIS file and commit it
with the code it describes.

## Agent rules (tool-neutral, postmortem-born)

Each rule exists because it was violated and something broke. The cost is
recorded in `docs/postmortems/`.

**1. Never copy live system output into committed source.**
Log lines, API responses and error text may contain credentials, tokens,
signed URLs or personal data. Test fixtures and examples must be synthesised.
If a fixture must mimic real output, replace every value with an inert
placeholder and assert on structure, not on the value.

**2. A predicate over machine-generated text must be validated against a real
captured sample before it ships.**
This includes regexes over error messages, log lines and CLI output. Capture
an actual failing sample, run the predicate against it, and show the result.
Error messages frequently embed the command line that produced them, so a
pattern can match the tool's own arguments.

**3. Docs travel with the code they describe.**
A gotcha is committed in the same commit as the fix that forged it. A lesson
that lands in a later "docs" commit can be reverted, cherry-picked away, or
never merged. The `gotcha-distill` skill is the procedure; the contract in
`scripts/assert-agent-workflow.py` is what CI runs.

## Environment gotchas — trigger index (full text lazy-loaded in `docs/gotchas/`)

2 gotchas, each earned by a production incident or near-miss. (The count is
hand-kept; the index-line ↔ file parity below is ASSERTED by
`scripts/assert-agent-workflow.py`.) The full stories live in
`docs/gotchas/` — this index stays ALWAYS loaded so the hazards are known, and
the moment your task touches a trigger, READ the file before editing.
New gotcha? Add it to the domain file AND its index line here, same commit —
load the `gotcha-distill` skill for the full procedure.

### Infra & AWS — read `docs/gotchas/infra-aws.md` when touching `infra/`, deploy workflows, artifact buckets, or cross-account IAM
- Cross-account S3 answers 403 not 404 for a missing key
- Never deploy from an artifact bucket you do not own

## Documentation map

- `docs/gotchas/` — lazy-loaded lessons, one file per domain.
- `docs/postmortems/` — one file per production incident, written once.
- `.agents/skills/gotcha-distill/SKILL.md` — how to add a gotcha.
- `scripts/assert-agent-workflow.py` — the contract; run it before committing.
