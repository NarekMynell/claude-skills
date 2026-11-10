"""Checks a game character or animal, however it is built: one skin, parts that overlap at the joints, separate objects or
one merged mesh. Anatomy, surfaces that poke through each other, what is hidden, symmetry, rig and skin weights, in the
rest pose and in deformation test poses.

Surfaces crossing is no defect by itself: a leg that enters a torso and stays there is how a body built from parts joins. A
defect is what the player can see go wrong: surfaces no joint connects cut each other; a part comes out the other side of what
it enters; a surface that runs under another shows through it; a joint comes apart in a pose; an opening shows the inside.

Run it as the modeling models guide's "Running the scripts" describes. Settings, all optional:
    TARGETS = ["Body", "Hair"]   the character's objects; default: what ARMATURE deforms or carries, else the selection
    ARMATURE = "Rig"             default: the armature deforming the targets
    BODY = "Body"                the skin mesh; default: the largest surface that spans head to feet, if there is one
    HUMANOID = None              whether to hold the rig to Unity Humanoid; default: by its bones and whether it stands upright.
                                 An animal or a creature gets the checks that fit any body, and bends of its own for poses
    WHOLE_PARTS = False          True on the parts before hidden faces are cut: what is hidden goes in `info`, and the receipt
                                 is inspect_character-<PROOF_NAME>-parts.json. A cut removes what tells a poke from a bump, so
                                 a character cut_hidden_faces.py has cut where parts cross needs this receipt too
    SINGLE_LAYER = True          a face covered by another part is a defect; False when outfits swap
    ALLOW_HIDDEN = ["Eyes", "Body<Hair"]  covered faces that are intended: a whole object, or "Object<Cover"
    ALLOW_CROSSING = ["Arrow+Head"]  pairs of objects that cross by design: an arrow through a head, ears through a hat, a wand
                                 through a fist, a hinge pin. The receipt lists them
    ALLOW_FLOATING = ["Halo"]    objects that touch nothing by design: a halo, the hands of a character with no arms
    SEE_THROUGH = ["HairCards"]  objects with transparent parts: they cover nothing, and may cross what they grow from and
                                 each other
    TWO_SIDED = ["Cape"]         objects drawn with both sides of their faces: looking at their back is fine
    PART_GROUPS = {"hair": ["HairShort", "HairLong"], "hat": ["Cap", "SunHat"]}  interchangeable parts: variants of the
                                 character. Parts of a group never appear together; parts of different groups do, so each
                                 pair of them, and each against the rest of the character, must fit without poking through
                                 each other. They aren't checked against their own group
    NEVER_TOGETHER = ["HairLong+Cap"]  pairs from different groups that the game never combines
    COVERS_FROM_ABOVE = ["SunHat"]  parts nothing may show through from above, besides what the check finds by shape: whatever
                                 crosses the line straight up through the head, or goes around it and reaches about as high
    OPEN_ON_TOP = ["Tiara"]      parts on the head that don't cover it: a tiara, a headband, a visor
    GROUND = 0.0                 ground height in metres; None for what doesn't stand on the ground, such as a fish
    LOWEST_VIEW = 0              degrees above the horizon: the lowest the camera looks from, for what an opening shows
    PROOF_DIR = "/abs/docs/proofs"  writes this report to inspect_character-<PROOF_NAME>.json there
    PROOF_NAME = "visitor"       default: the first target's name
    SYMMETRIC = ["Body"]         objects that must mirror across X = 0
    LEGS_JOINED = False          True for a long robe or dress in one skin, which joins the legs on purpose
    WAIST_BULGE = False          True for a body that is widest at the waist on purpose
    FINGERS = 5                  fingers per hand in the design, to hold the rig to it. By default both hands only have to match
    POSES = True                 also check the test poses (needs the armature). A list of names keeps to the poses the character really
                                 makes: a blocky figure that never twists at the waist, ["arms_down", "arms_up", "stride"]
    BONE_MAP = {}                Unity Humanoid role -> bone name, for names the script doesn't recognize

Sets `result`: `passed`, `issues` (name -> count or detail), `examples` (name -> up to 3 cases with world locations
in metres) and `info` (measurements). The scene is left as it was.
"""

import json
import math
import os
import types

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

MAX_EXAMPLES = 3
GRAZE = 0.005  # a crossing smaller than this share of the height can't be seen at any game distance


def _setting(name, default):
    return globals().get(name, default)


def _load_rig():
    path = _setting("RIG_HELPERS", None) or os.path.join(os.path.dirname(globals()["__file__"]), "rig.py")
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return types.SimpleNamespace(**namespace)


rig = _load_rig()


def _round(vector, digits=3):
    return [round(float(c), digits) for c in vector]


# --- Cross-sections --------------------------------------------------------------------------------------------------


def _islands(part, z):
    """Cross-section islands of one part at height z: lists of points, one per connected surface strip."""
    parent = {}

    def find(face):
        while parent.setdefault(face, face) != face:
            parent[face] = parent[parent[face]]
            face = parent[face]
        return face

    crossings = []
    for edge in part.bm.edges:
        a, b = edge.verts
        if (a.co.z - z) * (b.co.z - z) < 0.0:
            t = (z - a.co.z) / (b.co.z - a.co.z)
            point = a.co.lerp(b.co, t)
            faces = [f.index for f in edge.link_faces]
            if len(faces) > 1:
                for other in faces[1:]:
                    parent[find(faces[0])] = find(other)
            crossings.append((faces[0] if faces else -1 - len(crossings), point))
    groups = {}
    for face, point in crossings:
        groups.setdefault(find(face) if face >= 0 else face, []).append(point)
    return list(groups.values())


def _clusters(parts, z, margin):
    """Islands of all parts at height z, merged when their XY boxes overlap (a sleeve around an arm is one cluster).
    Each cluster: dict with box (xmin, xmax, ymin, ymax) and points."""
    boxes = []
    for part in parts:
        for points in _islands(part, z):
            xs, ys = [p.x for p in points], [p.y for p in points]
            boxes.append({"box": [min(xs), max(xs), min(ys), max(ys)], "points": points})
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i]["box"], boxes[j]["box"]
                if a[0] <= b[1] + margin and b[0] <= a[1] + margin and a[2] <= b[3] + margin and b[2] <= a[3] + margin:
                    boxes[i] = {"box": [min(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3])],
                                "points": boxes[i]["points"] + boxes[j]["points"]}
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes


def _overlap(a, b, margin):
    return a[0] <= b[1] + margin and b[0] <= a[1] + margin and a[2] <= b[3] + margin and b[2] <= a[3] + margin


def _min_gap(points_a, points_b):
    tree = KDTree(len(points_b))
    for i, p in enumerate(points_b):
        tree.insert(Vector((p.x, p.y, 0.0)), i)
    tree.balance()
    return min(tree.find(Vector((p.x, p.y, 0.0)))[2] for p in points_a)


