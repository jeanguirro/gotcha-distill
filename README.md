# gotcha-distill

An agent skill and a contract that turn incidents into durable, always-indexed,
lazily-loaded repository knowledge. **A fix is not done until its lesson is
durable** — written where the next agent will find it, cheap enough to keep in
context forever, and asserted by CI so it cannot drift.

Works with Claude Code, OpenCode, Cursor, and Codex from a single source of
truth. Stdlib Python, one shell script, no dependencies.

```
fix the bug
  └─ postmortem (if it reached production)      docs/postmortems/YYYY-MM-DD-slug.md
       └─ distill the lesson                    docs/gotchas/<domain>.md   ## <title>
            └─ index one line                   AGENTS.md                  - <title>
                 └─ assert parity               scripts/assert-agent-workflow.py
                      └─ commit together        one commit: code + docs
```

## Why this exists

Coding agents forget. Every session starts from the files on disk, and
whatever a previous agent learned the hard way is gone unless it was written
down somewhere the next agent will read. Three costs follow from that, and
this pattern is built to eliminate each one.

### 1. Context burn

The naive fix — put every lesson in the system prompt — does not scale. Fifty
lessons at 200 tokens each is 10,000 tokens loaded on every turn of every
session, most of it irrelevant to the task at hand.

The pattern splits each lesson into three levels with different load
frequencies:

| Level | Content | When loaded | Cost per lesson |
|-------|---------|-------------|-----------------|
| 1 | One bullet in `AGENTS.md` under a `### <Domain> — read <file> when touching <triggers>` heading | Every session, always | ~15 tokens |
| 2 | `SKILL.md` — how to write a lesson | Only when an agent has just fixed something | ~1,500 tokens, once per distillation |
| 3 | `docs/gotchas/<domain>.md` — the full entry | Only when the task touches that domain's trigger | ~150–300 tokens, only the relevant domain |

One private repository of the author's has run this pattern since its first
incident. Measured on 2026-09-22: 80 asserted gotchas, 5.3 KB of always-loaded
index (about 54 characters per lesson), 61 KB across its four domain files —
an 11.5:1 ratio between what every session pays and what a task actually
reads. The agent knows *that* eighty hazards exist and *which file* to open
for the domain it is about to touch.

### 2. Re-litigation

An agent that does not know a question is settled will investigate it again.
It will spend twenty tool calls and several thousand tokens rediscovering
that Google strips GPS from certain downloads by design, or that a
cross-account S3 403 usually means "missing", not "forbidden" — and it may
reach a different, wrong conclusion this time.

The index line carries the trigger; the entry carries the evidence; a
`(do not re-investigate)` annotation on the line closes the question. The
skill treats "I spent real time on something already settled" as a bug in
the index itself: the lesson was missing or unfindable, and the fix is to
make it findable.

### 3. Tribal memory

Without this loop the lesson lives in the head of whoever fixed it, or in a
chat transcript that will be compacted or deleted. Two things make the
lesson durable here:

- **It is committed with the code that forged it.** Same commit. Not a
  follow-up "docs" PR that never merges, not a wiki page nobody links.
- **It is asserted.** `scripts/assert-agent-workflow.py` fails CI if an index
  line has no entry, an entry has no index line, a domain file is orphaned,
  or a title is duplicated. Drift is a build failure, not a slow decay.

## How it works

The six steps, as the skill instructs the agent:

1. **Classify.** Production incident → write
   `docs/postmortems/YYYY-MM-DD-<slug>.md` first. Everything else starts
   at step 2.
2. **Distill** the lesson into `docs/gotchas/<domain>.md` as one `##` title
   plus one paragraph: bold restatement, date, cost, mechanism, fix, the
   rule that generalizes, files involved.
3. **Index** it: one bullet in `AGENTS.md` under the matching domain
   heading. The bullet text must equal the `##` title exactly.
