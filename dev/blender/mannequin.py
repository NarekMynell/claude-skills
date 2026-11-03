# Builds a test mannequin for the character and animation script tests: one Skin-modifier surface in A-pose, about
# 1.75 m, facing -Y, mitten hands with five finger bones each, and an armature with Blender-style .L/.R names, skinned
# with automatic weights. Finger joints are bone positions only: Skin-modifier fingers cut into each other where they
# branch. Variants add one known defect each.
import math

import bpy
from mathutils import Vector

A = math.radians(40)
ARM = Vector((math.cos(A), 0.0, -math.sin(A)))


def _left_joints(variant):
    """Joint positions of the left side: name -> (position, radius, parent)."""
    shoulder = Vector((0.18, 0.0, 1.42))
    elbow = shoulder + ARM * 0.28
    wrist = elbow + ARM * 0.26
    palm = wrist + ARM * 0.045
    joints = {
        "hip": (Vector((0.09, 0.0, 0.88)), 0.075, "pelvis"),
        "knee": (Vector((0.10, 0.0, 0.50)), 0.052, "hip"),
        "ankle": (Vector((0.10, 0.0, 0.09)), 0.04, "knee"),
        "ball": (Vector((0.10, -0.09, 0.035)), 0.033, "ankle"),
        "toe": (Vector((0.10, -0.15, 0.033)), 0.03, "ball"),
        "shoulder": (shoulder, 0.055, "chest"),
        "elbow": (elbow, 0.043, "shoulder"),
        "wrist": (wrist, 0.033, "elbow"),
        "palm": (palm, 0.03, "wrist"),
        "mitten": (palm + ARM * 0.085, 0.022, "palm"),
    }
    # Knuckles in a row across the palm, each finger starting from its own knuckle, so that the finger tubes don't
    # cut into each other where they branch.
    across = {"middle": (-0.008, "palm"), "index": (-0.024, "middle0"), "ring": (0.008, "middle0"), "little": (0.024, "ring0")}
    for finger, (y, knuckle_parent) in across.items():
        parent = knuckle_parent
        start = palm + ARM * 0.035 + Vector((0.0, y, 0.0))
        for k, length in enumerate((0.0, 0.03, 0.022, 0.018)):
            start = start + ARM * length
            joints[f"{finger}{k}"] = (start.copy(), None, parent)
            parent = f"{finger}{k}"
    thumb_dir = Vector((0.45, -0.75, -0.45)).normalized()
    side = 1.0 if variant == "thumb_back" else -1.0
    start = wrist + ARM * 0.025 + Vector((0.0, 0.028 * side, -0.01))
    thumb_dir.y *= -side
    parent = "wrist"
    for k, length in enumerate((0.0, 0.028, 0.024, 0.02)):
        start = start + thumb_dir * length
        joints[f"thumb{k}"] = (start.copy(), None, parent)
        parent = f"thumb{k}"
    if variant == "one_leg":
        for name in ("hip", "knee", "ankle", "ball", "toe"):
            position, radius, parent = joints[name]
            joints[name] = (Vector((0.0, position.y, position.z)), radius * (1.9 if name in ("hip", "knee") else 1.0), parent)
    return joints


def _center(variant):
    waist = (0.19, 0.14) if variant == "waist" else (0.12, 0.085)
    return {
        "pelvis": (Vector((0.0, 0.0, 0.95)), (0.15, 0.10), None),
        "waist": (Vector((0.0, 0.0, 1.12)), waist, "pelvis"),
        "chest": (Vector((0.0, 0.0, 1.30)), (0.16, 0.105), "waist"),
        "neck": (Vector((0.0, 0.0, 1.50)), (0.05, 0.05), "chest"),
        "head": (Vector((0.0, 0.0, 1.635)), (0.085, 0.10), "neck"),
        "crown": (Vector((0.0, 0.0, 1.72)), (0.065, 0.075), "head"),
    }


def _mirror(vector):
    return Vector((-vector.x, vector.y, vector.z))


def _surface(name, variant):
    center = _center(variant)
    left = _left_joints(variant)
    points, edges, radii, index = [], [], [], {}

    bone_points = {}

    def add(key, position, radius):
        if radius is None:
            bone_points[key] = position
            return
        index[key] = len(points)
        points.append(position)
        radii.append(radius)

    for key, (position, radius, _) in center.items():
        add(key, position, radius)
    one_leg = variant == "one_leg"
    for side, flip in (("L", False), ("R", True)):
        for key, (position, radius, _) in left.items():
            if one_leg and side == "R" and key in ("hip", "knee", "ankle", "ball", "toe"):
                continue
            add(f"{key}.{side}", _mirror(position) if flip else position, radius)
    for key, (_, _, parent) in center.items():
        if parent:
            edges.append((index[parent], index[key]))
    for side in ("L", "R"):
        for key, (_, _, parent) in left.items():
            if f"{key}.{side}" not in index:
                continue
            parent_key = parent if parent in center else f"{parent}.{side}"
            if parent_key not in index:
                continue
            edges.append((index[parent_key], index[f"{key}.{side}"]))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, edges, [])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    modifier = obj.modifiers.new("Skin", "SKIN")
    modifier.use_smooth_shade = True
    for i, radius in enumerate(radii):
        obj.data.skin_vertices[0].data[i].radius = radius if isinstance(radius, tuple) else (radius, radius)
    obj.data.skin_vertices[0].data[0].use_root = True
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Skin")
    positions = {key: points[i] for key, i in index.items()}
    positions.update(bone_points)
    return obj, positions


