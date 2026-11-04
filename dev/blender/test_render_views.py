# Runs game-assets/scripts/render_views.py and checks the contact sheet: its size and layout, the colors in its
# tiles, the character preset's close-ups, frames, and that the scene is restored with no helper left behind.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <render_views.py> <output dir>
import json
import os
import sys
import warnings

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mannequin  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
script_path, output_dir = args[0], args[1]
script = open(script_path).read()
problems = []


def run(**settings):
    namespace = {"__file__": script_path, "OUTPUT_DIR": output_dir}
    namespace.update(settings)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        exec(compile(script, script_path, "exec"), namespace)
    problems.extend(f"warning: {w.message}" for w in caught)
    return namespace["result"]


def snapshot(material=None):
    scene = bpy.context.scene
    return {
        "format": scene.render.image_settings.file_format, "color_type": scene.display.shading.color_type,
        "light": scene.display.shading.light, "engine": scene.render.engine,
        "camera": scene.camera.name if scene.camera else None, "frame": scene.frame_current,
        "resolution": (scene.render.resolution_x, scene.render.resolution_y),
        "diffuse": tuple(round(c, 4) for c in material.diffuse_color) if material else None,
        "objects": sorted(o.name for o in bpy.data.objects), "meshes": sorted(m.name for m in bpy.data.meshes),
        "materials": sorted(m.name for m in bpy.data.materials), "cameras": sorted(c.name for c in bpy.data.cameras),
        "images": sorted(i.name for i in bpy.data.images),
        "hidden": {o.name: o.hide_render for o in bpy.data.objects},
    }


def tile_centers(path, rows, columns, tile, gap=4):
    image = bpy.data.images.load(path, check_existing=False)
    width, height = image.size
    pixels = image.pixels[:]
    bpy.data.images.remove(image)
    centers = []
    for r in range(rows):
        for c in range(columns):
            x = c * (tile + gap) + tile // 2
            y = height - 1 - (r * (tile + gap) + tile // 2)  # pixel rows start at the bottom
            index = (y * width + x) * 4
            centers.append([round(v, 3) for v in pixels[index:index + 3]])
    return (width, height), centers


def expect(condition, message):
    if not condition:
        problems.append(message)


# A red cube next to a blue one that the sheet must hide.
mannequin.clear()


def colored_cube(name, rgba, location):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    material = bpy.data.materials.new(name)
    if not material.node_tree:
        material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    obj.data.materials.append(material)
    return obj, material


red, red_material = colored_cube("Red", (1, 0, 0, 1), (0, 0, 0))
colored_cube("Blue", (0, 0, 1, 1), (0.8, 0, 0))
scene = bpy.context.scene
scene.render.image_settings.file_format = "JPEG"
scene.display.shading.color_type = "OBJECT"
before = snapshot(red_material)
result = run(TARGETS=["Red"], TILE=64, WIREFRAME=True, GRID=4)
after = snapshot(red_material)
expect(before == after, f"scene not restored: {json.dumps({k: (before[k], after[k]) for k in before if before[k] != after[k]})}")
expect(result["layout"] == [["front", "left", "back", "top"], ["front_right", "back_left"]], f"prop layout {result['layout']}")
size, centers = tile_centers(result["sheet"], 2, 4, 64)
expect(size == (4 * 64 + 3 * 4, 2 * 64 + 4) and result["size"] == list(size), f"sheet size {size}, reported {result['size']}")
expect(open(result["sheet"], "rb").read(8) == b"\x89PNG\r\n\x1a\n", "the sheet isn't a PNG")
expect(all(c[0] > 0.3 and c[0] > 2 * c[2] and c[0] > 2 * c[1] for c in centers[:6]), f"red cube not in every tile: {centers[:6]}")
expect(not os.path.exists(os.path.join(output_dir, ".tiles")), "tile files left behind")

# The character preset on the mannequin, at two frames.
mannequin.clear()
body, rig = mannequin.build()
before = snapshot()
result = run(TARGETS=["Body"], PRESET="CHARACTER", TILE=48, FRAMES=[0, 1], NAME="character", WIREFRAME=True, GRID=8, LIGHT="MATCAP")
after = snapshot()
expect(before == after, f"scene not restored after the character preset: {[k for k in before if before[k] != after[k]]}")
labels = [label for row in result["layout"] for label in row]
expected = ["front", "back", "left", "right", "front_left", "back_right", "top", "face", "face_left", "head_top", "left_hand_top",
            "right_hand_top", "left_hand_bottom", "feet_front"]
expect(labels == [f"{name}@{frame}" for frame in (0, 1) for name in expected], f"character layout {result['layout']}")
expect(os.path.exists(result["sheet"]), "no character sheet")

# The game camera's view, and the model at the size it has on screen: few pixels, enlarged without smoothing.
result = run(TARGETS=["Body"], VIEWS=["front"], CLOSEUPS=[], TILE=96, COLUMNS=3, GAME_VIEW={"yaw": -30, "pitch": 55}, GAME_PIXELS=12, NAME="game", COLOR="OBJECT")
expect(result["layout"] == [["front", "game", "game_on_screen"]], f"game layout {result['layout']}")
image = bpy.data.images.load(result["sheet"], check_existing=False)
width, height = image.size
pixels = np.array(image.pixels[:]).reshape(height, width, -1)
bpy.data.images.remove(image)
on_screen = pixels[:96, 2 * (96 + 4):2 * (96 + 4) + 96, :3]
blocks = on_screen[::8, ::8]
expect(len({tuple(np.round(p, 3)) for p in blocks.reshape(-1, 3)}) > 1, "the on-screen tile is empty")
row = np.round(on_screen[48], 3)
runs = sum(1 for a, b in zip(row, row[1:]) if (a != b).any())
expect(runs <= 13, f"the on-screen tile isn't blocky: {runs} changes along a row of a 13-pixel render")
try:
    run(TARGETS=["Body"], VIEWS=["front"], GAME_PIXELS=12)
    expect(False, "GAME_PIXELS without GAME_VIEW was accepted")
except ValueError:
    pass

print("RENDER", json.dumps({"problems": problems}))
if problems:
    raise AssertionError("; ".join(problems))
