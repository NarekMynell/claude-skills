"""Checks a game character: anatomy, covered and intersecting surfaces, symmetry, rig and skin weights, in the rest
pose and in deformation test poses.

Run it as the game-assets guide's "Running the scripts" describes. Settings, all optional:
    TARGETS = ["Body", "Hair"]   the character's mesh objects; default: the meshes ARMATURE deforms, else the selection
    ARMATURE = "Rig"             default: the armature deforming the targets
    BODY = "Body"                the skin mesh; default: the largest target that spans head to feet
    SINGLE_LAYER = True          a face covered by another part is a defect; False when outfits swap
    ALLOW_HIDDEN = ["Eyes", "Body<Hair"]  covered faces that are intended: a whole object, or "Object<Cover"
    SEE_THROUGH = ["HairCards"]  objects with transparent parts: they cover nothing
    SYMMETRIC = ["Body"]         objects that must mirror across X = 0
    LEGS_JOINED = False          True for a long robe or dress that joins the legs on purpose
    WAIST_BULGE = False          True for a body that is widest at the waist on purpose
    FINGERS = 5                  fingers per hand in the design; 0 for mittens or no finger bones
    POSES = True                 also check the test poses (needs the armature)
    BONE_MAP = {}                Unity Humanoid role -> bone name, for names the script doesn't recognize

Sets `result`: `passed`, `issues` (name -> count or detail), `examples` (name -> up to 3 cases with world locations
in metres) and `info` (measurements). The scene is left as it was.
"""

import math
import os
import types

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

MAX_EXAMPLES = 3


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


class Part:
    """One mesh object, evaluated (modifiers and pose applied) in world space."""

    def __init__(self, obj):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        self.bm = bmesh.new()
        self.bm.from_mesh(mesh)
        evaluated.to_mesh_clear()
        self.bm.transform(obj.matrix_world)
        self.bm.normal_update()
        for sequence in (self.bm.verts, self.bm.edges, self.bm.faces):
            sequence.ensure_lookup_table()
            sequence.index_update()
        self.name = obj.name
        self.tree = BVHTree.FromBMesh(self.bm)

    def free(self):
        self.bm.free()


def _gather(objects):
    return [Part(obj) for obj in objects]


def _free(parts):
    for part in parts:
        part.free()


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
    """Follows both legs up from the feet until they join. Returns issues, examples, info."""
    issues, examples, info = {}, {}, {}
    margin = 0.002
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
    if gap is not None and gap < 0.002:
        issues["legs_touching"] = f"the legs come within {gap * 1000:.1f} mm of each other below the crotch"
    return issues, examples, info


def _torso(body, parts, armature, roles, bulge_ok):
    """Width and depth of the torso between the hip joints and the lower chest: the body's own surface, or the parts
    covering it where the body has none (faces deleted under clothes)."""
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
            center = [c for c in _clusters(parts, z, 0.002) if c["box"][0] <= 0.0 <= c["box"][1]]
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


def _face_center(part, index):
    return part.bm.faces[index].calc_center_median()


def _intersections(parts):
    """Face pairs that cut through each other, within a part and between parts."""
    within, between, examples = {}, {}, []
    for i, part in enumerate(parts):
        faces = part.bm.faces
        # Faces that share a vertex only touch there; a fold through a neighbor shows in the renders.
        pairs = {tuple(sorted(p)) for p in part.tree.overlap(part.tree)
                 if p[0] != p[1] and not {v.index for v in faces[p[0]].verts} & {v.index for v in faces[p[1]].verts}}
        if pairs:
            within[part.name] = len(pairs)
            a, b = next(iter(pairs))
            examples.append({"object": part.name, "faces": [a, b], "at": _round((_face_center(part, a) + _face_center(part, b)) / 2)})
        for other in parts[i + 1:]:
            pairs = part.tree.overlap(other.tree)
            if pairs:
                between[f"{part.name}/{other.name}"] = len(pairs)
                a, b = pairs[0]
                examples.append({"objects": [part.name, other.name], "faces": [a, b],
                                 "at": _round((_face_center(part, a) + _face_center(other, b)) / 2)})
    return within, between, examples


