"""Checks a character's or animal's animation clips (Blender actions), however the body is built: foot contact and sliding,
the speed the clip needs, the gait and footfall order, signs of robotic motion, arm swing, loop seams, joint pops, what passes
through what (surfaces no joint connects, layers that part at rest and meet in the clip), joints that come apart, and fingers
passing through held props.

Run it as the game-assets guide's "Running the scripts" describes. Settings:
    ARMATURE = "Rig"          required unless exactly one armature is selected
    ACTIONS = ["Walk"]        default: the armature's current action
    MESHES = ["Body", "Hair"]  skinned meshes; default: the meshes ARMATURE deforms, and those parented to it
    BODY = "Body"             the mesh that holds the feet; default: for each foot, the mesh weighted most to its bones
    SEE_THROUGH = ["HairCards"]  objects with transparent parts: they hide nothing, and may cross what they grow from
    PART_GROUPS = {"hat": ["Cap", "SunHat"]}  variants, as in inspect_character.py: only what appears together can cross
    NEVER_TOGETHER = ["HairLong+Cap"]  pairs from different groups that the game never combines
    ALLOW_CROSSING = ["Arrow+Head"]  pairs of objects that cross by design
    TWO_SIDED = ["Cape"]      objects drawn with both sides of their faces: looking at their back is fine
    LOWEST_VIEW = 0           degrees above the horizon: the lowest the camera looks from, for what an opening shows
    PROPS = ["Sword"]         held objects that fingers must touch without entering
    GROUND = 0.0              ground height in metres; None for clips without ground contact (swimming, falling)
    LOOP = True               the clip loops: its last frame must flow into its first
    STEP = 1                  check every Nth frame
    BONE_MAP = {}             Unity Humanoid role -> bone name, for names the script doesn't recognize
    FEET = ["paw.FL", ...]    foot bones, for anything but a Humanoid; default: the Humanoid's feet
    ROOT_BONE = "hips"        the body's root bone, for anything but a Humanoid
    GAIT = "walk"             the gait this clip must be, on four legs: walk, trot, pace or bound
    GAME_SPEED = 1.5          the speed the game moves the character at during this clip, m/s (in the character's size)
    MAX_PLAYBACK_CHANGE = 0.25  how far the playback rate may leave 1 to match GAME_SPEED
    MAX_WALK_FROUDE = 0.5     above this, feet on the ground can't look like a walk: Froude = speed^2 / (9.81 x leg)
    NATURAL = True            checks for robotic motion on clips of living things; False for machines and rigid props
    PROOF_DIR = "/abs/docs/proofs"  writes one receipt per clip, inspect_animation-<PROOF_NAME>-<clip>.json, with the
                              settings it ran with
    PROOF_NAME = "visitor"    default: the armature's name

Sets `result`: `passed` and, per action, `issues` (with frame numbers) and `info`. Restores the action, frame and
pose it found.
"""

import json
import math
import os
import types

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _setting(name, default):
    return globals().get(name, default)


def _load_rig():
    path = _setting("RIG_HELPERS", None) or os.path.join(os.path.dirname(globals()["__file__"]), "rig.py")
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return types.SimpleNamespace(**namespace)


rig = _load_rig()

FINGER_ROLES = tuple(f + s for f in rig.FINGERS for s in rig.SEGMENTS)


def _regions(mesh_object, armature, roles):
    """Each vertex's hand region from its strongest bone: 'L.arm', 'L.fingers' and so on, or None for the rest of the body."""
    by_bone = {}
    for role, bone in roles.items():
        side = "L." if role.startswith("Left") else "R." if role.startswith("Right") else ""
        base = role[4:] if role.startswith("Left") else role[5:] if role.startswith("Right") else role
        if base in FINGER_ROLES:
            by_bone[bone] = side + "fingers"
        elif base in ("LowerArm", "Hand"):
            by_bone[bone] = side + "arm"
    groups = {g.index: g.name for g in mesh_object.vertex_groups}
    vertex_region = []
    for vertex in mesh_object.data.vertices:
        best = max(vertex.groups, key=lambda g: g.weight, default=None)
        vertex_region.append(by_bone.get(groups.get(best.group)) if best else None)
    return vertex_region


def _foot_soles(mesh_object, names):
    """Indices of the lowest vertices weighted mostly to one foot's bones, in the rest shape, and how far their center
    sits above the lowest of them."""
    groups = {g.index for g in mesh_object.vertex_groups if g.name in names}
    candidates = []
    for vertex in mesh_object.data.vertices:
        weight = sum(g.weight for g in vertex.groups if g.group in groups)
        if weight >= 0.5:
            candidates.append(((mesh_object.matrix_world @ vertex.co).z, vertex.index))
    candidates.sort()
    sole = candidates[:12]
    if not sole:
        return [], 0.0
    return [index for _, index in sole], sum(z for z, _ in sole) / len(sole) - sole[0][0]


