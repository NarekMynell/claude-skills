"""Checks a character's animation clips (Blender actions): foot contact and sliding, the speed an in-place clip needs,
arm swing, loop seams, joint pops, limbs passing through the body, and fingers passing through held props.

Run it as the game-assets guide's "Running the scripts" describes. Settings:
    ARMATURE = "Rig"          required unless exactly one armature is selected
    ACTIONS = ["Walk"]        default: the armature's current action
    MESHES = ["Body"]         skinned meshes; default: the meshes ARMATURE deforms
    PROPS = ["Sword"]         held objects that fingers must touch without entering
    GROUND = 0.0              ground height in metres; None for clips without ground contact (swimming, falling)
    LOOP = True               the clip loops: its last frame must flow into its first
    STEP = 1                  check every Nth frame
    BONE_MAP = {}             Unity Humanoid role -> bone name, for names the script doesn't recognize

Sets `result`: `passed` and, per action, `issues` (with frame numbers) and `info`. Restores the action, frame and
pose it found.
"""

import math
import os
import types

import bmesh
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
TRUNK_ROLES = ("Hips", "Spine", "Chest", "UpperChest", "Neck", "Head", "Shoulder")
BODY_REGIONS = {"trunk", "L.thigh", "R.thigh", "L.leg", "R.leg"}


def _regions(mesh_object, armature, roles):
    """Each vertex's body region from its strongest bone: 'trunk', 'L.thigh', 'L.leg', 'L.arm', 'L.fingers'..."""
    by_bone = {}
    for role, bone in roles.items():
        side = "L." if role.startswith("Left") else "R." if role.startswith("Right") else ""
        base = role[4:] if role.startswith("Left") else role[5:] if role.startswith("Right") else role
        if base in TRUNK_ROLES:
            by_bone[bone] = "trunk"
        elif base in FINGER_ROLES:
            by_bone[bone] = side + "fingers"
        elif base in ("LowerArm", "Hand"):
            by_bone[bone] = side + "arm"
        elif base == "UpperLeg":
            by_bone[bone] = side + "thigh"
        elif base in ("LowerLeg", "Foot", "Toes"):
            by_bone[bone] = side + "leg"
    groups = {g.index: g.name for g in mesh_object.vertex_groups}
    vertex_region = []
    for vertex in mesh_object.data.vertices:
        best = max(vertex.groups, key=lambda g: g.weight, default=None)
        vertex_region.append(by_bone.get(groups.get(best.group)) if best else None)
    return vertex_region


def _foot_soles(mesh_object, roles, side):
    """Indices of the lowest vertices weighted mostly to one foot, in the rest shape, and how far their center sits
    above the lowest of them."""
    names = {roles.get(f"{side}Foot"), roles.get(f"{side}Toes")} - {None}
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
    """BVH of the faces whose vertices are mostly in the wanted regions. Faces of different regions that share a
    vertex are neighbors at a joint, which `_crossings` ignores."""
    faces = []
    for polygon in polygons:
        regions = [vertex_region[v] for v in polygon]
        if max(set(regions), key=regions.count) in wanted:
            faces.append(polygon)
    if not faces:
        return None, []
    return BVHTree.FromPolygons(coords, faces), faces


def _crossings(tree_a, faces_a, tree_b, faces_b):
    if tree_a is None or tree_b is None:
        return 0
    count = 0
    for a, b in tree_a.overlap(tree_b):
        if not set(faces_a[a]) & set(faces_b[b]):
            count += 1
    return count


