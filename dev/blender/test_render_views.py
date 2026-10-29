# Runs game-assets/scripts/render_views.py on a red cube next to a hidden-from-the-check blue one, and checks the
# files, the colors in them and that the scene is restored.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <render_views.py> <output dir>
import json
import os
import sys
import warnings

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
script, output_dir = open(args[0]).read(), args[1]

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


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
blue, _ = colored_cube("Blue", (0, 0, 1, 1), (0.8, 0, 0))  # overlaps the red cube's front view if not hidden

scene = bpy.context.scene
scene.render.image_settings.file_format = "JPEG"
scene.display.shading.color_type = "OBJECT"
before = {
    "format": scene.render.image_settings.file_format,
    "color_type": scene.display.shading.color_type,
    "engine": scene.render.engine,
    "camera": scene.camera.name if scene.camera else None,
    "diffuse": tuple(round(c, 4) for c in red_material.diffuse_color),
    "objects": sorted(o.name for o in bpy.data.objects),
    "blue_hidden": blue.hide_render,
}

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    g = {"OUTPUT_DIR": output_dir, "TARGETS": ["Red"], "RESOLUTION": 64}
    exec(compile(script, "render_views.py", "exec"), g)

after = {
    "format": scene.render.image_settings.file_format,
    "color_type": scene.display.shading.color_type,
    "engine": scene.render.engine,
    "camera": scene.camera.name if scene.camera else None,
    "diffuse": tuple(round(c, 4) for c in red_material.diffuse_color),
    "objects": sorted(o.name for o in bpy.data.objects),
    "blue_hidden": blue.hide_render,
}


def center_rgb(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    pixels = image.pixels[:]
    index = ((height // 2) * width + width // 2) * 4
    rgb = [round(v, 3) for v in pixels[index:index + 3]]
    bpy.data.images.remove(image)
    return rgb


files = g["result"]["files"]
colors = {os.path.basename(p): center_rgb(p) for p in files if os.path.exists(p)}
report = {
    "files": [os.path.basename(p) for p in files],
    "all_exist": all(os.path.exists(p) for p in files),
    "png_signature": all(open(p, "rb").read(8) == b"\x89PNG\r\n\x1a\n" for p in files if os.path.exists(p)),
    "center_colors": colors,
    "red_in_every_view": all(c[0] > 0.3 and c[0] > 2 * c[2] and c[0] > 2 * c[1] for c in colors.values()),
    "restored": before == after,
    "before": before,
    "after": after,
    "warnings": [str(w.message) for w in caught],
}
print("RENDER", json.dumps(report))
problems = [key for key in ("all_exist", "png_signature", "red_in_every_view", "restored") if not report[key]]
if problems or report["warnings"]:
    raise AssertionError(f"failed: {problems}, warnings: {report['warnings']}")
