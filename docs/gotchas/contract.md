---
domain: Contract validation
triggers: scripts/, skill frontmatter, trigger index parsing
updated: 2026-10-22
---

# Gotchas — contract validation

## Reject malformed routing boundaries before assigning index bullets

**Reject malformed routing boundaries before assigning index bullets**
(2026-10-22, recorded during review). Cost: unmeasured; review demonstrated
false success for an index pointing at a nonexistent domain. In
`scripts/assert-agent-workflow.py`, a heading outside the configured directory
was ignored while the previous domain stayed active, so later bullets were
silently attributed to that domain. Clear the active domain at every invalid
heading and report the heading itself. Test a valid heading followed by an
invalid one, not only an invalid first heading: parsers that retain state need
tests at transitions as well as isolated malformed inputs.
