# Post-mortems

Incident and delivery reviews, one file per event, named `YYYY-MM-DD-slug.md`.

**What belongs here:** the analysis of something that went wrong or cost more
than it should have — triggers, blind spots, and the rules that came out of
it. Written once and then left alone.

**What does not:**

- A living status or handoff document — that should say what IS, not how it
  came to be. When an incident is closed, its narrative moves here and the
  living document keeps a one-line pointer.
- Design decisions taken deliberately (a `docs/design/` or ADR directory,
  with a `Status:` header). A design doc argues for a choice; a post-mortem
  explains a cost.
- The durable gotcha extracted from the incident. The post-mortem is the
  story; `docs/gotchas/<domain>.md` is the one paragraph the next agent must
  read, and `AGENTS.md` is the one line that routes them to it.

## Shape

```markdown
# Post-mortem: <one-line narrative title>

**Date:** YYYY-MM-DD
**Trigger:** <the change or event that started it>
**Outcome:** <user-visible effect and duration>

## What happened
## The trigger: <the false belief or missing check>
## Blind spots
## What changed as a result
## Still open
```

Bold-led sub-claims inside `## Blind spots` rather than `###` headings. Every
concrete value (account IDs, ARNs, hostnames, tokens) is synthesised — rule 1
in `AGENTS.md` applies to post-mortems as much as to fixtures.
