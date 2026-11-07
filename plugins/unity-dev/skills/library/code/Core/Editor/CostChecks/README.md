# Cost checks

What a scene pays for that the player may not get anything from, and what its colliders do wrong. Real costs come from the Profiler on the device, as the [performance guide](../../../../../performance/SKILL.md) describes.

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

## Colliders

`ColliderAudit` reads the colliders and the meshes in scenes and prefabs, and needs no physics step. **Tools > Audit Colliders** audits the loaded scenes, and for `unity command eval`:

```csharp
ColliderAudit.AuditLoadedScenes(receiptName: "main", solidRoots: new[] { "Level/Walls" });
ColliderAudit.AuditPrefabs("Assets/_Project/Prefabs", receiptName: "prefabs");
```

| Rule | What the player meets |
|---|---|
| `collider-beyond-model` | The collider reaches past the model, by more than a quarter of its size: he stops at nothing. Below the model doesn't count: a floor's collider may be thick |
| `collider-off-model` | The collider and the model don't touch, measured along the model, so a turned wall hides nothing. Or a box touches nothing while a part of the model has none: he walks through that part and hits air here |
| `collider-closes-opening` | A box over a model with an arch or a gate in it: a person fits through the model, and he stops at air. A table as one block is fine: nobody walks under it |
| `no-collision-mesh` | A Mesh Collider with no mesh: he walks through it |
| `moving-concave` | A concave Mesh Collider on a moving Rigidbody: Unity doesn't simulate it |
| `convex-too-big` | A convex Mesh Collider over 255 triangles: its hull isn't the shape |
| `heavy-mesh-collider` | A concave Mesh Collider over 5,000 triangles: a simple collision mesh costs less, and snags less |
| `static-rigidbody` | Marked static and moved by physics: drawn where it was baked |
| `feet-off-ground` | What a character stands on isn't at the feet of its body, whether a CharacterController, a NavMeshAgent or the colliders of a Rigidbody with a rig or kept upright: it floats, or sinks. The skin is the body, not a sword or a blob shadow; arms on a first-person camera say nothing |
| `capsule-size` | An upright capsule far from the body's height: the head goes through ceilings, or it can't pass doors it fits |
| `solid-without-collider` | Under `solidRoots`, what is drawn and nothing stops the player at: a collider has to be on it, wherever it hangs. One for the floor or the whole level doesn't count. Only the project knows what is solid: decoration may be walked through |

Colliders on one Rigidbody or prefab count together, as one shape, and a ragdoll's or hitbox's bones with the character. A collider with nothing drawn under its owner, such as an invisible ramp or a boundary, is left alone, and so is one beside a model with a collider of its own. A terrain and a wheel have no shape to compare. A mirrored object is no defect: Unity's primitive colliders follow the mirror (`LibraryTests/GuideClaims/ColliderClaimsTests`). The Editor reads every mesh, Read/Write or not; run in Play Mode, the rules that need the mesh skip those without it. It reads what the components say, not what happens in play: whether an actor gets stuck is for a test of the real movement. For why a collision event doesn't fire: the official `unity:physics-3d-collision` skill.
