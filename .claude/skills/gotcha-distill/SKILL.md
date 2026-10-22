---
name: gotcha-distill
description: "Distill a fixed bug, near-miss, or incident into a repository lesson, trigger index, and parity check. Use for repository-specific hazards; skip routine edits and style preferences."
license: MIT
metadata:
  audience: all agents
  workflow: self-improvement
---

# Gotcha distillation

Turn an observed failure into a lesson a future agent can find before repeating
it. Keep the always-loaded index short; load the relevant domain file when a
task matches its trigger. The contract checks structure, not whether a lesson
is true or whether another agent will use it.

Paths and validation commands below belong to the target repository. The web
upload contains this procedure and its license; install the repository tools
separately for automated checks. If chat has no repository access or the tools
are absent, draft the lesson and index changes from supplied evidence and
report validation as pending. Do not claim files were changed or checks passed.

## Locate the lesson

Read `gotcha.toml` if present. Use its `[paths] contract`, `gotchas`, and
`postmortems` and `[index] heading`; the defaults below are `AGENTS.md`,
`docs/gotchas`, `docs/postmortems`, and `## Environment gotchas`.

Read the relevant index heading and domain file before writing. Extend an
existing entry if it covers the same mechanism; add a new entry only for a
distinct hazard. A repeated investigation may mean the trigger needs repair,
not that another lesson is needed. Skip routine fixes and preferences that
have no reusable, repository-specific lesson.

## Record the evidence

If the incident reached production, use the repository's existing incident
review location and template. Otherwise use `docs/postmortems/YYYY-MM-DD-<slug>.md`
and the guidance in that directory's README. If neither exists, create a
short review with the observed impact, timeline, cause, fix, and unresolved
follow-ups. Cite it from the lesson. A near-miss needs no production postmortem.

Separate observed facts from hypotheses. Record the actual incident date;
if unknown, label the date as the recording date. State measured cost when
available. Otherwise write `Cost: unmeasured` and describe the observed impact
or prevented failure. Never invent duration, money, or production impact to
satisfy the contract.

If the fix introduces a predicate over machine-generated text, check it
against a captured sample without committing that output. Commit synthesized
fixtures with inert values that preserve the relevant structure. Keep secrets
and personal data out of lessons and postmortems too.

## Write and index

In the matching domain file, use one `## <title>` followed by one paragraph:
bold restatement, date, cost or impact, mechanism, fix, and the rule that
applies next time. Cite relevant file paths in backticks. Keep a long incident
narrative in the postmortem.

For a new domain, include this frontmatter and add its index heading. Update
`updated` whenever its lessons change. Quote YAML values containing `: `.

```markdown
---
domain: Build tooling
triggers: scripts/, release workflows
updated: 2026-01-01
---

# Gotchas — build tooling

## Check the artifact before updating release configuration

**Check the artifact before changing release configuration** (2026-01-01).
Cost: unmeasured; a test deploy exposed mismatched code and configuration.
`scripts/deploy.sh` updated configuration before fetching the archive; a
failed fetch left the old code running. Fetch and validate the archive first,
and retain rollback handling for failures during later mutations.
```

This is a synthetic example; replace its date, impact, and paths with evidence
from the actual fix.

Under the configured index section, add a domain heading and a bullet:

```markdown
### Build tooling — read `docs/gotchas/build.md` when touching `scripts/` or release workflows
- Check the artifact before updating release configuration
```

The bullet must equal the entry's `##` title exactly and fit on one line.
A trailing parenthetical such as `(do not re-investigate)` may be an index
hint. It is a pointer to evidence, not a reason to ignore changed conditions.

Use the configured domain directory in the heading. Make its `when touching`
clause concrete: a complete backticked path/glob such as `scripts/` or `*.tf`,
or a descriptive phrase of at least three words. That syntax floor cannot
judge relevance; choose triggers that match the tasks affected by the hazard.

## Validate and deliver

Run `python3 scripts/assert-agent-workflow.py` from the repository root.
It checks index/file parity, routing syntax, duplicates, orphan files, dates,
configured postmortem references, and skill-copy consistency. When enabled,
`[index] require_cost` checks cost syntax; it does not verify the impact.
A production review kept outside the configured postmortem directory needs
its link checked separately.

If the contract changed, also run `--selftest`. If the repository maintains
`llms.txt`, run `python3 scripts/gen-llms-txt.py` and its `--check` mode. Run
any additional checks required by the repository.

Keep the fix, lesson, index, and generated documentation together for review
and the same eventual commit. Commit when authorized by the user's workflow.
Report the lesson added or updated, checks run, and any missing evidence.
