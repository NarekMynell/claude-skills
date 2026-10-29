---
name: ui-quality
description: Quality bar for Unity game and app UI - layout for every aspect ratio, safe area, no text overflow or overlaps, alignment and spacing, art direction, interaction states, UGUI performance, screenshot checks.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# UI quality

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The official `unity:ui`, `unity:ui-ugui` and `unity:ui-uitk` skills cover how each framework works. This skill sets the bar every screen must meet. The project records its framework choice (UGUI or UI Toolkit) in `docs/`.

## Layout

- **Any aspect ratio.** Anchors and a Canvas Scaler set to **Scale With Screen Size** (UGUI), or flex layout with relative units (UI Toolkit). Test at the extremes: 16:9, 20:9, 4:3, tablets, and portrait or landscape as relevant.
- **Safe area.** On mobile, every interactive or important element stays inside `Screen.safeArea`. A safe-area component (library UI module) on the root container applies it and reapplies it when the resolution or orientation changes. Backgrounds still extend to the full screen.
- **Nothing overflows or overlaps.**
  - Every text element has an overflow strategy: wrap, ellipsis, or auto-size within bounds.
  - Containers are sized for the longest realistic content: the maximum score digits, and localized text. Translations of short labels can be two to three times as long as the English; long sentences grow by about a third.
  - No element leaves its container or covers another at any supported aspect ratio.
- **One alignment system.** A spacing scale and shared margins. Elements on the same edge or row share alignment lines: a score in the top-left and a menu button in the top-right share the top margin and the vertical center.

## Visual quality

Crafted, not generic AI UI.

- The art direction comes first, in `docs/art-direction.md`: palette, typography, shape language, iconography, motion style, references. Every screen follows it.
- Every interactive element has all its states (normal, pressed, disabled, selected, plus hover on desktop), with animated transitions.
- Every interaction gives feedback: motion and sound, plus haptics on mobile.
- Not allowed: default Unity sprites or fonts, gray placeholder panels, emoji as icons, random gradients and glows.
- Fonts and art carry a license that allows commercial use (such as the SIL Open Font License), recorded in `docs/`.
- Sprites are made at their displayed resolution. Panels use 9-slicing. Simple shapes (rounded rectangles, gradients) are drawn by a shader when that saves texture memory.
- No user-facing text in code: it comes from the localization tables when the game is localized, otherwise from the UI assets or configs.

## Accessibility

- Touch targets at least 44 × 44 pt on iOS and 48 × 48 dp on Android, even when the visible graphic is smaller.
- Text contrast at least 4.5:1 against its background (WCAG AA), and color is never the only signal: pair it with a shape, an icon or text.
- Text stays readable at the smallest supported screen and allows a larger text setting where the game has much text.

## UGUI performance

- Static and frequently changing elements go on separate canvases: one change rebuilds its whole canvas.
- Raycast Target off on every non-interactive graphic.
- No nested layout groups on content that changes often. Long lists are pooled and virtualized.
- `RectMask2D` instead of `Mask`.
- Text via TextMeshPro; font setup and atlases: the official `unity:optimize-text-mesh-pro` skill.

## Verification

A screen is done only when screenshots at several resolutions and aspect ratios show no overflow, overlap or misalignment. Capture them from the running Editor through the Unity CLI (`unity command`, see `unity:unity-cli`), and look at every one before reporting.
