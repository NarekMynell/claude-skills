# Skills marketplace

This repo is a Claude Code plugin marketplace with one plugin, `unity-dev`: a pack of skills for Unity game development, including Blender 3D assets and project documentation. People install it from GitHub, so everything here has to work on any machine, for anyone.

## Layout

- `.claude-plugin/marketplace.json` lists the plugins. A new plugin needs an entry here.
- `plugins/<plugin>/.claude-plugin/plugin.json` is the plugin's manifest. Bump its `version` (semver) with every change users should receive.
- `plugins/<plugin>/skills/<skill>/SKILL.md` is one skill. Its supporting files (`references/`, `scripts/`, `templates/`) sit next to it. When a skill runs, Claude receives its base directory, so link supporting files with paths relative to the skill folder.
- `plugins/unity-dev/skills/standards/` is the one command users need: it loads the standards and routes Claude to every other skill, which it reads as a guide. A new skill gets a row in its table.
- `plugins/unity-dev/skills/library/` holds the Unity code library: `CATALOG.md`, and `code/`, which mirrors a project's `Assets/_Project/Scripts/` with the placeholder root namespace `ProjectName`. Projects copy from it under their own root namespace. Authoring rules: `plugins/unity-dev/skills/library/references/authoring.md`.

Put every new skill in `unity-dev`, so one command reaches it. A skill in another plugin couldn't be read from `standards`: each plugin is copied to its own folder.

## Nothing loads unless the user asks

The user decides when a plugin acts: no skill Claude can load by itself, and hooks that do nothing until the user turns them on for a project.

- Every skill sets `disable-model-invocation: true`, so it loads only when the user types its command. Claude never sees the descriptions: `description` is for people browsing the `/` menu, one sentence on what the skill does.
- Every skill pre-approves reading its own plugin's files with `allowed-tools: Read(~/.claude/plugins/cache/*/<plugin>/**)`. Plugin files sit outside the project, so without the rule each read asks for permission.
- Skills link each other with relative paths (`../library/SKILL.md`), never by skill name: Claude can't invoke them, so it reads the linked file. A plugin can't link another plugin's files, because each plugin is copied on its own; point the user to that plugin's command instead.
- `${CLAUDE_PLUGIN_ROOT}` and the other variables are substituted only in the skill the user invoked, not in files Claude reads from it. Use them only in `standards` and `toolchain`, and relative paths everywhere else.
- Every-session loading is a per-project switch: `UNITY_DEV_STANDARDS` set to `on` under `env` in the project's `.claude/settings.json` (or `.claude/settings.local.json`), next to the plugin's read rule, because outside a command nothing pre-approves those reads. `/unity-dev:standards` writes both on its first run in a project; `new-project` and `adopt-standards` write them through the team settings template. With the switch on:
  - the SessionStart hook (`hooks/standards.sh`) adds `skills/standards/SKILL.md` up to its `## When the user types the command` heading to the context on startup, `/clear` and compaction. That part must work without the command, use no variable but `${CLAUDE_SKILL_DIR}`, which the hook resolves, and stay under about 9,500 characters: the cap on hook output is 10,000, and the toolchain report can follow it;
  - the SubagentStart hook, the same script, gives it to subagents, except those that only read;
  - the Stop hook (`hooks/gates.sh`) compares what changed with the receipts in the project's `docs/proofs/`, and asks once to deal with those the change can have made wrong: C# for the architecture check, a model for that model's receipts, a whole-game check for its own area by the file's path, or after 30 changed files. A failure told once in a session isn't repeated until it changes. With the receipts in order, it costs nothing. A check family a project has no use for goes in `docs/proofs/not-applicable.txt`, and so does a failing receipt the user accepted, with their words;
  - the PreToolUse hook on Write and Edit (`hooks/receipts.sh`) refuses hand edits of receipts.

  The hooks find the switch from the session's current folder when the variable isn't set (`hooks/common.sh`): a session that started above a new project has no variable, and is exactly the session that builds the game.
- Templates copied into projects hold project knowledge only: what the project is, its decisions, its docs index. A project's `CLAUDE.md` loads in every session, so it never tells Claude to load or follow these skills; the switch does that.

## Musts and guides

Every guide separates what is binding from what is advice, and the user asked for both: quality that can't be traded, and solutions Claude chooses per project.