def _hidden_faces(parts, height, see_through, allowed):
    """Faces whose outward directions all run into the back of a surface: they sit inside or under it.
    Returns {(object, cover): count} and examples."""
    occluders = [p for p in parts if p.name not in see_through]
    reach = 0.2 * height
    counts, examples = {}, []
    for part in parts:
        if part.name in allowed:
            continue
        hidden = 0
        for face in part.bm.faces:
            normal = face.normal
            if normal.length < 0.5:
                continue
            tangent = normal.orthogonal().normalized()
            bitangent = normal.cross(tangent)
            origin = face.calc_center_median() + normal * 1e-5
            directions = [normal] + [(normal + axis * 0.84).normalized() for axis in (tangent, -tangent, bitangent, -bitangent)]
            cover = None
            for direction in directions:
                hit = None
                for occluder in occluders:
                    location, hit_normal, index, distance = occluder.tree.ray_cast(origin, direction, reach)
                    if location is None or (occluder is part and index == face.index):
                        continue
                    if hit is None or distance < hit[0]:
                        hit = (distance, hit_normal, occluder.name)
                if hit is None or hit[1].dot(direction) <= 0.0:
                    cover = None
                    break
                cover = cover or hit[2]
            if cover is None or f"{part.name}<{cover}" in allowed:
                continue
            counts[(part.name, cover)] = counts.get((part.name, cover), 0) + 1
            if len(examples) < MAX_EXAMPLES:
                examples.append({"object": part.name, "face": face.index, "covered_by": cover, "at": _round(face.calc_center_median())})
    return counts, examples


def _asymmetry(parts, height):
    """Distance from each vertex's mirror image across X = 0 to the nearest vertex, per part."""
    report, examples = {}, []
    for part in parts:
        coords = [v.co.copy() for v in part.bm.verts]
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
            report[part.name] = f"5% of vertices are over {p95 * 1000:.1f} mm from their mirror image"
            examples.append({"object": part.name, "at": _round(max(distances, key=lambda d: d[0])[1])})
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


def _rig_report(armature, roles, height, fingers):
    issues, examples, info = {}, {}, {}
    missing = [r for r in rig.REQUIRED if r not in roles]
    if missing:
        issues["missing_humanoid_bones"] = missing
    if not _applied(armature):
        issues["armature_transform_not_applied"] = True
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
        if foot and toes:
            direction = rig.head(armature, toes) - rig.head(armature, foot)
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
        if fingers and len(found) != fingers:
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
    info["deform_bones"] = sum(1 for b in armature.data.bones if b.use_deform)
    info["roles_mapped"] = len(roles)
    return issues, examples, info


def _hand_mirrored(armature, roles, side):
    """Whether a hand is the other side's mirror image, whatever way the palm faces: the fingers curl toward the
    palm, and on a left hand (along x across) points to the palm when 'across' runs from the little finger to the
    index. None when the fingers are too straight to tell the palm side."""
    hand, index, little = roles.get(f"{side}Hand"), roles.get(f"{side}IndexProximal"), roles.get(f"{side}LittleProximal") or roles.get(f"{side}RingProximal")
    middle = roles.get(f"{side}MiddleProximal") or index
    if not (hand and index and little):
        return None
    along = (rig.head(armature, middle) - rig.head(armature, hand)).normalized()
    across = rig.head(armature, index) - rig.head(armature, little)
    curl, length = Vector(), 0.0
    for finger in ("Index", "Middle", "Ring", "Little"):
        base, tip = roles.get(f"{side}{finger}Proximal"), roles.get(f"{side}{finger}Distal")
        if base and tip:
            reach = rig.tail(armature, tip) - rig.head(armature, base)
            curl += reach - along * reach.dot(along)
            length += reach.length
    if length == 0.0 or curl.length < 0.03 * length:
        return None
    toward_palm = along.cross(across).dot(curl)
    return toward_palm < 0 if side == "Left" else toward_palm > 0


def _bone_side(bone, height):
    side = rig.name_side(bone.name)
    if side:
        return side
    x = bone.head_local.x
    return "L" if x > 0.01 * height else "R" if x < -0.01 * height else None