def _legs(parts, bottom, height, roles, armature, joined_ok):
    """Follows both legs of one skin up from the feet until they join. Returns issues, examples, info."""
    issues, examples, info = {}, {}, {}
    margin = 0.001 * height
    step = 0.02 * height
    levels = [bottom + step * (k + 1) for k in range(30)]
    first = _clusters(parts, levels[0], margin)
    feet = sorted(first, key=lambda c: len(c["points"]), reverse=True)[:2]
    left = [c for c in feet if (c["box"][0] + c["box"][1]) / 2 > 0]
    right = [c for c in feet if (c["box"][0] + c["box"][1]) / 2 < 0]
    if not left or not right:
        spans = [c for c in first if c["box"][0] < 0 < c["box"][1]]
        if spans and not joined_ok:
            issues["fused_legs"] = "the feet are one surface at the ground"
            examples["fused_legs"] = [{"z": round(levels[0], 3)}]
        return issues, examples, info
    chains = [left[0]["box"], right[0]["box"]]
    crotch, gap = None, None
    for z in levels[1:]:
        clusters = _clusters(parts, z, margin)
        current = []
        for box in chains:
            match = next((c for c in clusters if _overlap(c["box"], box, margin)), None)
            current.append(match)
        if current[0] is None or current[1] is None:
            break
        if current[0] is current[1]:
            crotch = z
            break
        distance = _min_gap(current[0]["points"], current[1]["points"])
        gap = distance if gap is None else min(gap, distance)
        chains = [current[0]["box"], current[1]["box"]]
    if crotch is not None:
        info["legs_join_at_height_ratio"] = round((crotch - bottom) / height, 3)
    if gap is not None:
        info["leg_gap_min_cm"] = round(gap * 100, 2)
    if joined_ok:
        return issues, examples, info
    knees = [rig.head(armature, roles[r]).z for r in ("LeftLowerLeg", "RightLowerLeg") if r in roles] if armature else []
    hips = [rig.head(armature, roles[r]).z for r in ("LeftUpperLeg", "RightUpperLeg") if r in roles] if armature else []
    if crotch is not None:
        if knees and hips:
            knee, hip = sum(knees) / len(knees), sum(hips) / len(hips)
            expected = knee + 0.6 * (hip - knee)
            if crotch < expected:
                issues["fused_legs"] = f"the legs join at {crotch:.3f} m, below {expected:.3f} m (60% from knees to hips)"
                examples["fused_legs"] = [{"z": round(crotch, 3)}]
        elif (crotch - bottom) / height < 0.15:
            issues["fused_legs"] = f"the legs join at {(crotch - bottom) / height:.0%} of the height"
            examples["fused_legs"] = [{"z": round(crotch, 3)}]
    if gap is not None and gap < 0.001 * height:
        issues["legs_touching"] = f"the legs come within {gap * 1000:.1f} mm of each other below the crotch"
    return issues, examples, info


def _torso(body, parts, armature, roles, bulge_ok):
    """Width and depth of the torso between the hip joints and the lower chest: the surface that carries the trunk, or the parts
    covering it where it has none (faces deleted under clothes). A belt on it isn't the waist."""
    issues, examples, info = {}, {}, {}
    hips = [rig.head(armature, roles[r]).z for r in ("LeftUpperLeg", "RightUpperLeg") if r in roles]
    shoulders = [rig.head(armature, roles[r]).z for r in ("LeftUpperArm", "RightUpperArm") if r in roles]
    if not hips or not shoulders:
        return issues, examples, info
    low, high = sum(hips) / len(hips), sum(shoulders) / len(shoulders)
    # Up to the lower chest: higher, an A-pose armpit or a sleeve joins the arms to the torso's slice.
    top = low + 0.6 * (high - low)
    samples = []
    for k in range(11):
        z = low + (top - low) * k / 10
        # The body's own island around the center line: not merged with an arm that passes close to it.
        center = []
        for points in _islands(body, z):
            xs, ys = [p.x for p in points], [p.y for p in points]
            if min(xs) <= 0.0 <= max(xs):
                center.append({"box": [min(xs), max(xs), min(ys), max(ys)], "points": points})
        center.sort(key=lambda c: len(c["points"]), reverse=True)
        if not center:
            center = [c for c in _clusters(parts, z, 0.001 * (top - low)) if c["box"][0] <= 0.0 <= c["box"][1]]
        if not center:
            continue
        box = center[0]["box"]
        samples.append((z, box[1] - box[0], box[3] - box[2]))
    if len(samples) < 3:
        return issues, examples, info
    ends_width = max(samples[0][1], samples[-1][1])
    ends_depth = max(samples[0][2], samples[-1][2])
    widest = max(samples[1:-1], key=lambda s: s[1])
    deepest = max(samples[1:-1], key=lambda s: s[2])
    info["torso_cm"] = {
        "hip_width": round(samples[0][1] * 100, 1), "waist_width": round(min(s[1] for s in samples[1:-1]) * 100, 1),
        "chest_width": round(samples[-1][1] * 100, 1), "hip_depth": round(samples[0][2] * 100, 1),
        "waist_depth": round(min(s[2] for s in samples[1:-1]) * 100, 1), "chest_depth": round(samples[-1][2] * 100, 1),
    }
    if not bulge_ok:
        if widest[1] > ends_width * 1.03:
            issues["waist_bulge"] = f"the torso is {widest[1] * 100:.1f} cm wide at {widest[0]:.3f} m, wider than hips and chest ({ends_width * 100:.1f} cm)"
            examples["waist_bulge"] = [{"z": round(widest[0], 3)}]
        elif deepest[2] > ends_depth * 1.08:
            issues["waist_bulge"] = f"the belly is {deepest[2] * 100:.1f} cm deep at {deepest[0]:.3f} m, deeper than hips and chest ({ends_depth * 100:.1f} cm)"
            examples["waist_bulge"] = [{"z": round(deepest[0], 3)}]
    return issues, examples, info


# --- Surfaces ----------------------------------------------------------------------------------------------------------


def _group_of(groups):
    return {name: group for group, names in groups.items() for name in names}


def _without_variants(parts, groups):
    """The parts with one variant of each group, the first: the character as it appears."""
    skipped = {name for names in groups.values() for name in names[1:]}
    return [p for p in parts if p.owner not in skipped]


def _sights(parts, groups, see_through, height):
    """A view of the character for judging two surfaces: what else is there with them hides what it hides, and another
    variant, which isn't there, hides nothing."""
    group_of = _group_of(groups)
    base = [p for p in parts if p.owner not in see_through and p.owner not in group_of]
    shared = rig.Sight(base, height)
    built = {}

    def sight_for(a, b):
        owners = tuple(sorted({a.owner, b.owner} & set(group_of)))
        if not owners:
            return shared
        if owners not in built:
            built[owners] = rig.Sight(base + [p for p in parts if p.owner in owners and p.owner not in see_through], height)
        return built[owners]

    return sight_for


def _skipper(groups, never_together, allow_crossing):
    """Pairs that never need judging: variants of one group, pairs the game never combines, and pairs crossing on purpose."""
    group_of = _group_of(groups)

    def skip(a, b):
        if a.owner != b.owner and group_of.get(a.owner) and group_of.get(a.owner) == group_of.get(b.owner):
            return True
        together = (f"{a.owner}+{b.owner}", f"{b.owner}+{a.owner}")
        return any(pair in never_together or pair in allow_crossing for pair in together)

    return skip


def _hull(points):
    """Convex hull of (x, y) points, counter-clockwise."""
    points = sorted(set(points))
    if len(points) < 3:
        return points

    def half(items):
        chain = []
        for p in items:
            while len(chain) >= 2 and (chain[-1][0] - chain[-2][0]) * (p[1] - chain[-2][1]) - (chain[-1][1] - chain[-2][1]) * (p[0] - chain[-2][0]) <= 0:
                chain.pop()
            chain.append(p)
        return chain[:-1]

    return half(points) + half(reversed(points))


def _inside(hull, x, y):
    return all((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) >= 0 for a, b in zip(hull, hull[1:] + hull[:1]))


def _top_center(points):
    """The highest height of a set of points, at the middle of what is near that height: a low-poly head's top is a ring."""
    high = max(p.z for p in points)
    low = min(p.z for p in points)
    near = [p for p in points if p.z >= high - 0.03 * (high - low)]
    return Vector((sum(p.x for p in near) / len(near), sum(p.y for p in near) / len(near), high))


def _head_top(parts, body, armature, roles, group_of):
    """The surface that is the head, its highest point, and the height of its base. No rig: the body's highest point. A rig with no
    head: nothing to cover. Of what holds the base of the head's bone, the head is what lies closest around it: hair or a
    hood around the head lies further out. Variants count when the head itself is one."""
    if armature is None:
        return body, _top_center([v.co for v in body.bm.verts]), min(v.co.z for v in body.bm.verts)
    name = rig.head_bone(armature, roles)
    if name is None:
        return None, None, None
    base = rig.head(armature, name)
    candidates = []
    for part in parts:
        faces = [f for f in part.bm.faces if part.face_bone[f.index] == name]
        if faces:
            candidates.append((part, faces))
    if not candidates:
        return None, None, None
    fixed = [c for c in candidates if c[0].owner not in group_of] or candidates

    def closeness(candidate):
        verts = {v.index: v.co for f in candidate[1] for v in f.verts}
        return sum((co - base).length for co in verts.values()) / len(verts)

    holding = [c for c in fixed if rig.inside(c[0], base)]
    part, faces = min(holding, key=closeness) if holding else max(fixed, key=lambda c: sum(f.calc_area() for f in c[1]))
    return part, _top_center([v.co for f in faces for v in f.verts]), base.z


