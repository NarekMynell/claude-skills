"""Builds a character or animal body from a joint skeleton: a Skin-modifier surface, cleaned of what the modifier leaves
(duplicate and loose vertices, faces with no area), smoothed, set on the ground, with an armature on the same joints, skinned
and cleaned (no weight from the other side's bones, at most 4 influences, normalized). The surface follows the joints, so limbs
stay apart and the body is symmetric when the joints are.

Run it as the game-assets guide's "Running the scripts" describes. Settings:
    NAME = "Hero"              required: the mesh object's name; the armature is NAME + "Rig"
    JOINTS = {...}             required: key -> (position, (radius_x, radius_y) or None, parent key or None).
                               A None radius makes a point for bones only, such as finger joints inside a mitten.
                               Exactly one joint has no parent: the root, usually the pelvis.
    BONES = [...]              required: (bone name, head joint, tail joint, parent bone or None), with Humanoid
                               names and side markers (hips, spine, head, thigh.L, upper_arm.R ...)
    SUBDIVISIONS = 1           smoothing levels applied before rigging: 0 low poly, 1 to 2 mid poly

Sets `result`: `mesh`, `armature`, `triangles`. Then run inspect_character.py on it.
"""

import bmesh
import bpy
from mathutils import Vector


def _setting(name, default=None):
    return globals().get(name, default)


def build():
    name, joints, bones = _setting("NAME"), _setting("JOINTS"), _setting("BONES")
    if not (name and joints and bones):
        raise ValueError("NAME, JOINTS and BONES are required")
    keys = [k for k, joint in joints.items() if joint[1] is not None]
    index = {k: i for i, k in enumerate(keys)}
    roots = [k for k in keys if joints[k][2] is None]
    if len(roots) != 1:
        raise ValueError(f"exactly one surface joint needs no parent, found {roots}")
    edges = [(index[joints[k][2]], index[k]) for k in keys if joints[k][2] in index]

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([Vector(joints[k][0]) for k in keys], edges, [])
    body = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(body)
    skin = body.modifiers.new("Skin", "SKIN")
    skin.use_smooth_shade = True
    for k in keys:
        mesh.skin_vertices[0].data[index[k]].radius = tuple(joints[k][1])
    mesh.skin_vertices[0].data[index[roots[0]]].use_root = True
    view_layer = bpy.context.view_layer
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier="Skin")
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-4)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    levels = int(_setting("SUBDIVISIONS", 1))
    if levels:
        # Smoothed before rigging, so the weights fit the final surface.
        body.modifiers.new("Subdivision", "SUBSURF").levels = levels
        bpy.ops.object.modifier_apply(modifier="Subdivision")
    lowest = min(v.co.z for v in mesh.vertices)  # smoothing shrinks the shape off the ground
    for vertex in mesh.vertices:
        vertex.co.z -= lowest

    rig = bpy.data.objects.new(name + "Rig", bpy.data.armatures.new(name + "Rig"))
    bpy.context.scene.collection.objects.link(rig)
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name, head, tail, parent in bones:
        bone = rig.data.edit_bones.new(bone_name)
        bone.head = Vector(joints[head][0]) - Vector((0.0, 0.0, lowest))
        bone.tail = Vector(joints[tail][0]) - Vector((0.0, 0.0, lowest))
        bone.parent = rig.data.edit_bones.get(parent) if parent else None
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")

    # Automatic weights can reach across the body: drop the other side's bones outside a center strip.
    groups = {g.index: g.name for g in body.vertex_groups}
    strip = 0.04 * body.dimensions.z
    for vertex in mesh.vertices:
        wrong = (".R", "_r") if vertex.co.x > strip else (".L", "_l") if vertex.co.x < -strip else None
        for element in list(vertex.groups) if wrong else []:
            if groups[element.group].endswith(wrong):
                body.vertex_groups[groups[element.group]].remove([vertex.index])
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    view_layer.objects.active = body
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    return {"mesh": body.name, "armature": rig.name, "triangles": sum(len(p.vertices) - 2 for p in mesh.polygons)}


result = build()
