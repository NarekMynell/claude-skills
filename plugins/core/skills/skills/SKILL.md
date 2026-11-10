---
name: skills
description: Shows which domains and skills of this marketplace a project has on, and turns them on or off in its settings, for the whole team or for you alone. Without arguments it looks at the project and turns on what it needs.
disable-model-invocation: true
argument-hint: "[on | off <domain or domain:skill>... | what the project is]"
allowed-tools:
  - Read(~/.claude/plugins/cache/*/core/**)
  - Bash(claude plugin list *)
---

# Skills in a project

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Arguments: `$ARGUMENTS`

The [catalog](catalog.md) lists every domain and skill of this marketplace, what each covers, its switch and its read rule. Read it first, then open a domain's guides only when a choice depends on them.

## Switches

Under `env` in the project's `.claude/settings.json`, which the team shares, or `.claude/settings.local.json`, which is personal and wins key by key:

| Switch | Values | Turns on or off |
|---|---|---|
| `<DOMAIN>_STANDARDS` | `on`, `off` | A domain and all its skills: `UNITY_DEV_STANDARDS` |
| `<DOMAIN>_SKILL_<SKILL>` | `on`, `off` | One skill, whatever its domain's switch says: `UNITY_DEV_SKILL_VFX` |

- A domain with no switch follows the domains that build on it: game-design and modeling are on wherever unity-dev's switch is. `off` keeps one out, such as `MODELING_STANDARDS: off` in a 2D Unity game. A single skill switched on brings no other domain.
- Core is the base: it is on wherever any domain or skill is, and can't be switched off while one is. Its own guides can.
- A skill needs the skills in the catalog's Needs column: don't switch those off while it is on, and if the user asks to, say what breaks.
- A domain that is on loads its standards at the start of every session, after `/clear` and after compaction, and gives them to subagents. Its guides load when the work needs them.
- Every domain that is on needs its read rule under `permissions.allow`, `Read(~/.claude/plugins/cache/*/<domain>/**)`, so its guides open without asking each time. Add the rules of the domains a switch brings with it too. A project set up before the domains split has `UNITY_DEV_STANDARDS` with only unity-dev's rule: add the others.
- A domain turned on loads with the user's next message. One turned off leaves the session's context only in the next session, or after `/clear`.
- The settings belong to the session's project folder (`${CLAUDE_PROJECT_DIR}`). Never write switches into the home folder's `.claude/settings.json`: that turns them on in every project.

## Steps

1. **Read** both settings files with the Read tool (a missing file sets nothing), and the catalog. `claude plugin list --json` says which domains are installed.
2. **Decide:**
   - `on` or `off` followed by names: each name is a domain (`modeling`) or one skill (`unity-dev:vfx`). An unknown name: say so, name the closest ones, and stop.
   - Anything else, or nothing: look at the project and the user's words. What it is made with and of: `ProjectSettings/ProjectVersion.txt` makes a Unity project; `.blend`, `.fbx` or `.glb` files mean 3D models; a game's design docs mean game design. Choose the smallest set that covers the work: the domains, and skills switched off inside them where the project clearly has no use for them, each with one line of why. Write it, unless the user asked only for a proposal.
3. **Write** with Edit or Write, not through the shell, merging and keeping every other key: into `.claude/settings.json`, unless the user asked for themselves alone, or `.claude/settings.local.json` already sets that switch. Claude Code asks the user to approve changes to settings files. In `.claude/settings.json` also list the marketplace and the domains that are on, so teammates are offered them once they trust the folder; with unity-dev on, Anthropic's official marketplace too, where its `unity` and `csharp-lsp` come from:

   ```json
   {
     "extraKnownMarketplaces": {
       "narek-skills": { "source": { "source": "github", "repo": "NarekMynell/claude-skills" } },
       "claude-plugins-official": { "source": { "source": "github", "repo": "anthropics/claude-plugins-official" } }
     },
     "enabledPlugins": { "<domain>@narek-skills": true }
   }
   ```

   A domain that isn't installed loads nothing: give the user `claude plugin install <domain>@narek-skills` for each (for unity-dev, after `claude plugin marketplace add anthropics/claude-plugins-official`), and say that plugins load after Claude Code restarts.
4. **Report** in a short table: each domain or skill changed, its value and the file. Then one line on what loads from the next message, what a domain brings with it, and how to switch a part off.