def _weights_report(objects, armature, height):
    issues, examples, info = {}, {}, {}
    deform = {b.name: _bone_side(b, height) for b in armature.data.bones if b.use_deform}
    orphans = sorted({g.name for obj in objects for g in obj.vertex_groups if g.name not in armature.data.bones})
    if orphans:
        info["vertex_groups_without_bones"] = orphans[:10]
    margin = 0.04 * height
    unweighted, over_four, cross, cross_examples, unweighted_examples = 0, 0, 0, [], []
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
    if over_four:
        issues["over_four_influences"] = over_four
    if cross:
        issues["opposite_side_weights"] = cross
        examples["opposite_side_weights"] = cross_examples
    return issues, examples, info


def _edge_lengths(parts):
    return [[e.calc_length() for e in part.bm.edges] for part in parts]


def _poses_report(objects, armature, roles, rest_lengths, rest_between):
    issues, examples, info = {}, {}, {}
    poses = rig.test_poses(roles)
    stretched_total, poke_total = {}, {}
    with rig.PoseState(armature) as state:
        for name, steps in poses.items():
            state.reset()
            rig.apply_pose(armature, roles, steps)
            parts = _gather(objects)
            try:
                within, between, cut_examples = _intersections(parts)
                for key, count in between.items():
                    if key not in rest_between:
                        poke_total[f"{name}: {key}"] = count
                        examples.setdefault("poke_through_in_poses", []).extend(
                            [dict(e, pose=name) for e in cut_examples if "objects" in e][:1])
                if within:
                    info.setdefault("self_contact_in_poses", {})[name] = within
                for part, lengths in zip(parts, rest_lengths):
                    bad = []
                    for edge, rest in zip(part.bm.edges, lengths):
                        if rest > 1e-6:
                            ratio = edge.calc_length() / rest
                            # Creases fold hard in deep poses; below a fifth the surface collapses.
                            if ratio > 2.0 or ratio < 0.2:
                                bad.append((abs(math.log(ratio)), edge, ratio))
                    if bad:
                        stretched_total[f"{name}: {part.name}"] = len(bad)
                        _, worst, ratio = max(bad, key=lambda b: b[0])
                        if len(examples.get("stretched_in_poses", [])) < MAX_EXAMPLES:
                            examples.setdefault("stretched_in_poses", []).append(
                                {"pose": name, "object": part.name, "edge": worst.index, "length_ratio": round(ratio, 2),
                                 "at": _round((worst.verts[0].co + worst.verts[1].co) / 2)})
            finally:
                _free(parts)
    info["poses_checked"] = list(poses)
    if poke_total:
        issues["poke_through_in_poses"] = poke_total
    if stretched_total:
        issues["stretched_in_poses"] = stretched_total
    return issues, examples, info


# --- Entry point -------------------------------------------------------------------------------------------------------


def _targets():
    names = _setting("TARGETS", None)
    if names:
        missing = [n for n in names if n not in bpy.data.objects]
        if missing:
            raise ValueError(f"TARGETS not found: {missing}")
        return [bpy.data.objects[n] for n in names if bpy.data.objects[n].type == "MESH"]
    armature_name = _setting("ARMATURE", None)
    if armature_name:
        armature = bpy.data.objects[armature_name]
        return [o for o in bpy.context.scene.objects if o.type == "MESH" and rig.deforming_armature(o) is armature]
    selected = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    return selected


