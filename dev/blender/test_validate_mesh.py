# Runs game-assets/scripts/validate_mesh.py against meshes with known defects and checks each report.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <validate_mesh.py>
import json
import warnings
import math
import sys

import bmesh
import bpy

script = open(sys.argv[sys.argv.index("--") + 1]).read()


def clear():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def from_bmesh(name, build, uv=True):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if uv:
        mesh.uv_layers.new(name="UVMap")
        # A distinct, non-degenerate UV triangle per face corner.
        for poly in mesh.polygons:
            for k, loop_index in enumerate(poly.loop_indices):
                angle = 2 * math.pi * k / poly.loop_total
                mesh.uv_layers.active.data[loop_index].uv = (0.5 + 0.4 * math.cos(angle), 0.5 + 0.4 * math.sin(angle))
    return obj


def cube(bm, size=1.0):
    bmesh.ops.create_cube(bm, size=size)


def run(name, budget=None):
    g = {"TARGETS": [name]}
    if budget is not None:
        g["TRIANGLE_BUDGET"] = budget
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        exec(compile(script, "validate_mesh.py", "exec"), g)
    for w in caught:
        print("WARNING", w.message)
    return g["result"]


cases = []


def case(label, expected, build_scene, budget=None):
    clear()
    name = build_scene()
    report = run(name, budget)
    found = sorted(report["objects"][0]["issues"].keys()) if report["objects"] else ["<no object>"]
    cases.append({"case": label, "expected": sorted(expected), "found": found, "ok": found == sorted(expected) and report["passed"] == (not expected),
                  "issues": report["objects"][0]["issues"] if report["objects"] else None})


case("clean cube", [], lambda: from_bmesh("Clean", cube).name)


def duplicate_vertex():
    def build(bm):
        cube(bm)
        bm.verts.ensure_lookup_table()
        first = bm.verts[0].co.copy()
        bm.verts.new(first)
        bm.verts.new(first)  # also a loose vertex: two issues expected
    return from_bmesh("DupVert", build).name


case("duplicate + loose vertex", ["duplicate_vertices", "loose_vertices"], duplicate_vertex)


def overlapping_plane():
    def build(bm):
        a = [bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))]
        bm.faces.new(a)
        b = [bm.verts.new(p) for p in ((0.2, 0.2, 0), (1.2, 0.2, 0), (1.2, 1.2, 0), (0.2, 1.2, 0))]
        bm.faces.new(b)
    return from_bmesh("Overlap", build).name


case("overlapping coplanar quads", ["overlapping_coplanar_faces"], overlapping_plane)


def back_to_back():
    def build(bm):
        a = [bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))]
        bm.faces.new(a)
        b = [bm.verts.new(p) for p in ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))]
        bm.faces.new(b)
    return from_bmesh("BackToBack", build).name


# Coincident vertices too, since the second face uses new vertices at the same places.
case("back-to-back quads", ["back_to_back_coplanar_faces", "duplicate_vertices"], back_to_back)


def fin():
    def build(bm):
        v = [bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (0.5, 1, 0), (0.5, -1, 0), (0.5, 0, 1))]
        bm.faces.new((v[0], v[1], v[2]))
        bm.faces.new((v[1], v[0], v[3]))
        bm.faces.new((v[0], v[1], v[4]))
    return from_bmesh("Fin", build).name


case("three faces on one edge", ["non_manifold_edges"], fin)


def loose_edge():
    def build(bm):
        cube(bm)
        a, b = bm.verts.new((3, 0, 0)), bm.verts.new((4, 0, 0))
        bm.edges.new((a, b))
    return from_bmesh("LooseEdge", build).name


case("loose edge", ["loose_edges"], loose_edge)


def zero_area():
    def build(bm):
        cube(bm)
        v = [bm.verts.new(p) for p in ((3, 0, 0), (4, 0, 0), (5, 0, 0))]
        bm.faces.new(v)
    return from_bmesh("ZeroArea", build).name


# A collinear triangle also has no UV area to compare: zero-area faces are skipped by the UV check.
case("collinear triangle", ["zero_area_faces"], zero_area)


def flipped_face():
    def build(bm):
        cube(bm)
        bm.faces.ensure_lookup_table()
        bm.faces[0].normal_flip()
    return from_bmesh("Flipped", build).name


case("cube with one flipped face", ["inconsistent_normals"], flipped_face)


def flipped_open():
    def build(bm):
        v = [bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0), (2, 1, 0), (3, 0, 0), (3, 1, 0))]
        bm.faces.new((v[0], v[1], v[2], v[3]))
        bm.faces.new((v[1], v[4], v[5], v[2]))
        bm.faces.new((v[4], v[6], v[7], v[5]))
        bm.faces.ensure_lookup_table()
        bm.faces[2].normal_flip()
    return from_bmesh("FlippedOpen", build).name


case("open strip with one flipped face", ["inconsistent_normals"], flipped_open)

case("no UV map", ["no_uv_map"], lambda: from_bmesh("NoUV", cube, uv=False).name)


def degenerate_uv():
    obj = from_bmesh("DegenerateUV", cube)
    for loop in obj.data.uv_layers.active.data:
        loop.uv = (0.25, 0.25)
    return obj.name