def _evaluated(mesh_object):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh_object.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    matrix = mesh_object.matrix_world
    coords = [matrix @ v.co for v in mesh.vertices]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return coords, polygons


def _tree(coords, polygons, vertex_region, wanted):
    """BVH of the faces whose vertices are mostly in the wanted regions."""
    faces = []
    for polygon in polygons:
        regions = [vertex_region[v] for v in polygon]
        if max(set(regions), key=regions.count) in wanted:
            faces.append(polygon)
    if not faces:
        return None, []
    return BVHTree.FromPolygons(coords, faces), faces


def _angle(q1, q2):
    dot = abs(q1.dot(q2))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def _frames_text(frames):
    frames = sorted(frames)
    if len(frames) > 6:
        return f"{len(frames)} frames, first {frames[:5]}"
    return f"frames {frames}"


def _foot_weight(mesh_object, bones):
    """How many vertices of a mesh are weighted mostly to these bones: how much of a foot it holds."""
    groups = {g.index for g in mesh_object.vertex_groups if g.name in bones}
    if not groups:
        return 0
    return sum(1 for vertex in mesh_object.data.vertices if sum(g.weight for g in vertex.groups if g.group in groups) >= 0.5)


def _feet(armature, roles):
    """Foot label -> the bones of that foot: the FEET setting, else the Humanoid's two feet."""
    names = _setting("FEET", None)
    if names:
        feet = {}
        for name in names:
            bone = armature.data.bones[name]
            feet[name] = {name} | {child.name for child in bone.children_recursive}
        return feet
    return {side: {roles.get(f"{side}Foot"), roles.get(f"{side}Toes")} - {None}
            for side in ("Left", "Right") if roles.get(f"{side}Foot")}


def _planted_frames(track, limit):
    """Indices of the frames where the sole's center is within `limit` of its lowest height in the clip."""
    lowest = min(center.z for center, _ in track)
    return [i for i, (center, _) in enumerate(track) if center.z < lowest + limit]


def _strike_phases(planted, count):
    """Where in the cycle (0..1) the foot lands: the start of its longest planted run, read cyclically."""
    if not planted or len(planted) == count:
        return None
    marks = set(planted)
    starts = [i for i in planted if (i - 1) % count not in marks]
    best, best_length = None, -1
    for start in starts:
        length, i = 0, start
        while i % count in marks and length < count:
            length, i = length + 1, i + 1
        if length > best_length:
            best, best_length = start, length
    return best / count


def _cyclic_near(a, b, tolerance=0.13):
    difference = abs((a - b) % 1.0)
    return min(difference, 1.0 - difference) <= tolerance


def _classify_quadruped(phases):
    """Gait from when each foot lands. The hind left foot's landing is phase 0."""
    base = phases["hind_left"]
    fore_left = (phases["fore_left"] - base) % 1.0
    hind_right = (phases["hind_right"] - base) % 1.0
    fore_right = (phases["fore_right"] - base) % 1.0
    offsets = {"fore_left": round(fore_left, 2), "hind_right": round(hind_right, 2), "fore_right": round(fore_right, 2)}
    if _cyclic_near(fore_left, 0.25) and _cyclic_near(hind_right, 0.5) and _cyclic_near(fore_right, 0.75):
        return "walk", offsets
    if _cyclic_near(fore_right, 0.0) and _cyclic_near(fore_left, 0.5) and _cyclic_near(hind_right, 0.5):
        return "trot", offsets
    if _cyclic_near(fore_left, 0.0) and _cyclic_near(hind_right, 0.5) and _cyclic_near(fore_right, 0.5):
        return "pace", offsets
    if _cyclic_near(hind_right, 0.0) and _cyclic_near(fore_left, fore_right, 0.1):
        return "bound", offsets
    return "other", offsets


def _leg_sides(armature, feet):
    """For four feet: label -> hind_left, fore_right and so on, from the rest pose (the character faces -Y, its left is +X)."""
    centers = {label: rig.head(armature, next(n for n in names if armature.data.bones[n].parent is None
                                              or armature.data.bones[n].parent.name not in names))
               for label, names in feet.items()}
    middle_y = sum(c.y for c in centers.values()) / 4
    sides = {}
    for label, center in centers.items():
        sides[("fore_" if center.y < middle_y else "hind_") + ("left" if center.x > 0 else "right")] = label
    return sides if len(sides) == 4 else None


