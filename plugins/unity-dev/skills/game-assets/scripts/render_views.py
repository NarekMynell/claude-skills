"""Renders front, side, top and perspective views of objects for a visual check.

Run through the Blender MCP `execute_blender_code` tool. Settings, defined before this code:
    OUTPUT_DIR = "/abs/path"  required; PNGs are written here
    TARGETS = ["Crate"]       object names; default: selected objects, else all meshes
    RESOLUTION = 768          pixels per side
    COLOR = "TEXTURE"         "TEXTURE": image textures, else the base color; "VERTEX": color attributes

Uses a temporary camera and the Workbench engine, then restores the scene, including the render
output format, the shading settings and the materials' viewport colors.
Sets `result` to the written file paths.
"""

import os

import bpy
from mathutils import Vector

VIEWS = {
    "front": Vector((0.0, -1.0, 0.0)),
    "side": Vector((1.0, 0.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "perspective": Vector((1.0, -1.0, 0.8)).normalized(),
}


def _targets(names):
    if names:
        return [bpy.data.objects[name] for name in names]
    selected = list(bpy.context.selected_objects)
    return selected or [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _bounds(objects):
    corners = [o.matrix_world @ Vector(corner) for o in objects for corner in o.bound_box]
    low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return (low + high) / 2.0, max((high - low).length, 1e-3)


def _show_base_colors(objects):
    """Workbench draws a material's viewport color, which Blender doesn't sync with the Principled BSDF's
    base color. Copies the base color over for the render and returns the colors to restore."""
    saved = {}
    for obj in objects:
        for slot in getattr(obj, "material_slots", ()):
            material = slot.material
            if material is None or material.name in saved or material.node_tree is None:
                continue
            # Blender 5 deprecates use_nodes, to be removed in 6.0: read it only where it still applies.
            if bpy.app.version < (5, 0, 0) and not material.use_nodes:
                continue
            bsdf = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is None or bsdf.inputs["Base Color"].is_linked:
                continue
            saved[material.name] = tuple(material.diffuse_color)
            material.diffuse_color = tuple(bsdf.inputs["Base Color"].default_value)
    return saved


def render_views(output_dir, names=None, resolution=768, color="TEXTURE"):
    scene = bpy.context.scene
    objects = _targets(names)
    center, size = _bounds(objects)
    os.makedirs(output_dir, exist_ok=True)

    shading = scene.display.shading
    image = scene.render.image_settings
    saved = {
        "camera": scene.camera,
        "engine": scene.render.engine,
        "x": scene.render.resolution_x,
        "y": scene.render.resolution_y,
        "percentage": scene.render.resolution_percentage,
        "path": scene.render.filepath,
        "format": image.file_format,
        "color_mode": image.color_mode,
        "color_depth": image.color_depth,
        "light": shading.light,
        "color_type": shading.color_type,
        "cavity": shading.show_cavity,
        "hidden": {o.name: o.hide_render for o in scene.objects},
    }
    material_colors = {}
    camera_data = bpy.data.cameras.new("ValidationCamera")
    camera = bpy.data.objects.new("ValidationCamera", camera_data)
    scene.collection.objects.link(camera)
    paths = []
    try:
        for obj in scene.objects:
            if obj.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"} and obj not in objects:
                obj.hide_render = True
        scene.camera = camera
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = resolution
        scene.render.resolution_y = resolution
        scene.render.resolution_percentage = 100
        image.file_format = "PNG"
        image.color_mode = "RGB"
        shading.light = "STUDIO"
        shading.color_type = color
        shading.show_cavity = True
        if color == "TEXTURE":
            material_colors = _show_base_colors(objects)

        for view, direction in VIEWS.items():
            orthographic = view != "perspective"
            camera_data.type = "ORTHO" if orthographic else "PERSP"
            camera_data.ortho_scale = size * 1.15
            camera_data.lens = 50.0
            distance = size * (2.5 if orthographic else 1.8)
            camera.location = center + direction * distance
            camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
            camera_data.clip_start = distance * 0.01
            camera_data.clip_end = distance * 4.0
            path = os.path.join(output_dir, f"{view}.png")
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            paths.append(path)
    finally:
        for name, diffuse in material_colors.items():
            bpy.data.materials[name].diffuse_color = diffuse
        shading.light = saved["light"]
        shading.color_type = saved["color_type"]
        shading.show_cavity = saved["cavity"]
        image.file_format = saved["format"]
        image.color_mode = saved["color_mode"]
        try:
            image.color_depth = saved["color_depth"]
        except TypeError:
            pass  # the restored format already chose its own depth
        scene.camera = saved["camera"]
        scene.render.engine = saved["engine"]
        scene.render.resolution_x = saved["x"]
        scene.render.resolution_y = saved["y"]
        scene.render.resolution_percentage = saved["percentage"]
        scene.render.filepath = saved["path"]
        for name, hidden in saved["hidden"].items():
            if name in scene.objects:
                scene.objects[name].hide_render = hidden
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
    return {"files": paths}


result = render_views(
    globals()["OUTPUT_DIR"],
    globals().get("TARGETS"),
    globals().get("RESOLUTION", 768),
    globals().get("COLOR", "TEXTURE"),
)