case("all UVs on one point", ["degenerate_uv_faces"], degenerate_uv)


def scaled():
    obj = from_bmesh("Scaled", cube)
    obj.scale = (2, 2, 2)
    return obj.name


case("unapplied scale", ["transforms_not_applied"], scaled)


def rotated_quaternion():
    obj = from_bmesh("RotatedQ", cube)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = (0.7071, 0.7071, 0, 0)
    return obj.name


case("unapplied quaternion rotation", ["transforms_not_applied"], rotated_quaternion)

case("over budget (12 > 10)", ["over_triangle_budget"], lambda: from_bmesh("Budget", cube).name, budget=10)
case("within budget (12 <= 12)", [], lambda: from_bmesh("Budget2", cube).name, budget=12)


def mirrored_onto_itself():
    obj = from_bmesh("Mirror", cube)
    modifier = obj.modifiers.new("Mirror", "MIRROR")
    modifier.use_mirror_merge = False
    return obj.name


# The mirror copy lands exactly on the original: only visible if modifiers are applied first.
case("modifier output is checked", ["duplicate_vertices", "overlapping_coplanar_faces"], mirrored_onto_itself)



def run_many(names, **settings):
    g = {"TARGETS": names}
    g.update(settings)
    exec(compile(script, "validate_mesh.py", "exec"), g)
    return g["result"]


def scene_case(label, expected, build_scene, **settings):
    """expected: object name -> sorted issue names."""
    clear()
    names = build_scene()
    report = run_many(names, **settings)
    found = {o["name"]: sorted(o["issues"]) for o in report["objects"]}
    ok = found == {k: sorted(v) for k, v in expected.items()} and report["passed"] == (not any(expected.values()))
    cases.append({"case": label, "expected": expected, "found": found, "ok": ok, "issues": [o["issues"] for o in report["objects"]]})


def quad(bm, z, size=1.0, flip=False, shift=0.0):
    points = [(shift, 0, z), (shift + size, 0, z), (shift + size, size, z), (shift, size, z)]
    verts = [bm.verts.new(p) for p in (reversed(points) if flip else points)]
    bm.faces.new(verts)


def floor_and_box():
    floor = from_bmesh("Floor", lambda bm: quad(bm, 0.0, size=2.0, shift=-0.5))
    box = from_bmesh("Box", cube)
    box.location.z = 0.5  # its bottom face lies on the floor, facing down: back to back with the floor
    bpy.ops.object.select_all(action="DESELECT")
    box.select_set(True)
    bpy.context.view_layer.objects.active = box
    bpy.ops.object.transform_apply(location=True)
    return ["Floor", "Box"]


# Facing opposite ways, the two faces never show at once with back faces culled: information only.
scene_case("box standing on a floor", {"Floor": [], "Box": []}, floor_and_box)


def stacked_objects(gap):
    def build():
        from_bmesh("Lower", lambda bm: quad(bm, 0.0))
        from_bmesh("Upper", lambda bm: quad(bm, gap, shift=0.3))
        return ["Lower", "Upper"]
    return build


scene_case("two objects' faces 0.5 mm apart", {"Lower": ["z_fighting"], "Upper": ["z_fighting"]}, stacked_objects(0.0005))
scene_case("decal 5 mm above a surface", {"Lower": [], "Upper": []}, stacked_objects(0.005))
scene_case("decal 5 mm above, with a 1 cm z-fighting distance", {"Lower": ["z_fighting"], "Upper": ["z_fighting"]},
           stacked_objects(0.005), ZFIGHT_DISTANCE=0.01)


def near_coplanar_in_one_object():
    def build(bm):
        quad(bm, 0.0)
        quad(bm, 0.0005, shift=0.3)
    from_bmesh("Layered", build)
    return ["Layered"]


scene_case("one object, faces 0.5 mm apart", {"Layered": ["z_fighting"]}, near_coplanar_in_one_object)


def lods():
    from_bmesh("Rock_LOD0", cube)
    from_bmesh("Rock_LOD1", cube)
    return ["Rock_LOD0", "Rock_LOD1"]


scene_case("LOD siblings in the same place", {"Rock_LOD0": [], "Rock_LOD1": []}, lods)


def grid():
    def build(bm):
        bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=1.0)
    obj = from_bmesh("Grid", build, uv=False)
    layer = obj.data.uv_layers.new(name="UVMap")
    for loop in obj.data.loops:  # one continuous island: a planar projection
        co = obj.data.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = ((co.x + 1) / 2, (co.y + 1) / 2)
    return ["Grid"]


scene_case("flat plane split into 162 triangles", {"Grid": ["over_tessellated_flat_areas"]}, grid)
scene_case("flat plane that deforms", {"Grid": []}, grid, FLAT_DETAIL=True)

failed = [c for c in cases if not c["ok"]]
for c in cases:
    print("CASE", "ok  " if c["ok"] else "FAIL", c["case"], "expected", c["expected"], "found", c["found"])
if failed:
    raise AssertionError(f"{len(failed)} of {len(cases)} cases failed")
