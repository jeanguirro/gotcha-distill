# Gotchas — full text, lazy-loaded by domain

The trigger index in `AGENTS.md` (§ "Environment gotchas") stays always
loaded; the files in this directory load on demand the moment a task touches
a trigger. Each entry says what broke, carries its date, names the cost, and
lists the files involved. Use the `gotcha-distill` skill to add one:
fix → distill → index line → commit together.

One file per domain (`infra-aws.md`, `frontend.md`, `backend.md`, …), each
created when that domain earns its first entry. A new domain is a new file
here plus its `###` trigger heading in `AGENTS.md`, in the same commit.

## Entry shape

```markdown
## <Title — the rule, stated as a fact; must equal the AGENTS.md index line>

**<Bold restatement of the title>** (<YYYY-MM-DD>, cost <what it cost>):
  <mechanism — why it happens>. <the fix, with `file/paths.ext`>. <the rule
  that generalises beyond this instance>.
```

One paragraph. No sub-headings, no bullet lists inside an entry. Continuation
lines are indented two spaces so the paragraph reads as a block. The title —
and therefore its index line in `AGENTS.md` — must fit on one line; the
contract compares whole lines and does not join wrapped bullets.

## Contract

`python3 scripts/assert-agent-workflow.py` asserts, for every domain file the
index references:

- the index heading carries a `when touching …` trigger clause;
- every index bullet has an identical `##` heading here;
- every `##` heading here has an identical index bullet;
- no duplicate titles on either side;
- every `*.md` in this directory except this README is referenced by an
  index heading (no orphan files);
- every `docs/postmortems/…md` path cited in an entry exists;
- every entry carries a `YYYY-MM-DD` date (`--no-require-dates` only while
  backfilling a legacy repository).

An index bullet may carry a trailing `(annotation)` that the `##` title does
not — `(do not re-investigate)` is the common one. The exact form is tried
first, so a title that legitimately ends in a parenthetical, such as
`(staging only)`, compares literally and needs no special handling.

This file is exempt from the parity check by name.
