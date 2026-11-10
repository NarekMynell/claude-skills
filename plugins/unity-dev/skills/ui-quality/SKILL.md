---
name: ui-quality
description: Designs and checks game UI that looks made for this game - concept from the game's world, tokens and component kit first, no template or AI look, corners and sprites done right, world markers, typography, automated UI audit, device-size reviews against references.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# UI quality

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The official `unity:ui`, `unity:ui-ugui` and `unity:ui-uitk` skills cover how each framework works. This guide covers what makes a UI good. The project records its framework choice (UGUI or UI Toolkit) in `docs/`.

## Must

- **Made for this game.** Cover the game's name in a screenshot: the UI still says which game it is. A UI that could belong to any game isn't finished, however clean it is.
- **No template or AI look:**
  - capsule (pill) containers, or one rounded rectangle used for everything;
  - flat fills with no material, light or depth;
  - cards in a grid with identical spacing, predictable centered layouts;
  - purple gradients, random glows, emoji as icons, default fonts, gray placeholder panels;
  - decoration standing in for hierarchy.
- **One system.** One radius scale, one type scale, one spacing scale, one light direction, one icon family: nothing stretched, no corners squeezed, nothing almost aligned.
- **Clear hierarchy.** One primary action per screen. Blurred, the screen still shows what matters first.
- **The game comes first.** The HUD stays small and at the edges; the project sets its share of the screen in `docs/ui-design.md`, and measures it.
- **Works everywhere.** Every aspect ratio and safe area, no overflow or overlap, touch targets of at least 44 pt on iOS and 48 dp on Android, every state, feedback on every interaction.
- **The proof:** `UiAudit` clean on every screen at each target aspect ratio, against the project's tokens in a `UiAuditSettings` asset, leaving its receipts in `docs/proofs/` (in UI Toolkit, `UssTokenAudit`), and a written critique of device-size screenshots against references, following the [UI review](references/review.md). A screen isn't done until both pass. An exception states its reason in the asset, and the user sees it.

The method below is a guide. How the UI looks is your decision, and it should surprise: the first idea is usually the template.

## What has failed

From a real project, in the owner's words: template-like, primitive, full of AI traces.

- **Dark capsules** stretched to different widths for every resource. Corners changed with each element's size, sprites stretched, a progress bar turned into a sliver.
- **The fix that also failed:** wooden boards on ropes, dashed stitching and ticket notches. A theme was there, but piled on: too much decoration everywhere, an oversized HUD over the game, icons rendered blurry, no hierarchy, a close button that had lost its shape.
- **Raw numbers:** `$1.12e60` on the main screen.

A theme is not a UI. Hierarchy, restraint and craft make it one.

## How to work

1. **Look first.** Study real screens of the genre's top games: [Game UI Database](https://www.gameuidatabase.com), [Interface In Game](https://interfaceingame.com), store screenshots. Write down what each does and why: shapes, depth, how buttons are built, how much screen the HUD takes, where the primary action sits. Learn the principles; never copy an identity. Keep the images as references for the review (`game-design:art-direction` says how to get them).
2. **Three concepts,** truly different, each from the game's own world: where would this interface exist if the game were real, what is it made of? Write each in a few lines with one key screen sketched. Choose the best yourself, tell the user why.
3. **Tokens.** Write them in `docs/ui-design.md` before any screen: radius scale, spacing scale, type scale, color roles, light direction, stroke weights, icon grid and style, motion durations. The radius scale, type scale and fonts also go in a [UiAuditSettings](../library/code/Core/Editor/UiChecks/README.md) asset, so every screen is held to them.
4. **Kit first.** Build every component in every state, render them on one sheet, and critique that sheet at device scale. Most craft problems show here and are cheap to fix.
5. **One key screen at final quality,** in the running game, at device size, next to its references. Only then the rest.
6. **Every screen** through the review, with its real content: the longest names, the largest numbers, translated text.

## Shape and depth

- **Several container types, each with a job:** a bar, a panel, a chip, a badge, not one rounded rectangle at many sizes. Shape carries meaning.
- **Silhouette.** Corners are one tool among many: cut corners, tabs, banners and frames are others. Whatever the shape, one idea, used with restraint: decorate the frame, keep the information areas calm.
- **Depth, in one light direction:** a thick outline, a highlight and a shadow, all from the same side, on everything. Good buttons show volume and a position above the background. Elevation has few levels.
- **Radii.** A small scale, as in Material's 4, 8, 12, 16, 28 dp. A nested corner follows its parent: inner radius = outer radius − padding − border, at least 0 (Apple's concentric corners use the same math). Otherwise the gap between them looks wrong.
- **Capsules** are justified only on small elements of one fixed height, such as a toggle or a tag, and never stretched to different widths.

## Sprites in UGUI

From the UGUI source (`com.unity.ugui` 2.6, `Image.cs`):

- **A sliced image's corner is drawn at** `border pixels ÷ (sprite PPU ÷ canvas Reference PPU × Pixels Per Unit Multiplier)` canvas units, whatever the element's size. Different PPUs or multipliers give different corners: use one PPU for all UI sprites, and multipliers only as a token of the radius scale.
- **An element smaller than its two borders squeezes them** to fit, which distorts the corners. Size the sprite's corners for the smallest element that uses it.
- **Simple and filled images stretch** to their rect. Keep a sprite's aspect, or slice it. Bars slice or use a mask, so their ends keep their shape at every value.
- Non-uniform `localScale` distorts everything inside. Motion scales evenly.
- Sprites at their displayed resolution, in an atlas, grouped by what is on screen together.