def inspect():
    objects = _targets()
    if not objects:
        return {"passed": False, "issues": {"no_targets": "no mesh objects to check"}, "examples": {}, "info": {}}
    armature_name = _setting("ARMATURE", None)
    armature = bpy.data.objects[armature_name] if armature_name else next(
        (a for a in (rig.deforming_armature(o) for o in objects) if a), None)
    see_through = set(_setting("SEE_THROUGH", []))
    allowed = set(_setting("ALLOW_HIDDEN", []))
    issues, examples, info = {}, {}, {}

    saved_position = armature.data.pose_position if armature else None
    if armature:
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
    parts = _gather(objects)
    try:
        zs = [v.co.z for part in parts for v in part.bm.verts]
        xs = [v.co.x for part in parts for v in part.bm.verts]
        bottom, top = min(zs), max(zs)
        height = top - bottom
        info["height_m"] = round(height, 3)
        if abs(bottom) > 0.01:
            issues["not_on_ground"] = f"the lowest point is at z = {bottom:.3f} m, not 0"
        symmetric = [bpy.data.objects[n] for n in _setting("SYMMETRIC", []) if n in bpy.data.objects]
        center_x = [(obj.matrix_world @ Vector(c)).x for obj in (symmetric or objects) for c in obj.bound_box]
        middle = (min(center_x) + max(center_x)) / 2
        if abs(middle) > max(0.01, 0.005 * height):
            issues["off_center"] = f"the body's center is at x = {middle:.3f} m, not 0"
        info["width_m"] = round(max(xs) - min(xs), 3)

        roles = rig.map_roles(armature, _setting("BONE_MAP", {})) if armature else {}
        opaque = [p for p in parts if p.name not in see_through]
        body_name = _setting("BODY", None)
        if body_name is None:
            spanning = [p for p in parts if min(v.co.z for v in p.bm.verts) < bottom + 0.1 * height
                        and max(v.co.z for v in p.bm.verts) > bottom + 0.9 * height]
            body_name = max(spanning or parts, key=lambda p: len(p.bm.faces)).name
        info["body"] = body_name
        body = next(p for p in parts if p.name == body_name)
        for found in (_legs([body], bottom, height, roles, armature, _setting("LEGS_JOINED", False)),
                      _torso(body, opaque, armature, roles, _setting("WAIST_BULGE", False)) if armature else ({}, {}, {})):
            issues.update(found[0])
            examples.update(found[1])
            info.update(found[2])

        within, between, cut_examples = _intersections(parts)
        if within:
            issues["self_intersections"] = within
        if between:
            issues["parts_intersect"] = between
        if cut_examples:
            examples["intersections"] = cut_examples[:MAX_EXAMPLES]

        hidden, hidden_examples = _hidden_faces(parts, height, see_through, allowed)
        inside = {f"{o}": n for (o, cover), n in hidden.items() if cover == o}
        sunk = {f"{o}<{cover}": n for (o, cover), n in hidden.items() if cover != o and cover == body_name}
        covered = {f"{o}<{cover}": n for (o, cover), n in hidden.items() if cover != o and cover != body_name}
        if inside:
            issues["hidden_inside"] = inside
        if sunk:
            issues["sunk_into_body"] = sunk
        if covered:
            (issues if _setting("SINGLE_LAYER", True) else info)["covered_faces"] = covered
        if hidden_examples:
            examples["hidden"] = hidden_examples

        asymmetric, asymmetry_examples = _asymmetry([p for p in parts if p.name in {o.name for o in symmetric}], height)
        if asymmetric:
            issues["asymmetric"] = asymmetric
            examples["asymmetric"] = asymmetry_examples

        info["triangles"] = sum(len(f.verts) - 2 for part in parts for f in part.bm.faces)
        rest_lengths = _edge_lengths(parts)
    finally:
        _free(parts)
        if armature:
            armature.data.pose_position = saved_position
            bpy.context.view_layer.update()

    for obj in objects:
        if not _applied(obj) and obj.parent is None:
            issues.setdefault("transforms_not_applied", []).append(obj.name)

    if armature:
        found = _rig_report(armature, roles, height, _setting("FINGERS", 5))
        issues.update(found[0])
        examples.update(found[1])
        info.update(found[2])
        deformed = [o for o in objects if rig.deforming_armature(o) is armature]
        not_deformed = [o.name for o in objects if o not in deformed]
        if not_deformed:
            issues["not_skinned"] = not_deformed
        found = _weights_report(deformed, armature, height)
        issues.update(found[0])
        examples.update(found[1])
        info.update(found[2])
        if _setting("POSES", True) and not [r for r in rig.REQUIRED if r not in roles]:
            found = _poses_report(objects, armature, roles, rest_lengths, between)
            issues.update(found[0])
            examples.update(found[1])
            info.update(found[2])
    else:
        info["rig"] = "no armature deforms the targets: rig checks skipped"

    return {"passed": not issues, "issues": issues, "examples": examples, "info": info}


result = inspect()
