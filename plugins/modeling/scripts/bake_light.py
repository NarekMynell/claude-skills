"""Bakes the scene's light into objects' vertex colors or textures with Cycles, so the game draws them with a simple
shader and pays nothing for that light at runtime.

Run it as the modeling models guide's "Running the scripts" describes. Settings:
    TARGETS = ["Shop", "Ground"]  required: mesh objects with a material and a UV map. Everything visible in the scene
                                  casts light and shadow on them, so place what should show in the bake
    INTO = "VERTEX_COLORS"        or "TEXTURE": one image per object, a UV layout without overlaps
    NAME = "BakedLight"           the color attribute's name, or the image's name after the object's
    SIZE = 512                    the texture's side in pixels
    OUTPUT_DIR = "/abs/path"      required for TEXTURE: where the PNGs go
    SAMPLES = 64                  more for less noise in soft shadows; a noisy bake looks like dirt
    WITH_COLOR = True             light times the surface's color. False bakes light alone, for a shader that multiplies
                                  it by its own texture or palette, so instances can have different colors
    MARGIN = 16                   pixels of edge extension in a texture

Sets `result`: `baked` (object -> attribute or image path), `seconds`. Restores the render engine, samples, selection
and active color attribute it found.
"""

import os
import time

import bpy


def _layout_issues(obj):
    """What validate_mesh.py finds wrong with the object's UV map for a baked texture."""
    path = os.path.join(os.path.dirname(globals()["__file__"]), "validate_mesh.py")
    namespace = {"__file__": path, "TARGETS": [obj.name], "UV_KIND": "UNIQUE"}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    issues = namespace["result"]["objects"][0]["issues"]
    return [str(issues[key]) for key in ("uv_overlap", "uv_stacked_islands", "uv_collapsed", "uv_outside_0_1") if key in issues]


def _setting(name, default=None):
    return globals().get(name, default)


def _prepare_image(obj, name, size):
    image = bpy.data.images.new(f"{obj.name}_{name}", size, size, alpha=False)
    image.colorspace_settings.name = "sRGB"
    for slot in obj.material_slots:
        material = slot.material
        if not material or not material.use_nodes:
            raise ValueError(f"{obj.name}: its material needs nodes to bake")
        node = material.node_tree.nodes.new("ShaderNodeTexImage")
        node.name = "BakeTarget"
        node.image = image
        node.select = True
        material.node_tree.nodes.active = node
    return image


def _remove_target_nodes(obj):
    for slot in obj.material_slots:
        material = slot.material
        node = material.node_tree.nodes.get("BakeTarget") if material and material.use_nodes else None
        if node:
            material.node_tree.nodes.remove(node)


def bake():
    names = _setting("TARGETS")
    if not names:
        raise ValueError("TARGETS is required")
    into = _setting("INTO", "VERTEX_COLORS")
    if into not in ("VERTEX_COLORS", "TEXTURE"):
        raise ValueError("INTO is VERTEX_COLORS or TEXTURE")
    output_dir = _setting("OUTPUT_DIR")
    if into == "TEXTURE" and not output_dir:
        raise ValueError("OUTPUT_DIR is required for TEXTURE")
    name = _setting("NAME", "BakedLight")
    size = int(_setting("SIZE", 512))
    with_color = _setting("WITH_COLOR", True)
    objects = [bpy.data.objects[n] for n in names]
    for obj in objects:
        if not obj.data.uv_layers:
            raise ValueError(f"{obj.name}: baking needs a UV map, also for vertex colors")
        if not obj.material_slots or not any(slot.material for slot in obj.material_slots):
            raise ValueError(f"{obj.name}: baking needs a material")
        if into == "TEXTURE":
            wrong = _layout_issues(obj)
            if wrong:
                raise ValueError(f"{obj.name}: each face needs its own texels to bake into. {'; '.join(wrong)}")

    scene = bpy.context.scene
    settings = scene.render.bake
    saved = {
        "engine": scene.render.engine, "samples": scene.cycles.samples if hasattr(scene, "cycles") else None,
        "direct": settings.use_pass_direct, "indirect": settings.use_pass_indirect, "color": settings.use_pass_color,
        "selected": list(bpy.context.selected_objects), "active": bpy.context.view_layer.objects.active,
    }
    scene.render.engine = "CYCLES"
    scene.cycles.samples = int(_setting("SAMPLES", 64))
    settings.use_pass_direct = settings.use_pass_indirect = True
    settings.use_pass_color = bool(with_color)
    baked = {}
    start = time.time()
    try:
        for obj in objects:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            if into == "VERTEX_COLORS":
                attributes = obj.data.color_attributes
                saved_color = attributes.active_color.name if attributes.active_color else None
                target = attributes.get(name) or attributes.new(name, "BYTE_COLOR", "CORNER")
                attributes.active_color = target
                bpy.ops.object.bake(type="COMBINED", target="VERTEX_COLORS", use_clear=False)
                if saved_color and saved_color != name:
                    attributes.active_color = attributes[saved_color]
                baked[obj.name] = name
            else:
                image = _prepare_image(obj, name, size)
                try:
                    bpy.ops.object.bake(type="COMBINED", target="IMAGE_TEXTURES", margin=int(_setting("MARGIN", 16)), use_clear=True)
                    os.makedirs(output_dir, exist_ok=True)
                    path = os.path.join(output_dir, f"{obj.name}_{name}.png")
                    image.filepath_raw = path
                    image.file_format = "PNG"
                    image.save()
                    baked[obj.name] = path
                finally:
                    _remove_target_nodes(obj)
                    bpy.data.images.remove(image)
    finally:
        scene.render.engine = saved["engine"]
        if saved["samples"] is not None:
            scene.cycles.samples = saved["samples"]
        settings.use_pass_direct, settings.use_pass_indirect, settings.use_pass_color = saved["direct"], saved["indirect"], saved["color"]
        bpy.ops.object.select_all(action="DESELECT")
        for obj in saved["selected"]:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = saved["active"]
    return {"baked": baked, "seconds": round(time.time() - start, 2)}


result = bake()
