# Skills marketplace

This repo is a Claude Code plugin marketplace: it lists several plugins, and each plugin is a themed pack of skills. People install it from GitHub, so everything here has to work on any machine, for anyone.

## Layout

- `.claude-plugin/marketplace.json` lists the plugins. A new plugin needs an entry here.
- `plugins/<plugin>/.claude-plugin/plugin.json` is the plugin's manifest. Bump its `version` (semver) with every change users should receive.
- `plugins/<plugin>/skills/<skill>/SKILL.md` is one skill. Its supporting files (`references/`, `scripts/`, `templates/`) sit next to it. When a skill runs, Claude receives its base directory, so link supporting files with paths relative to the skill folder.
- `plugins/unity-dev/skills/standards/` is the command that loads the unity-dev standards for a session. It reads the other unity-dev skills as guides: a new guide gets a row in its table.
- `plugins/unity-dev/skills/library/` holds the Unity code library: `CATALOG.md`, and `code/`, which mirrors a project's `Assets/_Project/Scripts/` with the placeholder prefix `Company.Product`. Projects copy from it under their own namespace. Authoring rules: `plugins/unity-dev/skills/library/references/authoring.md`.

Put a new skill in the plugin whose `description` in `marketplace.json` fits. If none fits, add a new plugin.

## Nothing loads on its own

The user decides when a plugin acts: no hooks, and no skill Claude can load by itself.

- Every skill sets `disable-model-invocation: true`, so it loads only when the user types its command. Claude never sees the descriptions: `description` is for people browsing the `/` menu, one sentence on what the skill does.
- Every skill pre-approves reading its own plugin's files with `allowed-tools: Read(~/.claude/plugins/cache/*/<plugin>/**)`. Plugin files sit outside the project, so without the rule each read asks for permission.
- Skills link each other with relative paths (`../library/SKILL.md`), never by skill name: Claude can't invoke them, so it reads the linked file. A plugin can't link another plugin's files, because each plugin is copied on its own; point the user to that plugin's command instead.
- `${CLAUDE_PLUGIN_ROOT}` and the other variables are substituted only in the skill the user invoked, not in files Claude reads from it. Use them only in skills no other skill reads (`standards`, `toolchain`), and relative paths everywhere else.
- Templates copied into projects hold project knowledge only: what the project is, its decisions, its docs index. A project's `CLAUDE.md` loads in every session, so it never tells Claude to load or follow these skills.

## Writing a skill

- The folder name matches `name` in the frontmatter: lowercase, hyphens.
- Write only what Claude doesn't already know: decisions, conventions, gotchas. Skip textbook explanations.
- Keep SKILL.md under ~500 lines. Move details into `references/` and link them from SKILL.md.
- Verify every command, API name and URL before writing it: in the official docs, in the package source, or by running it.

## Keeping it shareable

- Write everything in English.
- No personal preferences (reply language, tone, names). Those belong in each user's own `~/.claude/CLAUDE.md`.
- No absolute paths, usernames or secrets.
- Scripts are bash 3.2 compatible (macOS default), use only POSIX tools, always exit 0, and print nothing when there is nothing to report.
- unity-dev restates the essentials of core's `project-docs` in `new-project`, `adopt-standards` and `standards`, so it works without core. Change them together.
- Don't duplicate what the official `unity` plugin already covers: link to its skills.

## Testing

- `claude plugin validate .` and `claude plugin validate plugins/<plugin>` before pushing.
- `claude --plugin-dir plugins/<plugin> plugin details <plugin>` shows the per-skill token cost. Its always-on figure counts descriptions that `disable-model-invocation` keeps out of context.
- End-to-end: run `claude -p --plugin-dir <repo>/plugins --add-dir <repo>/plugins "<prompt>"` from a test project outside this repo (this file would leak into one inside it). Check both directions: a plain prompt loads nothing from these plugins, and a command loads what it should. `--add-dir` stands in for the read rule, which matches only the installed cache.
- Blender scripts: run them headless (`Blender -b --factory-startup --python <test>`) against meshes with known defects.
- Library modules: see the authoring rules.

## Releasing

A plugin's `version` pins users to it, so every release bumps it in `plugin.json` (never also in `marketplace.json`). Tag the release from the plugin folder with `claude plugin tag --push`, which creates `<plugin>--v<version>`; dependency version ranges resolve against these tags.
