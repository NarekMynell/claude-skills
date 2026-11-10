#!/usr/bin/env bash
# The SessionStart, SubagentStart and UserPromptSubmit hook of every domain plugin, identical in each (source: shared/hooks/).
# Gives Claude the domain's standards where the project turned the domain on, or where the user typed the standards command of
# a domain that builds on this one. Prints nothing otherwise. Always exits 0.
#   SessionStart: startup and clear give them where the project has the domain on; compact gives them back to a session that
#     had them, from the switches or from a command; resume and fork only note that the session has them in its transcript.
#   SubagentStart: what the session has; not for agents that only read.
#   UserPromptSubmit: "/<domain>:standards <task>" of a domain that builds on this one, unless this one is switched off; or the
#     domain came on during the session, as when /core:skills turned it on, and the session doesn't have its standards yet.
# The hook output's cap is 10,000 characters, past which Claude gets only a preview: a toolchain report is cut to fit.

self="$1"
root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
hooks_dir="$root/hooks"
[ -n "$self" ] && [ -f "$root/skills/standards/SKILL.md" ] && [ -f "$hooks_dir/domains.txt" ] || exit 0
. "$hooks_dir/lib.sh"

input="$(cat)"
event="$(input_field "$input" hook_event_name)"
session="$(input_field "$input" session_id)"
# A session that has this domain's standards gets nothing more at a prompt: most prompts end here.
[ "$event" = UserPromptSubmit ] && marked "$session" && exit 0
load_domains
prefix_of "$self"
[ -n "$prefix" ] || exit 0
self_prefix="$prefix"
cwd="$(working_folder "$(hook_cwd "$input")")"
load_settings "$cwd"

# Whether a command brings this domain in: not when the project switched it off. The base comes whatever its switch says.
command_brings() {
  switch_value "${self_prefix}_STANDARDS"
  [ "$value" != off ] || [ "$self" = "$base" ]
}

reason=""
asked=""
mode=switches
case "$event" in
  SessionStart)
    source_of="$(input_field "$input" source)"
    if any_switch && domain_loads "$self"; then
      case "$source_of" in
        resume | fork) mark "$session"; exit 0 ;;
      esac
      reason=project
    elif [ "$source_of" = compact ] && marked "$session" && command_brings; then
      reason=compacted
      mode=command
    else
      exit 0
    fi
    ;;
  SubagentStart)
    case "$input" in
      *'"agent_type":"Explore"'* | *'"agent_type": "Explore"'* | *'"agent_type":"claude-code-guide"'* | *'"agent_type": "claude-code-guide"'* | *'"agent_type":"statusline-setup"'* | *'"agent_type": "statusline-setup"'*) exit 0 ;;
    esac
    if any_switch && domain_loads "$self"; then
      reason=subagent
    elif marked "$session" && command_brings; then
      reason=subagent
      mode=command
    else
      exit 0
    fi
    ;;
  UserPromptSubmit)
    asked="$(prompt_domain "$input")"
    if [ -n "$asked" ] && [ "$asked" = "$self" ]; then
      # The command itself gives the standards.
      mark "$session"
      exit 0
    fi
    if [ -n "$asked" ] && builds_on "$asked" "$self" && command_brings; then
      reason=pulled
      mode=command
    elif any_switch && domain_loads "$self"; then
      reason=turned-on
    else
      exit 0
    fi
    ;;
  *) exit 0 ;;
esac

# The skills that load: the project's switches, or for a command all of them but those switched off one by one.
if [ "$mode" = switches ]; then
  active_skills "$self"
else
  skill_pairs_of "$self"
  on_skills=""
  for pair in $pairs; do
    switch_value "${self_prefix}_SKILL_${pair#*=}"
    [ "$value" = off ] || on_skills="${on_skills:+$on_skills }${pair%%=*}"
  done
fi
# The base loads its standards even with all its own guides off; another domain with none on has nothing to give.
[ -n "$on_skills" ] || [ "$self" = "$base" ] || exit 0

skill_pairs_of "$self"
all=""
off=""
for pair in $pairs; do
  all="${all:+$all }${pair%%=*}"
  case " $on_skills " in *" ${pair%%=*} "*) ;; *) off="${off:+$off, }${pair%%=*}" ;; esac
done
hub_text "$root" "$on_skills" "$all"

