# gotcha-distill — usage & impact report

**Date:** 2026-10-22
**Scope:** the nine repositories running the canonical `scripts/assert-agent-workflow.py` contract. `solar_farm` is excluded — it still runs the legacy `verify-workflow.sh` and has no `gotcha.toml` (see "What is still open").

---

## 1. Executive verdict

The skill works. The parity contract — the part the whole design rests on — has held in
every canonical repository since installation: 8 of 9 repos are fully compliant with the
current contract, and the one exception (`photos_backup`) is not a violation but a
pre-contract repo still on its original format. The token economics the README advertises
are real and reproducible: the two largest repos keep an always-loaded index of ~5–8 KB
against 64–105 KB of lazy-loaded lessons, an ~12:1 ratio.

The honest caveat: **the evidence is strong at the "written down and asserted" layer and
weak at the "actually reused and re-litigation prevented" layer.** 236 gotchas exist and
are indexed, but only one carries the `(do not re-investigate)` marker that closes a
settled question, and postmortems exist in only 4 of 9 repos. The skill reliably turns
incidents into durable text; whether that text prevents the *next* agent from burning
time is not yet measured. That is the next metric to build, not a reason to stop.

---

## 2. Method & data sources

- **Repository scan:** `scripts/measure-adoption.py` (added in this change) — read-only,
  stdlib-only, walks `--fleet-root` and reports each repo with the canonical contract.
- **Contract status:** each repo's own contract (subprocess) plus the fleet-canonical
  contract run against it, so a repo still on an older format is visible.
- **Claude Code history:** 2.5 GB / ~2,009 session transcripts under `~/.claude/projects`
  were searched for skill invocations and gotcha-file access.
- **Adversarial review:** a fresh-eyes review of this repository was run against the
  README claims, the contract's evasion surface, `install.sh`, and the selftest. Its
  findings are folded into this report and its backlog below.

Numbers were measured against the working tree that includes this change set
(the "after" state of the fixes in the backlog below).

---

## 3. What gotcha-distill is

A three-level knowledge loop with a CI-enforced parity contract:

| Level | Where | Loaded when | Cost |
|---|---|---|---|
| 1 | one bullet in `AGENTS.md` under a `### <Domain> — read <file> when touching <triggers>` heading | every session | ~15 tokens/bullet (marginal) |
| 2 | `SKILL.md` — how to write a lesson | only after a fix | ~1.5k tokens, once |
| 3 | `docs/gotchas/<domain>.md` — the full entry | only when a task touches the trigger | ~150–300 tokens/entry |

The contract (`assert-agent-workflow.py`) asserts index↔entry parity in both directions,
that every domain heading has a *specific* trigger clause, that entries carry a date (and,
opt-in, a stated cost), that postmortem links resolve, and that every skill copy is
byte-identical. A 20-mutation selftest proves each check trips.

---

## 4. Adoption

| Repo | Gotchas | Domains | Postmortems | Index (always) | Lazy | Ratio | Skill |
|---|---|---|---|---|---|---|---|
| photos_backup | 81 | 4 | 5 | 5.3 KB | 64 KB | 12.1 | **old** |
| pixel_it_office | 70 | 4 | 6 | 8.4 KB | 105 KB | 12.5 | prev |
| jeansantos.me | 36 | 3 | 0 | 7.5 KB | 66 KB | 8.7 | prev |
| ja_genau | 16 | 4 | 0 | 3.0 KB | 20 KB | 6.6 | prev |
| solarpunk_farm | 10 | 6 | 0 | 2.5 KB | 13 KB | 5.3 | prev |
| dreadnought | 9 | 3 | 0 | 2.1 KB | 7.8 KB | 3.8 | prev |
| edu-platform | 8 | 6 | 2 | 2.2 KB | 14 KB | 6.3 | prev |
| incubator-foundation | 4 | 1 | 0 | 1.1 KB | 2.8 KB | 2.5 | prev |
| gotcha-skill | 2 | 1 | 1 | 0.7 KB | 2.8 KB | 3.8 | **current** |
| **total** | **236** | 31 | 14 | 32 KB | 295 KB | | |

"Skill" column: `current` = the canonical skill in this commit; `prev` = the previous
canonical release; `old` = the pre-extraction original still installed in `photos_backup`.
The skill exists in **three versions across the fleet** — see "What is still open".