## Making UI art without an artist

| Method | Gives | Costs |
|---|---|---|
| Rendered from Blender with one light, then cut and sliced | Real material and depth, the richest look | Atlas memory. Render above the target size, shrink with a good filter, and check at device size: blurry icons come from skipping that |
| SDF shapes in a UGUI shader | Crisp at any size, one shape language by construction, small memory | Passes width and height to keep corners round (Shader Graph's UGUI samples show how); artifacts at very small sizes; a new material breaks batching. The graphic implements `IUiShape`, so the audit can measure it |
| Vector shapes rasterized to sprites | Exact icons and frames, consistent strokes | Flat unless layered |
| Layers: fill, inner shadow, highlight, outline | Depth from flat shapes | Stacked transparent layers are overdraw: bake them into one sprite |

Mix them on purpose. Keep one icon family: the same stroke, corner treatment, perspective and fill logic.

## Type

- A display font with character and a clean body font: the font is half the personality, and system-looking sans fonts are the template. At least one big size jump between levels.
- Fonts need a license for games. SIL OFL allows bundling; keep its copyright and license text in the game. Some Google Fonts are Apache 2.0: read each license. When a font can't be downloaded here, the choice stays open: name the font you want in the report, for the user to supply. Settling for what's already there is not a decision.
- **Numbers:** letters in steps of three digits (1.2K, 3.4M, 5.6B, 7.8T, then aa, ab), never exponents. Digits of one width, by the font or `<mspace>`, so counting values don't jitter.
- Over a game scene: TMP's outline and underlay, from one material per style. They are limited by the atlas padding, so large outlines clip.
- Sizes from the type scale, with an overflow strategy on every text: wrap, ellipsis, or auto-size within bounds. Translated labels can be two to three times as long.
- No user-facing text in code: it comes from the localization tables when the game is localized, otherwise from the UI assets or configs.

## Layout and color

- **Thumb first.** Main controls in the lower half, one-handed, as in Clash Royale: a permanent bottom bar, popups that don't fill the screen and close on a tap outside, depth rarely past one level.
- **One alignment system:** a spacing scale and shared margins. Elements on one edge or row share alignment lines.
- **Safe area.** On mobile, everything interactive stays inside `Screen.safeArea` (library UI module on the root container); backgrounds still extend to the full screen.
- **Color roles, and discipline with them.** Clash Royale uses yellow for the main action, green for the secondary, blue as the base, and red only for notifications. Choose your own, and keep a color from meaning two things. Contrast of at least 4.5:1 for text, and color is never the only signal.
- **Resources** in one consistent pattern, small: icon, number, and a plus where more can be bought.

## World UI

Markers over the world are where clutter starts, and a tycoon or strategy game has hundreds of candidates.

- **Priority.** Few tiers: what needs the player now, what can be read, what can wait. Higher tiers cover or hide lower ones.
- **Group on screen,** not in the world: things apart in the world still overlap on screen at a distance. Show one marker with a count. The selected thing stays out of a group.
- **Scale with zoom,** with a minimum and a maximum, and fade by distance instead of popping.
- **Clamp off-screen markers** that matter to the screen's edge.
- **Show less.** Show a marker when it is a reason to act, not because the thing exists. Coins that collect themselves need no label.
- Cheap on the CPU: pooled, updated by one system, not per frame when nothing changed.

## Motion

- Every interactive element has its states (normal, pressed, disabled, selected, plus hover on desktop) with animated transitions, and every interaction answers with motion and sound, plus haptics on mobile.
- Starting points from Material's tokens: 50–200 ms for small changes, 250–400 ms for medium, 450–600 ms for large, decelerating into place. No source gives good numbers for press timing or count-ups: tune them by eye at full frame rate.
- One orchestrated, staggered reveal beats many scattered effects. Motion serves the hierarchy.
- Scale evenly, anchor sensibly, and tie every tween to its owner.

## UGUI performance

- Static and frequently changing elements go on separate canvases: one change rebuilds its whole canvas.
- Raycast Target off on every non-interactive graphic.
- No nested layout groups on content that changes often. Long lists are pooled and virtualized.
- `RectMask2D` instead of `Mask`.
- Text via TextMeshPro; font setup and atlases: the official `unity:optimize-text-mesh-pro` skill.

## Check

1. **[UiAudit](../library/code/Core/Editor/UiChecks/README.md)** on each open screen, at each target aspect ratio, in Play Mode for UI built at runtime: `UiAudit.AuditAllCanvases(receiptName: "shop-20x9")`, with `noPanelOpen: true` for the HUD alone. It reports capsules, stretched sprites, squeezed corners, corners and text off the project's scales, shapes it can't measure, text and spacing problems. Copy it into every project with UI.
2. **Screenshots at device size,** captured from the running game through the Unity CLI: several resolutions and aspect ratios, looked at one by one.
3. **`study_screenshot.py`** (`game-design:art-direction`) on the key screen next to its references: blur and gray show the hierarchy.
4. **The written [UI review](references/review.md),** then a [fresh review](../standards/references/reviews.md) at milestones.