case "$reason" in
  project) intro="This project has the $self skills on for every session, so its standards load here as if the user had typed \`/$self:standards\`." ;;
  pulled) intro="The user typed \`/$asked:standards\`, which builds on $self: its standards load here too." ;;
  turned-on) intro="The $self skills were turned on in this project during this session: its standards load here." ;;
  compacted) intro="This session had the $self standards before compaction: they load here again." ;;
  subagent) intro="You are a subagent in a project with the $self standards on: they bind your work as they bind the main session's. Before working, read the guides in the tables below that match your task, with the Read tool." ;;
esac
[ -z "$off" ] || intro="$intro Off in this project, so their rows are left out: $off. Read one only when a guide that is on sends you to it, or the user asks."
context="$intro

$hub"

if [ "$event" = SessionStart ]; then
  mark "$session"
  event_name=SessionStart
elif [ "$event" = UserPromptSubmit ]; then
  mark "$session"
  event_name=UserPromptSubmit
else
  event_name=SubagentStart
fi

case "$input" in
  *'"source":"startup"'* | *'"source": "startup"'*)
    if [ -f "$root/skills/toolchain/scripts/check.sh" ]; then
      # The check can wait on the network. A watchdog stops it after 15 seconds, well inside the hook's 30-second timeout,
      # so a slow network costs the toolchain report, never the standards.
      report_file="$(mktemp 2> /dev/null || echo "${TMPDIR:-/tmp}/$self-check.$$")"
      bash "$root/skills/toolchain/scripts/check.sh" "${CLAUDE_PROJECT_DIR:-$cwd}" "$CLAUDE_PLUGIN_DATA" \
        > "$report_file" 2> /dev/null < /dev/null &
      check_pid=$!
      ( sleep 15; kill "$check_pid" 2> /dev/null ) > /dev/null 2>&1 < /dev/null &
      watchdog_pid=$!
      wait "$check_pid" 2> /dev/null
      { kill "$watchdog_pid"; wait "$watchdog_pid"; } 2> /dev/null
      problems="$(cat "$report_file" 2> /dev/null)"
      rm -f "$report_file"
      if [ -n "$problems" ]; then
        advice="Tell the user about these problems in a few lines at the start of your first reply, with the command that fixes them: \`/$self:toolchain\`, or \`/$self:version-notes\` for the version notes."
        room=$((9800 - ${#context} - ${#advice}))
        if [ "$room" -lt 0 ]; then room=0; fi
        if [ "${#problems}" -gt "$room" ]; then
          problems="$(printf '%s\n' "$problems" | awk -v room="$room" '{ used += length($0) + 1; if (used > room) exit; print }')
(more: /$self:toolchain)"
        fi
        context="$context

$problems
$advice"
      fi
    fi
    ;;
esac

# Core, which comes with every domain, names in the session's first line what this project has on, and which of those domains
# its settings don't let Claude read without asking: a project set up before the domains split has unity-dev's read rule only.
message=""
if [ "$event" = SessionStart ] && [ "$self" = core ]; then
  summary=""
  unreadable=""
  for domain in $domains; do
    domain_loads "$domain" || continue
    skill_pairs_of "$domain"
    skipped=""
    for pair in $pairs; do
      skill_on "$domain" "${pair%%=*}" || skipped="${skipped:+$skipped, }${pair%%=*}"
    done
    summary="${summary:+$summary; }$domain${skipped:+ (off: $skipped)}"
    rule="Read(~/.claude/plugins/cache/*/$domain/**)"
    readable=""
    while IFS= read -r file; do
      [ -n "$file" ] && [ -f "$file" ] && grep -qF -- "$rule" "$file" 2> /dev/null && { readable=1; break; }
    done <<FILES
$files
$HOME/.claude/settings.json
FILES
    [ -n "$readable" ] || unreadable="${unreadable:+$unreadable, }$domain"
  done
  line="Switched on in this project: $summary"
  if [ -n "$unreadable" ]; then
    line="$line. No read rule for: $unreadable, so their guides ask before opening; /core:skills adds the rules"
    context="$context

This project's settings have no read rule for: $unreadable. Reading those domains' guides asks the user each time until \`/core:skills\` adds the rules: tell the user once."
  fi
  message="\"systemMessage\":\"$(printf '%s' "$line" | json_escape)\","
fi

printf '{%s"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$message" "$event_name" "$(printf '%s' "$context" | json_escape)"
exit 0