def _over_the_top(part, point):
    """Whether a part goes all around the point: a crown, a band of hair. A horn to one side doesn't."""
    level = min(point.z, max(v.co.z for v in part.bm.verts) - 0.002)
    center = Vector((point.x, point.y, level))
    around = [Vector((math.cos(k * math.pi / 4.0), math.sin(k * math.pi / 4.0), 0.0)) for k in range(8)]
    return sum(1 for d in around if part.tree.ray_cast(center, d, 10.0)[0] is not None) >= 6


def _hull_area(hull):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(hull, hull[1:] + hull[:1]))) / 2.0


def _tops(parts, skull, highest, height, head_name, see_through, armature_bones=None):
    """Whatever covers the top of the head: it crosses the line straight up through the head, however low it sits, or it
    reaches about as high and goes all around that line. And it is about as wide as the head. By shape, not by name: a fedora, a
    crown or a helmet all count; a horn to one side, an antenna or a bobble don't. Names can add to it, or take away from it."""
    named = set(_setting("COVERS_FROM_ABOVE", []))
    open_on_top = set(_setting("OPEN_ON_TOP", []))
    if skull is None:
        return [p for p in parts if p.owner in named]
    head = [v.co for f in skull.bm.faces if head_name is None or skull.face_bone[f.index] == head_name for v in f.verts]
    head_width = _hull_area(_hull([(p.x, p.y) for p in head]))
    start = Vector((highest.x, highest.y, sum(p.z for p in head) / len(head)))
    tops, crowns = [], []
    for part in parts:
        if part is skull or part.owner in see_through or part.owner in open_on_top:
            continue
        if part.owner in named:
            tops.append(part)
            continue
        hull = _hull([(v.co.x, v.co.y) for v in part.bm.verts])
        if len(hull) < 3 or _hull_area(hull) < 0.25 * head_width or not _inside(hull, highest.x, highest.y):
            continue
        hit = part.tree.ray_cast(start, Vector((0.0, 0.0, 1.0)), 10.0)
        close_enough = max(v.co.z for v in part.bm.verts) >= highest.z - 0.03 * height
        as_high = max(v.co.z for v in part.bm.verts) >= highest.z - 0.01 * height  # a headband stops short of that
        if hit[0] is not None:
            # A hat sunk low still crosses that line, on the head's bone. So does a hat on the wrong bone, which the check reports;
            # a neck that rises behind a horse's head is the bone next to the head, and no hat.
            bone = part.bone_at(hit[2], [hit[0]])
            on_the_head = head_name is None or bone == head_name
            is_neck = armature_bones is not None and armature_bones[head_name].parent is not None and bone == armature_bones[head_name].parent.name
            if on_the_head or (not is_neck and close_enough):
                tops.append(part)
        elif as_high and _over_the_top(part, highest):
            crowns.append(part)
    # A ring around the head is an open crown, unless something already covers the head: then it's a band on that. And a flat
    # disc, such as a top hat's brim made apart from its crown, is no cover under what rises above it.
    head_height = max(p.z for p in head) - min(p.z for p in head)
    tall = [p for p in tops if p.highest - p.lowest >= 0.15 * head_height]
    return (tall or tops) + ([] if tops else crowns)


def _is_hair(part, groups):
    words = {"hair", "hairs", "wig", "bun", "ponytail", "braid", "fringe", "bangs", "mohawk", "afro"}
    return bool(set(rig.words(part.owner)) & words or set(rig.words(_group_of(groups).get(part.owner, ""))) & words)


def _open_loops(part):
    """The separate openings of a surface: each a list of connected open edges."""
    edges = [edge for edge in part.bm.edges if len(edge.link_faces) == 1]
    left = {edge.index for edge in edges}
    loops = []
    for edge in edges:
        if edge.index not in left:
            continue
        left.remove(edge.index)
        stack, loop = [edge], []
        while stack:
            current = stack.pop()
            loop.append(current)
            for vertex in current.verts:
                for other in vertex.link_edges:
                    if other.index in left and len(other.link_faces) == 1:
                        left.remove(other.index)
                        stack.append(other)
        loops.append(loop)
    return loops


def _open_parts(tops, head_level, sight):
    """Holes in what covers the head. Its largest opening is where it goes on: an open underside, a hairline. Another opening
    lying wholly above the head's base is a hole, and it shows from the side too, which looking down can't see. A hood's face
    opening starts lower than that. A hole under another part shows nothing."""
    openings = {}
    for part in tops:
        loops = _open_loops(part)
        if len(loops) < 2:
            continue
        largest = max(loops, key=lambda loop: sum(e.calc_length() for e in loop))

        def shows(loop):
            points = [v.co for e in loop for v in e.verts]
            return sight.visible(sum(points, Vector()) / len(points))

        holes = [loop for loop in loops if loop is not largest and min(v.co.z for e in loop for v in e.verts) > head_level and shows(loop)]
        if holes:
            openings[part.name] = sum(len(loop) for loop in holes)
    return openings


def _ornament(other, top, group_of, skull, scale):
    """A knob, a feather or a bun on what covers the head: it starts no lower than that, most of it isn't under it, and it doesn't
    cross the head itself, as rabbit ears do. What comes up from under a hat is none of these, nor is a variant, whose fit each
    combination has to show."""
    if other.owner in group_of or other.owner in _setting("SEE_THROUGH", ()) or other.lowest < top.lowest - 0.02 * scale:
        return False
    if skull is not None and other.tree.overlap(skull.tree):
        return False  # standing on the head itself
    return len(rig.under(other, top)) < 0.75 * len(other.bm.faces)


def _shows_through(parts, tops, groups, never_together, allow_crossing, skull, head_level, height, scale, see_through, judge):
    """Looking straight down inside the outline of what covers the head: whatever the look meets first, at the height of the head,
    shows through it. It finds a head out of an open crown and a hat swallowed by hair, which cut no surface. What lies lower,
    such as the shoulders under the gap between a helmet's horns, comes through nothing. One object is one cover: chunks of
    hair, a hat and its band. {"Hat<Hair": rays}, parts seen from inside out, and examples."""
    group_of = _group_of(groups)
    counts, inside_out, examples = {}, {}, []
    down = Vector((0.0, 0.0, -1.0))
    graze = GRAZE * scale
    covers = {}
    for top in tops:
        # A character in one mesh holds its hat too: there, each island stands alone.
        covers.setdefault(top.name if skull is not None and skull.owner == top.owner else top.owner, []).append(top)
    for name, cover in covers.items():
        owner = cover[0].owner
        points = [(v.co.x, v.co.y) for part in cover for v in part.bm.verts]
        hull = _hull(points)
        if len(hull) < 3:
            continue
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        ceiling = max(v.co.z for part in cover for v in part.bm.verts) + 1.0
        others = []
        for other in parts:
            if other in cover or (other.owner == owner and (skull is None or skull.owner != owner)):
                continue
            if other.owner != owner and group_of.get(other.owner) and group_of.get(other.owner) == group_of.get(owner):
                continue
            if f"{owner}+{other.owner}" in never_together or f"{other.owner}+{owner}" in never_together:
                continue
            if f"{owner}+{other.owner}" in allow_crossing or f"{other.owner}+{owner}" in allow_crossing:
                continue
            # Hair may be under a hat, never the other way: for hair, only the body can show through.
            if _is_hair(cover[0], groups) and other.owner in group_of:
                continue
            others.append(other)
        # What else is on screen with it can hide what's under it too; another variant, which isn't there, can't.
        solid = [p for p in parts if p.owner not in see_through and p.owner not in group_of]
        for other in others:
            # Hair cards stand edge-on to a look from above: what counts is whether they rise out of the cover.
            if other.owner in see_through:
                rising = [v.co for v in other.bm.verts if any((h := part.tree.ray_cast(v.co, down, 10.0))[0] is not None and h[3] > graze for part in cover)]
                if len(rising) >= 3:
                    counts[f"{name}<{other.name}"] = len(rising)
                    examples.append({"objects": [name, other.name], "at": _round(rising[0])})
                continue
            if other is not skull and (_ornament(other, cover[0], group_of, skull, scale) or judge._wraps(other, cover[0])):
                continue
            hiding = [p for p in solid if p is not other and p not in cover]
            hits = seen = 0
            for i in range(25):
                for j in range(25):
                    # Slightly inside the outline's cells, so a ray doesn't run exactly along an edge.
                    x = min(xs) + (max(xs) - min(xs)) * (i + 0.5) / 25
                    y = min(ys) + (max(ys) - min(ys)) * (j + 0.5) / 25
                    if not _inside(hull, x, y):
                        continue
                    seen += 1
                    origin = Vector((x, y, ceiling))
                    other_hit = other.tree.ray_cast(origin, down, 10.0)
                    if other_hit[0] is None or other_hit[0].z < head_level:
                        continue
                    if any((h := part.tree.ray_cast(origin, down, 10.0))[0] is not None and h[3] < other_hit[3] + graze for part in cover):
                        continue  # the cover is over it, or under it by less than can be seen
                    if any((h := part.tree.ray_cast(origin, down, 10.0))[0] is not None and h[3] < other_hit[3] for part in hiding):
                        continue
                    hits += 1
                    if len(examples) < MAX_EXAMPLES:
                        examples.append({"objects": [name, other.name], "at": _round(other_hit[0])})
            # A chink between two chunks of hair isn't the head coming through.
            if hits >= max(3, 0.03 * seen):
                counts[f"{name}<{other.name}"] = hits
        # From above, a surface shows its outside. Seen from behind, backface culling would make it vanish.
        if owner in _setting("TWO_SIDED", ()):
            continue
        backs = fronts = 0
        for i in range(25):
            for j in range(25):
                x = min(xs) + (max(xs) - min(xs)) * (i + 0.5) / 25
                y = min(ys) + (max(ys) - min(ys)) * (j + 0.5) / 25
                best = None
                for part in cover:
                    hit = part.tree.ray_cast(Vector((x, y, ceiling)), down, 10.0)
                    if hit[0] is not None and (best is None or hit[3] < best[3]):
                        best = hit
                if best is not None:
                    if best[1].dot(down) > 0.0:
                        backs += 1
                    else:
                        fronts += 1
        if backs > fronts:
            inside_out[name] = backs
    return counts, inside_out, examples


