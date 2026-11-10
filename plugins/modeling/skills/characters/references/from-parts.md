# Characters from parts

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

A body of solid parts that overlap where they join: torso, head, upper and lower limbs, each carried by its own bones. It suits styles where the joints are meant to show: toys, robots, wooden or blocky figures, simple low-poly people and animals. Parts are modeled like props, so proportions are free, and parts can be swapped per character. Every joint stays a crease: for a body meant to read as one living surface, use a [base](../SKILL.md#2-choose-the-method) or a [skeleton-first body](from-scratch.md).

Overlap isn't a defect. A leg that enters a torso and stays there is how such a body joins, and [inspect_character.py](../../../scripts/inspect_character.py) accepts it. It fails what the player can see go wrong, listed below.

## Build it

- **Each part is a closed surface,** separate objects or one mesh with separate islands: the check treats both the same. In one mesh, name parts by their bones in reports (`Merged[head]`); `ALLOW_CROSSING` and the other lists need separate objects, so run them before merging.
- **Each joint sits inside the overlap.** Round the part's end around the joint's center: it stays inside its neighbor however the joint turns. A part that starts past the joint comes out when the joint bends (`joint_opens_in_poses`).
- **Enough overlap, no more.** A part's end stays inside what it enters. If it comes out at the far side (`parts_intersect`, "comes out the other side"), shorten it.
- **Weights follow the parts.** Each part hangs on the bones it spans, and two neighboring parts share no bone at the joint between them. A part that follows only the upper arm leaves the hand behind at the elbow's bend.
- **Worn parts are layers:** a sleeve or a trouser leg on the same bones as the limb under it. Keep only the end of the limb under it, entering the cuff or the hem. A whole limb kept under a sleeve pokes through at a deep bend, truly, and the check says so.
- **Rigid parts,** such as robot plates, are weighted fully to one bone, or parented to it.
- **Parts sit on their neighbors.** A part that crosses nothing, comes close to nothing and surrounds nothing reports as `floating_part`. Floating hands, halos and such go in `ALLOW_FLOATING`.

## Cost: cut what stays hidden

The ends inside other parts cost triangles the player never sees. On the test figure, 82 of 928 triangles.

1. Run `inspect_character.py` on the whole parts, with `WHOLE_PARTS = True`, `PROOF_DIR` and `PROOF_NAME`. Fix what it finds. Hidden faces go in `info`, and the receipt is `inspect_character-<name>-parts.json`.
2. Run [cut_hidden_faces.py](../../../scripts/cut_hidden_faces.py): it deletes only faces hidden at rest, in every test pose and in the clips listed in `ACTIONS`, with each set of `PART_GROUPS` variants. List every clip that bends further than the test poses: a clip left out can open what was cut, and the clip check doesn't always see that.
3. Run `inspect_character.py` on the result, with the same `PROOF_DIR` and `PROOF_NAME`.

The order matters: a cut removes what tells a poke from a bump. After it, a knee that came through trousers is only a small patch on them, like a button. So the tool marks what it cut with what those parts were, and the check asks for a receipt of those very parts (`parts_not_checked_before_cut`). A model that came cut from its maker has no whole parts to check, and isn't asked.

**What has failed:**

- Cutting by the rest pose alone: raising an arm opens the torso where it was (`see_inside_in_poses`).
- Deleting a face because its center is covered, while its corner still shows: holes at the seams (`see_inside`).
- Checking only the raw mesh, and never the cut one: `hidden_inside` fails on it forever, and nobody can tell a real defect from that noise.
- Rebuilding bodies as one closed surface to quiet the check: on the test figure a boolean union has 988 triangles against 846 cut, and its joints stretch in every pose until the weights are redone by hand. It is an option for a look with no creases, not a fix.

## What the check fails

| Report | What the player sees |
|---|---|
| `parts_intersect`, `self_intersections` in one mesh | Parts with no joint between them cut each other; a part comes out the far side of what it enters; a surface that runs under another shows through it. `examples` say which, and where |
| `shows_through_from_above`, `open_part` | Something comes through what covers the head, or through a hole in it |
| `poke_through_in_poses` | A pose brings a hand into a hip, or a limb through its garment |
| `joint_opens_in_poses` | Two parts that join at rest come apart in a pose |
| `see_inside`, `see_inside_in_poses` | An opening shows the inside of a surface; backface culling draws it as a hole |
| `floating_part` | A part hangs in the air |
| `hidden_inside`, `covered_faces`, `sunk_into_body` | Nothing to see: triangles paid for and never shown |

A surface's own crossing that nobody can see, or a graze under half a percent of the character's height, is no defect, and neither is anything inside a third part. On purpose, an arrow through a head, ears through a hat, a wand in a fist or a hinge pin: `ALLOW_CROSSING = ["Arrow+Head"]`. The receipt lists it. Hair of several pieces goes in one object: pieces rooted in the scalp as separate objects read like ears through a hat.

## What the check can't tell

Geometry can't tell everything, and these pass it. The pose sheet and the [review](review.md) have to catch them:

- a lump where a limb's root swings out of the torso, when it runs on from the limb's surface with no second line of crossing;
- a thigh through a rigid skirt in a squat: entering once, it reads as a joint;
- a whole limb swallowed by a very wide belly, coming out once;
- a nose or a similar small bump through a small mask.

The full list, with the scenes, is `dev/blender/attacks/accepted.txt` in the plugin's repository.

## Look

The check says nothing of how it looks. After it, a sheet of [render_views.py](../../../scripts/render_views.py) with `COLOR="OBJECT"`, and the [review](review.md): seams where the design wants them, no step where the design wants a smooth line, the same at game distance.
