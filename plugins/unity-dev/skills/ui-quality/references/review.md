# UI review

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

For each screen, on a device-size screenshot from the running game, next to its references. Write the findings before fixing: where, what is wrong, why, the fix. "Looks good" isn't a review.

## Would a professional ship this?

- **Whose game is it?** Hide the title. Does the screen belong to this game, or to any game?
- **Against the references.** Put them side by side. Name three things the reference does better, then fix them. Comparing with the previous version instead is how weak work gets approved.
- **What was the first idea?** If the screen looks like what a generator would make first, it is the template. Name what is unexpected here.

## Hierarchy

- Blur it (`study_screenshot.py`). What reads first? It should be the one primary action or the one fact the player came for.
- Count the levels of emphasis: more than three is noise.
- Is anything decorated that doesn't need attention? Remove it before adding anything.

## Craft

Read the `UiAudit` report first, then look for what numbers don't see:

- Corners: the same radius family; nested corners concentric; none deformed.
- Edges: outlines the same weight; highlights and shadows from one side; no halos or cut edges around sprites.
- Icons: one family, sharp at device size, centered optically in their shapes.
- Text: sits optically centered in its container; no text touching an edge; digits steady when they count.
- Alignment: edges and centers line up across groups; spacing from the scale.
- Bars and meters at empty, low and full: their ends keep their shape.

## In the game

- Does the HUD leave the game visible? Is its coverage within the target?
- World markers at the farthest and the nearest zoom, with the fullest scene the game can produce.
- Text over the busiest background.
- Every state: pressed, disabled, selected, empty lists, unaffordable, long names, the largest number, translated text.
- Motion: capture frames of the transitions. Nothing pops, nothing distorts.