def _variant_coverage(parts, groups, see_through, allowed, never_together):
    """Each variant against each part it can appear with: a variant mostly hidden by another is lost inside it. It runs
    beyond the first variants, which are the only ones the plain hidden-face check sees."""
    group_of = _group_of(groups)
    height = max(v.co.z for p in parts for v in p.bm.verts) - min(v.co.z for p in parts for v in p.bm.verts)
    base = [p for p in parts if p.owner not in group_of]
    swallowed = {}
    for part in parts:
        if part.owner not in group_of:
            continue
        for other in parts:
            if other is part or group_of.get(other.owner) == group_of[part.owner]:
                continue
            if f"{part.owner}+{other.owner}" in never_together or f"{other.owner}+{part.owner}" in never_together:
                continue
            if _is_hair(part, groups) and not _is_hair(other, groups):
                continue  # hair under a hat is how a hat is worn
            found = rig.hidden_faces(base + [q for q in (part, other) if q not in base], see_through, 0.2 * height, allowed, among={(part.name, f.index) for f in part.bm.faces})
            hidden = sum(1 for cover in found.values() if cover == other.name)
            if f"{part.owner}<{other.owner}" not in allowed and hidden > 0.3 * len(part.bm.faces):
                swallowed[f"{part.name}<{other.name}"] = hidden
    return swallowed


def _asymmetry(parts, height):
    """Distance from each vertex's mirror image across X = 0 to the nearest vertex, per object: one side's parts mirror the
    other side's."""
    report, examples = {}, []
    by_owner = {}
    for part in parts:
        by_owner.setdefault(part.owner, []).extend(v.co.copy() for v in part.bm.verts)
    for owner, coords in by_owner.items():
        if not coords:
            continue
        tree = KDTree(len(coords))
        for i, co in enumerate(coords):
            tree.insert(co, i)
        tree.balance()
        distances = [(tree.find(Vector((-co.x, co.y, co.z)))[2], co) for co in coords]
        ordered = sorted(d for d, _ in distances)
        p95 = ordered[int(0.95 * (len(ordered) - 1))]
        if p95 > max(0.002, 0.002 * height):
            report[owner] = f"5% of vertices are over {p95 * 1000:.1f} mm from their mirror image"
            examples.append({"object": owner, "at": _round(max(distances, key=lambda d: d[0])[1])})
    return report, examples


# --- Rig and weights ---------------------------------------------------------------------------------------------------

_CHAINS = [
    ("Hips", "Spine"), ("Spine", "Head"), ("Hips", "LeftUpperLeg"), ("Hips", "RightUpperLeg"),
    ("LeftUpperArm", "LeftLowerArm"), ("LeftLowerArm", "LeftHand"), ("RightUpperArm", "RightLowerArm"),
    ("RightLowerArm", "RightHand"), ("LeftUpperLeg", "LeftLowerLeg"), ("LeftLowerLeg", "LeftFoot"),
    ("RightUpperLeg", "RightLowerLeg"), ("RightLowerLeg", "RightFoot"), ("Spine", "LeftUpperArm"), ("Spine", "RightUpperArm"),
]


def _applied(obj):
    rotation = obj.matrix_world.to_3x3().normalized()
    identity = all(abs(rotation[i][j] - (1.0 if i == j else 0.0)) < 1e-4 for i in range(3) for j in range(3))
    return identity and all(abs(s - 1.0) < 1e-4 for s in obj.matrix_world.to_scale())


def _armature_transform(armature, issues, info):
    """A file's unit scale and axes on an imported rig skin as they should, and Unity's import check sees where they end up. A scale
    that differs between axes shears every bone that turns."""
    scale = armature.matrix_world.to_scale()
    if max(abs(c) for c in scale) - min(abs(c) for c in scale) > 1e-3 * max(abs(c) for c in scale) or min(scale) < 0.0:
        issues["armature_scale_uneven"] = f"scale {[round(c, 3) for c in scale]}: limbs shear when they turn. Apply it"
    elif not _applied(armature):
        info["armature_transform"] = "rotated or scaled: after export, check rotation 0 and scale 1 on the model root in Unity"


def _creature_rig_report(armature, roles, height):
    """What holds for any skeleton: sides, facing, transforms."""
    issues, examples, info = {}, {}, {}
    _armature_transform(armature, issues, info)
    sides = []
    for bone in armature.data.bones:
        side, x = rig.name_side(bone.name), rig.head(armature, bone.name).x
        if (side == "L" and x < 0.005 * height) or (side == "R" and x > -0.005 * height):
            sides.append(bone.name)
    # No avatar maps a creature by its names: whose left they mean is the artist's business.
    if sides:
        info["bones_named_for_the_other_side"] = len(sides)
    if "Hips" in roles and "Head" in roles and rig.head(armature, roles["Head"]).y > rig.head(armature, roles["Hips"]).y + 0.02 * height:
        issues["not_facing_minus_y"] = "the head is behind the hips along -Y: the animal faces the wrong way"
    info["deform_bones"] = sum(1 for b in armature.data.bones if b.use_deform)
    return issues, examples, info