4. **Validate** any predicate the fix introduced (a regex over error text,
   for instance) against a real captured sample — and never paste that
   sample into the repo. Synthesize; assert on structure.
5. **Run the contract:** `python3 scripts/assert-agent-workflow.py`.
6. **Commit** the gotcha with the fix, in the same commit.

The skill file is
[`.agents/skills/gotcha-distill/SKILL.md`](.agents/skills/gotcha-distill/SKILL.md).
Its frontmatter `description` is the trigger — it tells the agent's skill
loader exactly when to pull the body into context.

## Case study: the 403 that was not a permission

This incident is a synthesized composite, built to exercise every step of
the loop; its numbers are internally consistent but it did not happen to a
real system. Everything below nonetheless exists in this repository as real
files, and the contract passes against them. The postmortem is
[`docs/postmortems/2026-09-14-cross-account-artifact-expiry.md`](docs/postmortems/2026-09-14-cross-account-artifact-expiry.md);
the gotchas are in
[`docs/gotchas/infra-aws.md`](docs/gotchas/infra-aws.md); the index is in
[`AGENTS.md`](AGENTS.md).

### The setup

Two AWS accounts. The **build** account (`111111111111`) owns
`s3://acme-build-artifacts` and expires objects under `api/` after 30 days
to control cost. The **prod** account (`222222222222`) runs `deploy:prod`
through an OIDC-assumed role, and its deploy script reads the Lambda bundle
straight from the build bucket:

```bash
# scripts/deploy.sh (before)
ARTIFACT="s3://acme-build-artifacts/api/api-${VERSION}.zip"

aws lambda update-function-configuration \
  --function-name api \
  --environment "Variables={RELEASE=${VERSION}}"

aws s3 cp "$ARTIFACT" ./api.zip
aws lambda update-function-code --function-name api --zip-file fileb://api.zip
```

Release `v42` was built 34 days ago. A hotfix requires redeploying it.

### The symptom

```
$ aws s3 cp s3://acme-build-artifacts/api/api-v42.zip ./api.zip
fatal error: An error occurred (403) when calling the HeadObject operation: Forbidden
```

The pipeline is red. `update-function-configuration` already succeeded, so
production is running `v41` code with `v42-hotfix` configuration.

### The detour

The agent reads `403 Forbidden` as an IAM denial and does what the error
text suggests: diffs the build bucket's policy against the deploy role ARN,
inspects the role's trust policy, and runs
`aws iam simulate-principal-policy` for `s3:GetObject` on the object ARN.
Every result is `allowed`. A rollback to `v41` is attempted and fails with
the identical 403 — `v41` is 41 days old. Thirty-five minutes have passed.

### The root cause

```
$ aws s3api list-objects-v2 --bucket acme-build-artifacts --prefix api/ --query 'Contents[].Key'
[ "api/api-v43.zip", "api/api-v44.zip", "api/api-v45.zip" ]
```

`api-v42.zip` is gone; the lifecycle rule expired it four days ago.
`simulate-principal-policy` was telling the truth — the role *was* allowed
to read the object. But the bucket policy granted `s3:GetObject` on
`arn:aws:s3:::acme-build-artifacts/*` and nothing on the bucket ARN itself,
and **without `s3:ListBucket`, S3 does not disclose whether a key exists**.
A missing key and a forbidden key both return 403.

### The fix

Three changes, all in one commit:

```diff
--- a/scripts/deploy.sh
+++ b/scripts/deploy.sh
-ARTIFACT="s3://acme-build-artifacts/api/api-${VERSION}.zip"
+BUCKET="acme-prod-release-artifacts"
+KEY="api/api-${VERSION}.zip"
+
+# Preflight: fail before any mutation. A 403 here means "missing" when the
+# caller lacks s3:ListBucket — see docs/gotchas/infra-aws.md.
+aws s3api head-object --bucket "$BUCKET" --key "$KEY" >/dev/null

-aws lambda update-function-configuration \
-  --function-name api \
-  --environment "Variables={RELEASE=${VERSION}}"
-
-aws s3 cp "$ARTIFACT" ./api.zip
+aws s3 cp "s3://${BUCKET}/${KEY}" ./api.zip
 aws lambda update-function-code --function-name api --zip-file fileb://api.zip
+aws lambda update-function-configuration \
+  --function-name api \
+  --environment "Variables={RELEASE=${VERSION}}"
```

