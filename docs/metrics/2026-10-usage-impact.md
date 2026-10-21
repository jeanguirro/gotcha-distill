# gotcha-distill — usage and impact snapshot

**Measured:** 2026-10-22, against local working trees after the review fixes.
**Scope:** nine sibling repositories containing `scripts/assert-agent-workflow.py`
and their configured agent contract. This is an author-owned convenience sample,
not a representative survey of agent workflows.

## What the evidence supports

The current canonical contract passes in **8 of 9 repositories**. All nine
pass their own installed contract. `photos_backup` fails the canonical check
with 51 violations while retaining an older contract and entry format.
This is a snapshot of current files: it does not establish that parity has
held continuously since installation, or that CI ran for every change.

The scan finds **237 entries**, including three in this repository (two
synthetic incident examples and one review-discovered parser failure).
It demonstrates adoption of the file layout and current structural checks.
It does not establish that the skill produced every entry, that agents read
them at the right time, or that they prevented repeated work or incidents.

## Method and reproduction

```bash
python3 scripts/measure-adoption.py --fleet-root /path/to/repos
python3 scripts/measure-adoption.py --fleet-root /path/to/repos --json
```

The scanner reads each repository's configured layout and uses the canonical
entry parser and cost predicate. It runs both the installed and canonical
contract as subprocesses. Run it only against repositories whose scripts you
trust. It does not inspect git history, installation dates, or CI runs.

- **Index bytes:** UTF-8 size of lines inside the configured index section,
  excluding its heading, joined with LF. Includes routing headings and prose.
- **Domain bytes:** UTF-8 size of domain Markdown files, excluding `README.md`.
  Includes frontmatter and preambles, not just entry bodies.
- **Ratio:** all domain bytes divided by index bytes, rounded to one decimal.
- **Index token estimate:** index bytes divided by four, rounded down. No
  tokenizer or model context accounting is used.
- **Date signal:** an entry body contains a `YYYY-MM-DD` pattern. This does
  not verify the date's provenance or establish when the entry was created.
- **Cost signal:** an entry matches the contract's cost syntax, such as
  `Cost: <impact>`, `cost a <consequence>`, or `took 35 minutes`.
  `Cost: unmeasured` is accepted to avoid fabricating numbers. The count is a
  heuristic, not a count of independently verified or quantified costs.
- **Skill drift:** installed skill bytes differ from this repository's skill.
  This does not check whether an agent actually discovered or invoked it.

The [raw JSON snapshot](2026-10-adoption.json) contains aggregate output only.
Several source repositories are private; public readers can inspect this
snapshot and rerun the tools here or on their own repositories, but cannot
independently recount the private source files. Future working-tree scans may
produce different results.

## Adoption and current contract health

All byte figures below are exact. All repositories pass their installed
contract; the canonical result is shown separately.

| Repository | Entries | Domains | Postmortems | Index bytes | Domain bytes | Ratio | Canonical |
|---|---:|---:|---:|---:|---:|---:|---|
| photos_backup | 81 | 4 | 5 | 5,263 | 63,758 | 12.1 | 51 violations |
| pixel_it_office | 70 | 4 | 6 | 8,404 | 104,773 | 12.5 | pass |
| jeansantos.me | 36 | 3 | 0 | 7,526 | 65,757 | 8.7 | pass |
| ja_genau | 16 | 4 | 0 | 2,979 | 19,569 | 6.6 | pass |
| solarpunk_farm | 10 | 6 | 0 | 2,488 | 13,256 | 5.3 | pass |
| dreadnought | 9 | 3 | 0 | 2,053 | 7,840 | 3.8 | pass |
| edu-platform | 8 | 6 | 2 | 2,249 | 14,087 | 6.3 | pass |
| incubator-foundation | 4 | 1 | 0 | 1,125 | 2,807 | 2.5 | pass |
| gotcha-skill | 3 | 2 | 1 | 957 | 3,823 | 4.0 | pass |
| **Total** | **237** | **33** | **14** | **33,044** | **295,670** | | **8/9** |

Three distinct skill hashes are installed across the fleet. Eight repositories
have a different skill from the current canonical copy. No fleet installations
were changed for this assessment.

## Context economics

For `photos_backup`, 63,758 / 5,263 = **12.114:1**, reported as **12.1:1**.
In decimal units these sizes are **5.3 KB / 63.8 KB**. The index averages
about **65 bytes per lesson** (roughly 16 tokens under the bytes/4 estimate).

This compares a trigger index with the entire domain corpus. Actual task
context includes the index plus whichever domain files are read, as well as
skill metadata and any loaded instructions. Neither token savings, prompt
caching effects, nor money saved were measured.

## Provenance and limits

- **Date signals:** 190 / 237 entries; `photos_backup` accounts for all 47
  entries without a date pattern.
- **Cost signals:** 65 / 237 entries (27.4%). The former 102 / 236 figure
  used loose keywords that matched incidental phrases such as “every day.”
  The revised predicate and the added parser lesson make these snapshots
  unsuitable for a before/after impact comparison.
- **Postmortems:** 14 files in four repositories. File counts alone cannot
  establish whether production incidents lack reviews: some reviews may live
  elsewhere, and some lessons concern non-production work.
- **Re-investigation markers:** one `(do not re-investigate)` occurrence.
  Markers are annotations, not observed prevention events.

Earlier exploratory transcript searches mixed mentions, directory listings,
and actual reads. They are excluded from the evidence here because the
scanner does not reproduce them and they do not establish causal reuse.

## Changes supported by review

The shipped YAML is now parsed by a real YAML loader in CI. Regression checks
cover invalid headings after valid ones, unmatched or empty backticks,
non-path tokens, plural time quantities, and incidental time words. The
measurement tool shares the contract's parser and cost heuristic instead of
maintaining a second definition. Documentation distinguishes synthetic examples,
current compliance, byte ratios, and unmeasured outcomes.

## Next evidence to collect

1. Evaluate realistic tasks in isolated repositories: does an agent select
   the right domain, update an existing lesson, and maintain a custom layout?
2. Record task-level lesson reads and subsequent decisions before claiming
   reduced re-investigation. Compare similar tasks with and without the index.
3. Save dated contract snapshots or CI history before making longitudinal
   health claims. Track distinct skill versions when upgrades are performed.

The portfolio claim supported today is a portable knowledge layout with
executable structural checks and documented regression cases. Claims about
agent behavior and operational savings remain future evaluation work.
