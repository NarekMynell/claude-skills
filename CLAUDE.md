# Skills marketplace

`narek-skills` is a Claude Code plugin marketplace organized by **domain**: each domain is one plugin, and each project turns on the domains and skills it needs. People install it from GitHub, so everything here has to work on any machine, for anyone.

## Architecture

<!-- catalog:architecture -->
| Domain | Builds on | Skills |
|---|---|---|
| [core](plugins/core/README.md) | - | project-docs, skills, standards, version-notes |
| [game-design](plugins/game-design/README.md) | core | art-direction, game-design, standards |
| [modeling](plugins/modeling/README.md) | core | animation, characters, models, standards |
| [unity-dev](plugins/unity-dev/README.md) | core, game-design, modeling | adopt-standards, animation, audio-design, code-standards, library, models, new-domain, new-project, npc-behavior, performance, standards, toolchain, ui-quality, version-notes, vfx |
<!-- /catalog -->

A domain builds on others through `dependencies` in its `plugin.json`: they install with it, and come on with it in a project. Every domain builds on core, the base: its standards define musts, guides, receipts and verification for all the others, so it loads wherever any domain does.

```
.claude-plugin/marketplace.json   the domains, in order; one entry per plugin
plugins/<domain>/
  .claude-plugin/plugin.json      version, description, dependencies
  README.md                       what the domain is; its skills table between catalog markers
  hooks/hooks.json                the domain's hooks; lib.sh, context.sh and domains.txt beside it are copies
  skills/standards/SKILL.md       the hub: what the domain loads (see below)
  skills/<skill>/SKILL.md         one skill; its references/, scripts/ and templates/ beside it
  scripts/                        tools several skills of the domain share (modeling's Blender checks)
shared/hooks/                     the hook code every domain runs; dev/sync.py copies it into each plugin
dev/                              generators and tests; never shipped
```

**Generated, never edited by hand:** the tables between `<!-- catalog:... -->` markers here, in `README.md` and in each plugin's `README.md`; `plugins/core/skills/skills/catalog.md`, which `/core:skills` reads; `shared/hooks/domains.txt`; the plugins' copies of `shared/hooks/`. `python3 dev/sync.py` rewrites them from the manifests and each skill's frontmatter. Run it after any change to a domain, a skill's name or description, or `shared/hooks/`.

### How a domain reaches Claude