```diff
--- a/infra/iam/deploy-role.tf
+++ b/infra/iam/deploy-role.tf
   statement {
     actions   = ["s3:GetObject"]
     resources = ["arn:aws:s3:::acme-build-artifacts/*"]
   }
+  statement {
+    # Without ListBucket a missing key returns 403, not 404.
+    actions   = ["s3:ListBucket"]
+    resources = ["arn:aws:s3:::acme-build-artifacts"]
+  }
```

And a new `scripts/promote.sh` that copies the artifact into a prod-owned
bucket with no expiration at promotion time, so `deploy.sh` reads only from
what prod owns.

### The postmortem

It reached production, so step 1 is mandatory. The agent writes
`docs/postmortems/2026-09-14-cross-account-artifact-expiry.md`:

```markdown
# Post-mortem: the 403 that was not a permission

**Date:** 2026-09-14
**Trigger:** hotfix redeploy of `api` release `v42` to production, 34 days
after `v42` was first built.
**Outcome:** `deploy:prod` failed for 52 minutes; for 45 of those the
production Lambda ran `v41` code with `v42-hotfix` configuration [...]

## What happened
## The trigger: a 403 that was not a permission
## Blind spots
## What changed as a result
## Still open
```

Account IDs are synthesized. Rule 1 in `AGENTS.md` — never commit live
output — applies to postmortems as much as to fixtures.

### The gotcha

One incident, two lessons with different triggers. Both go in
`docs/gotchas/infra-aws.md`. The first, verbatim:

