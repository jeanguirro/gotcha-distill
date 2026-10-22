#!/usr/bin/env bash
# Install the gotcha-distill skill and its contract into an existing repository.
#
# usage: scripts/install.sh <target-repo> [--tools claude[,opencode,cursor,codex]] [--force]
#
# The canonical copy lives in .agents/skills/, which Codex, Cursor and OpenCode
# read natively. Claude Code reads .claude/skills/, so the skill is copied
# there too. This installs repository tooling; Claude web uploads use the
# separate archive built by scripts/build-skill-zip.py.
#
#   --tools   comma-separated list of agent tools to wire up (default: claude)
#   --force   overwrite an existing skill directory, contract script and
#             llms.txt generator (gotcha.toml, docs/gotchas/ and
#             docs/postmortems/ are never overwritten)
#
# Idempotent: re-running reports what already exists and changes nothing else.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="gotcha-distill"
TOOLS="claude"
FORCE=0
TARGET=""

usage() {
  cat <<'EOF'
usage: scripts/install.sh <target-repo> [--tools claude[,opencode,cursor,codex]] [--force]

The canonical copy lives in .agents/skills/, which Codex, Cursor and OpenCode
read natively. Claude Code reads .claude/skills/, so the skill is copied there
too. This installs repository tooling; Claude web uploads use the separate
archive built by scripts/build-skill-zip.py.

  --tools   comma-separated list of agent tools to wire up (default: claude)
  --force   overwrite an existing skill directory, contract script and
            llms.txt generator (gotcha.toml, docs/gotchas/ and
            docs/postmortems/ are never overwritten)

Idempotent: re-running reports what already exists and changes nothing else.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --tools) TOOLS="$2"; shift 2 ;;
    --tools=*) TOOLS="${1#--tools=}"; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) if [ -n "$TARGET" ]; then echo "unexpected argument: $1" >&2; exit 2; fi; TARGET="$1"; shift ;;
  esac
done

if [ -z "$TARGET" ]; then usage >&2; exit 2; fi
if [ ! -d "$TARGET" ]; then echo "target is not a directory: $TARGET" >&2; exit 2; fi
TARGET="$(cd "$TARGET" && pwd)"
if [ "$TARGET" = "$SRC" ]; then echo "refusing to install the template into itself: $TARGET" >&2; exit 2; fi

log()  { printf '  %-9s %s\n' "$1" "$2"; }

# ---- canonical skill: .agents/skills/gotcha-distill ------------------------
dst="$TARGET/.agents/skills/$SKILL"
if [ -d "$dst" ] && [ "$FORCE" -eq 0 ]; then
  log exists ".agents/skills/$SKILL (use --force to overwrite)"
else
  mkdir -p "$(dirname "$dst")"
  rm -rf "${dst:?}"
  cp -R "$SRC/.agents/skills/$SKILL" "$dst"
  log installed ".agents/skills/$SKILL"
fi

# ---- contract script -------------------------------------------------------
dst="$TARGET/scripts/assert-agent-workflow.py"
if [ -f "$dst" ] && [ "$FORCE" -eq 0 ]; then
  log exists "scripts/assert-agent-workflow.py (use --force to overwrite)"
else
  mkdir -p "$TARGET/scripts"
  cp "$SRC/scripts/assert-agent-workflow.py" "$dst"
  chmod +x "$dst"
  log installed "scripts/assert-agent-workflow.py"
fi

# ---- llms.txt generator ----------------------------------------------------
# Domain-file front matter (domain, triggers, updated) is explained only by
# this script, so a repo with the contract needs it too.
dst="$TARGET/scripts/gen-llms-txt.py"
if [ -f "$dst" ] && [ "$FORCE" -eq 0 ]; then
  log exists "scripts/gen-llms-txt.py (use --force to overwrite)"
else
  mkdir -p "$TARGET/scripts"
  cp "$SRC/scripts/gen-llms-txt.py" "$dst"
  chmod +x "$dst"
  log installed "scripts/gen-llms-txt.py"
fi

# ---- gotcha.toml: written only when absent, never overwritten --------------
dst="$TARGET/gotcha.toml"
if [ -e "$dst" ]; then
  log exists "gotcha.toml"