def _gait_report(armature, feet, track, frames, issues, info, leg, loop, frame_limit):
    """Duty factor, step timing and footfall order, from when each sole touches down."""
    count = len(frames) - 1 if loop and len(frames) > 2 else len(frames)
    planted = {label: [i for i in _planted_frames(track[label], frame_limit) if i < count] for label in feet}
    duty = [len(p) / count for p in planted.values()]
    if not duty:
        return None
    mean_duty = sum(duty) / len(duty)
    info["duty_factor"] = round(mean_duty, 2)
    phases = {label: _strike_phases(p, count) for label, p in planted.items()}
    if any(phase is None for phase in phases.values()):
        return mean_duty
    if len(feet) == 2:
        first, second = phases.values()
        offset = (second - first) % 1.0
        info["step_offset"] = round(offset, 2)
        if not _cyclic_near(offset, 0.5, 0.1):
            issues["uneven_steps"] = (f"the feet land {offset:.2f} of a cycle apart, not 0.5: a limp, unless the character "
                                      "is meant to limp")
    elif len(feet) == 4:
        sides = _leg_sides(armature, feet)
        if sides:
            gait, offsets = _classify_quadruped({side: phases[label] for side, label in sides.items()})
            info["gait"] = gait
            info["footfall_offsets"] = offsets
            wanted = _setting("GAIT", None)
            if wanted and gait != wanted:
                issues["wrong_gait"] = f"footfalls read as {gait} ({offsets}), the clip should be a {wanted}"
            elif not wanted and gait == "other":
                issues["irregular_footfall"] = (f"the footfalls fit no gait: offsets from the hind left foot are {offsets}; "
                                                "a walk lands hind left, fore left, hind right, fore right at 0, 0.25, 0.5, 0.75")
    return mean_duty


def _range_degrees(quaternions):
    """How far a bone's rotation travels from its average orientation and back, in degrees."""
    if len(quaternions) < 2:
        return 0.0
    first = quaternions[0]
    return max(_angle(first, q) for q in quaternions)


def _natural_report(armature, roles, rotations, hips_track, travel, feet, root, moving, frames, issues, info, leg, props):
    """Signs of robotic motion. Thresholds sit far below natural values: they catch motion that is absent, not a style."""
    bones = armature.pose.bones
    feet_count = len(feet)
    ranges = {name: _range_degrees(q) for name, q in rotations.items()}
    moving_bones = {name for name, degrees in ranges.items() if degrees >= 2.0}
    secondary = [b.name for b in armature.data.bones
                 if set(rig.words(b.name)) & {"tail", "ear", "ears", "wing", "ponytail", "antenna"}]
    still = [name for name in secondary if ranges.get(name, 0.0) < 1.0]
    if secondary and still and len(still) == len(secondary) and hips_track:
        issues["secondary_still"] = f"{', '.join(still[:4])} never move: tails, ears and the like follow the body and bring it to life"

    if not moving:
        hips_range = max((p - hips_track[0]).length for p in hips_track) if hips_track else 0.0
        if not moving_bones and hips_range < 0.002:
            issues["frozen"] = "nothing moves: even an idle needs breathing and a shift of weight"
        return

    if hips_track and leg:
        forward = travel.normalized() if travel.length > 1e-6 else Vector((0.0, -1.0, 0.0))
        side = Vector((-forward.y, forward.x, 0.0))
        lateral = [(p - hips_track[0]).dot(side) for p in hips_track]
        bob = max(p.z for p in hips_track) - min(p.z for p in hips_track)
        info["pelvis_bob_cm"] = round(bob * 100, 1)
        info["pelvis_sway_cm"] = round((max(lateral) - min(lateral)) * 100, 1)
        if bob < (0.01 if feet_count == 2 else 0.004) * leg:
            issues["no_pelvis_motion"] = (f"the body travels level, {bob * 100:.1f} cm of rise and fall: a walking body rises over "
                                          "each planted leg and sinks between steps, about 5 cm on a 1.75 m person")

    if feet_count == 2 and roles:
        knees = [ranges.get(roles.get(f"{s}LowerLeg"), None) for s in ("Left", "Right")]
        knees = [k for k in knees if k is not None]
        if knees:
            info["knee_range_deg"] = round(min(knees))
            if min(knees) < 20.0:
                issues["stiff_knees"] = f"a knee bends only {min(knees):.0f} deg through the cycle: stiff legs, a real swing leg bends about 60"
        arms = [ranges.get(roles.get(f"{s}UpperArm"), None) for s in ("Left", "Right")]
        arms = [a for a in arms if a is not None]
        if arms and not props:
            info["arm_range_deg"] = round(min(arms))
            if min(arms) < 3.0:
                issues["arms_hang_still"] = f"an arm moves only {min(arms):.0f} deg: arms swing against the legs unless something holds them"
        trunk = [ranges.get(roles.get(r), None) for r in ("Spine", "Chest", "UpperChest", "Neck")]
        trunk = [t for t in trunk if t is not None]
        if trunk and max(trunk) < 1.0:
            issues["trunk_still"] = "the trunk is carried like a block: the shoulders turn against the hips in a walk"

    series = {name: _speeds(rotations[name]) for name in moving_bones}
    linear = [name for name, speeds in series.items() if _constant_share(speeds) >= 0.6]
    if len(series) >= 3 and len(linear) >= 0.5 * len(series):
        issues["linear_motion"] = (f"{len(linear)} of {len(series)} moving bones turn at a constant speed, then snap into reverse: "
                                   "motion needs ease in and out")
    # Legs follow planted feet, so their joints peak together in any walk: overlap shows in everything else.
    leg_bones = set()
    for names in feet.values():
        for name in names:
            bone = armature.data.bones[name]
            while bone is not None and bone.name != root:
                leg_bones.add(bone.name)
                bone = bone.parent
    pairs = lags = 0
    for name in moving_bones - leg_bones:
        parent = bones[name].parent
        if parent is None or parent.name not in moving_bones or parent.name == root:
            continue
        pairs += 1
        if _lag(series[parent.name], series[name]) != 0:
            lags += 1
    if pairs:
        info["overlapping_joints"] = f"{lags} of {pairs}"
    if pairs >= 3 and lags <= 0.1 * pairs:
        issues["everything_moves_together"] = (f"{pairs - lags} of {pairs} joints peak on the same frame as their parent: "
                                               "real motion breaks joint by joint, children trailing their parents")