`photos_backup` is the originating repo: its 81 gotchas predate the skill's extraction
(2026-09-22), which is why its entries use the older, terser format and only 34 of 81
carry a date.

---

## 5. Volume & timeline

236 gotchas across 9 repos (293 including `solar_farm`'s 57). Entry dates cluster in
September–October 2026 — 88 dated references in September and 165 in October, matching
the skill's extraction on 2026-09-22. The `photos_backup` core is older (August 2026 and
earlier) and was written down before the date was a contract requirement.

---

## 6. Contract health

- **Parity holds** in all 9 repos (their own contract is green in all 9).
- **Canonical-format compliance:** 8 of 9 pass the current contract; `photos_backup`
  reports 51 violations — all of them pre-existing (missing front matter and dates), none
  introduced by the changes in this commit.
- **The anti-drift assertion does its job:** it is the reason a repo still on the old
  format is visible at all rather than silently accepted.

---

## 7. Token economics

The README's headline numbers were recomputed against the real fleet and corrected
(they were previously unattributable and internally inconsistent):

- `photos_backup`: 5.3 KB always-loaded index for 81 lessons ≈ **66 bytes (~17 tokens) per
  lesson**; 64 KB lazy — an **~12:1** ratio between what every session pays and what a task
  actually reads.
- `pixel_it_office`: 8.4 KB always / 105 KB lazy — **~12.5:1**.

The `~15 tokens per lesson` figure is the *marginal* cost of one bullet; the skill's own
`description` is a fixed ~200-character always-loaded cost on top, which is now budgeted
at 250 characters so a busy multi-skill session does not truncate its trigger words.

---

## 8. Provenance & quality

- **Dates:** 189 / 236 entries carry a date (100% in every repo except `photos_backup`,
  where the older entries predate the requirement).
- **Cost:** 102 / 236 entries (43%) state a cost. Cost is now assertable via
  `[index] require_cost`, enabled for this repo and available to any repo that opts in.
- **Postmortems:** 14 total across only 4 repos (photos_backup 5, pixel_it_office 6,
  edu-platform 2, gotcha-skill 1). Five repos have dozens of gotchas and zero postmortems —
  step 1 of the skill ("production incident → postmortem") is being skipped, or most of
  these lessons were near-misses in non-production work.
- **Re-litigation marker:** 1 `(do not re-investigate)` across 236 gotchas. The mechanism
  exists but is essentially unused.

---

## 9. Reuse / re-litigation evidence

The weakest link, measured honestly. Across ~2,009 session transcripts:

- The `gotcha-distill` skill was actually invoked (`Skill` tool) in ~13 sessions — modest.
- `assert-agent-workflow.py` appears in ~1.4k transcripts (mostly as always-loaded
  `AGENTS.md` content, not execution).
- Gotcha files are opened by agents regularly (the top domain files are referenced
  thousands of times across transcripts), but this count is inflated by directory
  listings and cannot, on its own, distinguish "read because the trigger matched" from
  "listed as part of the tree."

There is no mechanical signal yet that a gotcha prevented a re-investigation. The next
iteration should log re-investigation events so the anti-re-litigation claim can be tested
rather than asserted.

---

## 10. Adversarial review — summary of findings

A fresh-eyes adversarial review of this repository (run before the fixes in this commit)
found the core strong and the *claims around it* ahead of what the code enforced. Fixed in
this commit:

1. `paths.gotchas` config was broken — the heading regex hardcoded `docs/gotchas`, so a
   configured path was only honored for file resolution, and a heading pointing at a
   non-existent path could be certified. **Fixed:** the regex now derives from the
   configured path, and a selftest proves honest-passes / lying-fails.
2. Trigger *quality* was unasserted — `when touching stuff` passed. **Fixed:** a clause
   must name a backticked path/glob or at least three words.
3. A stated cost was never asserted — an opinion with a date passed. **Fixed:** opt-in
   `require_cost` (enabled here), with a mutation proving it trips.
4. The `core.symlinks=false` CI check read the git index, not the working tree, so it
   never caught the failure it claimed to. **Fixed:** CI now asserts `test -L`.
5. The description budget ignored Claude Code's per-skill truncation, so the author's own
   description lost its trigger words. **Fixed:** budget lowered to 250 and the description
   front-loads its triggers.