- **Only when the user asks.** Every skill sets `disable-model-invocation: true`, so Claude can't load one by itself; `description` is one sentence for people browsing the `/` menu. A command (`/<domain>:<skill>`) loads one skill; `/<domain>:standards` loads the domain.
- **The hub.** `skills/standards/SKILL.md` up to its `## When the user types the command` heading is what the domain loads: one line of scope, a **Musts** table, `## Verify before relying on them` (the domain's sources), a **Guides** table with one row per kind of work, and what the domain adds to the done checklist. A row's first `../<skill>/` link names the skill it belongs to: that is how a switch removes it. Another skill linked after it in the row is one it needs, such as `[characters](../characters/SKILL.md), after [models](../models/SKILL.md)`. The hub stays under 9,500 characters: the hook cap is 10,000, and unity-dev's toolchain report can follow it.
- **Switches,** under `env` in a project's `.claude/settings.json`, or `.claude/settings.local.json`, which wins key by key: `<DOMAIN>_STANDARDS` turns a domain on or off, `<DOMAIN>_SKILL_<SKILL>` one skill (`UNITY_DEV_SKILL_VFX`). A domain with no switch is on wherever a domain that builds on it is on, so `UNITY_DEV_STANDARDS` brings game-design and modeling; a single skill switched on brings no other domain. Core is the base: it is on wherever any domain is active (has a skill on), and can't be switched off while one is. A domain that is on also needs its read rule there, `Read(~/.claude/plugins/cache/*/<domain>/**)`, because nothing else pre-approves reading plugin files outside a command. `/core:skills` writes them; each `/<domain>:standards` writes its own on its first run in a project.
- **The hook,** `shared/hooks/context.sh`, run by each domain for itself. SessionStart (startup, `/clear`) and SubagentStart give an active domain's hub, with the rows of skills that are off removed and its variables resolved; read-only subagents get nothing. UserPromptSubmit gives a domain's hub in the same turn when the user types `/<domain>:standards <task>` of a domain that builds on it, and once when the domain came on during the session. Each hook notes the sessions that have its hub (in its plugin's data folder): compaction gives them the hub again, whether it came from the switches or from a command, and a resumed or forked session, whose transcript has it, gets nothing twice. The hooks find the switches from the session's current folder when the variables aren't set (a session that started above a new project has none).
- **Proofs.** Checks write receipts to the project's `docs/proofs/`. Core's PreToolUse hook refuses hand edits of receipts wherever a domain is on. In a Unity project, unity-dev's Stop hook (`gates.sh`) compares what changed with the receipts, only for families whose skill is on, and asks once about those the change can have made wrong; a family a project has no use for goes in `docs/proofs/not-applicable.txt`, and so does a failing receipt the user accepted, with their words.
- **Across domains.** A plugin can't read another plugin's files: each is copied on its own. Inside a domain, link with relative paths. Name another domain's guide as `` `domain:skill` `` (`` `modeling:characters` ``): its path is in that domain's hub in context. `${CLAUDE_PLUGIN_ROOT}` and the other variables are substituted only in the SKILL.md the user invoked, and by the hook in a hub; everywhere else use relative paths.
- **Templates** copied into projects hold project knowledge only. A project's `CLAUDE.md` never tells Claude to load these skills: the switches do.

### Adding

- **A skill:** `plugins/<domain>/skills/<name>/SKILL.md`, the folder named as `name`; a row in the hub's Guides table, and in its Musts table if the skill has a must; then `python3 dev/sync.py`.
- **A check that writes receipts:** a new family also goes into `family_on` and the sweep list in `plugins/unity-dev/hooks/gates.sh`, with the skill whose must it proves, or the gate never asks for it; and into `dev/run-hook-tests.sh`.
- **A domain:** `plugins/<domain>/` with `plugin.json` (`dependencies`: core and every domain it builds on), `README.md` with `<!-- catalog:skills -->` and `<!-- /catalog -->`, a hub, and `hooks/hooks.json` running `context.sh <domain>` on SessionStart (`startup|resume|clear|compact|fork`), SubagentStart and UserPromptSubmit; an entry in `marketplace.json`; then `python3 dev/sync.py`. Engine knowledge stays in its engine's domain: modeling and game-design name the engine's guide (`unity-dev:models`), never hold its settings.
- **A dependency from another marketplace,** such as unity-dev's `unity` and `csharp-lsp`: that marketplace goes into `allowCrossMarketplaceDependenciesOn` in `marketplace.json`, the install steps of `README.md` and the domain's README, and the team settings (`/core:skills`, the new-project template). Where it isn't added, the domain fails to load.

## Musts and guides

Every guide separates what is binding from what is advice; the user asked for both: quality that can't be traded, and solutions Claude chooses per project.

- **A must** is a bar for the result, with a proof that can fail: a script, a test, a measurement, a review. A plain instruction with a clear trigger, such as JSON through Newtonsoft, is proven by review. It opens the guide under `## Must`, and the domain's hub lists it, because the hub stays in context after compaction. Only the user changes a must.
- **Everything else is a guide:** methods known to work, failures seen, strong defaults. It says what worked and why, not "always".
- **Text alone doesn't hold.** A real game ran for hours under these standards, with them in context, and ended with 136 classes on 6 interfaces, none of the Blender checks run, and its own "Decisions" replacing them. A rule that matters gets a check that fails on its own, with a case for the defect and a clean case, writing a receipt in `docs/proofs/`.
- **A check has to earn its cost:** a run, code to keep, and a turn each time it speaks. It earns that when text has already failed on the rule, when the defect shows late and costs much to fix, or when Claude can't see the defect without a measurement, as in a mesh, a UV map or a rig. A script says only what a script can tell: what takes judgement, such as whether an architecture is good, belongs to a review, and a number that points there is a signal, not a failure.
- **A check is attacked before it is trusted, from both sides:** a review that tries to pass a real defect through it, and to fail a good result built another way. `inspect_character.py` once failed 71 of 73 characters of a real game, because every clean case in its tests was built the same way: a check that fails everything hides real defects as surely as one that passes everything. So a check gets a clean case per way of building the thing, and each test scene is confirmed by a render.
- **Clean cases come from work the check didn't help build:** `dev/run-real-assets.sh` holds the Blender checks to the professional models and clips inside a Unity install, and `dev/run-real-colliders.sh` holds `ColliderAudit` to Unity's samples. When a check fails professional work, it is wrong until a render says otherwise. A rule that sounds right gets the same test: "a mirrored collider isn't where the model is" failed 25 colliders there, and a physics query showed Unity's colliders follow the mirror.
- **The hook speaks only about what a change can have broken,** and **a report is for the user:** it says what the player would see and where, not only an issue's name.
- **Failures stay in the guides,** as "what has failed": they stop Claude from trying the obvious first idea again.

## Writing a skill

- Every skill and reference opens, right after its title, with the line saying it can be wrong or out of date and must be verified, linked to its domain's `standards#verify-before-relying-on-them` (copy it from an existing skill). The user asked for this on every guide.
- Every skill sets `disable-model-invocation: true` and pre-approves reading its own plugin, `allowed-tools: Read(~/.claude/plugins/cache/*/<domain>/**)`; a hub also pre-approves the domains it builds on.
- Write only what Claude doesn't already know: decisions, conventions, gotchas, failures. No textbook explanations, no filler: every sentence carries information.
- SKILL.md under ~500 lines; details in `references/`, one level deep, linked from it.
- Verify every command, API name and URL before writing it: in the official docs, the package source, or by running it. Name the version a fact depends on when it is new or version-specific.
- C# rules and library code follow `plugins/unity-dev/skills/code-standards/references/resource-lifetimes.md`. The Unity code library's authoring rules: `plugins/unity-dev/skills/library/references/authoring.md`.
- Don't duplicate what the official `unity` plugin covers: link to its skills.

## Keeping it shareable

- Everything in English. No personal preferences (reply language, tone, names), absolute paths, usernames or secrets.
- Scripts are bash 3.2 compatible (macOS default), use only POSIX tools, always exit 0, and print nothing when there is nothing to report. The hooks run on every prompt: no subshell or process they can do without.

## Testing

- `python3 dev/sync.py --check` and `python3 dev/check-links.py`: the generated files are current, and every relative link, heading and `domain:skill` name resolves.
- `claude plugin validate --strict .` and the same for each `plugins/<domain>`. `claude --plugin-dir plugins/<domain> plugin details <domain>` shows each skill's token cost; its always-on figure counts descriptions that `disable-model-invocation` keeps out of context.
- Hooks: `dev/run-hook-tests.sh` runs every hook against known inputs: the switches and what each domain brings, the commands that pull domains in, the gates and the receipts.
- End-to-end: from a test project outside this repository (this file would leak into one inside it), `claude -p --plugin-dir <repo>/plugins --add-dir <repo>/plugins "<prompt>"`. Check both directions: a plain prompt loads nothing, and a command or a switch loads what it should. `--add-dir` stands in for the read rules, which match only the installed cache. A change to what a guide tells Claude to do is tested on Claude this way: read what it did, not what it says it did.
- Blender scripts: `dev/run-blender-tests.sh` runs them headless against scenes with known results (`dev/blender/`), a defect and a clean case on each way of building: one skin, separate parts, one merged mesh, an animal. `dev/run-attack-tests.sh` runs the 321 scenes of an adversarial review of `inspect_character.py`; a verdict that differs from its scene needs a line with its reason in `dev/blender/attacks/accepted.txt`, and its "open" lines are work left. `dev/run-real-assets.sh` holds the checks to professional models against `dev/blender/real_assets_expected.txt`.
- Unity: `dev/run-library-tests.sh` (and `player`, `player WebGL`) for the library; `dev/run-real-colliders.sh` for `ColliderAudit`. A C# snippet added to or changed in a guide is mirrored in `dev/library-tests/Assets/LibraryTests/SnippetCheck/`; a claim about how VContainer, MessagePipe, UniTask or Unity behaves gets a test in `LibraryTests/GuideClaims/`; Humanoid import claims are tested in `LibraryTests/AnimationClaims/` on `dev/library-tests/Fixtures/Mannequin.fbx`, regenerated by `dev/blender/make_fixtures.py`.

## Releasing

A plugin's `version` pins its users, so every change users should receive bumps it in that plugin's `plugin.json` (never in `marketplace.json`). A change to `shared/hooks/`, or to the domains and skills (which changes `domains.txt`), reaches every plugin's copy: bump every plugin, or the installed copies disagree. Tag each changed plugin from its folder with `claude plugin tag --push`, which creates `<plugin>--v<version>`; dependencies resolve against these tags.
