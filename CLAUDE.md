# Skills marketplace

This repo is a Claude Code plugin marketplace with one plugin, `unity-dev`: a pack of skills for Unity game development, including Blender 3D assets and project documentation. People install it from GitHub, so everything here has to work on any machine, for anyone.

## Layout

- `.claude-plugin/marketplace.json` lists the plugins. A new plugin needs an entry here.
- `plugins/<plugin>/.claude-plugin/plugin.json` is the plugin's manifest. Bump its `version` (semver) with every change users should receive.
- `plugins/<plugin>/skills/<skill>/SKILL.md` is one skill. Its supporting files (`references/`, `scripts/`, `templates/`) sit next to it. When a skill runs, Claude receives its base directory, so link supporting files with paths relative to the skill folder.
- `plugins/unity-dev/skills/standards/` is the one command users need: it loads the standards and routes Claude to every other skill, which it reads as a guide. A new skill gets a row in its table.
- `plugins/unity-dev/skills/library/` holds the Unity code library: `CATALOG.md`, and `code/`, which mirrors a project's `Assets/_Project/Scripts/` with the placeholder prefix `Company.Product`. Projects copy from it under their own namespace. Authoring rules: `plugins/unity-dev/skills/library/references/authoring.md`.

Put every new skill in `unity-dev`, so one command reaches it. A skill in another plugin couldn't be read from `standards`: each plugin is copied to its own folder.

## Nothing loads unless the user asks

The user decides when a plugin acts: no skill Claude can load by itself, and one hook that does nothing until the user turns it on for a project.

- Every skill sets `disable-model-invocation: true`, so it loads only when the user types its command. Claude never sees the descriptions: `description` is for people browsing the `/` menu, one sentence on what the skill does.
- Every skill pre-approves reading its own plugin's files with `allowed-tools: Read(~/.claude/plugins/cache/*/<plugin>/**)`. Plugin files sit outside the project, so without the rule each read asks for permission.
- Skills link each other with relative paths (`../library/SKILL.md`), never by skill name: Claude can't invoke them, so it reads the linked file. A plugin can't link another plugin's files, because each plugin is copied on its own; point the user to that plugin's command instead.
- `${CLAUDE_PLUGIN_ROOT}` and the other variables are substituted only in the skill the user invoked, not in files Claude reads from it. Use them only in `standards` and `toolchain`, and relative paths everywhere else.
- Every-session loading is a per-project switch: `UNITY_DEV_STANDARDS` set to `on` under `env` in the project's `.claude/settings.json` (or `.claude/settings.local.json`), next to the plugin's read rule, because outside a command nothing pre-approves those reads. `/unity-dev:standards` writes both on its first run in a project; `new-project` and `adopt-standards` write them through the team settings template. With the switch on, unity-dev's SessionStart hook (`hooks/standards.sh`) adds `skills/standards/SKILL.md` up to its `## When the user types the command` heading to the context on startup, `/clear` and compaction. That part must work without the command, use no variable but `${CLAUDE_SKILL_DIR}`, which the hook resolves, and stay well under the 10,000-character cap on hook output.
- Templates copied into projects hold project knowledge only: what the project is, its decisions, its docs index. A project's `CLAUDE.md` loads in every session, so it never tells Claude to load or follow these skills; the switch does that.

## Writing a skill

- The folder name matches `name` in the frontmatter: lowercase, hyphens.
- Every skill and reference opens, right after its title, with the line saying it can be wrong or out of date and must be verified, linked to the rule in `standards` (copy it from an existing skill). The user asked for this on every guide: Claude must never treat these files as unquestionable.
- Write only what Claude doesn't already know: decisions, conventions, gotchas. Skip textbook explanations.
- Keep SKILL.md under ~500 lines. Move details into `references/` and link them from SKILL.md.
- Verify every command, API name and URL before writing it: in the official docs, in the package source, or by running it. Name the version a fact depends on when it is new or version-specific.
- C# rules and library code follow the resource-lifetime rules in `plugins/unity-dev/skills/code-standards/references/resource-lifetimes.md`.

## Keeping it shareable

- Write everything in English.
- No personal preferences (reply language, tone, names). Those belong in each user's own `~/.claude/CLAUDE.md`.
- No absolute paths, usernames or secrets.
- Scripts are bash 3.2 compatible (macOS default), use only POSIX tools, always exit 0, and print nothing when there is nothing to report.
- Don't duplicate what the official `unity` plugin already covers: link to its skills.

## Testing

- `claude plugin validate .` and `claude plugin validate plugins/<plugin>` before pushing.
- `claude --plugin-dir plugins/<plugin> plugin details <plugin>` shows the per-skill token cost. Its always-on figure counts descriptions that `disable-model-invocation` keeps out of context.
- End-to-end: run `claude -p --plugin-dir <repo>/plugins --add-dir <repo>/plugins "<prompt>"` from a test project outside this repo (this file would leak into one inside it). Check both directions: a plain prompt loads nothing from these plugins, and a command loads what it should. With the switch in the test project's `.claude/settings.json`, a plain prompt gets the standards. `--add-dir` stands in for the read rule, which matches only the installed cache.
- The session-start hook alone: pipe `{"source":"startup"}` into `plugins/unity-dev/hooks/standards.sh` with `UNITY_DEV_STANDARDS=on` and `CLAUDE_PLUGIN_ROOT` set. The output must be valid JSON whose `additionalContext` holds the standards, with every variable resolved and no `$ARGUMENTS`.
- Blender scripts: run them headless (`Blender -b --factory-startup --python <test>`) against meshes with known defects.
- Library modules: see the authoring rules.

## Releasing

A plugin's `version` pins users to it, so every release bumps it in `plugin.json` (never also in `marketplace.json`). Tag the release from the plugin folder with `claude plugin tag --push`, which creates `<plugin>--v<version>`; dependency version ranges resolve against these tags.
