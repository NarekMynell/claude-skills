# Skills marketplace

This repo is a Claude Code plugin marketplace: it lists several plugins, and each plugin is a themed pack of skills. People install it from GitHub, so everything here has to work on any machine, for anyone.

## Layout

- `.claude-plugin/marketplace.json` lists the plugins. A new plugin needs an entry here.
- `plugins/<plugin>/.claude-plugin/plugin.json` is the plugin's manifest. Bump its `version` (semver) with every change users should receive.
- `plugins/<plugin>/skills/<skill>/SKILL.md` is one skill. Its supporting files (`references/`, `scripts/`, `templates/`) sit next to it. When a skill runs, Claude receives its base directory, so link supporting files with paths relative to the skill folder.
- `plugins/<plugin>/hooks/hooks.json` declares hooks; their scripts sit next to it and are reached through `${CLAUDE_PLUGIN_ROOT}`.
- `plugins/unity-dev/skills/library/` holds the Unity code library: `CATALOG.md`, and `code/`, which mirrors a project's `Assets/_Project/Scripts/` with the placeholder prefix `Company.Product`. Projects copy from it under their own namespace. Authoring rules: `plugins/unity-dev/skills/library/references/authoring.md`.

Put a new skill in the plugin whose `description` in `marketplace.json` fits. If none fits, add a new plugin.

## Writing a skill

- The folder name matches `name` in the frontmatter: lowercase, hyphens.
- `description` decides when Claude loads the skill. Say what it does and when to use it, in the words a user would actually type. Every description is loaded in every session: keep it tight.
- Write only what Claude doesn't already know: decisions, conventions, gotchas. Skip textbook explanations.
- Keep SKILL.md under ~500 lines. Move details into `references/` and link them from SKILL.md.
- Verify every command, API name and URL before writing it: in the official docs, in the package source, or by running it.
- A skill that should run only when the user types its command gets `disable-model-invocation: true`. Skills that other skills invoke must stay model-invocable.

## Keeping it shareable

- Write everything in English.
- No personal preferences (reply language, tone, names). Those belong in each user's own `~/.claude/CLAUDE.md`.
- No absolute paths, usernames or secrets.
- Hook scripts are bash 3.2 compatible (macOS default), use only POSIX tools, never fail the session (exit 0), and print nothing when there is nothing to report.
- Don't duplicate what the official `unity` plugin already covers: link to its skills.

## Testing

- `claude plugin validate .` and `claude plugin validate plugins/<plugin>` before pushing.
- `claude --plugin-dir plugins/<plugin> plugin details <plugin>` shows the always-on and per-skill token cost.
- End-to-end: run `claude -p --plugin-dir plugins/<plugin> "<prompt>"` from a test project folder.
- Blender scripts: run them headless (`Blender -b --factory-startup --python <test>`) against meshes with known defects.
- Library modules: see the authoring rules.

## Releasing

A plugin's `version` pins users to it, so every release bumps it in `plugin.json` (never also in `marketplace.json`). Tag the release from the plugin folder with `claude plugin tag --push`, which creates `<plugin>--v<version>`; dependency version ranges resolve against these tags.