6. Token-economics numbers were unattributable and inconsistent. **Fixed:** attributed to
   `photos_backup` and recomputed.

**Accepted as-is (documented, not fixed):** the `ANNOTATION_RE` wildcard (a bullet may
still carry an arbitrary trailing parenthetical), the hand-rolled `llms.txt` anchor slugger,
and the "one private repository" framing now that it is named.

---

## 11. Metrics framework

Numbers worth tracking over time, each computable by `scripts/measure-adoption.py`:

| Metric | Definition | Signal / target |
|---|---|---|
| **Adoption breadth** | repos with the canonical contract / active repos | plateau or grow |
| **Skill uniformity** | distinct `SKILL.md` hashes in the fleet | **1** (today: 3) |
| **Distillation rate** | new gotchas per week | steady, not bursty |
| **Parity health** | contract result per repo | 100% `hold` on canonical |
| **Provenance — dates** | dated entries / total | → 100% |
| **Provenance — cost** | costed entries / total | → 100% (opt-in) |
| **Postmortem rate** | postmortems / gotchas | non-zero in prod repos |
| **Re-litigation** | `(do not re-investigate)` lines / gotchas | rising (needs event logging) |
| **Index budget** | index bytes; ratio | index ≪ lazy; ratio ≥ ~8:1 |

The two metrics with the most untapped value are **skill uniformity** (three versions
exist today) and **re-litigation** (unmeasured).

---

## 12. Improvement backlog

Done in this commit:

- [x] Repair configurable gotchas path; assert the heading's literal target
- [x] Enforce trigger specificity and (opt-in) stated cost
- [x] Real symlink assertion in CI; honest description budget
- [x] Correct and attribute the token-economics claims
- [x] Drop the `AGENTS.md` template boilerplate; soften the vendor-compatibility claim

Still open, ordered by value:

1. **Unify the skill across the fleet.** One upgrade path — extend `install.sh` with an
   `--upgrade`/`--force` run that refreshes `SKILL.md`, the contract, and `gen-llms-txt.py`
   in every repo, so `photos_backup`'s old skill and the previous-canonical copies converge
   on the current one. The `skill_drift` column in the metrics script is the acceptance test.
2. **Instrument re-litigation.** Log when an agent re-investigates a settled question;
   drive the `(do not re-investigate)` marker from that signal instead of leaving it to
   memory.
3. **Close the postmortem gap.** Either relax step 1 for near-misses (a one-line "did this
   reach production?" tag) or enforce a postmortem for production incidents.
4. **Adopt the `ANNOTATION_RE` allowlist** (reject arbitrary parentheticals) and validate
   `gen-llms-txt.py`'s anchor slugger against GitHub's real slugger in CI.
5. **Index scaling.** As repos pass ~50 gotchas (photos_backup, pixel_it_office), consider
   per-package domain files to keep the always-loaded index from growing linearly.

---

## 13. Appendix — raw numbers

```
repo               gotchas domains pm  index   idxTok lazy    ratio dated costed rinv  skill   self       canonical
dreadnought              9      3   0  2053B   513  7840B    3.8     9      9    0 a3267084 hold       hold
edu-platform             8      6   2  2249B   562 14087B    6.3     8      6    0 a3267084 hold       hold
gotcha-skill             2      1   1   734B   183  2819B    3.8     2      2    0 552994fc hold       hold
incubator-foundation     4      1   0  1125B   281  2807B    2.5     4      1    0 a3267084 hold       hold
ja_genau                16      4   0  2979B   744 19569B    6.6    16     10    0 a3267084 hold       hold
jeansantos.me           36      3   0  7526B  1881 65757B    8.7    36      9    0 a3267084 hold       hold
photos_backup           81      4   5  5263B  1315 63758B   12.1    34     17    1 a0b509b7 hold       violate-51
pixel_it_office         70      4   6  8404B  2101 104773B   12.5    70     43    0 a3267084 hold       hold
solarpunk_farm          10      6   0  2488B   622 13256B    5.3    10      5    0 a3267084 hold       hold
```

Skill hashes: `552994fc` = this commit's canonical; `a3267084` = previous canonical
release; `a0b509b7` = the pre-extraction original (photos_backup).
