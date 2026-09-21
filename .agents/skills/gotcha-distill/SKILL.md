---
name: gotcha-distill
description: Distill a bug, near-miss, or incident into durable repo knowledge — a postmortem if it reached production, a gotcha entry in docs/gotchas/<domain>.md, and its one-line trigger in AGENTS.md. Use after fixing any non-trivial bug, after a near-miss, whenever you re-investigated something already settled, or after any production incident, so every future agent loads the lesson.
license: MIT
compatibility: claude-code, opencode, cursor, codex
metadata:
  audience: all agents
  workflow: self-improvement
---

# Gotcha distillation — the repository's self-improvement loop

Every entry in `docs/gotchas/` was forged by something breaking, and is the
reason the next agent does not break it again. This skill makes that loop
repeatable and enforceable: **a fix is not done until its lesson is durable,
findable, and asserted.**

## Progressive disclosure — three levels

The pattern exists to keep lessons out of the always-loaded context until the
moment they are needed. Each level costs more tokens and is loaded less often.

| Level | Where | Loaded | Cost per lesson |
|-------|-------|--------|-----------------|
| 1 | `AGENTS.md` → `## Environment gotchas` trigger index, plus this skill's `name`/`description` frontmatter | Always, every session | ~15 tokens (one bullet) |
| 2 | This `SKILL.md` body | Only when the skill triggers (you just fixed something) | ~1,500 tokens, once per distillation |
| 3 | `docs/gotchas/<domain>.md` | Only when a task touches that domain's trigger ("when touching `infra/`…") | ~150–300 tokens per entry, only for the relevant domain |

Compare with the alternative: re-investigating a settled question costs
thousands of tokens of exploration, plus the risk of repeating the incident.
The index line is the cheapest possible pointer to the most expensive possible
lesson. **Level 1 must therefore carry the trigger** — an index line nobody
can match to their task is a line nobody loads.

## When to use me

- You fixed a non-trivial bug, or nearly caused one. A near-miss counts.
- You spent real time investigating something that had already been settled.
  That means a gotcha was missing or unfindable — which is itself the bug.
  Distill it now, or extend the existing entry with why it was unfindable.
- Any production incident. Then the postmortem in step 1 is mandatory.

## Steps, in order

1. **Classify.** Production incident → write
   `docs/postmortems/YYYY-MM-DD-<slug>.md` first, following
   `docs/postmortems/README.md`. If that directory does not exist yet, create
   it and a README that states what belongs there (the gotcha-distill
   template ships one); do not park the narrative in a handoff note and
   forget it. Everything that did not reach production starts at step 2.

2. **Distill the gotcha** into the matching domain file under `docs/gotchas/`.
   The entry is one `## <title>` heading followed by a single paragraph:
   a bold restatement of the title, the date in parentheses, what it cost,
   the mechanism, the fix, the rule that generalizes, and every file involved
   in backticks. If the domain has no file yet, create it (copy the preamble
   shape from an existing one) — a new domain is a new file **and** a new
   `###` heading in the index, in the same commit.

3. **Add the index line** to `AGENTS.md` under
   `## Environment gotchas — trigger index`, beneath the matching
   `### <Domain> — read \`docs/gotchas/<file>.md\` when touching <triggers>`
   heading. The bullet text **must equal the `##` title in the domain file
   exactly** — the contract asserts this, both directions. A trailing
   parenthetical such as `(do not re-investigate)` is permitted on the index
   line and is stripped before comparison.

4. **Validate predicates against a real captured sample** before they ship —
   this includes any regex over error text, log lines, or CLI output that
   the fix introduced (AGENTS.md rule 2). Never paste live output into the
   entry or the fixture (rule 1): synthesize the sample with inert
   placeholders and assert on structure, not on values.

5. **Run the contract:** `python3 scripts/assert-agent-workflow.py`. It
   asserts index ↔ file parity for every domain, flags orphan files and
   duplicate titles, and checks this skill's frontmatter. If you changed the
   script itself, also run `--selftest`.

6. **Commit the gotcha with the code that forged it**, in the same commit.
   Docs travel with the change they describe; a lesson that lands in a later
   "docs" commit is a lesson that can be reverted, cherry-picked away, or
   never merged.

## Entry anatomy

The index line (Level 1):

```markdown
### Infra & AWS — read `docs/gotchas/infra-aws.md` when touching `infra/`, deploy workflows, artifact buckets, or cross-account IAM
- Cross-account S3 answers 403 not 404 for a missing key
```

The entry it points to (Level 3, in `docs/gotchas/infra-aws.md`):

```markdown
## Cross-account S3 answers 403 not 404 for a missing key

**A cross-account `HeadObject`/`GetObject` on a key that does not exist
  returns 403 Forbidden, not 404** (2026-09-14, cost a 35-minute IAM detour
  and one half-applied production deploy): S3 only discloses "not found" to
  callers holding `s3:ListBucket` on the bucket. [...mechanism, fix, rule,
  files...]
```

Title is the rule, stated as a fact. Paragraph opens with a bold restatement,
carries the date and the cost, and ends with the generalizing rule and the
files. No sub-headings, no bullet lists inside the entry.

## Anti-patterns — do not

- Write a gotcha with no trigger condition. The `###` heading's "when
  touching …" clause is what routes a future task to the file.
- Re-litigate a settled question. If a `(do not re-investigate)` line exists,
  extend it with the new evidence or leave it alone.
- Distill a style preference as a gotcha. Gotchas are incident-born; the bar
  is "this cost production or a near-miss", not "I would have written it
  differently".
- Treat the count in the index preamble as asserted. It is hand-kept.
  What the contract asserts is parity: every line has its entry, every entry
  has its line.
- Land the gotcha in a separate commit from the fix.
