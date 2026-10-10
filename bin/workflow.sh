#!/usr/bin/env bash
# workflow.sh — Munshi Ji's workflows: one folder per area of work, each with its own WORKFLOW.md.
#   workflow.sh current                     print "<slug>\t<title>" of the current workflow (default: general)
#   workflow.sh list                        print "<slug>\t<title>" for every workflow
#   workflow.sh menu                        send the owner tap-to-switch buttons on Telegram (don't also reply)
#   workflow.sh new "<Name>" [emoji]        create from the template and switch to it
#   workflow.sh switch "<name|slug>"        make it current and start a fresh session (memory kept)
#   workflow.sh rename "<New Name>" [emoji] rename the current workflow
#   workflow.sh show [name|slug]            title, goal and pending items (for confirmations)
# switch/new clear the session a few seconds after the turn ends (via session.sh new): reply first, run this last.
set -uo pipefail
. "$(dirname "$0")/common.sh"

WF_DIR="$AGENT_HOME/workflows"
CUR_FILE="$WF_DIR/.current"
PENDING="$AGENT_HOME/memory/pending.md"
mkdir -p "$WF_DIR"

slugify() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' | cut -c1-40; }
norm()    { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/\(current\)|✅//g; s/[^a-z0-9]+//g'; }
title_of() { head -n1 "$WF_DIR/$1/WORKFLOW.md" 2>/dev/null | sed -E 's/^#[[:space:]]*//'; }
cur_slug() { local s; s="$(cat "$CUR_FILE" 2>/dev/null)"; [[ -n "$s" && -d "$WF_DIR/$s" ]] && echo "$s" || echo general; }
all_slugs() { for d in "$WF_DIR"/*/; do [[ -f "$d/WORKFLOW.md" ]] && basename "$d"; done; }

resolve() {  # resolve <name|slug|button label> → slug
    local want s; want="$(norm "$1")"
    for s in $(all_slugs); do
        [[ "$(norm "$s")" == "$want" || "$(norm "$(title_of "$s")")" == "$want" ]] && { echo "$s"; return 0; }
    done
    return 1
}

pending_for() {  # lines of memory/pending.md tagged [slug]
    grep -E "^- .*\[$1\]" "$PENDING" 2>/dev/null | sed -E "s/ *\[$1\]//" | cut -c1-160
}

make_workflow() {  # make_workflow <slug> <emoji> <Name> [goal]
    mkdir -p "$WF_DIR/$1/outputs"
    cat > "$WF_DIR/$1/WORKFLOW.md" <<EOF
# $2 $3

Goal: ${4:-(not set yet — ask the owner in one line)}
Created: $(TZ=Asia/Kolkata date '+%Y-%m-%d')

## Context
<!-- What this workflow is about, who is involved, which browser/accounts it uses. -->

## Rules
<!-- Standing instructions the owner gives for this workflow. -->

## Key files & links
<!-- Paths (memory/…, workspace/…, workflows/$1/outputs/…) and URLs worth reopening. -->

## Open items
<!-- Backlog the agent is tracking. Questions waiting on the owner go in memory/pending.md tagged [$1]. -->

## Log
<!-- One line per completed task: - YYYY-MM-DD HH:MM — what — output path -->
EOF
}

cmd="${1:-current}"; shift || true
case "$cmd" in
  current) s="$(cur_slug)"; printf '%s\t%s\n' "$s" "$(title_of "$s")" ;;

  list) for s in $(all_slugs); do printf '%s\t%s\n' "$s" "$(title_of "$s")"; done ;;

  menu)
    cur="$(cur_slug)"; btns=()
    for s in $(all_slugs); do
        t="$(title_of "$s")"; [[ "$s" == "$cur" ]] && t="$t ✅"
        btns+=("/workflow $t")
    done
    "$BIN_DIR/tg-buttons.sh" --cols 2 "📂 Workflows — now in: $(title_of "$cur")
Tap one to switch (starts a fresh session; memory is kept), or create a new one." \
        "${btns[@]}" "/workflow ➕ New" "✖ Cancel" ;;

  new)
    name="${1:?usage: workflow.sh new \"<Name>\" [emoji]}"; emoji="${2:-📁}"
    slug="$(slugify "$name")"
    [[ -n "$slug" ]] || { echo "ERROR: name must contain letters or digits"; exit 1; }
    [[ -d "$WF_DIR/$slug" ]] && { echo "ERROR: workflow '$slug' already exists — use: workflow.sh switch $slug"; exit 1; }
    make_workflow "$slug" "$emoji" "$name"
    log workflow "created $slug"
    echo "OK: created $emoji $name ($WF_DIR/$slug/WORKFLOW.md)." ;;

  switch)
    slug="$(resolve "${1:?usage: workflow.sh switch <name|slug>}")" || { echo "ERROR: no workflow '$1'. Have: $(all_slugs | tr '\n' ' ')"; exit 1; }
    [[ "$slug" == "$(cur_slug)" ]] && { echo "Already in $(title_of "$slug")."; exit 0; }
    printf '%s\n' "$slug" > "$CUR_FILE"
    "$BIN_DIR/session.sh" new >/dev/null
    log workflow "switched to $slug"
    echo "OK: switched to $(title_of "$slug"); fresh session after this turn." ;;

  rename)
    new="${1:?usage: workflow.sh rename \"<New Name>\" [emoji]}"; old="$(cur_slug)"
    [[ "$old" == general ]] && { echo "ERROR: General can't be renamed"; exit 1; }
    emoji="${2:-$(title_of "$old" | awk '{print $1}')}"; slug="$(slugify "$new")"
    [[ "$slug" != "$old" && -d "$WF_DIR/$slug" ]] && { echo "ERROR: '$slug' already exists"; exit 1; }
    sed -i "1s|.*|# $emoji $new|" "$WF_DIR/$old/WORKFLOW.md"
    if [[ "$slug" != "$old" ]]; then
        mv "$WF_DIR/$old" "$WF_DIR/$slug"
        sed -i "s|\[$old\]|[$slug]|g" "$PENDING" 2>/dev/null
        sed -i "s|workflows/$old/|workflows/$slug/|g" "$WF_DIR/$slug/WORKFLOW.md"
        printf '%s\n' "$slug" > "$CUR_FILE"
    fi
    log workflow "renamed $old → $slug"
    echo "OK: renamed to $emoji $new ($WF_DIR/$slug)." ;;

  show)
    slug="$( [[ -n "${1:-}" ]] && resolve "$1" || cur_slug )" || { echo "ERROR: no workflow '$1'"; exit 1; }
    echo "$(title_of "$slug")"
    grep -m1 '^Goal:' "$WF_DIR/$slug/WORKFLOW.md"
    p="$(pending_for "$slug")"
    if [[ -n "$p" ]]; then echo "Pending:"; echo "$p"; else echo "Pending: nothing"; fi ;;

  *) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