def _rig_report(armature, roles, height, fingers):
    issues, examples, info = {}, {}, {}
    missing = [r for r in rig.REQUIRED if r not in roles]
    if missing:
        issues["missing_humanoid_bones"] = missing
    _armature_transform(armature, issues, info)
    sides = []
    for role, bone in roles.items():
        x = rig.head(armature, bone).x
        if (role.startswith("Left") and x < 0.005 * height) or (role.startswith("Right") and x > -0.005 * height):
            sides.append({"role": role, "bone": bone, "x": round(x, 3)})
    if sides:
        issues["left_right_swapped"] = len(sides)
        examples["left_right_swapped"] = sides[:MAX_EXAMPLES]
    order = [f"{a} -> {b}" for a, b in _CHAINS if a in roles and b in roles and not rig.is_ancestor(armature, roles[a], roles[b])]
    if order:
        issues["hierarchy"] = order
    forward = Vector()
    for side in ("Left", "Right"):
        foot, toes = roles.get(side + "Foot"), roles.get(side + "Toes")
        if foot:
            direction = (rig.head(armature, toes) if toes else rig.tail(armature, foot)) - rig.head(armature, foot)
            direction.z = 0.0
            if direction.length > 1e-6:
                forward += direction.normalized()
    if forward.length > 1e-6:
        facing = -forward.normalized().y
        info["facing_minus_y"] = round(facing, 2)
        if facing < 0.7:
            issues["not_facing_minus_y"] = "the toes point away from -Y: the character faces the wrong way"
    for side in ("Left", "Right"):
        upper, lower = roles.get(side + "UpperArm"), roles.get(side + "LowerArm")
        if upper and lower:
            direction = rig.head(armature, lower) - rig.head(armature, upper)
            angle = math.degrees(math.asin(max(-1.0, min(1.0, -direction.z / max(direction.length, 1e-9)))))
            info[f"{side.lower()}_arm_below_horizontal_deg"] = round(angle, 1)
            if angle > 60 or angle < -15:
                issues[f"{side.lower()}_arm_rest_angle"] = f"{angle:.0f} deg below horizontal; rest the arms between T-pose (0) and A-pose (about 45)"
        found = [f for f in rig.FINGERS if f"{side}{f}Proximal" in roles]
        info[f"{side.lower()}_finger_chains"] = len(found)
        if fingers is not None and len(found) != fingers:
            issues[f"{side.lower()}_finger_bones"] = f"{len(found)} finger chains, the design has {fingers}"
        roots = {f: rig.head(armature, roles[f"{side}{f}Proximal"]) for f in found}
        if "Thumb" in roots and "Index" in roots:
            distances = [(roots["Thumb"] - roots[f]).length for f in ("Index", "Middle", "Ring", "Little") if f in roots]
            if distances != sorted(distances):
                issues[f"{side.lower()}_finger_order"] = "finger bones aren't ordered index, middle, ring, little from the thumb"
        mirrored = _hand_mirrored(armature, roles, side)
        if mirrored is None:
            info[f"{side.lower()}_hand_chirality"] = "not checked: the fingers are straight in the rest pose"
        elif mirrored:
            issues[f"{side.lower()}_hand_mirrored"] = "the hand is the other side's, mirrored: its fingers curl toward the back of the hand"
    chains = [info.get(f"{side}_finger_chains", 0) for side in ("left", "right")]
    if fingers is None and chains[0] != chains[1]:
        issues["hands_differ"] = f"{chains[0]} finger chains on the left hand, {chains[1]} on the right"
    info["deform_bones"] = sum(1 for b in armature.data.bones if b.use_deform)
    info["roles_mapped"] = len(roles)
    return issues, examples, info


def _hand_mirrored(armature, roles, side):
    """Whether a hand is the other side's mirror image, whatever way the palm faces: fingers bend toward the palm, and on a left
    hand (along x across) points to the palm when 'across' runs from the little finger to the index. None when the fingers are too
    straight to tell the palm side: straight fingers on a palm tilted at the knuckles say nothing."""
    hand, index, little = roles.get(f"{side}Hand"), roles.get(f"{side}IndexProximal"), roles.get(f"{side}LittleProximal") or roles.get(f"{side}RingProximal")
    middle = roles.get(f"{side}MiddleProximal") or index
    if not (hand and index and little):
        return None
    along = (rig.head(armature, middle) - rig.head(armature, hand)).normalized()
    across = rig.head(armature, index) - rig.head(armature, little)
    palm = along.cross(across).normalized()
    bends = []
    for finger in ("Index", "Middle", "Ring", "Little"):
        base, tip = roles.get(f"{side}{finger}Proximal"), roles.get(f"{side}{finger}Distal")
        if not (base and tip):
            continue
        first = (rig.tail(armature, base) - rig.head(armature, base)).normalized()
        last = (rig.tail(armature, tip) - rig.head(armature, tip)).normalized()
        bends.append(last - first)
    if not bends:
        return None
    bend = sum(bends, Vector()) / len(bends)
    if abs(bend.dot(palm)) < 0.17:  # about 10 degrees from the first joint to the last
        return None
    toward_palm = palm.dot(bend)
    return toward_palm < 0 if side == "Left" else toward_palm > 0


def _bone_side(armature, bone, height, humanoid):
    """Which side a bone stands on, if it has one. A snake's spine winds from side to side and has none: what isn't named for a
    side counts only on a person. By where it stands: whose left a name means is no matter for the skin."""
    if not (rig.name_side(bone.name) or humanoid):
        return None
    x = rig.head(armature, bone.name).x
    return "L" if x > 0.01 * height else "R" if x < -0.01 * height else None


def _weights_report(objects, armature, height, humanoid):
    issues, examples, info = {}, {}, {}
    deform = {b.name: _bone_side(armature, b, height, humanoid) for b in armature.data.bones if b.use_deform}
    orphans = sorted({g.name for obj in objects for g in obj.vertex_groups if g.name not in armature.data.bones})
    if orphans:
        info["vertex_groups_without_bones"] = orphans[:10]
    margin = 0.04 * height
    unweighted, over_four, lost, cross, cross_examples, unweighted_examples = 0, 0, 0, 0, [], []
    for obj in objects:
        groups = {g.index: g.name for g in obj.vertex_groups}
        for vertex in obj.data.vertices:
            weights = [(groups[g.group], g.weight) for g in vertex.groups if groups.get(g.group) in deform and g.weight > 0.0]
            total = sum(w for _, w in weights)
            location = obj.matrix_world @ vertex.co
            if total < 1e-6:
                unweighted += 1
                if len(unweighted_examples) < MAX_EXAMPLES:
                    unweighted_examples.append({"object": obj.name, "vertex": vertex.index, "at": _round(location)})
                continue
            if sum(1 for _, w in weights if w / total >= 0.01) > 4:
                over_four += 1
                # Unity keeps the four strongest. What the rest carried is how far the vertex moves from where the review saw it.
                if sum(sorted((w for _, w in weights), reverse=True)[4:]) / total > 0.1:
                    lost += 1
            if abs(location.x) > margin:
                wrong = "R" if location.x > 0 else "L"
                share = sum(w for b, w in weights if deform[b] == wrong) / total
                if share >= 0.05:
                    cross += 1
                    if len(cross_examples) < MAX_EXAMPLES:
                        cross_examples.append({"object": obj.name, "vertex": vertex.index, "at": _round(location), "opposite_side_weight": round(share, 2)})
    if unweighted:
        issues["unweighted_vertices"] = unweighted
        examples["unweighted_vertices"] = unweighted_examples
    if lost:
        issues["over_four_influences"] = lost
    if over_four:
        info["vertices_over_four_influences"] = over_four
    if cross:
        issues["opposite_side_weights"] = cross
        examples["opposite_side_weights"] = cross_examples
    return issues, examples, info


def _edge_lengths(parts):
    return [[e.calc_length() for e in part.bm.edges] for part in parts]


