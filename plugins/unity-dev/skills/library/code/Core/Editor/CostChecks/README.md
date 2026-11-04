# Cost checks

What a scene pays for that the player may not get anything from. Real costs come from the Profiler on the device, as the [performance guide](../../../../../performance/SKILL.md) describes.

- **Destination:** `Core/Editor/CostChecks/`
- **Depends on:** Proofs, Culling.

`SceneCostAudit` lists realtime lights and shadows, objects that never move but aren't static, animation, skinning and particles that run off screen, readable meshes and uncompressed textures. **Tools > Audit Scene Cost** audits the loaded scenes, and for `unity command eval`:

```csharp
var options = new CostAuditOptions()
    .Allow("runtime-light", "Main/Sun", "The day cycle moves it: the look needs one realtime light.");
SceneCostAudit.AuditLoadedScenes(receiptName: "main", options: options);
```

Each finding is fixed, or accepted with its reason in `Allow(rule, subject, reason)`, where the subject is the end of the finding's path. The report lists them, and more than `MaxExceptions` (10) is a finding. Renderers placed at runtime count only when the audit runs in Play Mode.

**`could-be-static`** can only look: an object with a script of its own stays out of it, and a script on a parent doesn't count, since one script on a level's root would hide every prop under it. `NeverMovedProbe` settles the doubtful ones by watching a real session:

```csharp
var probe = new NeverMovedProbe(scene.GetRootGameObjects());
// ... play the session ...
foreach (CostFinding finding in probe.Report()) Debug.Log(finding);
```