def _speeds(quaternions):
    return [_angle(a, b) for a, b in zip(quaternions, quaternions[1:])]


def _constant_share(speeds):
    """Share of frames that keep the previous frame's turning speed, while turning."""
    peak = max(speeds, default=0.0)
    if peak <= 0.0:
        return 0.0
    steady = sum(1 for a, b in zip(speeds, speeds[1:]) if abs(a - b) < 0.03 * peak and b > 0.2 * peak)
    return steady / max(1, len(speeds) - 1)


def _lag(parent, child):
    """Frames by which the child's speed curve trails or leads its parent's, by cyclic cross-correlation."""
    count = min(len(parent), len(child))
    if count < 4:
        return 0
    a, b = parent[:count], child[:count]
    mean_a, mean_b = sum(a) / count, sum(b) / count
    best, best_score = 0, -math.inf
    window = max(1, count // 4)
    for lag in range(-window, window + 1):
        score = sum((a[i] - mean_a) * (b[(i + lag) % count] - mean_b) for i in range(count))
        # Ties go to no lag, so a flat or noiseless match doesn't count as overlap.
        if score > best_score + 1e-9 or (abs(score - best_score) <= 1e-9 and abs(lag) < abs(best)):
            best, best_score = lag, score
    return best


def _check_action(armature, action, roles, meshes, props, ground, loop, step):
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    start, end = (int(round(f)) for f in action.frame_range)
    frames = list(range(start, end + 1, step))
    if frames[-1] != end:
        frames.append(end)
    armature.animation_data.action = action
    slots = getattr(action, "slots", None)
    if slots and hasattr(armature.animation_data, "action_slot") and armature.animation_data.action_slot is None:
        armature.animation_data.action_slot = slots[0]

    body = meshes[0] if meshes else None
    regions = {m.name: _regions(m, armature, roles) for m in meshes}
    feet = _feet(armature, roles)
    # A body built from parts holds each foot in a part of its own.
    holders = {label: (body if _setting("BODY", None) else max(meshes, key=lambda m: _foot_weight(m, names))) for label, names in feet.items()} if body else {}
    soles = {label: _foot_soles(holders[label], names) for label, names in feet.items()} if body else {}
    hips = _setting("ROOT_BONE", None) or roles.get("Hips")
    track = {key: [] for key in ("hips", "LeftHand", "RightHand")}
    track.update({label: [] for label in feet})
    rotations = {pb.name: [] for pb in armature.pose.bones}
    collisions, opened_joints, prop_hits = {}, {}, {}

    # Each frame is judged as the rest pose is, by what its surfaces do now.
    see_through = set(_setting("SEE_THROUGH", []))
    groups = _setting("PART_GROUPS", {})
    never_together = set(_setting("NEVER_TOGETHER", []))
    allow_crossing = set(_setting("ALLOW_CROSSING", []))
    group_of = {name: group for group, names in groups.items() for name in names}
    two_sided = set(_setting("TWO_SIDED", []))
    character = rig.Character(meshes, armature, see_through) if meshes else None
    judge = None
    apart_at_rest, rest_within, cut_pairs = set(), {}, set()
    height = scale = 0.0

    def skip(a, b):
        if a.owner != b.owner and group_of.get(a.owner) and group_of.get(a.owner) == group_of.get(b.owner):
            return True
        together = (f"{a.owner}+{b.owner}", f"{b.owner}+{a.owner}")
        return any(pair in never_together or pair in allow_crossing for pair in together)

    def sight_of(surfaces):
        shared = rig.Sight([p for p in surfaces if p.owner not in see_through and p.owner not in group_of], height)
        built = {}

        def sight_for(a, b):
            owners = tuple(sorted({a.owner, b.owner} & set(group_of)))
            if not owners:
                return shared
            if owners not in built:
                built[owners] = rig.Sight([p for p in surfaces if p.owner not in see_through and (p.owner not in group_of or p.owner in owners)], height)
            return built[owners]

        return sight_for

    if character:
        saved_position = armature.data.pose_position
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
        surfaces = character.gather()
        zs = [v.co.z for surface in surfaces for v in surface.bm.verts]
        height = max(zs) - min(zs) if zs else 0.0
        deform = [b for b in armature.data.bones if b.use_deform]
        ends = [rig.head(armature, b.name).z for b in deform] + [rig.tail(armature, b.name).z for b in deform]
        scale = min(height, max(max(ends) - min(ends), 0.2 * height)) if ends else height
        joints = rig.Joints(armature, surfaces, roles)
        judge = rig.Judge(joints, scale, see_through=see_through, skip=skip)
        within, between = rig.crossings(surfaces)
        sight_for = sight_of(surfaces)
        # Cut where they cross: what could tell a poke there is gone, and inspect_character.py's receipt for the whole parts is the
        # proof. An opening that shows in the clip is still found.
        cut_pairs = {(surfaces[i].name, surfaces[j].name) for i, j in between
                     if rig.open_edges_inside(surfaces[i], surfaces[j]) or rig.open_edges_inside(surfaces[j], surfaces[i])}
        pair_names = {(surfaces[i].name, surfaces[j].name) for i, j in between}
        apart_at_rest = {p.name for p in rig.apart_from_body([p for p in surfaces if p.owner not in see_through and (p.owner not in group_of or groups[group_of[p.owner]][0] == p.owner)], pair_names, scale)}
        for i, pairs in within.items():
            known = set()
            for x, y in pairs:
                points = rig.crossing_points(surfaces[i], x, surfaces[i], y)
                ba, bb = surfaces[i].bone_at(x, points), surfaces[i].bone_at(y, points)
                known.add((ba, bb) if (ba or "") <= (bb or "") else (bb, ba))
            rest_within[surfaces[i].name] = known
        rig.free(surfaces)
        armature.data.pose_position = saved_position
        bpy.context.view_layer.update()

    lowest_view = _setting("LOWEST_VIEW", 0)
    holes = {}
    for frame in frames:
        scene.frame_set(frame)
        world = armature.matrix_world
        track["hips"].append(world @ armature.pose.bones[hips].head if hips else Vector())
        for side in ("Left", "Right"):
            hand = roles.get(f"{side}Hand")
            track[f"{side}Hand"].append(world @ armature.pose.bones[hand].head if hand else None)
        for pose_bone in armature.pose.bones:
            # The evaluated rotation relative to the parent, constraints included: a parent's pop isn't
            # reported again for every child.
            matrix = pose_bone.matrix
            local = pose_bone.parent.matrix.inverted() @ matrix if pose_bone.parent else matrix
            rotations[pose_bone.name].append(local.to_quaternion())
        if body:
            evaluated = {}

            def posed(mesh):
                if mesh.name not in evaluated:
                    evaluated[mesh.name] = _evaluated(mesh)
                return evaluated[mesh.name]

            for label in feet:
                coords, _ = posed(holders[label])
                points = [coords[i] for i in soles[label][0]]
                if points:
                    center = sum(points, Vector()) / len(points)
                    track[label].append((center, min(p.z for p in points)))
            surfaces = character.gather()
            try:
                pokes, _, between = rig.pose_pokes(surfaces, judge, sight_of(surfaces), cut_pairs, rest_within)
                for poke in pokes:
                    collisions.setdefault(poke["label"], []).append(frame)
                shown = [p for p in surfaces if p.owner not in see_through and (p.owner not in group_of or groups[group_of[p.owner]][0] == p.owner)]
                pair_names = {(surfaces[i].name, surfaces[j].name) for i, j in between}
                for part in rig.apart_from_body(shown, pair_names, scale, enclosed=False):
                    if part.name not in apart_at_rest:
                        opened_joints.setdefault(part.name, []).append(frame)
                sight = rig.Sight(shown, height)
                for part in shown:
                    if part.owner not in two_sided and rig.see_inside(part, sight, lowest_view):
                        holes.setdefault(part.owner, []).append(frame)
            finally:
                rig.free(surfaces)
            for prop in props:
                prop_coords, prop_polygons = _evaluated(prop)
                prop_tree = BVHTree.FromPolygons(prop_coords, prop_polygons)
                for side in ("L", "R"):
                    for mesh in meshes:
                        coords, polygons = posed(mesh)
                        fingers, _ = _tree(coords, polygons, regions[mesh.name], {f"{side}.fingers", f"{side}.arm"})
                        if fingers is not None and fingers.overlap(prop_tree):
                            prop_hits.setdefault(f"{side} hand into {prop.name}", []).append(frame)

    issues, info = {}, {"frames": [start, end], "fps": round(fps, 2), "duration_s": round((end - start) / fps, 3)}
    dt = step / fps
    hips_track = track["hips"]
    travel = Vector((hips_track[-1].x - hips_track[0].x, hips_track[-1].y - hips_track[0].y, 0.0))
    info["root_travel_m"] = round(travel.length, 3)
    duration = (frames[-1] - frames[0]) / fps
    info["root_speed_mps"] = round(travel.length / duration, 3) if duration > 0 else 0.0
    leg = None
    if "LeftUpperLeg" in roles and "LeftFoot" in roles:
        leg = (rig.head(armature, roles["LeftUpperLeg"]) - rig.head(armature, roles["LeftFoot"])).length
    elif hips and ground is not None:
        leg = rig.head(armature, hips).z - ground
    in_place = travel.length < (0.05 * leg if leg else 0.1)
    info["in_place"] = in_place
    if travel.length > 1e-6:
        direction = travel.normalized()
        info["travel_direction"] = [round(direction.x, 2), round(direction.y, 2)]

    tracked_feet = [label for label in feet if track[label]]
    plant_limit = max(0.004, 0.02 * leg) if leg else 0.015
    stride_speed = None
    if body and ground is not None and tracked_feet:
        lowest = min(low for side in tracked_feet for _, low in track[side])
        below = [frames[i] for side in tracked_feet for i, (_, low) in enumerate(track[side]) if low < ground - 0.01]
        if below:
            issues["feet_below_ground"] = f"{(ground - lowest) * 100:.1f} cm deep at worst, {_frames_text(set(below))}"
        if lowest > ground + 0.02:
            issues["feet_never_reach_ground"] = f"the lowest sole point is {(lowest - ground) * 100:.1f} cm above the ground"
        phases = []
        for side in tracked_feet:
            # Planted: the sole's center within 2% of the leg's length of its lowest height in the clip, where the
            # foot stands flat; measured from the foot itself, so feet sunk into or floating above the ground still
            # count. Heel and toe roll lift the center and end the phase; its first and last frames are transitions.
            limit = min(center.z for center, _ in track[side]) + plant_limit
            current = []
            for i, (center, _) in enumerate(track[side] + [(Vector((0.0, 0.0, math.inf)), math.inf)]):
                if center.z < limit:
                    current.append(i)
                    continue
                if len(current) >= 4:
                    first, last = track[side][current[1]][0], track[side][current[-2]][0]
                    phases.append((Vector((last.x - first.x, last.y - first.y, 0.0)), (current[-2] - current[1]) * dt,
                                   side, frames[current[1]], frames[current[-2]]))
                current = []
        if phases and not in_place:
            worst = max(phases, key=lambda ph: ph[0].length)
            info["planted_foot_slide_cm"] = round(worst[0].length * 100, 1)
            # The same limit as FootSlideMeter in the running game: about 3 cm for a person, less for a small character.
            if worst[0].length > max(0.01, 0.035 * (leg or 0.8)):
                label = worst[2].lower() if worst[2] in ("Left", "Right") else worst[2]
                issues["foot_sliding"] = (f"the {label} foot slides {worst[0].length * 100:.1f} cm while planted, "
                                          f"frames {worst[3]}-{worst[4]}")
        elif phases:
            # In place, planted feet move with the ground under the character: that speed is the speed the
            # character must move at, opposite to the feet.
            total = sum((ph[0] for ph in phases), Vector())
            if total.length > 1e-6:
                direction = total.normalized()
                speeds = [ph[0].dot(direction) / ph[1] for ph in phases if ph[1] > 0]
                drift = max(abs(ph[0].x * direction.y - ph[0].y * direction.x) for ph in phases)
                speed = sum(speeds) / len(speeds)
                stride_speed = speed
                info["stride_speed_mps"] = round(speed, 3)
                info["move_direction"] = [round(-direction.x, 2), round(-direction.y, 2)]
                if speed > 1e-6 and (max(speeds) - min(speeds)) / speed > 0.25:
                    issues["uneven_stride"] = (f"planted feet move at {min(speeds):.2f} to {max(speeds):.2f} m/s: "
                                               "no single movement speed matches every step")
                if drift > max(0.01, 0.035 * (leg or 0.8)):
                    issues["foot_sliding"] = f"a planted foot drifts {drift * 100:.1f} cm sideways"

    # What the clip's motion is worth: a body moving over planted feet, at a speed its legs can believably carry.
    speed = stride_speed if in_place else info["root_speed_mps"]
    moving = bool(speed and speed > 0.02)
    # Legs swinging count as locomotion even when the clip's feet never carry the body.
    swinging = False
    if not tracked_feet and hips and leg:
        for label, names in feet.items():
            bone = next(iter(names))
            swinging = swinging or _range_degrees(rotations.get(bone, [])) > 5.0
    if tracked_feet and hips and leg:
        for label in tracked_feet:
            forward_axis = [(center - h).y for (center, _), h in zip(track[label], hips_track)]
            swinging = swinging or max(forward_axis) - min(forward_axis) > 0.1 * leg
    duty = None
    # Legs swing or the body travels, but no sole was measured: nothing here proves the feet don't slide.
    if (moving or swinging or not in_place) and feet and ground is not None and not tracked_feet:
        issues["feet_not_measured"] = "no mesh holds the feet's bones, so foot contact wasn't measured: set BODY, FEET or BONE_MAP"
    if body and ground is not None and tracked_feet and moving and loop:
        duty = _gait_report(armature, {label: feet[label] for label in tracked_feet}, track, frames, issues, info, leg, loop, plant_limit)
    if moving and leg:
        froude = speed * speed / (9.81 * leg)
        info["froude"] = round(froude, 3)
        # A human walks at about Froude 0.2 and must run above 0.5: both hold at any body size, by dynamic similarity.
        info["natural_walk_speed_mps"] = round(math.sqrt(0.2 * 9.81 * leg), 2)
        limit = _setting("MAX_WALK_FROUDE", 0.5)
        if duty is not None and duty > 0.5 and froude > limit:
            issues["too_fast_for_a_walk"] = (f"{speed:.2f} m/s on {leg:.2f} m legs is Froude {froude:.2f}, above {limit}: legs this long "
                                             f"run at this speed. Walk near {math.sqrt(0.2 * 9.81 * leg):.2f} m/s, or use a run")
    game_speed = _setting("GAME_SPEED", None)
    if game_speed and moving:
        rate = game_speed / speed
        allowed = _setting("MAX_PLAYBACK_CHANGE", 0.25)
        info["playback_rate"] = round(rate, 2)
        if abs(rate - 1.0) > allowed:
            issues["playback_rate_out_of_range"] = (f"the game moves it at {game_speed} m/s and the clip's feet at {speed:.2f}: playing at "
                                                    f"{rate:.2f} times reads as wrong cadence. Change the game's speed or the clip's stride")
    if _setting("NATURAL", True):
        _natural_report(armature, roles, rotations, hips_track if hips else [], travel, {label: feet[label] for label in tracked_feet}, hips,
                        moving or swinging, frames, issues, info, leg, props)

    if track["LeftHand"][0] is not None and track["RightHand"][0] is not None and body and "Left" in tracked_feet and "Right" in tracked_feet:
        forward = travel.normalized() if travel.length > 1e-6 else Vector((0.0, -1.0, 0.0))

        def along(points):
            return [(p - h).dot(forward) for p, h in zip(points, hips_track)]

        left_foot, right_foot = along([c for c, _ in track["Left"]]), along([c for c, _ in track["Right"]])
        left_hand, right_hand = along(track["LeftHand"]), along(track["RightHand"])
        swing = max(left_hand) - min(left_hand)
        stride = max(left_foot) - min(left_foot)
        if swing > 0.04 and stride > 0.1:
            def correlation(a, b):
                ma, mb = sum(a) / len(a), sum(b) / len(b)
                num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
                den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
                return num / den if den > 1e-9 else 0.0
            opposite = correlation(left_foot, right_hand) + correlation(right_foot, left_hand)
            same = correlation(left_foot, left_hand) + correlation(right_foot, right_hand)
            info["arm_swing"] = "opposite legs" if opposite > same else "same-side legs"
            if same > opposite + 0.5:
                issues["same_side_arm_swing"] = "each arm swings forward with the leg on its own side; in a natural gait it moves with the opposite leg"

    pops = []
    for name, quaternions in rotations.items():
        changes = [_angle(a, b) for a, b in zip(quaternions, quaternions[1:])]
        if not changes:
            continue
        # A pop leaves the path its neighbors define: fast but smooth motion stays near their midpoint.
        for i in range(1, len(quaternions) - 1):
            before, after = quaternions[i - 1], quaternions[i + 1].copy()
            if before.dot(after) < 0.0:
                after.negate()
            deviation = _angle(quaternions[i], before.slerp(after, 0.5))
            if deviation > 30.0:
                pops.append((deviation, name, frames[i]))
        if loop and len(quaternions) > 2:
            seam = _angle(quaternions[-1], quaternions[0])
            if seam > 2.5 * max(changes) + 1.0:
                pops.append((seam, name, "loop"))
    seams = [p for p in pops if p[2] == "loop"]
    jumps = [p for p in pops if p[2] != "loop"]
    if seams:
        worst = max(seams)
        issues["loop_seam"] = f"{len(seams)} bones jump between the last and first frame, {worst[1]} by {worst[0]:.0f} deg"
        # Not a whole cycle, so its step timing means nothing.
        issues.pop("uneven_steps", None)
        issues.pop("irregular_footfall", None)
        issues.pop("wrong_gait", None)
    if jumps:
        worst = max(jumps)
        issues["joint_pops"] = f"{len(jumps)} poses jump off the motion, {worst[1]} by {worst[0]:.0f} deg at frame {worst[2]}"
    for label, hit_frames in collisions.items():
        issues.setdefault("limbs_through_body", {})[label] = _frames_text(hit_frames)
    for joint, open_frames in opened_joints.items():
        issues.setdefault("joint_opens", {})[joint] = _frames_text(open_frames)
    for owner, hole_frames in holes.items():
        issues.setdefault("see_inside", {})[owner] = _frames_text(hole_frames)
    for label, hit_frames in prop_hits.items():
        issues.setdefault("hand_through_prop", {})[label] = _frames_text(hit_frames)
    return issues, info


def inspect():
    name = _setting("ARMATURE", None)
    if name:
        armature = bpy.data.objects[name]
    else:
        selected = [o for o in bpy.context.selected_objects if o.type == "ARMATURE"]
        if len(selected) != 1:
            raise ValueError("set ARMATURE, or select exactly one armature")
        armature = selected[0]
    roles = rig.map_roles(armature, _setting("BONE_MAP", {}))
    meshes = [bpy.data.objects[n] for n in _setting("MESHES", [])] or [
        o for o in bpy.context.scene.objects if o.type == "MESH" and (rig.deforming_armature(o) is armature or o.parent is armature)]
    # The body is what holds the feet, however many triangles the hair has.
    foot_bones = set().union(*_feet(armature, roles).values()) if _feet(armature, roles) else set()
    body_name = _setting("BODY", None)
    meshes.sort(key=lambda o: (o.name == body_name, _foot_weight(o, foot_bones), len(o.data.polygons)), reverse=True)
    props = [bpy.data.objects[n] for n in _setting("PROPS", [])]
    if armature.animation_data is None:
        armature.animation_data_create()
    saved_action = armature.animation_data.action
    saved_slot = getattr(armature.animation_data, "action_slot", None)
    saved_frame = bpy.context.scene.frame_current
    action_names = _setting("ACTIONS", None)
    actions = [bpy.data.actions[n] for n in action_names] if action_names else [saved_action] if saved_action else []
    if not actions:
        raise ValueError("no action: set ACTIONS")
    report = {"passed": True, "actions": {}}
    with rig.PoseState(armature):
        try:
            for action in actions:
                issues, info = _check_action(armature, action, roles, meshes, props, _setting("GROUND", 0.0),
                                             _setting("LOOP", True), max(1, int(_setting("STEP", 1))))
                report["actions"][action.name] = {"issues": issues, "info": info}
                report["passed"] = report["passed"] and not issues
                folder = _setting("PROOF_DIR", None)
                if folder:
                    os.makedirs(folder, exist_ok=True)
                    settings = {key: _setting(key, None) for key in ("NATURAL", "GROUND", "LOOP", "STEP", "GAME_SPEED", "GAIT", "FEET", "BODY", "SEE_THROUGH", "PART_GROUPS", "NEVER_TOGETHER", "ALLOW_CROSSING", "TWO_SIDED", "LOWEST_VIEW", "MAX_WALK_FROUDE", "MAX_PLAYBACK_CHANGE") if key in globals()}
                    with open(os.path.join(folder, f"inspect_animation-{_setting('PROOF_NAME', None) or armature.name}-{action.name}.json"), "w") as out:
                        json.dump({"passed": not issues, "issues": issues, "info": info, "settings": settings, "meshes": [m.name for m in meshes]}, out, indent=1, default=str)
        finally:
            armature.animation_data.action = saved_action
            if saved_slot is not None and hasattr(armature.animation_data, "action_slot"):
                try:
                    armature.animation_data.action_slot = saved_slot
                except (TypeError, RuntimeError):
                    pass
            bpy.context.scene.frame_set(saved_frame)
    return report


result = inspect()
