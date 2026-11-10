---
name: version-notes
description: Researches what changed in a project's key technologies between the versions Claude knows well and the versions the project uses, and records what matters for it in docs/<technology>-version-notes.md.
disable-model-invocation: true
argument-hint: "[technology]"
allowed-tools:
  - Read(~/.claude/plugins/cache/*/core/**)
---

# Version notes

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Claude's training data lags behind new releases: a newer version brings APIs, features, deprecations and fixes Claude may not know. These notes close the gap from official sources once, and later sessions read them instead of repeating the research. A domain can name the exact sources and checks for its technology, and its guide wins for it: Unity's notes follow `unity-dev:version-notes`.

## Steps

1. **The versions:** read them from the project's manifests and lock files (`package.json` with its lock file, `pyproject.toml`, `go.mod`, `Cargo.toml`...). The key technologies are the language or runtime, the framework, and the dependencies most of the code touches.
2. **The range,** per technology: from the newest version you know in depth to the project's. If `docs/<technology>-version-notes.md` exists for an older version, research from that version on, and keep the entries that still apply.
3. **Official sources** for every release in the range: release notes, migration or upgrade guides, the changelog, and known issues of the exact version. Prefer the project's own documentation site to articles about it.
4. **Keep only what matters to this project:** features or APIs worth adopting, deprecations and their replacements, breaking changes that touch its code, known issues it could hit.
5. **Write** `docs/<technology>-version-notes.md` (`docs/react-version-notes.md`) in the format below. Its first line names what it covers, so a check can compare it with the project's version.
6. **Index** the file in `README.md` and `CLAUDE.md`. The notes themselves stay out of `CLAUDE.md`.

## Format

```markdown
Covers <Technology> <exact version>.

# <Technology> version notes

What changed since <newest version known in depth> that matters for this project.

## Use
- <feature or API worth adopting, why it helps here, link>

## Avoid
- <deprecated or obsolete API, its replacement, link>

## Breaking changes
- <change that affects this project's code, link>

## Known issues
- <issue in this exact version that the project could hit, workaround, link>
```

Every entry is one line with a link to its source. Leave out empty sections.

## Using the notes

- Adopt a feature only when it benefits the project, never because it is new.
- Don't rely on experimental or preview APIs without the user's approval.
- When a task touches something that changed recently, or you're unsure an API is current, check the documentation for the project's exact version before writing code.
