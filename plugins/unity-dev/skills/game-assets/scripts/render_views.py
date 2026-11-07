"""Renders a model from several angles, and close-ups, into one contact sheet image for a visual check.

Run it as the game-assets guide's "Running the scripts" describes. Settings:
    OUTPUT_DIR = "/abs/path"   required; the sheet is written here
    TARGETS = ["Crate"]        default: selected objects, else all meshes
    PRESET = "PROP"            "PROP": front, left, back, top and two 3/4 views. "CHARACTER": front, back, left, right,
                               two 3/4 views, top, a floor, and close-ups of the face, top of the head, hands and feet
                               (needs an armature)
    GAME_VIEW = {"yaw": -33, "pitch": 50}  adds a tile from the game camera's direction, in degrees: pitch above the
                               horizon, yaw around the model from its front. The player sees this side and no other
    GAME_PIXELS = 72           adds a tile at the size the model has on screen, in pixels of height, enlarged without
                               smoothing: what the player can actually read. Needs GAME_VIEW
    VIEWS = ["front", "left"]  replaces the preset's views: front, back, left, right, top, bottom, front_left,
                               front_right, back_left, back_right (left is the model's own left, +X)
    CLOSEUPS = [{"label": "buckle", "center": [0, -0.1, 1.0], "size": 0.2, "view": "front"}]  added zoomed tiles;
                               [] turns off the preset's close-ups
    FRAMES = [0, 5, 10]        renders every view at each frame (animation, test poses); default: the current frame
    TILE = 384                 pixels per tile side
    COLUMNS = 4                tiles per row
    COLOR = "TEXTURE"          "TEXTURE" (image textures, else base color), "MATERIAL", "VERTEX", "OBJECT" (a
                               random color per object: shows which part is which), "SINGLE" (clay), "CHECKER" (a grid
                               on the UVs: long cells are stretched texture, cell sizes that differ are uneven density, the
                               same letter in two places is an overlap)
    LIGHT = "STUDIO"           "STUDIO", or "MATCAP" for a clay look that shows dents, bumps and shading errors
    WIREFRAME = False          draws the edges over the surface: topology and density
    FLOOR = None               a floor at z = 0; default: on for CHARACTER
    GRID = None                lines dividing the target's height into this many parts, in front, back and side
                               views: 8 checks an 8-heads-tall figure
    NAME = "sheet"             file name, without .png

Sets `result`: `sheet` (path), `layout` (rows of tile labels, top to bottom) and `size` (pixels). Uses Workbench, a
temporary camera and temporary helper objects, and restores the scene: frame, render settings, shading, visibility,
material colors.
"""

import math
import os
import types

import bpy
import numpy as np
from mathutils import Matrix, Vector

DIRECTIONS = {
    "front": (0.0, -1.0, 0.0), "back": (0.0, 1.0, 0.0), "left": (1.0, 0.0, 0.0), "right": (-1.0, 0.0, 0.0),
    "top": (0.0, 0.0, 1.0), "bottom": (0.0, 0.0, -1.0),
    "front_left": (1.0, -1.0, 0.35), "front_right": (-1.0, -1.0, 0.35),
    "back_left": (1.0, 1.0, 0.35), "back_right": (-1.0, 1.0, 0.35),
}
PRESETS = {
    "PROP": ["front", "left", "back", "top", "front_right", "back_left"],
    "CHARACTER": ["front", "back", "left", "right", "front_left", "back_right", "top"],
}
ORTHOGRAPHIC = {"front", "back", "left", "right", "top", "bottom"}
GRID_VIEWS = {"front", "back", "left", "right"}


def _setting(name, default):
    return globals().get(name, default)


def _rig_helpers():
    path = os.path.join(os.path.dirname(globals().get("__file__", "")), "rig.py")
    if not os.path.exists(path):
        return None
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return types.SimpleNamespace(**namespace)