def _poses_report(character, armature, roles, humanoid, rest_lengths, floating_at_rest, judge, skip_pairs, groups, see_through, allowed, hidden, height, scale):
    """Bends the rig through the test poses, each judged as the rest pose is. `hidden` loses what a bend uncovers: those faces are
    paid for, and seen."""
    issues, examples, info = {}, {}, {}
    poses = rig.test_poses(roles) if humanoid else rig.creature_poses(armature, roles)
    chosen = _setting("POSES", True)
    if isinstance(chosen, (list, tuple)):
        poses = {name: steps for name, steps in poses.items() if name in chosen}
    pose_roles = roles if humanoid else rig.identity_roles(armature)
    stretched_total, poke_total, opened_total, inside_total, still = {}, {}, {}, {}, []
    lowest = _setting("LOWEST_VIEW", 0)
    two_sided = set(_setting("TWO_SIDED", []))
    rest_tails = {b.name: armature.matrix_world @ b.tail_local for b in armature.data.bones}
    judge.judge_layers = humanoid  # an animal's bends are a guess at how it moves: its clips judge how layers follow
    with rig.PoseState(armature, mute_constraints=True) as state:
        for name, steps in poses.items():
            state.reset()
            rig.apply_pose(armature, pose_roles, steps)
            moved = max(((armature.matrix_world @ armature.pose.bones[b].tail) - rest_tails[b]).length for b in rest_tails)
            if moved < 0.01 * height:
                still.append(name)
            parts = character.gather()
            try:
                sight_for = _sights(parts, groups, see_through, height)
                judge.head = next((p for p in parts if p.name == judge.skull), None)
                pokes, brushing, between = rig.pose_pokes(parts, judge, sight_for, skip_pairs)
                for poke in pokes:
                    poke_total[f"{name}: {poke['label']}"] = poke["count"]
                    if len(examples.get("poke_through_in_poses", [])) < MAX_EXAMPLES:
                        examples.setdefault("poke_through_in_poses", []).append({"pose": name, "what": poke["why"], "at": _round(poke["at"])})
                shown = [p for p in _without_variants(parts, groups) if p.owner not in see_through]
                pair_names = {(parts[i].name, parts[j].name) for i, j in between}
                opened = sorted(p.name for p in rig.apart_from_body(shown, pair_names, scale, enclosed=False) if p.name not in floating_at_rest and p.owner not in _setting("ALLOW_FLOATING", ()))
                if opened:
                    opened_total[name] = opened
                if brushing:
                    info.setdefault("self_contact_in_poses", {})[name] = brushing
                together = [p for p in _without_variants(parts, groups) if p.owner not in see_through]
                sight = rig.Sight(together, height)
                for part in together:
                    edges = [] if part.owner in two_sided else rig.see_inside(part, sight, lowest)
                    if edges:
                        inside_total[f"{name}: {part.owner}"] = inside_total.get(f"{name}: {part.owner}", 0) + len(edges)
                        if len(examples.get("see_inside_in_poses", [])) < MAX_EXAMPLES:
                            edge = part.bm.edges[edges[0]]
                            examples.setdefault("see_inside_in_poses", []).append({"pose": name, "object": part.owner, "at": _round((edge.verts[0].co + edge.verts[1].co) / 2)})
                if hidden:
                    now = rig.hidden_faces(_without_variants(parts, groups), see_through, 0.2 * height, allowed, among=hidden)
                    for key in [key for key in hidden if key not in now]:
                        del hidden[key]
                for part, lengths in zip(parts, rest_lengths):
                    bad = []
                    for edge, rest_length in zip(part.bm.edges, lengths):
                        if rest_length > 1e-6:
                            length = edge.calc_length()
                            ratio = length / rest_length
                            # Creases fold hard in deep poses; below a fifth the surface collapses. A small edge can do either
                            # where a joint folds and nobody sees it: what shows is how far the surface moved.
                            if (ratio > 2.0 and length - rest_length >= 0.06 * scale) or (ratio < 0.2 and rest_length - length >= 0.03 * scale):
                                bad.append((abs(math.log(ratio)), edge, ratio))
                    if bad:
                        stretched_total[f"{name}: {part.name}"] = len(bad)
                        _, worst, ratio = max(bad, key=lambda b: b[0])
                        if len(examples.get("stretched_in_poses", [])) < MAX_EXAMPLES:
                            examples.setdefault("stretched_in_poses", []).append(
                                {"pose": name, "object": part.owner, "edge": worst.index, "length_ratio": round(ratio, 2),
                                 "at": _round((worst.verts[0].co + worst.verts[1].co) / 2)})
            finally:
                rig.free(parts)
    info["poses_checked"] = [name for name in poses if name not in still]
    if poses and len(still) == len(poses):
        issues["poses_moved_nothing"] = still
    if poke_total:
        issues["poke_through_in_poses"] = poke_total
    if opened_total:
        issues["joint_opens_in_poses"] = opened_total
    if inside_total:
        issues["see_inside_in_poses"] = inside_total
    if stretched_total:
        issues["stretched_in_poses"] = stretched_total
    return issues, examples, info


SURFACE_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}


def _is_attached(obj, armature):
    """A rigid part that hangs from the armature or one of its bones, directly or through another part, which the rigging reference
    allows."""
    if armature is None:
        return False
    parent = obj.parent
    while parent is not None:
        if parent is armature:
            return True
        parent = parent.parent
    return False


def _targets():
    names = _setting("TARGETS", None)
    if names:
        missing = [n for n in names if n not in bpy.data.objects]
        if missing:
            raise ValueError(f"TARGETS not found: {missing}")
        return [bpy.data.objects[n] for n in names if bpy.data.objects[n].type in SURFACE_TYPES]
    armature_name = _setting("ARMATURE", None)
    if armature_name:
        armature = bpy.data.objects[armature_name]
        return [o for o in bpy.context.scene.objects if o.type in SURFACE_TYPES and (rig.deforming_armature(o) is armature or _is_attached(o, armature))]
    selected = [o for o in bpy.context.selected_objects if o.type in SURFACE_TYPES]
    return selected


def _creature_legs(body, armature, roles, bottom, joined_ok):
    """The legs of one skin stay apart near the ground, on any number of them: as many separate sections as legs."""
    chains = rig.leg_chains(armature, roles)
    if len(chains) < 2 or joined_ok:
        return {}, {}, {}
    lengths = [sum(rig.limb_length(armature, b.name) for b in chain) for chain in chains]
    level = bottom + 0.35 * min(lengths)
    sections = _islands(body, level)
    info = {"legs": len(chains)}
    if len(sections) < len(chains):
        return {"fused_legs": f"{len(chains)} legs, and {len(sections)} separate sections at {level:.3f} m"}, {"fused_legs": [{"z": round(level, 3)}]}, info
    return {}, {}, info


def _parts_checked(folder, name, height, triangles, objects):
    """Whether the parts' own receipt exists, passed, and is of this character: the very parts the cut tool cut, or, cut some other way,
    as tall, with at least the faces it has now. A cut takes faces away and leaves the rest as they are; anything else is another
    character, and its parts need their own run."""
    path = os.path.join(folder, f"inspect_character-{name}-parts.json") if folder else None
    if not path or not os.path.exists(path):
        return False
    with open(path) as receipt:
        found = json.load(receipt)
    if found.get("passed") is not True:
        return False
    cut_from = {o.get("cut_hidden_faces") for o in objects} - {None}
    if cut_from:
        return found.get("geometry") in cut_from
    info = found.get("info", {})
    same_size = abs(info.get("height_m", 0.0) - height) <= max(0.002, 0.01 * height)
    return same_size and info.get("triangles", 0) >= triangles


