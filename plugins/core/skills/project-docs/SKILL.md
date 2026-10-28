---
name: project-docs
description: Sets up and maintains a project's documentation layout so people and Claude share one source of truth - README.md and CLAUDE.md as indexes, project knowledge in docs/, Claude instructions in CLAUDE.md and .claude/rules/. Use when creating a project, adding or reorganizing documentation, writing a CLAUDE.md or a rule file, or when docs are scattered, duplicated or out of date.
---

# Project documentation layout

## Principle

Files are split by **content**, not by reader:

- **Knowledge** about the project (what it is, how it works) goes in `docs/`. People and Claude read the same files, so nothing is written twice and nothing drifts.
- **Instructions** for Claude (how to work on the project) go in `CLAUDE.md` and `.claude/rules/`.

Entry files stay small and act as indexes: read the index, then open only the file the task needs.

## Layout

```
<project root>/
├── README.md          Entry point for people: overview, setup, index of docs/
├── CLAUDE.md          Entry point for Claude: rules for every task, index of docs/ and .claude/rules/
├── docs/              Project knowledge, one topic per file
└── .claude/
    └── rules/         Instructions for one area of work, one topic per file
```

| File | Contains | Does not contain |
|---|---|---|
| `README.md` | What the project is, requirements, how to open and run it, one line per `docs/` file | Topic details |
| `docs/<topic>.md` | The full documentation of one topic | Other topics: link to them |
| `CLAUDE.md` | Rules that apply to every task; one "read when" line per `docs/` and `.claude/rules/` file | Knowledge; rules for only some tasks |
| `.claude/rules/<topic>.md` | Instructions for one area (UI, networking) | Knowledge |

## Rules files

- `CLAUDE.md` loads at the start of every session: keep it as short as possible.
- A file in `.claude/rules/` declares the files it applies to with `paths` frontmatter (globs such as `src/**/*.{ts,tsx}`). It loads when Claude reads, writes or edits a matching file. A rule without `paths` loads at the start of every session, so a rule that applies everywhere belongs in `CLAUDE.md` instead.

  ```markdown
  ---
  paths:
    - "src/network/**/*.cs"
  ---
  # Networking rules
  ```

- A path-scoped rule loads together with the tool call that touches the file, which is too late for the first file written in an area. Before creating files in an area, read that area's rule from the `CLAUDE.md` index.

## Writing standards

- **Concise.** No filler, no repetition, nothing the reader already knows. Every sentence carries information.
- **Complete.** Concise doesn't mean missing something: the reader must not have to guess.
- **Clear.** Plain, direct English, short sentences, one term per concept.
- **Structured.** One topic per file, opening with a one-line statement of its purpose. Headings, lists and tables for scanning; code blocks for code, paths and commands.
- **Linked, not duplicated.** If something is documented, link to it.
- **Named clearly.** Lowercase kebab-case names that describe the topic: `save-system.md`, not `notes2.md`.
- **No empty placeholders.** Create a file only when there is real content for it.

## Keeping it current

- A change that affects documented behavior updates the matching `docs/` file in the same change.
- A file added, renamed or removed updates the indexes in `README.md` and `CLAUDE.md`.
- A file that grows to cover more than one topic is split.

## Setting up a project

1. Create `README.md` and `CLAUDE.md` from [templates/README.md](templates/README.md) and [templates/CLAUDE.md](templates/CLAUDE.md). If they already exist, merge: keep the project's content and add the missing parts.
2. Create `docs/` and `.claude/rules/` files only for topics that have content.
3. Fill every index.