def _angle(q1, q2):
    dot = abs(q1.dot(q2))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def _frames_text(frames):
    frames = sorted(frames)
    if len(frames) > 6:
        return f"{len(frames)} frames, first {frames[:5]}"
    return f"frames {frames}"


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
    regions = _regions(body, armature, roles) if body else None
    soles = {side: _foot_soles(body, roles, side) for side in ("Left", "Right")} if body else {}
    hips = roles.get("Hips")
    track = {key: [] for key in ("hips", "Left", "Right", "LeftHand", "RightHand")}
    rotations = {pb.name: [] for pb in armature.pose.bones}
    collisions, prop_hits = {}, {}

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
            coords, polygons = _evaluated(body)
            for side in ("Left", "Right"):
                points = [coords[i] for i in soles[side][0]]
                if points:
                    center = sum(points, Vector()) / len(points)
                    track[side].append((center, min(p.z for p in points)))
            trunk, trunk_faces = _tree(coords, polygons, regions, BODY_REGIONS)
            for side in ("L", "R"):
                arm, arm_faces = _tree(coords, polygons, regions, {f"{side}.arm", f"{side}.fingers"})
                if _crossings(arm, arm_faces, trunk, trunk_faces):
                    collisions.setdefault(f"{side} forearm or hand into the body", []).append(frame)
            left_leg, left_faces = _tree(coords, polygons, regions, {"L.leg"})
            right_leg, right_faces = _tree(coords, polygons, regions, {"R.leg"})
            if _crossings(left_leg, left_faces, right_leg, right_faces):
                collisions.setdefault("legs through each other", []).append(frame)
            for prop in props:
                prop_coords, prop_polygons = _evaluated(prop)
                prop_tree = BVHTree.FromPolygons(prop_coords, prop_polygons)
                for side in ("L", "R"):
                    fingers, finger_faces = _tree(coords, polygons, regions, {f"{side}.fingers", f"{side}.arm"})
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
    in_place = travel.length < (0.05 * leg if leg else 0.1)
    info["in_place"] = in_place
    if travel.length > 1e-6:
        direction = travel.normalized()
        info["travel_direction"] = [round(direction.x, 2), round(direction.y, 2)]

    if body and ground is not None and track["Left"] and track["Right"]:
        lowest = min(low for side in ("Left", "Right") for _, low in track[side])
        below = [frames[i] for side in ("Left", "Right") for i, (_, low) in enumerate(track[side]) if low < ground - 0.01]
        if below:
            issues["feet_below_ground"] = f"{(ground - lowest) * 100:.1f} cm deep at worst, {_frames_text(set(below))}"
        if lowest > ground + 0.02:
            issues["feet_never_reach_ground"] = f"the lowest sole point is {(lowest - ground) * 100:.1f} cm above the ground"
        phases = []
        for side in ("Left", "Right"):
            # Planted: the sole's center within 1.5 cm of its lowest height in the clip, where the foot stands
            # flat; measured from the foot itself, so feet sunk into or floating above the ground still count.
            # Heel and toe roll lift the center and end the phase; its first and last frames are transitions.
            limit = min(center.z for center, _ in track[side]) + 0.015
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
            if worst[0].length > 0.03:
                issues["foot_sliding"] = (f"the {worst[2].lower()} foot slides {worst[0].length * 100:.1f} cm while planted, "
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
                info["stride_speed_mps"] = round(speed, 3)
                info["move_direction"] = [round(-direction.x, 2), round(-direction.y, 2)]
                if speed > 1e-6 and (max(speeds) - min(speeds)) / speed > 0.25:
                    issues["uneven_stride"] = (f"planted feet move at {min(speeds):.2f} to {max(speeds):.2f} m/s: "
                                               "no single movement speed matches every step")
                if drift > 0.03:
                    issues["foot_sliding"] = f"a planted foot drifts {drift * 100:.1f} cm sideways"

    if track["LeftHand"][0] is not None and track["RightHand"][0] is not None and body and track["Left"]:
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
    if jumps:
        worst = max(jumps)
        issues["joint_pops"] = f"{len(jumps)} poses jump off the motion, {worst[1]} by {worst[0]:.0f} deg at frame {worst[2]}"
    for label, hit_frames in collisions.items():
        issues.setdefault("limbs_through_body", {})[label] = _frames_text(hit_frames)
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
        o for o in bpy.context.scene.objects if o.type == "MESH" and rig.deforming_armature(o) is armature]
    meshes.sort(key=lambda o: len(o.data.polygons), reverse=True)
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
