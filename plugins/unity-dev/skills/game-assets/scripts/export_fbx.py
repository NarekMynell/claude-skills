"""Exports one asset to FBX for Unity, only after its checks pass, with the settings of references/export.md.

Run it as the game-assets guide's "Running the scripts" describes. Settings:
    TARGETS = ["Crate"]          required: the asset's meshes (and empties); a rigged asset's armature is added
    FILEPATH = "/abs/Crate.fbx"  required
    TRIANGLE_BUDGET = 800        for the mesh check
    MESH_CHECK = {}              other validate_mesh.py settings, such as {"FLAT_DETAIL": True}
    CHARACTER_CHECK = {}         inspect_character.py settings for a rigged asset, such as {"FINGERS": 4}
    ANIMATION = False            a rigged asset: also export its current action, unreduced
    FORCE = False                export despite failed checks: only after the user accepted each listed issue

Sets `result`: `exported` (the path, or None), `issues` (what failed) and `checks` (the full reports). Selection and
the active object are restored.
"""

import os

import bpy

SCRIPTS = os.path.dirname(globals().get("__file__", ""))


def _setting(name, default):
    return globals().get(name, default)


def _run(script, settings):
    path = os.path.join(SCRIPTS, script)
    namespace = {"__file__": path}
    namespace.update(settings)
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return namespace["result"]


def _armature_of(objects):
    for obj in objects:
        for modifier in getattr(obj, "modifiers", ()):
            if modifier.type == "ARMATURE" and modifier.object:
                return modifier.object
    return None


def export():
    names = _setting("TARGETS", None)
    filepath = _setting("FILEPATH", None)
    if not names or not filepath:
        raise ValueError("TARGETS and FILEPATH are required")
    objects = [bpy.data.objects[name] for name in names]
    meshes = [o for o in objects if o.type == "MESH"]
    armature = next((o for o in objects if o.type == "ARMATURE"), None) or _armature_of(meshes)
    if armature and armature not in objects:
        objects.append(armature)

    checks, issues = {}, {}
    mesh_settings = {"TARGETS": [o.name for o in meshes], "TRIANGLE_BUDGET": _setting("TRIANGLE_BUDGET", None)}
    mesh_settings.update(_setting("MESH_CHECK", {}))
    checks["mesh"] = _run("validate_mesh.py", mesh_settings)
    for entry in checks["mesh"]["objects"]:
        if entry["issues"]:
            issues[entry["name"]] = entry["issues"]
    if armature:
        character_settings = {"TARGETS": [o.name for o in meshes], "ARMATURE": armature.name}
        character_settings.update(_setting("CHARACTER_CHECK", {}))
        checks["character"] = _run("inspect_character.py", character_settings)
        if checks["character"]["issues"]:
            issues["character"] = checks["character"]["issues"]
    shape_keys = [o.name for o in meshes if o.data.shape_keys]
    stacked = [o.name for o in meshes if o.data.shape_keys and any(m.type != "ARMATURE" for m in o.modifiers)]
    if stacked:
        # The exporter can't apply modifiers and keep shape keys: apply the other modifiers to the source first.
        issues["modifiers_with_shape_keys"] = stacked
    if issues and not _setting("FORCE", False):
        return {"exported": None, "issues": issues, "checks": checks}

    view_layer = bpy.context.view_layer
    scene = bpy.context.scene
    selected = [o for o in scene.objects if o.select_get()]
    active = view_layer.objects.active
    frame_range = (scene.frame_start, scene.frame_end)
    try:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        view_layer.objects.active = armature or objects[0]
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        types = {o.type for o in objects} & {"MESH", "EMPTY", "ARMATURE"}
        common = dict(
            filepath=filepath, use_selection=True, object_types=types, apply_scale_options="FBX_SCALE_ALL",
            apply_unit_scale=True, axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE", colors_type="LINEAR",
            add_leaf_bones=False, path_mode="STRIP",
        )
        if armature:
            animation = bool(_setting("ANIMATION", False))
            action = armature.animation_data.action if armature.animation_data else None
            if animation and action:
                # The exporter bakes the scene's frame range: make it the action's.
                scene.frame_start, scene.frame_end = (int(round(f)) for f in action.frame_range)
            bpy.ops.export_scene.fbx(
                **common, bake_space_transform=False, use_armature_deform_only=True,
                # Armature modifiers are never applied; other modifiers only when no mesh has shape keys.
                use_mesh_modifiers=not shape_keys, bake_anim=animation, bake_anim_use_all_actions=False,
                bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
            )
        else:
            bpy.ops.export_scene.fbx(**common, bake_space_transform=True, use_mesh_modifiers=True, bake_anim=False)
    finally:
        scene.frame_start, scene.frame_end = frame_range
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected:
            obj.select_set(True)
        view_layer.objects.active = active
    return {"exported": filepath, "issues": issues, "checks": checks}


result = export()