else
  name="$(basename "$TARGET")"
  name="${name//\\/\\\\}"
  name="${name//\"/\\\"}"
  {
    echo "# Layout and project name for scripts/assert-agent-workflow.py and"
    echo "# scripts/gen-llms-txt.py. Every other key is optional; see the README."
    echo
    echo "[project]"
    echo "# Used as the llms.txt H1. Set this explicitly: it defaults here to the"
    echo "# directory name, and a CI checkout can be named differently, which would"
    echo "# make the generated llms.txt differ between machines and fail its drift check."
    echo "name = \"$name\""
  } > "$dst"
  log created "gotcha.toml (set [project] name explicitly)"
fi

# ---- docs scaffolding: never overwritten -----------------------------------
for rel in docs/gotchas/README.md docs/postmortems/README.md; do
  if [ -e "$TARGET/$rel" ]; then
    log exists "$rel"
  else
    mkdir -p "$(dirname "$TARGET/$rel")"
    cp "$SRC/$rel" "$TARGET/$rel"
    log installed "$rel"
  fi
done

# ---- AGENTS.md: create, or append the index section if absent --------------
agents="$TARGET/AGENTS.md"
if [ ! -e "$agents" ]; then
  cat > "$agents" <<'EOF'
# AGENTS.md — agent contract

<!-- Two or three lines on what this repository is and the commands an agent
     needs. Keep the gotcha trigger index below: gotcha-distill and
     scripts/assert-agent-workflow.py depend on it. -->

## Agent rules (tool-neutral, postmortem-born)

**1. Never copy live system output into committed source.** Synthesise
fixtures; assert on structure, not values.

**2. A predicate over machine-generated text must be validated against a real
captured sample before it ships.**

**3. Docs travel with the code they describe.** A gotcha is committed in the
same commit as the fix that forged it.

EOF
  log created "AGENTS.md"
fi

if grep -q '^## Environment gotchas' "$agents"; then
  log exists "AGENTS.md § Environment gotchas"
else
  cat >> "$agents" <<'EOF'

## Environment gotchas — trigger index (full text lazy-loaded in `docs/gotchas/`)

0 gotchas so far. (The count is hand-kept; the index-line ↔ file parity below
is ASSERTED by `scripts/assert-agent-workflow.py`.) The full stories live in
`docs/gotchas/` — this index stays ALWAYS loaded so the hazards are known, and
the moment your task touches a trigger, READ the file before editing.
New gotcha? Add it to the domain file AND its index line here, same commit —
load the `gotcha-distill` skill for the full procedure.

<!-- One heading per domain, then one bullet per lesson. The bullet must equal
     the `##` title in the domain file exactly. Example:

### Infra — read `docs/gotchas/infra.md` when touching `infra/` or deploy scripts
- Cross-account S3 answers 403 not 404 for a missing key
-->
EOF
  log appended "AGENTS.md § Environment gotchas"
fi

# ---- per-tool wiring -------------------------------------------------------
copy_skill() {
  # $1 = tool dir relative to target (e.g. .claude/skills)
  local dir="$TARGET/$1"
  if [ -e "$dir/$SKILL" ] && [ "$FORCE" -eq 0 ]; then
    log exists "$1/$SKILL"
  else
    mkdir -p "$dir"
    rm -rf "${dir:?}/${SKILL:?}"
    cp -R "$TARGET/.agents/skills/$SKILL" "$dir/$SKILL"
    log copied "$1/$SKILL"
  fi
}

IFS=',' read -r -a tool_list <<< "$TOOLS"
for tool in "${tool_list[@]:-}"; do
  case "$tool" in
    claude)   copy_skill ".claude/skills" ;;
    opencode) copy_skill ".opencode/skills" ;;
    cursor)   copy_skill ".cursor/skills" ;;
    codex)    log native ".agents/skills is Codex's native location" ;;
    "") ;;
    *) echo "unknown tool: $tool (expected claude, opencode, cursor, codex)" >&2; exit 2 ;;
  esac
done

# ---- CLAUDE.md -> AGENTS.md (Claude Code reads CLAUDE.md, not AGENTS.md) ----
# A real file that imports AGENTS.md, consistent with copy-based installation.
case ",$TOOLS," in
  *,claude,*)
    if [ -e "$TARGET/CLAUDE.md" ] || [ -L "$TARGET/CLAUDE.md" ]; then
      log exists "CLAUDE.md (make sure it references AGENTS.md or its gotcha index)"
    else
      printf '@AGENTS.md\n' > "$TARGET/CLAUDE.md"
      log created "CLAUDE.md (@AGENTS.md)"
    fi
    ;;
esac

echo
echo "done. next: cd $TARGET && python3 scripts/gen-llms-txt.py && python3 scripts/assert-agent-workflow.py"
