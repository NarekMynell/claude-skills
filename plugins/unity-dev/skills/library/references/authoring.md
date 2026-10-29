# Authoring the code library

## Structure

- `code/` mirrors `Assets/_Project/Scripts/` of a project whose prefix is `Company.Product`:
  - `code/Core/<Module>/`: generic building blocks, all in the `Company.Product.Core` assembly, with `Company.Product.Core.Editor` and `Company.Product.Core.Tests` beside it;
  - `code/<Domain>/`: ready domains, each with its own assembly (`Company.Product.Audio`).
- Every module folder has a `README.md`: what it is for, when to use it, the API with a short example, dependencies (modules, packages, scripting defines), and setup steps (scene objects, configs, installer registration).
- `CATALOG.md` lists every module with one line on its purpose, its destination and its dependencies. Update it in the same change as the module.
- No `.meta` files: the code is copied into projects, and Unity creates them there.

## Rules

- The library is the reference codebase: it follows the [code standards](../../code-standards/SKILL.md) exactly, because projects copy its style along with its code.
- **One purpose per module.** No grab bags such as `Utils` or `Common`.
- **Dependencies** between modules are few, explicit in the README, and acyclic. Third-party dependencies are kept to a minimum.
- **Builds on what exists.** Never re-implement Unity, its packages or the standard stack; add only what they lack. The Pooling module builds on `UnityEngine.Pool`.
- **Namespaces** never equal the name of a type inside them or of a common Unity type, because the namespace would hide the type: `StateMachines`, not `StateMachine`; `ContentLoading`, not `Addressables`. The conventional `.Editor` and `.Tests` segments are the exception; Editor code then writes `UnityEditor.Editor` in full.
- **Complete.** No placeholder logic, no TODOs. A module ships complete or not at all.

## Quality bar

- Written from scratch to the standards. No code is copied from existing projects.
- All logic is covered by tests. Hot paths also have allocation tests (`Is.Not.AllocatingGCMemory()`). Every disposable type has disposal tests: disposed twice, used after disposal, disposed with work in flight.
- Resource lifetimes follow the [rules](../../code-standards/references/resource-lifetimes.md): every subscription, handle, buffer and created object has one owner that releases it on every path.
- Every API the code calls is checked against the package source or documentation of the versions in `dev/library-tests`, not recalled from memory.
- Before a release, the whole library compiles with no errors or warnings and its Edit Mode and Play Mode tests pass in the library's Unity test project, on the newest stable Unity version: `dev/run-library-tests.sh` at the repository root copies the library into `dev/library-tests` and runs both. The Play Mode tests also pass in a player: `dev/run-library-tests.sh player` for the desktop player, and `dev/run-library-tests.sh player WebGL` (IL2CPP, no threads) when a change touches threading, files or platform code.
- Every C# snippet in the guides and the module READMEs compiles: `dev/library-tests/Assets/LibraryTests/SnippetCheck/` holds each one verbatim, and changes with it. What the guides claim about package and engine behavior is checked by `LibraryTests/GuideClaims/`.
- A release bumps the unity-dev `version`. Projects record that version when they copy code.
