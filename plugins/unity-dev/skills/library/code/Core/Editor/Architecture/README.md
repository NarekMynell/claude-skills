# Architecture audit

Checks the project's compiled code against the [architecture rules](../../../../../code-standards/SKILL.md#architecture) from an Edit Mode test, so a violation fails the test run instead of depending on someone noticing it.

- **Destination:** `Core/Editor/Architecture/`
- **Depends on:** Proofs.

```csharp
[Test]
public void CodeFollowsTheArchitectureRules()
{
    var options = new ArchitectureAuditOptions("StarHarbor")
        .Allow("mutable-static", "StarHarbor.Core.DI.GlobalResolver", "The one documented last-resort access point.");
    ArchitectureReport report = ArchitectureAudit.Run(options);
    ProofReceipt.Write("architecture", report.IsClean, report.ToString());
    Assert.That(report.IsClean, report.ToString());
}
```

`Core/Tests/Architecture/ProjectArchitectureTests.cs` is this test, ready to copy. It audits every assembly named `<Root>` or `<Root>.*`, except `.Editor` and `.Tests` ones, from all loaded assemblies.

| Rule | Finds |
|---|---|
| `concrete-dependency` | A constructor, `[Inject]` member, method parameter or return value, property or field typed as a class that does work, instead of an interface. Data types, ScriptableObjects and Unity types are fine. A class may own a small helper it creates itself (up to 8 methods, no dependencies, holding no other class that does work, no Unity lifetime) and Core's building blocks, such as a pool |
| `hidden-dependency` | `new` on a class that needs other classes, in source files outside factories and installers |
| `no-interfaces`, `few-interfaces` | An assembly with 3 or more classes that do work and no interface at all, or outside Core fewer than one interface per five such classes |
| `capability-not-in-map`, `map-without-type`, `no-capability-map` | The capability map in `docs/architecture.md`, compared with the code: a domain's interface it doesn't list, a listed interface that doesn't exist, no map |
| `no-contract` | A class with public behavior and no interface, when it is public, a MonoBehaviour or has dependencies of its own (not checked in Core) |
| `public-implementation` | A public class implementing a public interface: implementations are internal (not checked in Core or on Unity objects) |
| `concrete-base`, `deep-inheritance`, `base-class` | A project class inheriting a concrete project class, two or more levels of project base classes, or any base class of a domain's own, which needs its reason as an exception: a true is-a with shared behavior |
| `too-many-dependencies`, `large-class`, `long-file`, `fat-interface` | Size limits that point to more than one responsibility, in `ArchitectureAuditOptions` |
| `mutable-static` | A static field or auto-property that can change, a static collection, a static instance of a class that does work (a singleton), a static event, a shared static array |
| `stateful-asset` | A ScriptableObject with fields that aren't serialized, or that receives injection |
| `frame-method` | A MonoBehaviour with `Update`, `LateUpdate` or `FixedUpdate` |
| `dependency-direction`, `no-assembly` | Core referencing a domain, anything referencing App, any code in `Assembly-CSharp` |
| `json-not-newtonsoft` | `JsonUtility` or `System.Text.Json` in source files under `SourceFolder`, `Editor` and `Tests` folders included. `EditorJsonUtility` is fine |
| `loosened-limit`, `too-many-exceptions` | A limit set looser than its default, a check turned off, more than `MaxExceptions`. These need a reason like any other exception |
| `nothing-audited` | No assembly named after the root namespace, or no source folder: a test that checks nothing can't pass |
| `scene-search`, `string-messaging`, `coroutine`, `async-void`, `resources-load`, `creation-outside-factory` | Forbidden calls in source files under `SourceFolder`, outside `Editor` and `Tests` folders. Files named `*Factory`, `*Pool`, `*Installer`, `*LifetimeScope` and `*Registration` or `*RegistrationExtensions` may create objects |

- **Installers and scopes** (classes deriving from `ScopeInstaller` or `LifetimeScope`) are the composition root and may name concrete types.
- **An exception states its reason:** `Allow(rule, subject, reason)`, where the subject is the type, assembly or file the finding names. The report lists accepted exceptions, `IsClean` is false when an exception no longer matches anything, and more than `MaxExceptions` (10) is a finding of its own. Show the list to the user.
- **What it can't see:** whether interfaces are well chosen. A class implementing a meaningless interface passes. That part stays with review. Neither does it see source files outside `SourceFolder`, or JSON parsed by hand.