- **A must** is a bar for the result, with a proof that can fail: a script, a test, a measurement, a review. A plain instruction with a clear trigger, such as JSON through Newtonsoft, is proven by review: it needs no script. It opens the guide under `## Must`, and the standards table lists it, because the table stays in context after compaction. Only the user changes a must.
- **Everything else is a guide:** methods known to work, failures seen, strong defaults. It says what worked and why, not "always".
- **Text alone doesn't hold.** A real game ran for hours under these standards, with them in context, and ended with 136 classes on 6 interfaces, none of the Blender checks run, and its own "Decisions" replacing them. So a rule that matters gets a check that fails on its own: in the library (`ProjectArchitectureTests`, `UiAudit`, `SceneCostAudit`, `ColliderAudit`, `PacingAnalyzer`, `FootSlideMeter`) or in `game-assets/scripts`. Each has a case with the defect and a clean case, and writes a receipt in the project's `docs/proofs/`, so what ran doesn't rest on anyone's word.
- **A check has to earn its cost.** It costs a run, code to keep, and a turn each time it speaks. It earns that when text has already failed on the rule, when the defect shows late and costs much to fix, or when Claude can't see the defect without a measurement, as with everything in a mesh, a UV map or a rig. Otherwise a sentence does the job. And a script says only what a script can tell: what takes judgement, such as whether an architecture is good, belongs to a review, and a number that points there is a signal, not a failure, or it gets gamed.
- **A check is attacked before it is trusted, from both sides.** Run an adversarial review that tries to pass a real defect through it, and to fail a good result built another way. Each check here passed its own tests and still let real defects through on the first such review. `inspect_character.py` failed 71 of 73 characters of a real game, because every clean case in its tests was built the same way: a check that fails everything hides real defects as surely as one that passes everything. So a check gets a clean case per way of building the thing, and each test scene is confirmed by a render: one "head through a hat" here turned out to graze it by 2 mm where nobody could see.
- **Clean cases come from work the check didn't help build.** After all that, the same check still failed every professional character inside Unity's own packages, and `validate_mesh.py` half of its models: test poses tore apart any imported rig, and a palette texture counted as a defect. `dev/run-real-assets.sh` holds the checks to those models and clips, and `dev/run-real-colliders.sh` holds `ColliderAudit` to the prefabs and scenes of Unity's samples. When one fails a professional model, it is wrong until a render says otherwise. A rule that sounds right gets the same test: "a mirrored collider isn't where the model is" failed 25 colliders there, and a physics query showed Unity's colliders follow the mirror.
- **The hook speaks only about what a change can have broken.** It costs a turn, and one that lists eight checks on each line of C# is one that nobody hears.
- **A report is for the user.** A check says what the player would see and where, not only an issue's name: the user decides on it, and can't decide on a name.
- **Failures stay in the guides,** as "what has failed": they are the most useful part, and they stop Claude from trying the obvious first idea again.

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
- Blender scripts: `dev/run-blender-tests.sh` runs them headless against scenes with known results (`dev/blender/`; the test mannequin, animal and walk cycles are built by `mannequin.py`, `quadruped.py` and `gait.py`, and bodies of overlapping parts by `partsbody.py`). A new check or script gets a case there, both a defect it must catch and a clean case it must pass, on each way of building: one skin, separate parts, one merged mesh, an animal. `dev/run-attack-tests.sh` runs the 321 scenes an adversarial review built against `inspect_character.py`, from both sides; a verdict that differs from what its scene asks for needs a line with its reason in `dev/blender/attacks/accepted.txt`, and the "open" lines there are work left. `dev/run-real-assets.sh` runs the checks over the professional models and clips inside a Unity install, against `dev/blender/real_assets_expected.txt`; none of them is copied here.
- Colliders: `dev/run-real-colliders.sh` runs `ColliderAudit` over the prefabs and scenes in Unity's package samples, against `dev/library-tests/real_colliders_expected.txt`, copying what it needs into the test project only for the run.
- Hooks: `dev/run-hook-tests.sh` runs them against known inputs in a temporary repository.
- A change to what a guide tells Claude to do is tested on Claude: run the end-to-end command above with a real task, and read what it did, not what it says it did.
- Humanoid import claims (sides, facing, root-motion speed) are tested in `LibraryTests/AnimationClaims/` on `dev/library-tests/Fixtures/Mannequin.fbx`. Regenerate the fixture with `dev/blender/make_fixtures.py` when the export settings or the mannequin change.
- Library modules: see the authoring rules, including the player runs (`dev/run-library-tests.sh player`).
- A C# snippet added to or changed in a guide or README is mirrored in `dev/library-tests/Assets/LibraryTests/SnippetCheck/SnippetCheck.cs`; a claim about how VContainer, MessagePipe, UniTask or Unity behaves gets a test in `LibraryTests/GuideClaims/`.

## Releasing

A plugin's `version` pins users to it, so every release bumps it in `plugin.json` (never also in `marketplace.json`). Tag the release from the plugin folder with `claude plugin tag --push`, which creates `<plugin>--v<version>`; dependency version ranges resolve against these tags.
