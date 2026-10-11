# Roadmap

Milestones are `## <id> <Title>` headings, marked 🤖 (agents alone) or 👤 (needs the owner). Work items are
`- [ ]` checkboxes under them. Tick an item (`- [x]`) in the same commit that delivers it, and never reword an
item's first sentence: it is the item's title and its stable key. Every open item carries a "Done when" clause.

## R0 Roadmap 🤖

- [ ] Draft and refine the gotcha-distill roadmap. Read README.md, AGENTS.md, the skill
  (`.agents/skills/gotcha-distill/SKILL.md`), `scripts/`, `docs/`, the git log and the open GitHub issues, then
  propose the milestones that follow R0 in this file: each a `## M<n> <Title> 🤖|👤` heading with one or two lines
  of intent and 3–10 `- [ ]` items, ordered by value. Each item names its files, a suggested model
  (sonnet or opus, written in square brackets after the item's first sentence) and a "Done when" that a reviewer can check. Keep scope to what the evidence supports:
  contract and selftest gaps, `install.sh` and multi-tool layout, `gen-llms-txt.py`, docs, and adoption in other
  repositories. Owner decisions (licence, releases and tags, anything public) go in 👤 items, not agent items.
  Refine with the owner: the change holds for review because it edits the roadmap beyond a tick. Done when this
  file has at least one itemized milestone after R0, every new item has a "Done when", the owner has approved the
  draft, and this item is ticked.
