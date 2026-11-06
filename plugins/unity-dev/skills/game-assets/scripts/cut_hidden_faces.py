"""Deletes the faces of a character the player can never see: those that stay inside or under other parts, at rest, in every
test pose and in every clip listed. For a body built from parts that overlap at the joints, this removes what the overlap
costs, and nothing opens when the body moves. A face that shows even in part, in any of those states, stays.

Run it on the whole parts, after inspect_character.py passes on them with WHOLE_PARTS = True: a cut removes what tells a poke
from a bump. Then run inspect_character.py on the result. It changes the meshes: keep a copy if the build can't run again.

Run it as the game-assets guide's "Running the scripts" describes. Settings, all optional:
    TARGETS = ["Body", "Hat"]    the character's mesh objects; default: the meshes ARMATURE deforms, else the selection
    ARMATURE = "Rig"             default: the armature deforming the targets
    SEE_THROUGH = ["HairCards"]  objects with transparent parts: they hide nothing
    KEEP = ["Eyes"]              objects that keep all their faces
    PART_GROUPS = {"hat": ["Cap", "SunHat"]}  variants, as in inspect_character.py: only what appears together can hide a face
    NEVER_TOGETHER = ["HairLong+Cap"]  as in inspect_character.py
    ACTIONS = ["Walk", "Sit"]    clips whose frames count too; they matter when they bend further than the test poses
    STEP = 2                     check every Nth frame of the clips
    HUMANOID = None              as in inspect_character.py
    BONE_MAP = {}                as in inspect_character.py

Sets `result`: `deleted` (object -> faces), `triangles_before`, `triangles_after`.
"""

import os
import types

import bmesh
import bpy


def _setting(name, default):
    return globals().get(name, default)


def _load_rig():
    path = _setting("RIG_HELPERS", None) or os.path.join(os.path.dirname(globals()["__file__"]), "rig.py")
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return types.SimpleNamespace(**namespace)


rig = _load_rig()


def _targets(armature):
    names = _setting("TARGETS", None)
    if names:
        return [bpy.data.objects[n] for n in names if bpy.data.objects[n].type == "MESH"]
    if armature:
        return [o for o in bpy.context.scene.objects if o.type == "MESH" and (rig.deforming_armature(o) is armature or o.parent is armature)]
    return [o for o in bpy.context.selected_objects if o.type == "MESH"]


def _hidden(surfaces, see_through, reach, groups, never_together, among=None):
    """The faces hidden now, among those in question, in every set of parts that can be on screen with them."""
    hidden = set(among) if among is not None else None
    for together in rig.appearing_together(surfaces, groups, never_together):
        names = {p.name for p in together}
        found = set(rig.hidden_faces(together, see_through, reach))
        if hidden is None:
            hidden = found
            continue
        # A face out of this set isn't on screen with it: it stands as it was.
        hidden = {key for key in hidden if key[0] not in names or key in found} | (found if among is None else set())
    return hidden if hidden is not None else set()


def _one_pass(character, armature, see_through, groups, never_together):
    """The faces hidden at rest, in every test pose and in every clip listed, by object and face."""
    saved_position = armature.data.pose_position if armature else None
    if armature:
        armature.data.pose_position = "REST"
        bpy.context.view_layer.update()
    surfaces = character.gather()
    zs = [v.co.z for surface in surfaces for v in surface.bm.verts]
    reach = 0.2 * (max(zs) - min(zs))
    source = {(surface.name, face): (surface.owner, surface.source[face]) for surface in surfaces for face in range(len(surface.bm.faces))}
    hidden = _hidden(surfaces, see_through, reach, groups, never_together)
    rig.free(surfaces)
    if armature:
        armature.data.pose_position = saved_position
        bpy.context.view_layer.update()
    if armature and hidden:
        roles = rig.map_roles(armature, _setting("BONE_MAP", {}))
        humanoid = _setting("HUMANOID", None)
        humanoid = rig.is_humanoid(armature, roles) if humanoid is None else humanoid
        poses = rig.test_poses(roles) if humanoid else rig.creature_poses(armature, roles)
        pose_roles = roles if humanoid else rig.identity_roles(armature)
        with rig.PoseState(armature, mute_constraints=True) as state:
            for steps in poses.values():
                state.reset()
                rig.apply_pose(armature, pose_roles, steps)
                surfaces = character.gather()
                hidden = _hidden(surfaces, see_through, reach, groups, never_together, hidden)
                rig.free(surfaces)
            state.reset()
        with rig.PoseState(armature) as state:
            for action_name in _setting("ACTIONS", []):
                action = bpy.data.actions[action_name]
                if armature.animation_data is None:
                    armature.animation_data_create()
                armature.animation_data.action = action
                slots = getattr(action, "slots", None)
                if slots and hasattr(armature.animation_data, "action_slot") and armature.animation_data.action_slot is None:
                    armature.animation_data.action_slot = slots[0]
                start, end = (int(round(f)) for f in action.frame_range)
                for frame in range(start, end + 1, max(1, int(_setting("STEP", 1)))):
                    bpy.context.scene.frame_set(frame)
                    surfaces = character.gather()
                    hidden = _hidden(surfaces, see_through, reach, groups, never_together, hidden)
                    rig.free(surfaces)
            if armature.animation_data:
                armature.animation_data.action = None
    return {source[key] for key in hidden}


def cut():
    armature_name = _setting("ARMATURE", None)
    armature = bpy.data.objects[armature_name] if armature_name else None
    objects = _targets(armature)
    if not objects:
        raise ValueError("no mesh objects: set TARGETS or ARMATURE")
    armature = armature or next((a for a in (rig.deforming_armature(o) for o in objects) if a), None)
    for obj in objects:
        changing = [m.name for m in obj.modifiers if m.type != "ARMATURE"]
        if changing:
            raise ValueError(f"{obj.name} has modifiers that may change its faces, {changing}: apply them first")
    see_through = set(_setting("SEE_THROUGH", []))
    keep = set(_setting("KEEP", []))
    groups = _setting("PART_GROUPS", {})
    never_together = set(_setting("NEVER_TOGETHER", []))
    before = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    deleted = {}
    # What is deleted can uncover what it hid behind it from a look outward: again until nothing more goes.
    for _ in range(6):
        doomed = {}
        for owner, face in _one_pass(rig.Character(objects, armature, see_through), armature, see_through, groups, never_together):
            if owner not in keep:
                doomed.setdefault(owner, set()).add(face)
        if not doomed:
            break
        for obj in objects:
            if obj.name in doomed:
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.faces.ensure_lookup_table()
                bmesh.ops.delete(bm, geom=[bm.faces[i] for i in doomed[obj.name]], context="FACES")
                bm.to_mesh(obj.data)
                bm.free()
                obj.data.update()
                deleted[obj.name] = deleted.get(obj.name, 0) + len(doomed[obj.name])
        bpy.context.view_layer.update()
    return {"deleted": deleted, "triangles_before": before, "triangles_after": sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)}


result = cut()
