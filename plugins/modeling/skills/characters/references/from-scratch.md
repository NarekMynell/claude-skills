# Characters from scratch, skeleton first

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

For cartoon and abstract humanoids and simple animals: bodies whose forms are simple by design and read as one surface. Detailed realistic faces and hands start from a base instead; robots and toy-like figures, whose joints show, from [parts](from-parts.md) ([method table](../SKILL.md#2-choose-the-method)).

## The idea

The body isn't modeled; it's described as a skeleton. Each joint has a position and a thickness (two radii: across and front to back), and Blender's Skin modifier turns the joints into one closed quad surface. Each limb is its own tube from its joint, so legs and arms can't fuse, and mirrored joints give a symmetric body. The armature comes from the same joints, so the bones sit exactly in the limbs. Proportions are numbers that can be checked: height in heads, leg length, shoulder width.

## Build the body

[build_body.py](../../../scripts/build_body.py) does it in one call: surface, smoothing, ground, armature, weights and their cleanup. The joint table for a cartoon figure about 3.5 heads tall, from the script's tests:

```python
JOINTS = {
    "pelvis": ((0, 0, 0.45), (0.10, 0.07), None),        # position, (radius across, radius front to back), parent
    "chest": ((0, 0, 0.62), (0.13, 0.09), "pelvis"),
    "neck": ((0, 0, 0.74), (0.045, 0.045), "chest"),
    "head": ((0, 0, 0.86), (0.13, 0.12), "neck"),
    "crown": ((0, 0, 0.98), (0.09, 0.085), "head"),
    "hip.L": ((0.06, 0, 0.35), (0.05, 0.05), "pelvis"),
    "thigh.L": ((0.063, 0, 0.29), (0.047, 0.047), "hip.L"),  # a joint below the hip gives the crease loops to fold
    "knee.L": ((0.065, 0, 0.21), (0.042, 0.042), "thigh.L"),
    # ... ankle, toe, shoulder, elbow, wrist, hand; the right side mirrors x
}
BONES = [("hips", "pelvis", "chest", None), ("thigh.L", "hip.L", "knee.L", "hips")]  # ... one per Humanoid bone
```

Run it with `NAME`, `JOINTS`, `BONES` and `SUBDIVISIONS` (0 for low poly, 1 or 2 for mid poly), then `inspect_character.py`. Rules that come from running it:

- **Facing −Y, left at +X**, feet at z = 0; the script puts the lowest point on the ground after smoothing, which shrinks the shape.
- **Limbs start outside the torso's joint:** the first joint of a limb sits farther from the torso joint than that joint's radius, and is thinner than it. Inside, the surface breaks where they branch: `non_manifold_edges` and `self_intersections` report it, on an animal with four legs and a tail most of all. On the test animal, with a pelvis of radius 0.11 m, a hip joint 0.13 m from it broke the surface and one 0.16 m from it didn't, until the two hips came within 0.12 m of each other. Check after every change of the table.
- **Each long limb has a joint near its root** (below the hip, below the shoulder). Without those loops a squat or a raised arm collapses the crease: `stretched_in_poses` reports it.
- **Thickness changes gradually** between neighboring joints; a joint much thicker than its neighbors makes a bulge, and two thick joints close together make a lump.
- **Smooth before rigging:** the script applies the subdivision first, so the weights fit the final surface. A Subdivision modifier added after skinning lifts the feet off the ground and stretches the joints.
- **Hands:** mittens (one tube, with finger bones as bone-only joints, `None` radius) or separate fingers from separate knuckle joints spaced more than twice the finger radius apart. Fingers branching from one point cut into each other: `self_intersections` reports it.
- **Bone names** with Humanoid roles and side markers (`hips`, `spine`, `head`, `thigh.L`, `upper_arm.R`), and only one surface joint without a parent.
- **Automatic weights reach across the body:** the script removes the other side's bones outside a center strip and limits and normalizes the weights. Check them anyway.

## Make it a character

The body is a base: the design goes on top of it.

- **Head and face:** the head's joints set its shape (a stack of joints with their own radii gives a jaw, a skull, a brow). Eyes, brows, nose, mouth and ears are parts modeled like props and fitted to the head, weighted to the head bone; eyes that move get their own bones.
- **Hair, clothes and accessories:** parts modeled like props and fitted with 2–5 mm clearance, measured against the largest part they can sit over; where a garment covers the body, its body faces are deleted, as the characters guide describes. Variants go in `PART_GROUPS`.
- **Colors** from the project's palette: a small palette texture or vertex colors, no noise.
- **Rigid parts** (armor, helmets) weighted fully to one bone each.

Then the whole check and review loop of the characters guide, as for any character.