def inspect():
    objects = _targets()
    if not objects:
        return {"passed": False, "issues": {"no_targets": "no objects with a surface to check"}, "examples": {}, "info": {}}
    armature_name = _setting("ARMATURE", None)
    armature = bpy.data.objects[armature_name] if armature_name else next(
        (a for a in (rig.deforming_armature(o) for o in objects) if a), None)
    if armature is None:
        armature = next((p for p in (o.parent for o in objects) if p is not None and p.type == "ARMATURE"), None)
    see_through = set(_setting("SEE_THROUGH", []))
    allowed = set(_setting("ALLOW_HIDDEN", []))
    groups = _setting("PART_GROUPS", {})
    group_of = _group_of(groups)
    never_together = set(_setting("NEVER_TOGETHER", []))
    allow_crossing = set(_setting("ALLOW_CROSSING", []))
    two_sided = set(_setting("TWO_SIDED", []))
    whole_parts = _setting("WHOLE_PARTS", False)
    ground = _setting("GROUND", 0.0)
    folder = _setting("PROOF_DIR", None)
    proof_name = _setting("PROOF_NAME", None) or objects[0].name
    issues, examples, info = {}, {}, {}

    saved_position = armature.data.pose_position if armature else None
    if armature:
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
    character = rig.Character(objects, armature, see_through)
    parts = character.gather()
    if not parts:
        return {"passed": False, "issues": {"no_targets": "the targets have no faces"}, "examples": {}, "info": {}}
    owners = {p.owner for p in parts}
    humanoid = False
    roles = {}
    joints = judge = None
    seam_names, reported_pairs, floating_at_rest = set(), set(), set()
    try:
        zs = [v.co.z for part in parts for v in part.bm.verts]
        xs = [v.co.x for part in parts for v in part.bm.verts]
        bottom, top = min(zs), max(zs)
        height = top - bottom
        info["height_m"] = round(height, 3)
        roles = rig.map_roles(armature, _setting("BONE_MAP", {})) if armature else {}
        forced = _setting("HUMANOID", None)
        humanoid = armature is not None and (forced if forced is not None else rig.is_humanoid(armature, roles))
        info["body_plan"] = "no rig" if armature is None else "humanoid" if humanoid else "creature"
        # What a defect is measured against: the body, not a 6 m pole it carries.
        scale = height
        deform = [b for b in armature.data.bones if b.use_deform] if armature else []
        if deform:
            ends = [rig.head(armature, b.name).z for b in deform] + [rig.tail(armature, b.name).z for b in deform]
            scale = min(height, max(max(ends) - min(ends), 0.2 * height))
        info["scale_m"] = round(scale, 3)
        # What has no legs may swim or fly.
        legs_here = rig.leg_chains(armature, roles) if armature else []
        stands = ground is not None and (armature is None or humanoid or bool(legs_here) or not any(b.children for b in armature.data.bones))
        if stands and abs(bottom - ground) > (0.01 if humanoid else 0.03) * scale:
            issues["not_on_ground"] = f"the lowest point is at z = {bottom:.3f} m, not {ground}"
        symmetric = [bpy.data.objects[n] for n in _setting("SYMMETRIC", []) if n in bpy.data.objects]
        sided = armature is not None and any(rig.name_side(b.name) for b in armature.data.bones)
        if armature is not None and not symmetric and deform:
            # What it holds in a hand doesn't move its center: the root bone is where it stands. A body with no sides, such as a
            # coiled snake, has no center line to hold to.
            middle = rig.head(armature, max((b for b in armature.data.bones if b.parent is None), key=lambda b: len(b.children_recursive)).name).x if sided else 0.0
        else:
            center_x = [(obj.matrix_world @ Vector(c)).x for obj in (symmetric or objects) for c in obj.bound_box]
            middle = (min(center_x) + max(center_x)) / 2
        if abs(middle) > max(0.005 * scale, 1e-4):
            issues["off_center"] = f"the body's center is at x = {middle:.3f} m, not 0"
        info["width_m"] = round(max(xs) - min(xs), 3)

        opaque = [p for p in parts if p.owner not in see_through]
        fixed = [p for p in opaque if p.owner not in group_of]
        # A body of one skin, or one built from parts.
        spanning = [p for p in (fixed or opaque) if p.lowest < bottom + 0.1 * height and p.highest > bottom + 0.9 * height]
        named = [p for p in parts if p.owner == _setting("BODY", None)]
        body = max(named or spanning or fixed or parts, key=lambda p: len(p.bm.faces))
        one_skin = bool(named or spanning)
        info["body"] = body.owner if one_skin else "built from parts"
        body_owner = body.owner
        joined_ok = _setting("LEGS_JOINED", False)
        # Parts can't fuse: if they cut each other, the judgement below says so. One skin shows it in its sections.
        if armature is not None and one_skin:
            found = _legs([body], bottom, height, roles, armature, joined_ok) if humanoid else _creature_legs(body, armature, roles, bottom, joined_ok)
            issues.update(found[0])
            examples.update(found[1])
            info.update(found[2])
        # A swollen waist is what organic bodies get wrong; a toy's torso is what it is designed to be.
        if humanoid and one_skin:
            found = _torso(body, opaque, armature, roles, _setting("WAIST_BULGE", False))
            issues.update(found[0])
            examples.update(found[1])
            info.update(found[2])

        # The surfaces: what crosses, and which of that the player can see go wrong.
        joints = rig.Joints(armature, parts, roles)
        skip = _skipper(groups, never_together, allow_crossing)
        skull, highest, head_level = _head_top(parts, body, armature, roles, group_of)
        head_name = rig.head_bone(armature, roles) if armature else None
        tops = _tops(parts, skull, highest, height, head_name, see_through, armature.data.bones if armature and head_name else None)
        info["covers_from_above"] = sorted({p.owner for p in tops})
        if armature is not None and head_name:
            on_head = {head_name} | {b.name for b in armature.data.bones[head_name].children_recursive}
            astray = sorted({p.owner for p in tops if not p.bones & on_head})
            if astray:
                issues["top_not_on_head"] = {name: "it covers the head and doesn't move with it" for name in astray}
        within, between = rig.crossings(parts)
        sight_for = _sights(parts, groups, see_through, height)
        judge = rig.Judge(joints, scale, [p.name for p in tops], skull.name if skull else None, see_through, skip)
        judge.skull_owner = skull.owner if skull else None
        judge.head = skull
        # A cut where parts cross leaves pieces no check can tell from a button: the whole parts' receipt is the proof there.
        seams = set()
        if not whole_parts:
            seams = {(i, j) for (i, j) in between if not skip(parts[i], parts[j]) and parts[i].owner not in see_through and parts[j].owner not in see_through
                     and (rig.open_edges_inside(parts[i], parts[j]) or rig.open_edges_inside(parts[j], parts[i]))}
            seam_names = {(parts[i].name, parts[j].name) for i, j in seams}
            if seams:
                info["open_where_parts_cross"] = sorted(f"{x}/{y}" for x, y in seam_names)[:10]
                # A model that came cut from its maker has no whole parts to check. This project's cuts are marked by the tool, and
                # a receipt of whole parts says they exist.
                ours = any(o.get("cut_hidden_faces") for o in objects) or (folder and os.path.exists(os.path.join(folder, f"inspect_character-{proof_name}-parts.json")))
                if ours and not _parts_checked(folder, proof_name, height, sum(len(f.verts) - 2 for part in parts for f in part.bm.faces), objects):
                    issues["parts_not_checked_before_cut"] = (f"{len(seams)} crossings have open edges inside the other part, as after hidden faces are cut: "
                                                              "run this check on the whole parts too, with WHOLE_PARTS = True and the same PROOF_DIR and PROOF_NAME")
        pokes, rest_joints = rig.judge_rest(parts, between, judge, sight_for, seams)
        reported_pairs = {(poke["a"].name, poke["b"].name) for poke in pokes}
        cuts, cut_examples = {}, []
        for i, pairs in within.items():
            surface = parts[i]
            if surface.owner in see_through:
                continue
            sight = sight_for(surface, surface)
            for ring in rig.rings_of(surface, surface, pairs, judge.tolerance):
                points = [p for p in ring.points if sight.visible(p)]
                if points and rig.extent(ring.points) >= judge.graze and not rig.folds_on_itself(surface, ring, judge):
                    cuts[surface.owner] = cuts.get(surface.owner, 0) + len(ring.details)
                    cut_examples.append({"object": surface.owner, "what": "the surface cuts into itself", "at": _round(points[0])})
        between_report, clashes = {}, {}
        for poke in pokes:
            a, b = poke["a"], poke["b"]
            cut_examples.append({"objects": [a.name, b.name], "what": poke["why"], "at": _round(poke["at"])})
            if a.owner in group_of or b.owner in group_of:
                clashes[f"{a.name}/{b.name}"] = poke["count"]
            elif a.owner == b.owner:
                cuts[a.owner] = cuts.get(a.owner, 0) + poke["count"]
            else:
                between_report[f"{a.name}/{b.name}"] = poke["count"]
        if cuts:
            issues["self_intersections"] = cuts
        if between_report:
            issues["parts_intersect"] = between_report
        if clashes:
            issues["variants_clash"] = clashes
        if cut_examples:
            examples["intersections"] = cut_examples[:MAX_EXAMPLES]
        info["joints_between_parts"] = len(rest_joints)
        if allow_crossing:
            info["allowed_crossings"] = sorted(allow_crossing)

        if groups:
            info["variant_pairs_checked"] = sum(len(a) * len(b) for i, a in enumerate(groups.values()) for b in list(groups.values())[i + 1:])
            swallowed = _variant_coverage(parts, groups, see_through, allowed, never_together)
            if swallowed:
                issues["variant_swallowed"] = swallowed
            info["variant_groups"] = groups
            info["never_together"] = list(never_together)
        level = head_level if head_level is not None else bottom
        # From above, what matters is the top of the head: its sides may stand wider than what sits on it.
        crown_level = max(level, highest.z - 0.25 * (highest.z - level) * 2.0) if highest is not None else level
        through, inside_out, through_examples = _shows_through(parts, tops, groups, never_together, allow_crossing, skull, crown_level, height, scale, see_through, judge)
        if through:
            issues["shows_through_from_above"] = through
            examples["shows_through"] = through_examples
        if inside_out:
            issues["inside_out"] = inside_out
        openings = _open_parts(tops, level, sight_for(parts[0], parts[0]))
        if openings:
            issues["open_part"] = openings

        # Parts hanging in the air. Only what is on screen together counts: a variant holds nothing up.
        pair_names = {(parts[i].name, parts[j].name) for i, j in between}
        allow_floating = set(_setting("ALLOW_FLOATING", []))
        floating, floating_examples = {}, []
        for together in rig.appearing_together(parts, groups, never_together):
            shown = [p for p in together if p.owner not in see_through]
            for part in rig.apart_from_body(shown, pair_names, scale):
                if part.owner not in allow_floating and part.name not in floating:
                    held = [p for p in shown if p is not part]
                    floating[part.name] = f"{min(rig.distance_between(part, other, 0.0) for other in held) * 100:.1f} cm from anything"
                    floating_examples.append({"object": part.owner, "at": _round(part.bm.verts[0].co)})
        if floating:
            issues["floating_part"] = floating
            examples["floating_part"] = floating_examples[:MAX_EXAMPLES]
        floating_at_rest = set(floating)

        # A foot in the air: the lowest point alone doesn't show it.
        if armature is not None and ground is not None:
            feet = {}
            for chain in legs_here:
                names = {b.name for bone in chain for b in [bone] + list(bone.children_recursive)}
                points = [v.co.z for part in fixed for f in part.bm.faces if part.face_bone[f.index] in names for v in f.verts]
                if points:
                    feet[chain[-1].name] = min(points) - ground
            # With no foot on the ground, the whole body is off it, which the lowest point tells.
            if feet and min(feet.values()) <= 0.02 * scale:
                hovering = {name: f"{lift * 100:.1f} cm above the ground" for name, lift in feet.items() if lift > 0.02 * scale}
                if hovering:
                    issues["foot_off_ground"] = hovering

        # An opening that shows the inside, with each set of parts that can be on screen at once.
        lowest = _setting("LOWEST_VIEW", 0)
        inside_edges, inside_examples, checked = {}, [], set()
        for together in rig.appearing_together(parts, groups, never_together):
            shown = [p for p in together if p.owner not in see_through]
            sight = rig.Sight(shown, height)
            for part in shown:
                if part.owner in two_sided:
                    continue
                for edge_index in rig.see_inside(part, sight, lowest):
                    if (part.name, edge_index) in checked:
                        continue
                    checked.add((part.name, edge_index))
                    inside_edges[part.owner] = inside_edges.get(part.owner, 0) + 1
                    if len(inside_examples) < MAX_EXAMPLES:
                        edge = part.bm.edges[edge_index]
                        inside_examples.append({"object": part.owner, "at": _round((edge.verts[0].co + edge.verts[1].co) / 2)})
        if inside_edges:
            issues["see_inside"] = inside_edges
            examples["see_inside"] = inside_examples

        # What stays hidden costs triangles the player never sees. Variants can't cover each other: only what appears together
        # can hide a face. The poses below clear what a bend uncovers.
        owner_of = {p.name: p.owner for p in parts}
        hidden = rig.hidden_faces(_without_variants(parts, groups), see_through, 0.2 * height, allowed)
        by_name = {p.name: p for p in parts}
        hidden_at = {key: _round(by_name[key[0]].bm.faces[key[1]].calc_center_median()) for key in list(hidden)[:200]}

        asymmetric, asymmetry_examples = _asymmetry([p for p in parts if p.owner in {o.name for o in symmetric}], height)
        if asymmetric:
            issues["asymmetric"] = asymmetric
            examples["asymmetric"] = asymmetry_examples

        info["triangles"] = sum(len(f.verts) - 2 for part in parts for f in part.bm.faces)
        rest_lengths = _edge_lengths(parts)
    finally:
        rig.free(parts)
        if armature:
            armature.data.pose_position = saved_position
            bpy.context.view_layer.update()

    for obj in objects:
        if not _applied(obj) and obj.parent is None:
            issues.setdefault("transforms_not_applied", []).append(obj.name)

    # Whatever is on the rig is part of the character: a hat left out of TARGETS was never checked.
    if armature:
        left_out = [o.name for o in bpy.context.scene.objects if o.type in SURFACE_TYPES and o not in objects
                    and (rig.deforming_armature(o) is armature or _is_attached(o, armature))]
        if left_out:
            issues["parts_left_out"] = left_out

    if armature:
        found = _rig_report(armature, roles, height, _setting("FINGERS", None)) if humanoid else _creature_rig_report(armature, roles, height)
        issues.update(found[0])
        examples.update(found[1])
        info.update(found[2])
        deformed = [o for o in objects if rig.deforming_armature(o) is armature]
        not_deformed = [o.name for o in objects if o not in deformed and not _is_attached(o, armature) and o.name in owners]
        if not_deformed:
            issues["not_skinned"] = not_deformed
        found = _weights_report(deformed, armature, height, humanoid)
        issues.update(found[0])
        examples.update(found[1])
        info.update(found[2])
        if _setting("POSES", True) and (not humanoid or not [r for r in rig.REQUIRED if r not in roles]):
            found = _poses_report(character, armature, roles, humanoid, rest_lengths, floating_at_rest, judge, seam_names | reported_pairs, groups, see_through, allowed, hidden, height, scale)
            issues.update(found[0])
            examples.update(found[1])
            info.update(found[2])
    else:
        info["rig"] = "no armature deforms the targets: rig checks skipped"

    inside_faces, sunk, covered = {}, {}, {}
    for (surface, _), cover in hidden.items():
        owner, cover_owner = owner_of[surface], owner_of[cover]
        if owner == cover_owner:
            inside_faces[owner] = inside_faces.get(owner, 0) + 1
        elif cover_owner == body_owner:
            sunk[f"{owner}<{cover_owner}"] = sunk.get(f"{owner}<{cover_owner}", 0) + 1
        else:
            covered[f"{owner}<{cover_owner}"] = covered.get(f"{owner}<{cover_owner}", 0) + 1
    # Nobody sees it: what it costs is the defect, and a mouth's few hidden faces cost nothing. Most of an object buried in the body
    # is another matter: the player doesn't get what it was made to show.
    worth_cutting = len(hidden) >= max(20, 0.05 * sum(len(p.vertices) - 2 for o in objects if o.type == "MESH" for p in o.data.polygons))
    faces_of = {o.name: max(1, len(o.data.polygons)) for o in objects if o.type == "MESH"}
    buried = any(sum(count for pair, count in sunk.items() if pair.split("<")[0] == owner) >= 0.3 * total for owner, total in faces_of.items())
    worth_cutting = worth_cutting or buried
    hidden_bucket = info if whole_parts or not worth_cutting else issues
    if hidden and not whole_parts:
        kept = [key for key in hidden if key in hidden_at][:MAX_EXAMPLES]
        if kept:
            examples["hidden"] = [{"object": owner_of[key[0]], "covered_by": owner_of[hidden[key]], "at": hidden_at[key]} for key in kept]
    if inside_faces:
        hidden_bucket["hidden_inside"] = inside_faces
    if sunk:
        hidden_bucket["sunk_into_body"] = sunk
    if covered:
        (hidden_bucket if _setting("SINGLE_LAYER", True) else info)["covered_faces"] = covered
    if hidden and not worth_cutting:
        examples.pop("hidden", None)

    report = {"passed": not issues, "issues": issues, "examples": examples, "info": info}
    if folder:
        os.makedirs(folder, exist_ok=True)
        keys = ("TARGETS", "ALLOW_HIDDEN", "ALLOW_CROSSING", "ALLOW_FLOATING", "SEE_THROUGH", "TWO_SIDED", "COVERS_FROM_ABOVE", "OPEN_ON_TOP", "NEVER_TOGETHER", "POSES", "LEGS_JOINED", "WAIST_BULGE", "SINGLE_LAYER", "HUMANOID", "WHOLE_PARTS", "GROUND", "LOWEST_VIEW")
        settings = {key: _setting(key, None) for key in keys if key in globals()}
        suffix = "-parts" if whole_parts else ""
        if whole_parts:
            report_out = dict(report, settings=settings, geometry=rig.geometry_key(objects))
        else:
            report_out = dict(report, settings=settings)
        with open(os.path.join(folder, f"inspect_character-{proof_name}{suffix}.json"), "w") as out:
            json.dump(report_out, out, indent=1, default=str)
    return report


result = inspect()
