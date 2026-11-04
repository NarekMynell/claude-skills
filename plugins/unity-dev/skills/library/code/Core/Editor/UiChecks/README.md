# UI checks

`UiAudit` finds what makes a UGUI screen look unmade, on the laid-out screen. It catches craft mistakes by the numbers; beauty stays with the [UI review](../../../../../ui-quality/SKILL.md).

- **Destination:** `Core/Editor/UiChecks/`
- **Depends on:** Proofs, UI. `Core.Editor` then references `UnityEngine.UI` and `Unity.TextMeshPro`.

Create one `UiAuditSettings` asset (**Assets > Create > Tools > UI Audit Settings**) with the project's radius scale, type scale and fonts from `docs/ui-design.md`, and the HUD's share of the screen. Every screen is then held to the same tokens. Without it the audit reports `no-ui-tokens`.

Run it on the real screen, at each target aspect ratio, with each screen open in turn: **Tools > Audit UI** audits every canvas in the loaded scenes, and for `unity command eval`:

```csharp
UiAudit.AuditAllCanvases(receiptName: "hud-20x9", noPanelOpen: true);
```

returns the same text, and writes `docs/proofs/ui-hud-20x9.txt`. `noPanelOpen` says this is the HUD alone, so its coverage limit applies. UI built at runtime needs Play Mode. A test or a tool can audit one root with options of its own:

```csharp
var options = new UiAuditOptions { MaxCoverage = 0.2f }
    .Allow("near-miss-alignment", "Hud/CoinBadge", "It overlaps its panel by design, for the sticker look.");
UiAuditReport report = UiAudit.Run(hudRoot, options);
Debug.Log(report);
```

| Rule | Finds |
|---|---|
| `capsule` | A long element whose corners are half circles, measured from the sprite's alpha. Parts of a `Toggle` or a `Slider` are allowed up to `MaxControlCapsule`: small, of one fixed height |
| `stretched-sprite` | A simple or filled image drawn at another aspect ratio than its sprite |
| `squashed-corners` | A sliced image too small for its sprite's corners, which Unity then squeezes |
| `off-scale-corner`, `off-scale-font`, `no-ui-tokens` | A corner, text size or font that isn't in the project's tokens, or no tokens to check against |
| `corner-spread` | More corner sizes on the screen than `MaxCornerSizes`. The report lists them: the screen's real radius scale |
| `unmeasured-shape` | A custom graphic or material that draws a shape this audit can't see, such as an SDF, without `IUiShape` on it. With it, its corners count like any other |
| `uneven-scale` | A transform with different X and Y scale |
| `font-spread`, `font-size-spread`, `default-font`, `legacy-text`, `text-too-small` | The type system |
| `text-overflow`, `off-screen`, `overlap`, `near-miss-alignment` | Layout |
| `small-touch-target`, `no-press-state`, `needless-raycast` | Interaction. A button animated by code passes `no-press-state` through a component on it that handles `IPointerDownHandler` |
| `plain-rectangle`, `default-sprite`, `placeholder-text`, `emoji`, `scientific-number` | Placeholder and template tells |
| `covers-too-much` | More of the screen than `MaxCoverage`. Set it when auditing a HUD |
| `no-screen-scaling` | A screen-space canvas without Scale With Screen Size |

- Only active, enabled, visible elements count, so open each panel before auditing it.
- **Exceptions state their reason:** in the `UiAuditSettings` asset, or `Allow(rule, path, reason)` in code. The report lists them, and more than `MaxExceptions` (10) is a finding.
- A run with no canvas loaded writes a failing receipt, and each receipt records the screen's size, so the aspect ratios covered can be read from them.
- Elements under a `Mask` or `RectMask2D`, such as scrolling lists, are left out of `off-screen` and `overlap`.
- **UI Toolkit:** radii, text sizes and fonts come from USS variables in one file. `UssTokenAudit.Run("Assets/_Project/UI", "tokens.uss", receiptName: "main")` finds literal values anywhere else, and writes the receipt. It looks only at the files, so screenshots carry more of the review there.
