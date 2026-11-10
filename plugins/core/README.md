# core

Working standards for projects of any kind, and the switches that choose which domains of this marketplace a project uses. Every other domain builds on it, so it comes on wherever any domain is on.

- **Standards:** musts with proofs that can fail and guides that are advice, receipts in `docs/proofs/`, verification against the project's own versions, fresh reviews, honest reports, the done checklist.
- **Switches:** `/core:skills` shows what a project has on, turns domains and skills on or off, or looks at the project and turns on what it needs.

Switch: `CORE_STANDARDS`. Its hooks also refuse hand edits of receipts in `docs/proofs/` wherever any domain is on.

## Install

```sh
claude plugin install core --marketplace NarekMynell/claude-skills
```

## Skills

<!-- catalog:skills -->
| Skill | Command | What it does | Switch |
|---|---|---|---|
| [project-docs](skills/project-docs/SKILL.md) | `/core:project-docs` | Sets up or tidies a project's documentation so people and Claude share one source of truth - README.md and CLAUDE.md as indexes, knowledge in docs/, Claude instructions in CLAUDE.md and .claude/rules/. | `CORE_SKILL_PROJECT_DOCS` |
| [skills](skills/skills/SKILL.md) | `/core:skills` | Shows which domains and skills of this marketplace a project has on, and turns them on or off in its settings, for the whole team or for you alone. Without arguments it looks at the project and turns on what it needs. | `CORE_SKILL_SKILLS` |
| [standards](skills/standards/SKILL.md) | `/core:standards` | Loads the working standards for any project - musts with proofs and guides, receipts, verification against the project's own versions, fresh reviews, honest reports, the done checklist - and turns core on for every session in the project. Add a task to start it right away; `off` and `on` switch every-session loading. | `CORE_STANDARDS` |
| [version-notes](skills/version-notes/SKILL.md) | `/core:version-notes` | Researches what changed in a project's key technologies between the versions Claude knows well and the versions the project uses, and records what matters for it in docs/<technology>-version-notes.md. | `CORE_SKILL_VERSION_NOTES` |
<!-- /catalog -->
