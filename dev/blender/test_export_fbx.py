# Runs modeling/scripts/export_fbx.py: it refuses assets that fail their checks, exports the rest, and the FBX it
# writes imports back with the expected bones, weights and animation frames.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <export_fbx.py> <output dir>
import json
import os
import sys
import types

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gait  # noqa: E402
import mannequin  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
script_path, output_dir = args[0], args[1]
script = open(script_path).read()
rig_path = os.path.join(os.path.dirname(script_path), "rig.py")
with open(rig_path) as source:
    helpers_namespace = {"__file__": rig_path}
    exec(compile(source.read(), rig_path, "exec"), helpers_namespace)
helpers = types.SimpleNamespace(**helpers_namespace)
problems = []


def export(**settings):
    namespace = {"__file__": script_path}
    namespace.update(settings)
    exec(compile(script, script_path, "exec"), namespace)
    return namespace["result"]


def expect(condition, message):
    if not condition:
        problems.append(message)


def cube(name, duplicate_face=False):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if duplicate_face:
        bm.faces.ensure_lookup_table()
        bm.faces.new([bm.verts.new(v.co) for v in bm.faces[0].verts])
    bm.to_mesh(mesh)
    bm.free()
    mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for k, loop in enumerate(poly.loop_indices):
            mesh.uv_layers.active.data[loop].uv = ((k in (1, 2)) * 0.5, (k in (2, 3)) * 0.5)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def reimport(path):
    mannequin.clear()
    bpy.ops.import_scene.fbx(filepath=path)
    return list(bpy.data.objects)


path = os.path.join(output_dir, "Crate.fbx")
mannequin.clear()
cube("Crate")
result = export(TARGETS=["Crate"], FILEPATH=path)
expect(result["exported"] == path and os.path.getsize(path) > 0, f"clean cube not exported: {result['issues']}")

size = max(max(o.dimensions) for o in reimport(path) if o.type == "MESH")
expect(abs(size - 1.0) < 0.01, f"the default export changed the cube's size: {size}")

# FBX lays another engine's exporter options over the defaults: a scale here, read back from the file. The file stays the script's.
mannequin.clear()
cube("Crate")
scaled = os.path.join(output_dir, "Scaled.fbx")
result = export(TARGETS=["Crate"], FILEPATH=scaled, FBX={"global_scale": 2.0, "filepath": os.path.join(output_dir, "Elsewhere.fbx")})
expect(result["exported"] == scaled and os.path.exists(scaled), f"an FBX option moved or blocked the export: {result['exported']}")
expect(not os.path.exists(os.path.join(output_dir, "Elsewhere.fbx")), "FBX changed the file path")
size = max(max(o.dimensions) for o in reimport(scaled) if o.type == "MESH")
expect(abs(size - 2.0) < 0.01, f"FBX's global_scale didn't reach the file: {size}")

mannequin.clear()
cube("Broken", duplicate_face=True)
broken = os.path.join(output_dir, "Broken.fbx")
if os.path.exists(broken):
    os.remove(broken)
result = export(TARGETS=["Broken"], FILEPATH=broken)
expect(result["exported"] is None and not os.path.exists(broken), "a cube with a duplicate face was exported")
# The copy has its own vertices: reported as overlapping coplanar faces on duplicate vertices.
expect("overlapping_coplanar_faces" in result["issues"].get("Broken", {}), f"duplicate face not reported: {result['issues']}")
result = export(TARGETS=["Broken"], FILEPATH=broken, FORCE=True)
expect(result["exported"] == broken and os.path.exists(broken), "FORCE didn't export")

mannequin.clear()
body, rig = mannequin.build()
mannequin.add_uvs(body)
deform = sum(1 for b in rig.data.bones if b.use_deform)
character = os.path.join(output_dir, "Character.fbx")
result = export(TARGETS=["Body"], FILEPATH=character)
expect(result["exported"] == character, f"clean mannequin not exported: {result['issues']}")
objects = reimport(character)
armatures = [o for o in objects if o.type == "ARMATURE"]
meshes = [o for o in objects if o.type == "MESH"]
expect(len(armatures) == 1 and len(armatures[0].data.bones) == deform, f"bones after import: {[len(a.data.bones) for a in armatures]}, expected {deform}")
unweighted = [v.index for v in meshes[0].data.vertices if not any(g.weight > 0 for g in v.groups)] if len(meshes) == 1 else None
expect(unweighted == [] and any(m.type == "ARMATURE" for m in meshes[0].modifiers), f"skin weights missing after import: {unweighted}")

mannequin.clear()
body, rig = mannequin.build()
mannequin.add_uvs(body)
gait.key_walk(rig, rig_helpers=helpers)
walk = os.path.join(output_dir, "Character@Walk.fbx")
scene_range = (bpy.context.scene.frame_start, bpy.context.scene.frame_end)
result = export(TARGETS=["Body"], FILEPATH=walk, ANIMATION=True)
expect(result["exported"] == walk, f"walk not exported: {result['issues']}")
expect((bpy.context.scene.frame_start, bpy.context.scene.frame_end) == scene_range, "scene frame range not restored")
reimport(walk)
actions = list(bpy.data.actions)
ranges = [tuple(round(f) for f in a.frame_range) for a in actions]
expect(len(actions) == 1 and ranges[0][1] - ranges[0][0] == gait.FRAMES, f"imported animation ranges {ranges}, expected {gait.FRAMES} frames")

mannequin.clear()
body, rig = mannequin.build()
mannequin.add_uvs(body)
body.shape_key_add(name="Basis")
body.modifiers.new("Mirror", "MIRROR")
result = export(TARGETS=["Body"], FILEPATH=os.path.join(output_dir, "Keys.fbx"))
expect(result["exported"] is None and "modifiers_with_shape_keys" in result["issues"], f"shape keys with a modifier: {result['issues']}")

print("EXPORT", json.dumps({"problems": problems}))
if problems:
    raise AssertionError("; ".join(problems))