def _targets(names):
    if names:
        return [bpy.data.objects[name] for name in names]
    selected = list(bpy.context.selected_objects)
    return selected or [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _corners(objects):
    return [o.matrix_world @ Vector(c) for o in objects if o.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"} for c in o.bound_box]


def _bounds(points):
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def _character_closeups(objects, low, high):
    """Face, hands and feet tiles from the armature that deforms the targets."""
    rig = _rig_helpers()
    armature = None
    if rig:
        armature = next((a for a in (rig.deforming_armature(o) for o in objects if o.type == "MESH") if a), None)
    height = high.z - low.z
    if armature is None or rig is None:
        top = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, high.z - height * 0.07))
        return [{"label": "head", "center": top, "size": height * 0.2, "view": "front"},
                {"label": "head_left", "center": top, "size": height * 0.2, "view": "left"}]
    roles = rig.map_roles(armature)
    tiles, hands = [], {}
    if "Head" in roles:
        head = rig.head(armature, roles["Head"])
        center = Vector((head.x, head.y, (head.z + high.z) / 2))
        # Rigs start the head bone anywhere from the top of the neck to the middle of the skull.
        size = max((high.z - head.z) * 1.6, height * 0.16)
        tiles += [{"label": "face", "center": center, "size": size, "view": "front"},
                  {"label": "face_left", "center": center, "size": size, "view": "left"},
                  {"label": "head_top", "center": center, "size": size, "view": "top"}]
    for side in ("Left", "Right"):
        hand = roles.get(f"{side}Hand")
        if hand:
            start = rig.head(armature, hand)
            tips = [rig.tail(armature, roles[r]) for r in roles if r.startswith(side) and r.endswith("Distal")]
            end = sum(tips, Vector()) / len(tips) if tips else rig.tail(armature, hand)
            hands[side] = ((start + end) / 2, max((end - start).length * 1.6, height * 0.08))
            tiles.append({"label": f"{side.lower()}_hand_top", "center": hands[side][0], "size": hands[side][1], "view": "top"})
    if "Left" in hands:
        tiles.append({"label": "left_hand_bottom", "center": hands["Left"][0], "size": hands["Left"][1], "view": "bottom"})
    feet = [rig.head(armature, roles[r]) for r in ("LeftFoot", "RightFoot") if r in roles]
    if feet:
        center = sum(feet, Vector()) / len(feet)
        center.z = low.z + height * 0.05
        tiles.append({"label": "feet_front", "center": center, "size": height * 0.3, "view": "front"})
    return tiles


def _helper_material(name, rgba):
    material = bpy.data.materials.new(name)
    material.diffuse_color = rgba
    return material


def _show_base_colors(objects):
    """Workbench draws a material's viewport color, which Blender doesn't sync with the Principled BSDF's base color.
    Copies the base color over for the render and returns the colors to restore."""
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


def _show_checker(objects, created):
    """Puts a lettered grid on every target's UVs, and returns what it replaced."""
    image = bpy.data.images.new("ValidationChecker", 1024, 1024)
    image.generated_type = "COLOR_GRID"
    material = bpy.data.materials.new("ValidationChecker")
    if bpy.app.version < (5, 0, 0):
        material.use_nodes = True
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    material.node_tree.nodes.active = node
    created["materials"].append(material)
    created["images"].append(image)
    replaced = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        if not obj.material_slots:
            obj.data.materials.append(material)
            replaced.append((obj, None, None, None))
            continue
        for index, slot in enumerate(obj.material_slots):
            replaced.append((obj, index, slot.link, slot.material))
            slot.link = "OBJECT"
            slot.material = material
    return replaced


def _restore_materials(replaced):
    for obj, index, link, material in replaced:
        if index is None:
            obj.data.materials.pop()
        else:
            slot = obj.material_slots[index]
            slot.material = None
            slot.link = link
            if link == "OBJECT":
                slot.material = material


