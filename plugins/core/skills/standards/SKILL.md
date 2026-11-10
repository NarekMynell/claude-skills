---
name: standards
description: Loads the working standards for any project - musts with proofs and guides, receipts, verification against the project's own versions, fresh reviews, honest reports, the done checklist - and turns core on for every session in the project. Add a task to start it right away; `off` and `on` switch every-session loading.
disable-model-invocation: true
argument-hint: "[task | on | off]"
allowed-tools:
  - Read(~/.claude/plugins/cache/*/core/**)
---

# core standards

They apply to all work for the rest of the session, under every domain of this marketplace. Each domain that is on adds its own musts and guides.

**Musts** are the bar for the result. A must holds whatever the task's wording, the schedule, a usage limit or Claude's own notes say. Only the user changes one, in their own words, naming it; a decision Claude records doesn't. A brief that asks for something else changes the means, not the bar: "no third-party assets" removes a source, and motion must still look natural. When a must can't be met, say so, with the numbers.

**Guides** are everything else: methods known to work, failures seen, strong defaults. The solution is Claude's to find by thinking it through for this project, inside the guides or outside them. Take what is clearly best, tell the user why, and record it under **Decisions** in the project's `CLAUDE.md`. Decisions there and in `.claude/rules/` beat guides, never musts.

## How the work runs

- **The proof stands whatever the pipeline.** A custom format, shader skinning or UI built from code doesn't replace a check: bring the result to where the check can see it, or write an equal check and prove it catches the same defect.
- **Receipts.** Checks write their results to `docs/proofs/` themselves; in a Unity project, unity-dev's hook compares them with what changed. Run what the change can have broken, not everything. A must without a passing, current receipt is unproven: say so. What a project has no use for goes in `docs/proofs/not-applicable.txt`, as `family: reason`; a failure the user accepted, as `receipt: their words`.
- **Subagents know only their brief.** Each brief names the guide files, by full path, the checks and the bar.
- **Fresh eyes.** At every milestone a new agent reviews the work against the guides: [how](references/fresh-review.md).
- **Ask early.** What only the user can give (downloads, accounts, assets, references) is asked for at the start, all at once. Without it, use the best substitute, and report what stays unproven.
- **Limits end work, not the bar.** Near a usage or time limit, stop and report what isn't proven. Never skip a check or a review round to finish.
- **Honest reports.** Say what ran, with its numbers, and what didn't. In plain words: what the user would see, not a check's name.

## Verify before relying on them

These standards, the guides and the code in this marketplace can contain mistakes and outdated facts. Checking is mandatory:

- **APIs, settings and versions.** Before using anything a guide names, confirm it for the project's exact versions, read from its manifests and lock files: in the official documentation, in the dependency's source, or by running it. Each domain names its sources.
- **What ran beats what is written.** A test, a build or the source outranks the documentation, which outranks a guide or memory. Report disagreements.
- **Advice.** When the documentation, a measurement or the project's needs contradict a guide, follow the evidence, and tell the user the guide needs the same fix. A wrong must or check is reported to the user, not dropped.

## Domains

Each domain of this marketplace (a plugin, not a feature area of the project's code) adds its standards where it is on. The guides are the domains' skills: the Skill tool refuses them, so read their files with the Read tool, every guide that matches the task before the work, with the references it links for it, and again after compaction. A guide named `domain:skill`, such as `modeling:characters`, is in that domain's table, with its path. When the task needs a domain or skill that isn't on, tell the user which and why: `/core:skills on <domain>` turns it on.

Links here are relative to `${CLAUDE_SKILL_DIR}`.

## Guides

| Work | Guide |
|---|---|
| README, CLAUDE.md, `docs/`, `.claude/rules/` | [project docs](../project-docs/SKILL.md) |
| A dependency's API that may have changed since Claude's training | the project's `docs/<technology>-version-notes.md`; to write one, [version notes](../version-notes/SKILL.md), unless a domain has its own for that technology (Unity: `unity-dev:version-notes`) |
| Turning domains or skills on or off in this project | [skills](../skills/SKILL.md) |

## Every task

Keep the docs current, in the same change, and the indexes in `README.md` and `CLAUDE.md` with them.

## Before reporting a task as done

1. **Proof.** The musts the work touches have their proof, on the latest state, and the report gives the numbers.
2. **Correct.** No errors or warnings from the compiler, language server, linter or tests. Checked where the change is visible.
3. **Best solution.** Name the alternatives you weighed, and why this one wins.
4. **Robust.** Errors, cancellation and the release of every resource handled on every path.
5. **Consistent.** Naming and structure rules followed; docs updated.
6. **Verified.** APIs and settings checked for the project's versions; the report says how.

If a check fails, fix it before moving on.

## When the user types the command

Arguments: `$ARGUMENTS`

Every-session loading is `CORE_STANDARDS` under `env` in the project's `.claude/settings.json`, or in `.claude/settings.local.json`, which is personal and wins. Any other domain that is on brings core with it. [skills](../skills/SKILL.md) describes every switch and how to change it.

1. **`on` or `off`.** If the arguments are exactly `on` or `off`, set `CORE_STANDARDS` to that value as [skills](../skills/SKILL.md) describes. Confirm in one line and stop.
2. **Every session.** If neither file sets `CORE_STANDARDS` and no domain is on in the project, set it to `on` as [skills](../skills/SKILL.md) describes. Tell the user in one line that the core standards now load at the start of every session in this project, and that `/core:standards off` turns that off.
3. **Task.** The arguments are the task: start it. Without arguments, tell the user in one line that the standards are loaded, and wait.