```markdown
## Cross-account S3 answers 403 not 404 for a missing key

**A cross-account `HeadObject` or `GetObject` on a key that does not exist
  returns `403 Forbidden`, not `404 Not Found`** (2026-09-14, cost a
  35-minute IAM detour and one half-applied production deploy — see
  `docs/postmortems/2026-09-14-cross-account-artifact-expiry.md`): S3 only
  discloses "not found" to callers that hold `s3:ListBucket` on the bucket,
  and a bucket policy that grants `s3:GetObject` on `arn:aws:s3:::bucket/*`
  says nothing about the bucket ARN itself. [...] Rule: a cross-account 403
  on a fetch is a missing object until proven otherwise — check the
  lifecycle policy and list the prefix before you touch IAM.
```

The title is the rule stated as a fact. The paragraph opens with a bold
restatement, carries the date and the cost, cites the postmortem, explains
the mechanism, names the files, and ends with the rule that generalizes.

### The index line

In `AGENTS.md`, under the domain heading whose "when touching" clause routes
future tasks here:

```markdown
### Infra & AWS — read `docs/gotchas/infra-aws.md` when touching `infra/`, deploy workflows, artifact buckets, or cross-account IAM
- Cross-account S3 answers 403 not 404 for a missing key
- Never deploy from an artifact bucket you do not own
```

### The contract

```
$ python3 scripts/assert-agent-workflow.py
agent-workflow contract holds (/work/acme-api).
```

Had the agent typo'd the title in either place:

```
$ python3 scripts/assert-agent-workflow.py
agent-workflow contract VIOLATED (2):
  - gotcha index line has NO H2 in docs/gotchas/infra-aws.md: 'Cross-account S3 answers 403 not 404 for a missing key'
  - docs/gotchas/infra-aws.md H2 has NO index line in AGENTS.md: 'Cross-account S3 answers 403 not 404 for missing keys'
```

### The commit

```
$ git show --stat HEAD
    fix(deploy): read artifacts from prod-owned bucket; preflight before mutating

    Cross-account 403 on an expired artifact was misread as IAM for 35 minutes.
    Two gotchas distilled; see docs/postmortems/2026-09-14-cross-account-artifact-expiry.md.

 AGENTS.md                                                  |  2 +
 docs/gotchas/infra-aws.md                                  | 38 +++
 docs/postmortems/2026-09-14-cross-account-artifact-expiry.md | 84 +++++
 infra/iam/deploy-role.tf                                   |  5 +
 infra/s3/release-artifacts.tf                              | 21 ++
 scripts/deploy.sh                                          | 14 +-
 scripts/promote.sh                                         | 18 ++
```

### What the next agent sees

Nothing but the index line — fifteen tokens, every session. The next time a
task touches `infra/` or a deploy workflow, the heading tells it to read
`docs/gotchas/infra-aws.md` first, and it will not spend thirty-five minutes
in IAM.

## The contract

`scripts/assert-agent-workflow.py` is stdlib Python (3.11+, for `tomllib`), about 500 lines
including its selftest, and asserts:

| # | Check | Direction |
|---|-------|-----------|
| 1 | `AGENTS.md` exists and carries a `## Environment gotchas` section | precondition |
| 2 | Every `### … \`docs/gotchas/<file>.md\` …` heading names a file that exists **and carries a `when touching …` trigger clause** | index → disk, routing |
| 3 | Every index bullet has an identical `##` title in its domain file | index → file |
| 4 | Every `##` title in a referenced domain file has an identical index bullet | file → index |
| 5 | No duplicate titles on either side, per domain; no domain declared twice | uniqueness |
| 6 | Every `docs/gotchas/*.md` except `README.md` is referenced by a heading | disk → index |
| 7 | No bullet appears in the section before the first domain heading | shape |
| 8 | Every `docs/postmortems/<file>.md` cited in a domain file exists | file → disk |
| 9 | Every entry carries a `YYYY-MM-DD` date (`--no-require-dates` while backfilling a legacy repo) | entry shape |
| 10 | Every copy of `SKILL.md` has `name: gotcha-distill` (or `--skill-name`) and a single-line description ≤ 512 chars, and all copies are byte-identical | skill |

Check 2 is the one the whole design rests on: a heading without a trigger
clause is consistent, present, and never read. Check 9 is the mechanical
half of "gotchas are incident-born" — it cannot tell an incident from an
opinion, but it makes writing an opinion require a deliberate lie rather than
mere laziness.

An index line may carry a trailing `(annotation)` that the title does not —
`(do not re-investigate)` is the common one. The exact form is tried first,
so a title that legitimately ends in a parenthetical (`(staging only)`,
`(GKE 1.30+)`) compares literally. HTML comments and fenced code blocks are
ignored, so `AGENTS.md` can carry an example heading without declaring a
domain. Files may be CRLF or carry a UTF-8 BOM; the selftest covers both. The
512-character description ceiling is a deliberate always-loaded budget, not a
vendor limit (Claude Code truncates `description` + `when_to_use` at 1,536).

The count in the index preamble ("80 gotchas") is deliberately **not**
asserted. Counts drift harmlessly; parity does not. Asserting the count would
make every distillation a two-file edit for no safety gain.

### Proof of failure

`--selftest` builds a synthetic repository in a temp directory (three times:
LF, CRLF, and with a BOM), asserts the contract holds, then applies seventeen
named mutations — an index line with no entry, an entry with no index line,
a deleted domain file, an orphan file, a duplicate on each side, a domain
declared twice, a heading with no trigger clause, a bullet outside any
domain, a removed section, a dangling postmortem link, an undated entry, a
renamed skill, a bloated description, a folded description, a drifted skill
copy, a missing skill — and asserts each one trips the expected check. A
check that cannot be shown to fail is not a check.

```
$ python3 scripts/assert-agent-workflow.py --selftest
selftest OK (17 mutations each trip their check).
```

CI runs both. See [`.github/workflows/contract.yml`](.github/workflows/contract.yml).

## Installation

### Option A — use this repository as a template

Click **Use this template** on GitHub, or clone and delete `.git`. Replace
the case-study content in `AGENTS.md`, `docs/gotchas/infra-aws.md`, and
`docs/postmortems/` with your own as lessons accrue — or delete the example
entries and their index lines together (the contract will tell you if you
miss one).

### Option B — install into an existing repository

```bash
git clone https://github.com/<you>/gotcha-distill
bash gotcha-distill/scripts/install.sh /path/to/your/repo
```

`install.sh` copies the skill to `.agents/skills/gotcha-distill/`, the
contract to `scripts/`, and the two `README.md` files under `docs/`; creates
or appends the `## Environment gotchas` section in `AGENTS.md`; and bridges
Claude Code to the canonical skill. It never overwrites an existing
`docs/gotchas/` or `docs/postmortems/` file, and is safe to re-run.

```
usage: scripts/install.sh <target-repo> [--tools claude[,opencode,cursor,codex]] [--copy] [--force]
```

- `--tools` selects which tool directories to bridge (default: `claude`,
  the only tool that needs one — see the table below). Name `opencode` or
  `cursor` only for versions that predate `.agents/skills` support.
- `--copy` copies the skill into each tool directory instead of symlinking —
  use it on Windows checkouts without `core.symlinks`, or if your tool's
  skill loader does not follow symlinks. The contract asserts every copy is
  byte-identical to the canonical one, so drift is caught.
- `--force` overwrites an existing skill directory and contract script
  (never the docs).

### Option C — by hand

One canonical copy in `.agents/skills/`. Who reads what, per current vendor
documentation:

| Tool | Reads skills from | Needs a bridge? | Always-loaded contract |
|------|-------------------|-----------------|------------------------|
| Codex | `.agents/skills/` | No | `AGENTS.md` |
| Cursor | `.agents/skills/`, `.cursor/skills/`, `.claude/skills/` | No | `AGENTS.md` |
| OpenCode | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` | No | `AGENTS.md` |
| Claude Code | `.claude/skills/` only | **Yes** | `CLAUDE.md` |

```bash
mkdir -p .agents/skills && cp -R gotcha-distill/.agents/skills/gotcha-distill .agents/skills/
cp gotcha-distill/scripts/assert-agent-workflow.py scripts/

ln -s ../.agents/skills .claude/skills
ln -s AGENTS.md CLAUDE.md
```

Commit the symlinks as symlinks (git mode `120000`). The CI workflow in this
repository includes a step that fails if a checkout with `core.symlinks=false`
turned them into regular files. If your team already has a `CLAUDE.md` with
content, keep it and add a line pointing at `AGENTS.md` instead of replacing
it. Cursor has had reports of symlinked skill directories being filtered out
when the resolved path escapes the project root; since Cursor reads
`.agents/skills/` directly, do not add a `.cursor/skills` link at all — or
use `--copy` if you must.

Then add the two contract commands to CI:

```yaml
- run: python3 scripts/assert-agent-workflow.py --selftest
- run: python3 scripts/assert-agent-workflow.py
```

## Configuration

Every path this contract cares about has a default, and the defaults are the
layout shown throughout this README. A repository whose layout matches needs no
configuration at all.

When it differs, `gotcha.toml` at the repository root overrides only the keys
you set:

```toml
[project]
name = "your-repo"          # llms.txt H1; the directory name is not the repo name

[paths]
contract    = "AGENTS.md"
gotchas     = "docs/gotchas"
postmortems = "docs/postmortems"

[index]
heading = "## Environment gotchas"

[skill]
name                  = "gotcha-distill"
description_max_chars = 512
```

## llms.txt

`scripts/gen-llms-txt.py` renders the trigger index as an
[llms.txt](https://llmstxt.org) file: an H1, a one-blockquote summary, an H2 per
domain, and one `- [title](file#anchor): trigger` line per gotcha. Postmortems
go under `Optional`, which is the spec's marker for links an agent can skip
when context is short.

This is a transformation rather than an invention — the index is already a list
of links with notes, which is exactly what the format asks for. Each domain
file carries front matter (`domain`, `triggers`, `updated`) that the generator
reads instead of re-parsing prose, and that the contract asserts is present.

```bash
python3 scripts/gen-llms-txt.py          # write llms.txt
python3 scripts/gen-llms-txt.py --check  # exit 1 if it is stale
```

CI runs `--check`, so a generated file cannot drift from its source.

## Writing a good gotcha

**The title is the rule, stated as a fact.** "Cross-account S3 answers 403
not 404 for a missing key" — not "S3 permissions issue" and not "Be careful
with S3". A future agent scanning the index should be able to act on the
title alone.

**The heading carries the trigger.** `### Infra & AWS — read
\`docs/gotchas/infra-aws.md\` when touching \`infra/\`, deploy workflows,
artifact buckets, or cross-account IAM`. The "when touching" clause is what
routes a task to the file. An index line with no trigger is a line nobody
loads.

**The entry is one paragraph.** Bold restatement, date in parentheses, what
it cost, the mechanism, the fix with file paths in backticks, the rule that
generalizes. No sub-headings, no nested lists. If it needs more than a
paragraph, that is the postmortem's job — link to it.

**Do not:**

- Distill a style preference. The bar is "this cost production or a
  near-miss", not "I would have written it differently".
- Re-litigate a `(do not re-investigate)` line. Extend it with new evidence
  or leave it alone.
- Land the gotcha in a separate commit from the fix.
- Paste live output into the entry. Synthesize; assert on structure.

## Adapting the pattern

**New domain.** Create `docs/gotchas/<domain>.md` with the preamble shape
from an existing file, add its `###` heading to the index, and add the first
entry — all in one commit. The contract's orphan check will refuse a file
with no heading, and the missing-file check will refuse a heading with no
file.

**No postmortems directory yet.** Create it with
`docs/postmortems/README.md` the first time an incident reaches production.
Do not park incident narratives in a handoff or status document and forget
them; those documents describe what *is*, not how it came to be.

**Monorepo.** One domain file per package or service is usually right, still
under `docs/gotchas/` at the repository root (`docs/gotchas/api.md`,
`docs/gotchas/web.md`) — the contract's path is fixed — with the heading's
trigger naming the package path. If a lesson spans packages, it belongs in
the domain where the *fix* landed, with the other package named in the
paragraph.

**Deriving triggers from an existing rules directory.** If the repository
already has path-scoped agent rules — `.cursor/rules/*.mdc` with `globs:`,
or an equivalent — those globs are reviewed, agreed statements of "which
files does this concern apply to", which is exactly what a trigger clause
is. Cut domain files along the same lines and copy the globs into the
`when touching …` clause: the triggers are then not invented, and a task
that loads a rule loads the matching gotcha file.

**An existing incident home.** If the team already runs a post-incident
review process — an RCA directory, an SRE template set — do not create
`docs/postmortems/` as a competing second home. Point step 1 of the skill at
the existing location and cite that path from the gotcha entry; the
contract's link check only requires that a cited `docs/postmortems/…` path
resolves, and does not care whether other paths are cited alongside it.

**Other always-loaded files.** The contract only knows about `AGENTS.md`.
If your team's always-loaded file is named differently, symlink it — that is
what `CLAUDE.md -> AGENTS.md` is for.

## Background

Why this is shaped the way it is — the token economics, and why the parity
assertion is the part that matters:
<https://jeansantos.me/work/gotcha-distill/>

## License

MIT. See [`LICENSE`](LICENSE).