def _add_helpers(objects, low, high, floor, grid, wire, created):
    """Temporary floor, grid bars and wireframe copies. Returns (grid objects, wire objects)."""
    scene = bpy.context.scene
    size = max((high - low).length, 1e-3)
    center = (low + high) / 2
    grid_objects, wire_objects = [], []

    def add_box(name, location, dimensions, material):
        mesh = bpy.data.meshes.new(name)
        x, y, z = (d / 2 for d in dimensions)
        verts = [(sx * x, sy * y, sz * z) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        mesh.from_pydata(verts, [], faces)
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        obj.location = location
        scene.collection.objects.link(obj)
        created["objects"].append(obj)
        created["meshes"].append(mesh)
        return obj

    if floor:
        material = _helper_material("ValidationFloor", (0.35, 0.37, 0.4, 1.0))
        created["materials"].append(material)
        extent = max(high.x - low.x, high.y - low.y) * 1.6 + size * 0.2
        add_box("ValidationFloor", (center.x, center.y, -size * 0.0025), (extent, extent, size * 0.005), material)
    if grid:
        material = _helper_material("ValidationGrid", (0.85, 0.1, 0.1, 1.0))
        created["materials"].append(material)
        height = high.z - low.z
        width = max(high.x - low.x, high.y - low.y) * 1.3
        for k in range(int(grid) + 1):
            z = low.z + height * k / grid
            grid_objects.append(add_box(f"ValidationGrid{k}", (center.x, center.y, z), (width, width, size * 0.002), material))
    if wire:
        material = _helper_material("ValidationWire", (0.02, 0.02, 0.02, 1.0))
        created["materials"].append(material)
        for obj in objects:
            if obj.type != "MESH":
                continue
            copy = obj.copy()
            copy.name = obj.name + "_ValidationWire"
            scene.collection.objects.link(copy)
            modifier = copy.modifiers.new("ValidationWire", "WIREFRAME")
            modifier.thickness = size * 0.0012
            modifier.use_replace = True
            modifier.use_even_offset = True
            if copy.material_slots:
                for slot in copy.material_slots:
                    slot.link = "OBJECT"  # the shared mesh keeps its own materials
                    slot.material = material
            else:
                copy.data = obj.data.copy()
                copy.data.materials.append(material)
                created["meshes"].append(copy.data)
            created["objects"].append(copy)
            wire_objects.append(copy)
    return grid_objects, wire_objects


def _game_direction(game_view):
    yaw, pitch = math.radians(game_view["yaw"]), math.radians(game_view["pitch"])
    return (math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch))


