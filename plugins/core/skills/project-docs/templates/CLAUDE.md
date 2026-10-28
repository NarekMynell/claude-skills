# <Project name>

<One or two sentences: what the project is and who it is for.>

## Documentation

- Project knowledge lives in `docs/`, instructions for Claude in this file and in `.claude/rules/`. Read this index, then open only what the task needs.
- A change that affects documented behavior updates the matching `docs/` file in the same change. Adding, renaming or removing a file updates this index and the one in `README.md`.
- New files follow the `core:project-docs` writing standards: concise, complete, one topic per file, linked instead of duplicated, no empty placeholders.

### docs/

| File | Read when |
|---|---|
| `docs/<topic>.md` | <when this file is needed> |

### .claude/rules/

| File | Applies to |
|---|---|
| `.claude/rules/<topic>.md` | <paths or area> |
