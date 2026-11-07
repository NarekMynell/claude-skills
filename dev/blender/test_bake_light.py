# Runs game-assets/scripts/bake_light.py: a box on a ground under a sun. The shadowed part of the ground must bake darker
# than the lit part, into vertex colors and into a texture, and the scene must be restored.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <bake_light.py> <output dir>
import json
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
script_path, output_dir = args[0], args[1]
script = open(script_path).read()
problems = []


def run(**settings):
    namespace = {"__file__": script_path}
    namespace.update(settings)
    exec(compile(script, script_path, "exec"), namespace)
    return namespace["result"]


def expect(condition, message):
    if not condition:
        problems.append(message)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_grid_add(x_subdivisions=20, y_subdivisions=20, size=10)
ground = bpy.context.active_object
ground.name = "Ground"
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.uv.smart_project(island_margin=0.02)
bpy.ops.object.mode_set(mode="OBJECT")
material = bpy.data.materials.new("Grass")
material.use_nodes = True
material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.6, 0.2, 1.0)
ground.data.materials.append(material)
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
bpy.ops.object.light_add(type="SUN", location=(0, 0, 10), rotation=(0.6, 0.0, 0.0))
bpy.context.active_object.data.energy = 4.0
scene = bpy.context.scene
engine = scene.render.engine

result = run(TARGETS=["Ground"], SAMPLES=4, NAME="Light")
expect(scene.render.engine == engine, "the render engine wasn't restored")
attribute = ground.data.color_attributes.get("Light")
expect(attribute is not None, "no color attribute")
if attribute:
    # The sun leans from -Y, so the shadow falls on the +Y side of the box. A corner attribute: one color per loop.
    colors = {}
    for loop in ground.data.loops:
        colors[loop.vertex_index] = attribute.data[loop.index].color[1]
    near = [colors[v.index] for v in ground.data.vertices if abs(v.co.x) < 0.5 and 1.2 < v.co.y < 2.5]
    far = [colors[v.index] for v in ground.data.vertices if abs(v.co.x) < 0.5 and -4.5 < v.co.y < -2.0]
    shade, sun = sum(near) / len(near), sum(far) / len(far)
    expect(shade < 0.6 * sun, f"the shadow didn't bake: shaded {shade:.3f}, lit {sun:.3f}")

result = run(TARGETS=["Ground"], INTO="TEXTURE", SIZE=64, SAMPLES=4, OUTPUT_DIR=output_dir)
path = result["baked"]["Ground"]
expect(os.path.exists(path), "no texture written")
expect(not [n for n in material.node_tree.nodes if n.name == "BakeTarget"], "bake nodes left in the material")
left = [i.name for i in bpy.data.images if i.name.startswith("Ground_")]
expect(not left, f"images left behind: {left}")

try:
    bpy.ops.mesh.primitive_cube_add()
    bpy.context.active_object.name = "NoUvs"
    uv_layers = bpy.context.active_object.data.uv_layers
    while uv_layers:
        uv_layers.remove(uv_layers[0])
    run(TARGETS=["NoUvs"])
    expect(False, "an object without UVs was accepted")
except ValueError:
    pass

# A layout whose faces share texels bakes one face's light onto another.
try:
    bpy.ops.mesh.primitive_cube_add(location=(20, 0, 0))
    stacked = bpy.context.active_object
    stacked.name = "Stacked"
    stacked.data.materials.append(material)
    layer = stacked.data.uv_layers.active or stacked.data.uv_layers.new()
    for poly in stacked.data.polygons:
        for k, loop_index in enumerate(poly.loop_indices):
            layer.data[loop_index].uv = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)][k]
    run(TARGETS=["Stacked"], INTO="TEXTURE", SIZE=64, SAMPLES=1, OUTPUT_DIR=output_dir)
    expect(False, "faces sharing texels were baked")
except ValueError as error:
    expect("own texels" in str(error), f"another refusal: {error}")

print("BAKE", json.dumps({"problems": problems}))
if problems:
    raise AssertionError("; ".join(problems))