def _render_tile(scene, camera, camera_data, path, view, center, size, orthographic):
    direction = Vector(DIRECTIONS[view]).normalized()
    camera_data.type = "ORTHO" if orthographic else "PERSP"
    camera_data.ortho_scale = size
    camera_data.lens = 50.0
    distance = size * (3.0 if orthographic else 1.9)
    camera.location = center + direction * distance
    # Image up is world +Z; looking straight down or up it is +Y, so the model's front (-Y) is at the bottom.
    up = Vector((0.0, 1.0, 0.0)) if abs(direction.z) > 0.99 else Vector((0.0, 0.0, 1.0))
    back = direction
    right = up.cross(back).normalized()
    camera.rotation_euler = Matrix((right, back.cross(right), back)).transposed().to_euler()
    camera_data.clip_start = distance * 0.01
    camera_data.clip_end = distance * 4.0
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _compose(paths_by_row, tile, output):
    rows = []
    gap = 4
    for row in paths_by_row:
        images = []
        for path in row:
            image = bpy.data.images.load(path, check_existing=False)
            side = image.size[0]
            pixels = np.empty(side * side * 4, dtype=np.float32)
            image.pixels.foreach_get(pixels)
            bpy.data.images.remove(image)
            pixels = np.flipud(pixels.reshape(side, side, 4))
            if side != tile:  # a tile at on-screen size, enlarged without smoothing
                nearest = (np.arange(tile) * side // tile).astype(int)
                pixels = pixels[nearest][:, nearest]
            images.append(pixels)
        rows.append(images)
    columns = max(len(r) for r in rows)
    width = columns * tile + (columns - 1) * gap
    height = len(rows) * tile + (len(rows) - 1) * gap
    sheet = np.zeros((height, width, 4), dtype=np.float32)
    sheet[..., 3] = 1.0
    sheet[..., :3] = 0.9
    for r, images in enumerate(rows):
        for c, pixels in enumerate(images):
            y, x = r * (tile + gap), c * (tile + gap)
            sheet[y:y + tile, x:x + tile] = pixels
    image = bpy.data.images.new("ValidationSheet", width, height, alpha=False)
    image.pixels.foreach_set(np.flipud(sheet).ravel())
    image.filepath_raw = output
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return [width, height]


def render_views():
    scene = bpy.context.scene
    output_dir = _setting("OUTPUT_DIR", None)
    if not output_dir:
        raise ValueError("OUTPUT_DIR is required")
    os.makedirs(output_dir, exist_ok=True)
    objects = _targets(_setting("TARGETS", None))
    preset = _setting("PRESET", "PROP")
    views = _setting("VIEWS", None) or PRESETS[preset]
    frames = _setting("FRAMES", None) or [scene.frame_current]
    tile = int(_setting("TILE", 384))
    columns = int(_setting("COLUMNS", 4))
    color = _setting("COLOR", "TEXTURE")
    floor = _setting("FLOOR", None)
    floor = preset == "CHARACTER" if floor is None else floor
    grid = _setting("GRID", None)
    game_view = _setting("GAME_VIEW", None)
    game_pixels = _setting("GAME_PIXELS", None)
    if game_pixels and not game_view:
        raise ValueError("GAME_PIXELS needs GAME_VIEW")
    if game_view:
        DIRECTIONS["game"] = _game_direction(game_view)
        DIRECTIONS["game_on_screen"] = DIRECTIONS["game"]
        ORTHOGRAPHIC.add("game_on_screen")
        views = list(views) + ["game"] + (["game_on_screen"] if game_pixels else [])

    shading = scene.display.shading
    image = scene.render.image_settings
    saved = {
        "frame": scene.frame_current, "camera": scene.camera, "engine": scene.render.engine,
        "x": scene.render.resolution_x, "y": scene.render.resolution_y, "percentage": scene.render.resolution_percentage,
        "path": scene.render.filepath, "format": image.file_format, "color_mode": image.color_mode,
        "color_depth": image.color_depth, "light": shading.light, "studio_light": shading.studio_light,
        "color_type": shading.color_type, "cavity": shading.show_cavity,
        "hidden": {o.name: o.hide_render for o in scene.objects},
    }
    created = {"objects": [], "meshes": [], "materials": [], "images": []}
    material_colors = {}
    replaced = []
    camera_data = bpy.data.cameras.new("ValidationCamera")
    camera = bpy.data.objects.new("ValidationCamera", camera_data)
    scene.collection.objects.link(camera)
    tiles_dir = os.path.join(output_dir, ".tiles")
    os.makedirs(tiles_dir, exist_ok=True)
    layout, paths = [], []
    try:
        corners = []
        for frame in frames:
            scene.frame_set(frame)
            corners += _corners(objects)
        low, high = _bounds(corners)
        closeups = _setting("CLOSEUPS", None)
        if closeups is None:
            closeups = _character_closeups(objects, low, high) if preset == "CHARACTER" else []
        for obj in scene.objects:
            if obj.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"} and obj not in objects:
                obj.hide_render = True
        grid_objects, _ = _add_helpers(objects, low, high, floor, grid, _setting("WIREFRAME", False), created)
        scene.camera = camera
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = scene.render.resolution_y = tile
        scene.render.resolution_percentage = 100
        image.file_format = "PNG"
        image.color_mode = "RGB"
        # Clay ("SINGLE") is drawn as material colors, so the helpers keep theirs.
        shading.color_type = {"SINGLE": "MATERIAL", "OBJECT": "RANDOM", "CHECKER": "TEXTURE"}.get(color, color)
        shading.show_cavity = True
        if _setting("LIGHT", "STUDIO") == "MATCAP":
            shading.light = "MATCAP"
            shading.studio_light = "clay_studio.exr" if "clay_studio.exr" in [s.name for s in bpy.context.preferences.studio_lights] else shading.studio_light
        else:
            shading.light = "STUDIO"
        if color == "CHECKER":
            replaced = _show_checker(objects, created)
        elif color in ("TEXTURE", "MATERIAL"):
            material_colors = _show_base_colors(objects)
        elif color == "SINGLE":
            for obj in objects:
                for slot in getattr(obj, "material_slots", ()):
                    if slot.material and slot.material.name not in material_colors:
                        material_colors[slot.material.name] = tuple(slot.material.diffuse_color)
                        slot.material.diffuse_color = (0.8, 0.78, 0.75, 1.0)

        entries = [(view, None) for view in views] + [(c.get("view", "front"), c) for c in closeups]
        for frame in frames:
            scene.frame_set(frame)
            for view, closeup in entries:
                if closeup is None:
                    orthographic = view in ORTHOGRAPHIC
                    direction = Vector(DIRECTIONS[view]).normalized()
                    # Fit the tile to the target's extent across the view.
                    right = direction.cross(Vector((0.0, 0.0, 1.0)))
                    right = right.normalized() if right.length > 1e-6 else Vector((1.0, 0.0, 0.0))
                    up = right.cross(direction).normalized()
                    center = (low + high) / 2
                    extent = max(max(abs((p - center).dot(right)) for p in corners), max(abs((p - center).dot(up)) for p in corners))
                    size = extent * 2.2 if orthographic else (high - low).length * 1.05
                    label = view
                else:
                    orthographic, center, size = True, Vector(closeup["center"]), closeup["size"]
                    label = closeup.get("label", "closeup")
                for obj in grid_objects:
                    obj.hide_render = closeup is not None or view not in GRID_VIEWS
                if len(frames) > 1:
                    label = f"{label}@{frame}"
                path = os.path.join(tiles_dir, f"{len(paths):03d}.png")
                pixels = int(game_pixels * 1.1) if view == "game_on_screen" and closeup is None else tile
                scene.render.resolution_x = scene.render.resolution_y = pixels
                _render_tile(scene, camera, camera_data, path, view, center, size, orthographic)
                paths.append(path)
                layout.append(label)
        rows = [paths[i:i + columns] for i in range(0, len(paths), columns)]
        labels = [layout[i:i + columns] for i in range(0, len(layout), columns)]
        output = os.path.join(output_dir, _setting("NAME", "sheet") + ".png")
        size = _compose(rows, tile, output)
    finally:
        _restore_materials(replaced)
        for name, diffuse in material_colors.items():
            bpy.data.materials[name].diffuse_color = diffuse
        for obj in created["objects"]:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in created["meshes"]:
            bpy.data.meshes.remove(mesh)
        for material in created["materials"]:
            bpy.data.materials.remove(material)
        for picture in created["images"]:
            bpy.data.images.remove(picture)
        shading.light = saved["light"]
        try:
            shading.studio_light = saved["studio_light"]
        except TypeError:
            pass
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
        scene.frame_set(saved["frame"])
        for path in paths:
            if os.path.exists(path):
                os.remove(path)
        if os.path.isdir(tiles_dir) and not os.listdir(tiles_dir):
            os.rmdir(tiles_dir)
    return {"sheet": output, "layout": labels, "size": size}


result = render_views()
