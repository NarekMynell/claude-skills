---
name: version-notes
description: Researches what changed in Unity between the versions Claude knows well and the project's version, and records what matters for the project in docs/unity-version-notes.md.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Unity version notes

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Claude's training data lags behind the newest Unity releases: newer versions bring optimizations, APIs and features Claude may not know. This skill closes the gap from official sources once, and saves the result so later sessions read it instead of repeating the research.

## Steps

1. Read `m_EditorVersion` from `ProjectSettings/ProjectVersion.txt`.
2. Set the range: from the newest Unity version you know in depth to the project's version. If `docs/unity-version-notes.md` exists for an older version, research only from that version on, and keep the entries that still apply.
3. Read the official sources for every minor version in the range:
   - What's new: `https://docs.unity.com/en-us/engine/<6000.N>/manual/whats-new/unity6N` (for example `6000.6` → `unity66`);
   - upgrade guide: `https://docs.unity.com/en-us/engine/<6000.N>/manual/upgrade-guides/upgrade-guide-unity6N`;
   - release notes of the exact version: `https://unity.com/releases/editor/whats-new/<version>`, for known issues and fixes;
   - changelogs of the project's key packages (render pipeline, Input System, Addressables) for the versions in `Packages/manifest.json`.
4. Keep only what is relevant to this project: its render pipeline, platforms and packages. Look for optimizations, new features and APIs, deprecations, breaking changes and known issues.
5. Write `docs/unity-version-notes.md` in the format below. The first line is read by the toolchain check and must stay exact.
6. List the file in the indexes of `README.md` and `CLAUDE.md`. The notes themselves stay out of `CLAUDE.md`.

## Format

```markdown
Covers Unity 6000.6.2f1.

# Unity version notes

What changed in Unity since <newest version known in depth> that matters for this project.

## Use
- <feature or API worth adopting, why it helps here, link>

## Avoid
- <deprecated or obsolete API, its replacement, link>

## Breaking changes
- <change that affects this project's code or assets, link>

## Known issues
- <issue in this exact version that the project could hit, workaround, link>
```

Every entry is one line with a link to its source. Omit empty sections.

## Using the notes

- Adopt a feature only when it benefits the project, never because it is new.
- Don't rely on experimental or preview APIs without the user's approval.
- During a task, if it touches a system that changed recently, or you're unsure whether an API is current, check the documentation for the project's exact Unity version before writing code.
