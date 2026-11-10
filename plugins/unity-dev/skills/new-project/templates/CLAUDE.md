# <Product name>

<What the game or app is, in one or two sentences.> Unity <version>, URP, targets <platforms>.

- Root namespace: `<Root>`. Every assembly is `<Root>.<Domain>`.
- Standards: the narek-skills domains switched on in `.claude/settings.json` (`UNITY_DEV_STANDARDS`, which brings core, game-design and modeling) load at the start of every session. The decisions below beat their guides, never their musts.

## Musts the user changed

<Only what the user asked for, in their own words, with the date. Remove this section when there are none.>

## Decisions

<Conventions of this project that differ from the guides, each with its reason. A decision can't change a must. Remove this section when there are none.>

## Documentation

Project knowledge lives in `docs/`. Read this index, then open only what the task needs.

| File | Read when |
|---|---|
| `docs/architecture.md` | Adding or changing a domain, a capability, a scope, an installer or a startup step |
| `docs/unity-version-notes.md` | Using an engine API or feature that may have changed in recent Unity versions |
| `docs/proofs/` | Reporting on or reviewing the work: each check's receipt of its last run |