BONES = [
    # name, head joint, tail joint, parent
    ("hips", "pelvis", "waist", None),
    ("spine", "waist", "chest", "hips"),
    ("chest", "chest", "neck", "spine"),
    ("neck", "neck", "head", "chest"),
    ("head", "head", "crown", "neck"),
]
LIMB_BONES = [
    ("shoulder", "chest", "shoulder", "chest"),
    ("upper_arm", "shoulder", "elbow", "shoulder"),
    ("forearm", "elbow", "wrist", "upper_arm"),
    ("hand", "wrist", "palm", "forearm"),
    ("thigh", "hip", "knee", "hips"),
    ("shin", "knee", "ankle", "thigh"),
    ("foot", "ankle", "ball", "shin"),
    ("toe", "ball", "toe", "foot"),
]
for _finger in ("thumb", "index", "middle", "ring", "little"):
    for _k in range(3):
        LIMB_BONES.append((f"{_finger}.0{_k + 1}", f"{_finger}{_k}", f"{_finger}{_k + 1}",
                           "hand" if _k == 0 else f"{_finger}.0{_k}"))


def _armature(name, positions, variant):
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    created = {}

    def point(key):
        return positions[key]

    for bone_name, head, tail, parent in BONES:
        bone = data.edit_bones.new(bone_name)
        bone.head, bone.tail = point(head), point(tail)
        if parent:
            bone.parent = created[parent]
        created[bone_name] = bone
    for side in ("L", "R"):
        for bone_name, head, tail, parent in LIMB_BONES:
            full = f"{bone_name}.{side}"
            head_key = head if head == "chest" else f"{head}.{side}"
            tail_key = f"{tail}.{side}"
            if head_key not in positions or tail_key not in positions:
                continue
            bone = data.edit_bones.new(full)
            bone.head, bone.tail = point(head_key), point(tail_key)
            if bone_name == "shoulder":
                bone.head = point("chest") + (point(tail_key) - point("chest")) * 0.2
            parent_name = parent if parent in ("chest", "hips") else f"{parent}.{side}"
            bone.parent = created.get(parent_name)
            created[full] = bone
    if variant == "swap_names":
        for bone in data.edit_bones:
            if bone.name.endswith(".L"):
                bone.name = bone.name[:-2] + ".tmp"
        for bone in data.edit_bones:
            if bone.name.endswith(".R"):
                bone.name = bone.name[:-2] + ".L"
        for bone in data.edit_bones:
            if bone.name.endswith(".tmp"):
                bone.name = bone.name[:-4] + ".R"
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def build(name="Body", variant=None, rigged=True):
    """Returns (mesh object, armature object or None)."""
    body, positions = _surface(name, variant)
    if not rigged:
        return body, None
    rig = _armature(name + "Rig", positions, variant)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    clean_weights(body, rig)
    return body, rig


def clean_weights(body, rig, margin=0.07):
    """The cleanup the characters guide asks for after automatic weights: no weights from the other side's bones
    beyond the center strip, at most 4 influences, normalized."""
    side = {b.name: b.name[-1] for b in rig.data.bones if b.name[-2:] in (".L", ".R")}
    groups = {g.index: g.name for g in body.vertex_groups}
    for vertex in body.data.vertices:
        x = (body.matrix_world @ vertex.co).x
        wrong = "R" if x > margin else "L" if x < -margin else None
        if wrong:
            for element in list(vertex.groups):
                if side.get(groups[element.group]) == wrong:
                    body.vertex_groups[groups[element.group]].remove([vertex.index])
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


def clear():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
        for block in list(collection):
            collection.remove(block)


def add_uvs(obj):
    """Box-projected UVs: overlapping, but no face without UV area, which is all the export tests need."""
    mesh = obj.data
    layer = mesh.uv_layers.new(name="UVMap")
    coords = [v.co for v in mesh.vertices]
    low = [min(c[i] for c in coords) for i in range(3)]
    span = [max(c[i] for c in coords) - low[i] or 1.0 for i in range(3)]
    for poly in mesh.polygons:
        axis = max(range(3), key=lambda i: abs(poly.normal[i]))
        u_axis, v_axis = [i for i in range(3) if i != axis]
        for loop in poly.loop_indices:
            co = coords[mesh.loops[loop].vertex_index]
            layer.data[loop].uv = ((co[u_axis] - low[u_axis]) / span[u_axis], (co[v_axis] - low[v_axis]) / span[v_axis])
