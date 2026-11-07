# Runs game-assets/scripts/validate_mesh.py against meshes with known defects and checks each report.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <validate_mesh.py>
import json
import warnings
import math
import sys

import bmesh
import bpy
import mathutils

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


def unwrap(obj):
    """Each face its own square in a grid on the UV map, as a unique layout has."""
    layer = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")
    count = len(obj.data.polygons)
    side = math.ceil(math.sqrt(count))
    cell = 1.0 / side
    for index, poly in enumerate(obj.data.polygons):
        x, y = (index % side) * cell, (index // side) * cell
        corners = [(x + 0.1 * cell, y + 0.1 * cell), (x + 0.9 * cell, y + 0.1 * cell), (x + 0.9 * cell, y + 0.9 * cell), (x + 0.1 * cell, y + 0.9 * cell)]
        for k, loop_index in enumerate(poly.loop_indices):
            layer.data[loop_index].uv = corners[k % 4]
    return obj


script_path = sys.argv[sys.argv.index("--") + 1]


def run(name, budget=None, **settings):
    g = {"TARGETS": [name], "__file__": script_path}
    g.update(settings)
    if budget is not None:
        g["TRIANGLE_BUDGET"] = budget
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        exec(compile(script, "validate_mesh.py", "exec"), g)
    for w in caught:
        print("WARNING", w.message)
    return g["result"]


cases = []


def _colored():
    obj = from_bmesh("Colored", cube, uv=False)
    obj.data.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    return obj


def _grid_on_a_box(bm):
    """A box whose sides are grids, with a little height so no side is flat."""
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)


def _split_cube(bm):
    """A cube whose six faces don't share vertices, as a file with hard edges has it."""
    for sign in (-1.0, 1.0):
        for axis in range(3):
            u, v = (axis + 1) % 3, (axis + 2) % 3
            points = []
            for du, dv in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
                p = [0.0, 0.0, 0.0]
                p[axis], p[u], p[v] = 0.5 * sign, du, dv
                points.append(p)
            verts = [bm.verts.new(p) for p in (points if sign > 0 else reversed(points))]
            bm.faces.new(verts)


def case(label, expected, build_scene, budget=None, notes=(), **settings):
    clear()
    name = build_scene()
    report = run(name, budget, **settings)
    found = sorted(report["objects"][0]["issues"].keys()) if report["objects"] else ["<no object>"]
    told = report["objects"][0]["notes"] if report["objects"] else {}
    cases.append({"case": label, "expected": sorted(expected), "found": found, "ok": found == sorted(expected) and report["passed"] == (not expected) and all(n in told for n in notes),
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


case("duplicate + loose vertex are leftovers: told, and no failure", [], duplicate_vertex, notes=["duplicate_vertices", "loose_vertices"])


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


# Two-sided foliage is built this way: with back faces culled, one face shows from each side.
case("back-to-back quads", [], back_to_back)


def fin():
    def build(bm):
        v = [bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (0.5, 1, 0), (0.5, -1, 0), (0.5, 0, 1))]
        bm.faces.new((v[0], v[1], v[2]))
        bm.faces.new((v[1], v[0], v[3]))
        bm.faces.new((v[0], v[1], v[4]))
    return from_bmesh("Fin", build).name


case("three faces on one edge is a leftover", [], fin, notes=["non_manifold_edges"])


def loose_edge():
    def build(bm):
        cube(bm)
        a, b = bm.verts.new((3, 0, 0)), bm.verts.new((4, 0, 0))
        bm.edges.new((a, b))
    return from_bmesh("LooseEdge", build).name


case("loose edge is a leftover", [], loose_edge, notes=["loose_edges"])


def zero_area():
    def build(bm):
        cube(bm)
        v = [bm.verts.new(p) for p in ((3, 0, 0), (4, 0, 0), (5, 0, 0))]
        bm.faces.new(v)
    return from_bmesh("ZeroArea", build).name


case("collinear triangle is a leftover", [], zero_area, notes=["zero_area_faces"])


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


case("a palette: all UVs on one color", [], degenerate_uv)
case("the same, for a texture painted on it", ["uv_collapsed"], degenerate_uv, UV_KIND="UNIQUE")
case("vertex colors and no UV map", [], lambda: _colored().name)
case("drawn with a flat color", [], lambda: from_bmesh("Flat", cube, uv=False).name, UV_KIND="NONE")
case("a unique layout", [], lambda: unwrap(from_bmesh("Unique", cube, uv=False)).name, UV_KIND="UNIQUE")
case("a unique layout, read as such", [], lambda: unwrap(from_bmesh("Unique", cube, uv=False)).name)


def collapsed_share(on_line=True, faces=3):
    def build():
        obj = unwrap(from_bmesh("Collapsed", _grid_on_a_box, uv=False))
        layer = obj.data.uv_layers.active
        seen = [poly for poly in obj.data.polygons if poly.normal.z > -0.5]
        for poly in seen[: len(obj.data.polygons) // faces]:
            start = layer.data[poly.loop_indices[0]].uv.copy()
            for k, loop_index in enumerate(poly.loop_indices):
                layer.data[loop_index].uv = (start.x + (0.03 * k if on_line else 0.0), start.y)
        return obj.name
    return build


case("a third of the surface on a line in UV: a smear", ["uv_collapsed"], collapsed_share(), FLAT_DETAIL=True)
case("a third of the surface on one spot: one color, a palette's way", [], collapsed_share(on_line=False), FLAT_DETAIL=True)
case("the same, for a texture painted on it", ["uv_collapsed"], collapsed_share(on_line=False), FLAT_DETAIL=True, UV_KIND="UNIQUE")
case("a twentieth on a line is a note, as a look can tell", [], collapsed_share(faces=20), FLAT_DETAIL=True, notes=["uv_collapsed_share"])
case("and a defect on what is painted", ["uv_collapsed"], collapsed_share(faces=20), FLAT_DETAIL=True, UV_KIND="UNIQUE")


def stretched():
    obj = unwrap(from_bmesh("Stretched", _grid_on_a_box, uv=False))
    layer = obj.data.uv_layers.active
    for poly in list(obj.data.polygons)[: len(obj.data.polygons) // 3]:
        center = sum((layer.data[i].uv.copy() for i in poly.loop_indices), mathutils.Vector((0.0, 0.0))) / poly.loop_total
        for loop_index in poly.loop_indices:
            uv = layer.data[loop_index].uv
            layer.data[loop_index].uv = (uv.x, center.y + (uv.y - center.y) * 0.05)
    return obj.name


case("a third of the surface pulled one way", ["uv_stretched"], stretched, FLAT_DETAIL=True)


def overlapped():
    obj = unwrap(from_bmesh("Overlap", cube, uv=False))
    layer = obj.data.uv_layers.active
    # Half of one island on another.
    first, second = list(obj.data.polygons)[:2]
    for k, (a, b) in enumerate(zip(first.loop_indices, second.loop_indices)):
        layer.data[b].uv = layer.data[a].uv + mathutils.Vector((0.15, 0.0))
    return obj.name


case("islands that lie on each other, for a baked texture", ["uv_overlap"], overlapped, UV_KIND="UNIQUE")
case("the same read from the layout: this much overlap is how an atlas looks", [], overlapped)


def mirrored_islands():
    obj = unwrap(from_bmesh("Mirrored", cube, uv=False))
    layer = obj.data.uv_layers.active
    first, second = list(obj.data.polygons)[:2]
    for a, b in zip(first.loop_indices, second.loop_indices):
        layer.data[b].uv = layer.data[a].uv
    return obj.name


case("mirrored islands on each other are on purpose", [], mirrored_islands)
case("but not under a bake", ["uv_stacked_islands"], mirrored_islands, UV_KIND="UNIQUE")


def tight():
    obj = from_bmesh("Tight", cube, uv=False)
    layer = obj.data.uv_layers.new(name="UVMap")
    side = 3
    cell = 1.0 / side
    for index, poly in enumerate(obj.data.polygons):
        x, y = (index % side) * cell, (index // side) * cell
        corners = [(x, y), (x + cell * 0.999, y), (x + cell * 0.999, y + cell * 0.999), (x, y + cell * 0.999)]
        for k, loop_index in enumerate(poly.loop_indices):
            layer.data[loop_index].uv = corners[k % 4]
    return obj.name


case("islands with no gap between them", ["uv_padding"], tight, UV_KIND="UNIQUE", TEXTURE_SIZE=1024, PADDING=4)
case("islands with a wide gap", [], lambda: unwrap(from_bmesh("Wide", cube, uv=False)).name, UV_KIND="UNIQUE", TEXTURE_SIZE=1024, PADDING=4)


def lightmap_overlap():
    obj = unwrap(from_bmesh("Lit", cube, uv=False))
    second = obj.data.uv_layers.new(name="Light")
    for poly in obj.data.polygons:
        for k, loop_index in enumerate(poly.loop_indices):
            second.data[loop_index].uv = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)][k % 4]
    obj.data.uv_layers.active = obj.data.uv_layers["UVMap"]
    return obj.name


case("a lightmap layout that lies on itself", ["lightmap_uv_overlap"], lightmap_overlap, LIGHTMAP_UV="Light")
case("no such lightmap layout", ["no_lightmap_uv"], lambda: unwrap(from_bmesh("Unlit", cube, uv=False)).name, LIGHTMAP_UV="Light")


def split_flat():
    obj = from_bmesh("SplitFlat", _split_cube, uv=False)
    return unwrap(obj).name


def split_smooth():
    obj = from_bmesh("SplitSmooth", _split_cube, uv=False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return unwrap(obj).name


def seam_on_a_ball():
    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.5)
        meridian = [e for e in bm.edges if all(abs(v.co.y) < 1e-5 and v.co.x > -1e-5 for v in e.verts)]
        bmesh.ops.split_edges(bm, edges=meridian)
    obj = from_bmesh("Ball", build, uv=False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj.name


case("hard edges split by hand: nothing shows on flat faces", [], split_flat, notes=["duplicate_vertices"])
case("the same on smooth faces: still hard edges", [], split_smooth, notes=["duplicate_vertices"])
case("a curve cut in two: a shading seam", ["shading_seam"], seam_on_a_ball, UV_KIND="NONE")


def shaded(build, smooth=True, sharp_corners=False):
    def scene():
        obj = from_bmesh("Shaded", build, uv=False)
        for poly in obj.data.polygons:
            poly.use_smooth = smooth
        if sharp_corners:
            normals = {}
            for poly in obj.data.polygons:
                for key in poly.edge_keys:
                    normals.setdefault(tuple(sorted(key)), []).append(poly.normal.copy())
            for edge in obj.data.edges:
                pair = normals.get(tuple(sorted(edge.vertices)))
                if pair and len(pair) == 2 and pair[0].dot(pair[1]) < 0.5:
                    edge.use_edge_sharp = True
        return obj.name
    return scene


def ball(bm):
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.5)


def beam(bm):
    bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Diagonal((0.04, 0.04, 3.0, 1.0)))


case("a box shaded smooth over its corners", ["smooth_across_corners"], shaded(cube), UV_KIND="NONE")
case("a box shaded smooth, with its corners sharp", [], shaded(cube, sharp_corners=True), UV_KIND="NONE")
case("a box shaded flat", [], shaded(cube, smooth=False), UV_KIND="NONE")
case("a thin beam shaded round: too thin to show", [], shaded(beam), UV_KIND="NONE")
case("a ball shaded smooth", [], shaded(ball), UV_KIND="NONE")


def hipped_roof(bm):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=2.0, radius2=0.0, depth=0.5, matrix=mathutils.Matrix.Translation((0.0, 0.0, 0.25)))


case("a low hipped roof shaded flat: panes, no curve", [], shaded(hipped_roof, smooth=False), UV_KIND="NONE")


def tin(bm):
    bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=0.5, radius2=0.5, depth=1.0)


case("a tin of many sides shaded smooth into its lids", ["smooth_across_corners"], shaded(tin), UV_KIND="NONE")
case("the same, its rims sharp", [], shaded(tin, sharp_corners=True), UV_KIND="NONE")
case("a ball shaded flat: every face shows", ["flat_shaded_curves"], shaded(ball, smooth=False), UV_KIND="NONE")
case("the same, a low-poly look on purpose", [], shaded(ball, smooth=False), UV_KIND="NONE", FACETED=True)
case("the same, on this object", [], shaded(ball, smooth=False), UV_KIND="NONE", FACETED=["Shaded"])


def linked_rotated():
    obj = from_bmesh("Original", cube)
    copy = obj.copy()
    bpy.context.scene.collection.objects.link(copy)
    copy.rotation_euler = (0.0, 0.0, 0.7)
    copy.scale = (1.2, 1.2, 1.2)
    return copy.name


case("one mesh placed again, turned and scaled", [], linked_rotated)


def door_on_hinge():
    frame = from_bmesh("Frame", cube)
    door = from_bmesh("Door", cube)
    door.parent = frame
    door.rotation_euler = (0.0, 0.0, 0.7)
    return door.name


case("a child turned on its parent", [], door_on_hinge)


def leg_in_table():
    def build(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Diagonal((2.0, 2.0, 0.2, 1.0)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((0.0, 0.0, -0.3)) @ mathutils.Matrix.Diagonal((0.3, 0.3, 1.0, 1.0)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((0.0, 0.0, 0.0)) @ mathutils.Matrix.Diagonal((0.2, 0.2, 0.1, 1.0)))
    return unwrap(from_bmesh("Table", build, uv=False)).name


case("a part wholly inside another", ["hidden_faces"], leg_in_table, FLAT_DETAIL=True, UV_KIND="SHARED")
case("the inside of glass shows", [], leg_in_table, FLAT_DETAIL=True, UV_KIND="SHARED", SEE_THROUGH=["Table"])


def collision_mesh(closed=True, far=False, dented=False):
    def build():
        from_bmesh("Crate", cube)
        def body(bm):
            bmesh.ops.create_cube(bm, size=1.0 if not far else 3.0)
            if dented:
                bm.verts.ensure_lookup_table()
                bm.verts[0].co *= 0.2
            if not closed:
                bm.faces.ensure_lookup_table()
                bmesh.ops.delete(bm, geom=[bm.faces[0]], context="FACES_ONLY")
        from_bmesh("Crate_COL", body, uv=False)
        return ["Crate", "Crate_COL"]
    return build


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
case("modifier output is checked", ["overlapping_coplanar_faces"], mirrored_onto_itself)
case("a mesh with no faces draws nothing", ["no_faces"], lambda: from_bmesh("Vanished", lambda bm: None, uv=False).name, UV_KIND="NONE")


def not_run_by_path():
    clear()
    name = from_bmesh("Crate", cube).name
    g = {"TARGETS": [name]}
    exec(compile(script, "validate_mesh.py", "exec"), g)
    report = g["result"]
    found = sorted(report["objects"][0]["issues"])
    cases.append({"case": "no way to find rig.py: not checked isn't passed", "expected": ["hidden_faces_not_checked"], "found": found, "ok": found == ["hidden_faces_not_checked"] and not report["passed"]})


not_run_by_path()


def small_item_in_a_crate():
    def build(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.08)
    return from_bmesh("Crate", build, uv=False).name


case("a small thing sealed in the middle of a crate", ["hidden_faces"], small_item_in_a_crate, UV_KIND="NONE", FACETED=True)


def hilly_ground():
    def build(bm):
        bmesh.ops.create_grid(bm, x_segments=24, y_segments=24, size=10.0)
        for v in bm.verts:
            v.co.z = 0.8 * math.sin(v.co.x) * math.cos(v.co.y)
    obj = from_bmesh("Ground", build, uv=False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj.name


case("hilly ground, open at its far edge: nothing to look into", [], hilly_ground, UV_KIND="NONE")


def textured(obj, width, height):
    image = bpy.data.images.new("Art", width, height)
    material = bpy.data.materials.new("Art")
    material.use_nodes = True
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    material.node_tree.links.new(node.outputs[0], material.node_tree.nodes["Principled BSDF"].inputs[0])
    obj.data.materials.append(material)
    return obj


def plank(strip):
    def build():
        def body(bm):
            quad(bm, 0.0)
            bm.verts.ensure_lookup_table()
            bm.verts[2].co.y = bm.verts[3].co.y = 0.125
            bm.verts[1].co.x = bm.verts[2].co.x = 2.0
        obj = from_bmesh("Plank", body, uv=False)
        layer = obj.data.uv_layers.new(name="UVMap")
        for loop_index, uv in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
            layer.data[loop_index].uv = uv
        if strip:
            textured(obj, 1024, 64)
        return obj.name
    return build


def quad(bm, z, size=1.0, flip=False, shift=0.0):
    points = [(shift, 0, z), (shift + size, 0, z), (shift + size, size, z), (shift, size, z)]
    verts = [bm.verts.new(p) for p in (reversed(points) if flip else points)]
    bm.faces.new(verts)


case("a plank mapped edge to edge on a square texture: streaks", ["uv_stretched"], plank(False))
case("the same on a strip of its own shape", [], plank(True))
case("UV_KIND NONE on what draws a texture hides its layout", ["uv_kind_none_with_texture"], plank(True), UV_KIND="NONE")


def squeezed(by=4.9):
    def build():
        obj = unwrap(from_bmesh("Squeezed", cube, uv=False))
        layer = obj.data.uv_layers.active
        for poly in obj.data.polygons:
            for loop_index in poly.loop_indices:
                uv = layer.data[loop_index].uv
                layer.data[loop_index].uv = (uv.x, uv.y / by)
        return obj.name
    return build


case("every face pulled 4.9 times, painted", ["uv_stretched"], squeezed(), UV_KIND="UNIQUE")
case("the same, not said to be painted: a note", [], squeezed(), notes=["uv_stretched_share"])


def blurred(index):
    def build():
        obj = unwrap(from_bmesh("Blurred", cube, uv=False))
        layer = obj.data.uv_layers.active
        poly = [p for p in obj.data.polygons if p.normal.z < -0.9][0] if index == "bottom" else [p for p in obj.data.polygons if abs(p.normal.z) < 0.1][0]
        uvs = [layer.data[i].uv.copy() for i in poly.loop_indices]
        center = sum(uvs, mathutils.Vector((0.0, 0.0))) / len(uvs)
        for loop_index, uv in zip(poly.loop_indices, uvs):
            layer.data[loop_index].uv = center + (uv - center) / 7.0
        return obj.name
    return build


case("one side at a fiftieth of the texels of the rest, painted", ["uv_uneven_density"], blurred("side"), UV_KIND="UNIQUE")
case("the same, not said to be painted: a note", [], blurred("side"), notes=["uv_uneven_density"])
case("its bottom instead, which nobody looks at", [], blurred("bottom"), UV_KIND="UNIQUE")


def scrambled():
    import random
    generator = random.Random(7)
    def body(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.5)
    obj = from_bmesh("Noise", body, uv=False)
    layer = obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        poly.use_smooth = True
        for loop_index in poly.loop_indices:
            layer.data[loop_index].uv = (generator.random(), generator.random())
    return obj.name


case("every corner's UV anywhere: noise", ["uv_scrambled"], scrambled)


def islands_apart(gap_uv):
    def build():
        def body(bm):
            quad(bm, 0.0)
            quad(bm, 0.0, shift=2.0)
        obj = from_bmesh("Apart", body, uv=False)
        layer = obj.data.uv_layers.new(name="UVMap")
        for poly, left in zip(obj.data.polygons, (0.1, 0.5 + gap_uv)):
            for loop_index, (x, y) in zip(poly.loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
                # Side by side, squarely, each as wide as tall.
                layer.data[loop_index].uv = (left + 0.4 * x if left == 0.1 else left + 0.4 * x, 0.1 + 0.4 * y)
        return obj.name
    return build


case("islands 2.2 px apart on 1024, asked for 4", ["uv_padding"], islands_apart(2.2 / 1024), TEXTURE_SIZE=1024, PADDING=4, FLAT_DETAIL=True)
case("islands 5 px apart on 1024, asked for 4", [], islands_apart(5 / 1024), TEXTURE_SIZE=1024, PADDING=4, FLAT_DETAIL=True)
case("islands 3 px apart on 4096, asked for 4", ["uv_padding"], islands_apart(3 / 4096), TEXTURE_SIZE=4096, PADDING=4, FLAT_DETAIL=True)
case("islands 7.5 px apart on 4096, asked for 4", [], islands_apart(7.5 / 4096), TEXTURE_SIZE=4096, PADDING=4, FLAT_DETAIL=True)



def run_many(names, **settings):
    g = {"TARGETS": names, "__file__": script_path}
    g.update(settings)
    exec(compile(script, "validate_mesh.py", "exec"), g)
    return g["result"]


def scene_case(label, expected, build_scene, notes=None, **settings):
    """expected: object name -> sorted issue names. notes: object name -> notes it must have."""
    clear()
    names = build_scene()
    report = run_many(names, **settings)
    found = {o["name"]: sorted(o["issues"]) for o in report["objects"]}
    ok = found == {k: sorted(v) for k, v in expected.items()} and report["passed"] == (not any(expected.values()))
    told = {o["name"]: o["notes"] for o in report["objects"]}
    ok = ok and all(n in told[name] for name, wanted in (notes or {}).items() for n in wanted)
    cases.append({"case": label, "expected": expected, "found": found, "ok": ok, "issues": [o["issues"] for o in report["objects"]]})


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


scene_case("a collision mesh that fits", {"Crate": [], "Crate_COL": []}, collision_mesh())
scene_case("a collision mesh with a hole", {"Crate": [], "Crate_COL": ["collision_not_closed"]}, collision_mesh(closed=False))
scene_case("a collision mesh three times the model", {"Crate": [], "Crate_COL": ["collision_doesnt_fit"]}, collision_mesh(far=True))
scene_case("a dented mesh on a convex collider", {"Crate": [], "Crate_COL": ["convex_with_dents"]}, collision_mesh(dented=True), CONVEX=["Crate_COL"])


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


def layers_in_one_object(gap):
    def build():
        def body(bm):
            quad(bm, 0.0)
            quad(bm, gap, shift=0.3)
        from_bmesh("Layered", body)
        return ["Layered"]
    return build


scene_case("one object, faces 0.09 mm apart, under what the plane count sees", {"Layered": ["z_fighting"]}, layers_in_one_object(0.00009))


def floors(overlap, gap=0.0, size=10.0):
    def build():
        from_bmesh("FloorA", lambda bm: quad(bm, 0.0, size=size), uv=False)
        from_bmesh("FloorB", lambda bm: quad(bm, gap, size=size, shift=size - overlap), uv=False)
        return ["FloorA", "FloorB"]
    return build


scene_case("floors side by side, sharing a side", {"FloorA": [], "FloorB": []}, floors(0.0), UV_KIND="NONE")
scene_case("floors over each other by a metre of ten, their sides in line", {"FloorA": ["z_fighting"], "FloorB": ["z_fighting"]}, floors(1.0), UV_KIND="NONE")
scene_case("the same, 0.5 mm apart", {"FloorA": ["z_fighting"], "FloorB": ["z_fighting"]}, floors(1.0, 0.0005), UV_KIND="NONE")
scene_case("floors over each other by half a millimetre: no pixel shows it", {"FloorA": [], "FloorB": []}, floors(0.0005), UV_KIND="NONE")


def dense_floors():
    def grid_at(x, z):
        def body(bm):
            bmesh.ops.create_grid(bm, x_segments=40, y_segments=40, size=2.0, matrix=mathutils.Matrix.Translation((x, 0.0, z)))
        return body
    from_bmesh("TileA", grid_at(0.0, 0.0), uv=False)
    from_bmesh("TileB", grid_at(3.0, 0.0005), uv=False)
    return ["TileA", "TileB"]


# And the lower one's faces there are under the other, for good.
scene_case("tiles of many small faces over each other by a metre, 0.5 mm apart", {"TileA": ["hidden_faces", "z_fighting"], "TileB": ["z_fighting"]}, dense_floors, UV_KIND="NONE", FLAT_DETAIL=True)


def small_layers():
    def body(bm):
        quad(bm, 0.0, size=0.03)
        quad(bm, 0.0005, size=0.03, shift=0.003)
    from_bmesh("Lens", body)
    return ["Lens"]


scene_case("the layers of something small, 0.5 mm apart: gone before they flicker", {"Lens": []}, small_layers)


def boxes(*parts):
    def body(bm):
        for (x, y, z), (w, d, h) in parts:
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((x, y, z)) @ mathutils.Matrix.Diagonal((w, d, h, 1.0)))
    return body


ARCH = (((-1.25, 0, 1.25), (0.5, 0.5, 2.5)), ((1.25, 0, 1.25), (0.5, 0.5, 2.5)), ((0, 0, 2.75), (3.0, 0.5, 0.5)))
TABLE = (((0, 0, 0.72), (2.0, 1.0, 0.06)), ((-0.9, -0.4, 0.35), (0.1, 0.1, 0.7)), ((0.9, -0.4, 0.35), (0.1, 0.1, 0.7)), ((-0.9, 0.4, 0.35), (0.1, 0.1, 0.7)), ((0.9, 0.4, 0.35), (0.1, 0.1, 0.7)))


def model_and_collider(name, parts, collider):
    def build():
        from_bmesh(name, boxes(*parts), uv=False)
        from_bmesh(name + "_COL", boxes(*collider), uv=False)
        return [name, name + "_COL"]
    return build


SETTINGS = {"UV_KIND": "NONE", "FLAT_DETAIL": True}
scene_case("an arch whose collision mesh closes it", {"Arch": [], "Arch_COL": ["collision_closes_opening"]}, model_and_collider("Arch", ARCH, (((0, 0, 1.5), (3.0, 0.5, 3.0)),)), **SETTINGS)
scene_case("an arch with a box per part", {"Arch": [], "Arch_COL": []}, model_and_collider("Arch", ARCH, ARCH), **SETTINGS)
scene_case("a table as one block: nobody walks under it", {"Table": [], "Table_COL": []}, model_and_collider("Table", TABLE, (((0, 0, 0.375), (2.0, 1.0, 0.75)),)), **SETTINGS)
scene_case("a long wall whose collision mesh is low", {"Wall": [], "Wall_COL": []}, model_and_collider("Wall", (((0, 0, 1.5), (20.0, 0.3, 3.0)),), (((0, 0, 0.6), (20.0, 0.3, 1.2)),)), notes={"Wall_COL": ["collision_lower_than_model"]}, **SETTINGS)
scene_case("a stair's collision mesh of boxes that overlap", {"Stairs": [], "Stairs_COL": []},
           model_and_collider("Stairs", (((0, 0, 0.25), (1.0, 2.0, 0.5)), ((0, 0.5, 0.75), (1.0, 1.0, 0.5))), (((0, 0, 0.25), (1.0, 2.0, 0.5)), ((0, 0.5, 0.5), (1.0, 1.0, 1.0)))), **SETTINGS)


def walkable_sheet():
    from_bmesh("Ground", boxes(((0, 0, -0.05), (20.0, 20.0, 0.1))), uv=False)
    from_bmesh("Ground_COL", lambda bm: quad(bm, 0.0, size=20.0, shift=-10.0), uv=False)
    bpy.data.objects["Ground_COL"].location.y = -10.0
    return ["Ground", "Ground_COL"]


scene_case("a sheet to walk on, open and enclosing nothing", {"Ground": [], "Ground_COL": []}, walkable_sheet, **SETTINGS)


def big_flat_grid():
    import time
    clear()
    def build(bm):
        bmesh.ops.create_grid(bm, x_segments=200, y_segments=200, size=10.0)
    name = from_bmesh("Big", build, uv=False).name
    started = time.time()
    report = run(name, UV_KIND="NONE")
    seconds = time.time() - started
    found = sorted(report["objects"][0]["issues"])
    cases.append({"case": f"a flat grid of 40,000 faces, in seconds ({seconds:.1f})", "expected": ["over_tessellated_flat_areas"], "found": found, "ok": found == ["over_tessellated_flat_areas"] and seconds < 15.0})


big_flat_grid()

# ---- what an adversarial review found: faces read by where they are

def split_crate(flip_top):
    def build():
        def body(bm):
            _split_cube(bm)
            if flip_top:
                top = max(bm.faces, key=lambda f: f.calc_center_median().z)
                bmesh.ops.reverse_faces(bm, faces=[top])
        return from_bmesh("Crate", body, uv=False).name
    return build


case("a crate of split faces, its top inside out", ["inconsistent_normals"], split_crate(True), UV_KIND="NONE")
case("the same, all faces looking out", [], split_crate(False), UV_KIND="NONE")


def tall_open_box_inside_out():
    def body(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Diagonal((1.0, 1.0, 6.0, 1.0)))
        top = max(bm.faces, key=lambda f: f.calc_center_median().z)
        bmesh.ops.delete(bm, geom=[top], context="FACES_ONLY")
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return from_bmesh("Trunk", body, uv=False).name


case("an open box six times as tall as wide, inside out", ["inconsistent_normals"], tall_open_box_inside_out, UV_KIND="NONE")


def thick_room(flip):
    def body(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Diagonal((6.0, 6.0, 3.0, 1.0)))
        inner = bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Diagonal((5.0, 5.0, 2.0, 1.0)))
        faces = list({face for vert in inner["verts"] for face in vert.link_faces})
        bmesh.ops.reverse_faces(bm, faces=faces)
        if flip:
            floor = min(faces, key=lambda f: f.calc_center_median().z)
            bmesh.ops.reverse_faces(bm, faces=[floor])
    return body


case("a hollow in a solid looks inward, and is sealed: hidden", ["hidden_faces"], lambda: from_bmesh("Room", thick_room(False), uv=False).name, UV_KIND="NONE")
case("one face of the hollow turned the other way", ["inconsistent_normals"], lambda: from_bmesh("Room", thick_room(True), uv=False).name, UV_KIND="NONE")


def floor_facing_down():
    from_bmesh("Floor", lambda bm: quad(bm, 0.0, size=4.0, flip=True), uv=False)
    return "Floor"


case("a floor turned over: drawn by nothing from above", ["inconsistent_normals"], floor_facing_down, UV_KIND="NONE")
case("the same, a camera that goes below it", [], floor_facing_down, UV_KIND="NONE", LOWEST_VIEW=-60)


def sword():
    section = [(0.03, 0.0), (0.018, 0.005), (0.008, 0.005), (0.0, 0.002), (-0.008, 0.005), (-0.018, 0.005), (-0.03, 0.0), (-0.018, -0.005), (-0.008, -0.005), (0.0, -0.002), (0.008, -0.005), (0.018, -0.005)]
    def body(bm):
        rows = [[bm.verts.new((x, y, z)) for x, y in section] for z in (0.0, 0.8)]
        tip = bm.verts.new((0.0, 0.0, 0.95))
        n = len(section)
        for k in range(n):
            m = (k + 1) % n
            bm.faces.new((rows[0][k], rows[0][m], rows[1][m], rows[1][k]))
            bm.faces.new((rows[1][k], rows[1][m], tip))
        bm.faces.new(list(reversed(rows[0])))
    return from_bmesh("Sword", body, uv=False).name


case("a thin blade with a groove, looking out: Blender's guess at outward fails on it", [], sword, UV_KIND="NONE", FACETED=True)


# ---- shading

def smooth_boxes(*parts):
    def build():
        obj = from_bmesh("Part", boxes(*parts), uv=False)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        return obj.name
    return build


case("a door shaded smooth: its thin sides don't excuse its faces", ["smooth_across_corners"], smooth_boxes(((0, 0, 1), (1.0, 0.05, 2.0))), UV_KIND="NONE")
case("forty boxes merged, each shaded smooth", ["smooth_across_corners"], smooth_boxes(*[((x * 1.2, y * 1.2, 0.5), (1.0, 1.0, 1.0)) for x in range(8) for y in range(5)]), UV_KIND="NONE", FLAT_DETAIL=True)
case("a crate shaded smooth on a yard of one mesh", ["smooth_across_corners"], smooth_boxes(((0, 0, -0.05), (20.0, 20.0, 0.1)), ((0, 0, 0.5), (1.0, 1.0, 1.0))), UV_KIND="NONE", FLAT_DETAIL=True)


def bevelled(segments, weighted=False):
    def build():
        obj = from_bmesh("Crate", cube, uv=False)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        modifier = obj.modifiers.new("Bevel", "BEVEL")
        modifier.width = 0.02
        modifier.segments = segments
        if weighted:
            normals = obj.modifiers.new("Weighted", "WEIGHTED_NORMAL")
            normals.mode = "FACE_AREA"
        return obj.name
    return build


case("a bevel shaded smooth: the large faces go dark to the corners", ["smooth_across_corners"], bevelled(3), UV_KIND="NONE", FLAT_DETAIL=True)
case("the same with weighted normals", [], bevelled(3, weighted=True), UV_KIND="NONE", FLAT_DETAIL=True)


def boulder():
    def body(bm):
        bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
        for vert in bm.verts:
            vert.co.z = max(vert.co.z, -0.4)
    obj = from_bmesh("Boulder", body, uv=False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj.name


case("a smooth boulder with a flat bottom, shaded across its rim: nobody looks there", [], boulder, UV_KIND="NONE", FLAT_DETAIL=True)


def holding_loops():
    def body(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        result = bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=0.02, segments=3, affect="EDGES", profile=0.5)
    obj = from_bmesh("Box", body, uv=False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.modifiers.new("Weighted", "WEIGHTED_NORMAL")
    return obj.name


def chamfered_plinth():
    def body(bm):
        ring = lambda r, z: [bm.verts.new((r * math.cos(k * math.pi / 4.0), r * math.sin(k * math.pi / 4.0), z)) for k in range(8)]
        bottom, top, inner = ring(1.0, 0.0), ring(1.0, 0.5), ring(0.9, 0.55)
        for k in range(8):
            m = (k + 1) % 8
            bm.faces.new((bottom[k], bottom[m], top[m], top[k]))
            bm.faces.new((top[k], top[m], inner[m], inner[k]))
        bm.faces.new(inner)
        bm.faces.new(list(reversed(bottom)))
    return from_bmesh("Plinth", body, uv=False).name


case("an octagonal plinth with a chamfer, shaded flat: nothing curves", [], chamfered_plinth, UV_KIND="NONE")


def flat_ball_split():
    def body(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.5)
        bmesh.ops.split_edges(bm, edges=bm.edges[:])
    return from_bmesh("Ball", body, uv=False).name


case("a ball of faces that share no vertex, shaded flat", ["flat_shaded_curves"], flat_ball_split, UV_KIND="NONE", FLAT_DETAIL=True)


# ---- what hides, what flickers

def rug(size):
    def build():
        def body(bm):
            quad(bm, 0.0, size=12.0)
            quad(bm, 0.0002, size=size, shift=2.0)
        return from_bmesh("Room", body, uv=False).name
    return build


case("a rug 90 cm wide, 0.2 mm over a floor of one mesh", ["z_fighting"], rug(0.9), UV_KIND="NONE")


def mirrored_on_floor():
    from_bmesh("Floor", boxes(((0, 0, -0.05), (10.0, 10.0, 0.1))), uv=False)
    crate = from_bmesh("Crate", boxes(((0, 0, 0.5), (1.0, 1.0, 1.0))), uv=False)
    crate.scale = (-1.0, 1.0, 1.0)
    return ["Floor", "Crate"]


def mirrored_floor_over_floor():
    from_bmesh("FloorA", lambda bm: quad(bm, 0.0, size=10.0), uv=False)
    other = from_bmesh("FloorB", lambda bm: quad(bm, 0.0005, size=10.0, shift=-9.0), uv=False)
    other.data.update()
    # One mesh placed again, mirrored: it can't be applied, and needn't be.
    from_bmesh("FloorB_Original", lambda bm: quad(bm, 50.0, size=1.0), uv=False)
    other.scale = (1.0, -1.0, 1.0)
    other.location.y = 10.0
    return ["FloorA", "FloorB"]


scene_case("a mirrored floor over a floor faces the same way", {"FloorA": ["z_fighting"], "FloorB": ["transforms_not_applied", "z_fighting"]}, mirrored_floor_over_floor, UV_KIND="NONE")
scene_case("a mirrored crate on a floor: back to back, as any crate", {"Floor": [], "Crate": ["transforms_not_applied"]}, mirrored_on_floor, UV_KIND="NONE")


def split_floors():
    def tiles(z, shift):
        def body(bm):
            for x in range(5):
                for y in range(5):
                    verts = [bm.verts.new((shift + x + dx, y + dy, z)) for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1))]
                    bm.faces.new(verts)
        return body
    from_bmesh("TileA", tiles(0.0, 0.0), uv=False)
    from_bmesh("TileB", tiles(0.0005, 3.0), uv=False)
    return ["TileA", "TileB"]


scene_case("tiles of quads sharing no vertex over each other, 0.5 mm apart: one patch", {"TileA": ["hidden_faces", "z_fighting"], "TileB": ["z_fighting"]}, split_floors, UV_KIND="NONE", FLAT_DETAIL=True)


def banner():
    from_bmesh("Wall", boxes(((0, 0, 2), (6.0, 0.2, 4.0))), uv=False)
    def body(bm):
        verts = [bm.verts.new(p) for p in ((-1, -0.1003, 1), (1, -0.1003, 1), (1, -0.1003, 3), (-1, -0.1003, 3))]
        bm.faces.new(list(reversed(verts)))
    from_bmesh("Banner", body, uv=False)
    return ["Wall", "Banner"]


scene_case("a banner drawn both sides, 0.3 mm off a wall", {"Wall": ["z_fighting"], "Banner": ["z_fighting"]}, banner, UV_KIND="NONE", TWO_SIDED=["Banner"])


def rivets():
    def body(bm):
        for x in range(20):
            for y in range(20):
                verts = [bm.verts.new((x * 0.1 + dx, y * 0.1 + dy, 0.0005)) for dx, dy in ((0, 0), (0.02, 0), (0.02, 0.02), (0, 0.02))]
                bm.faces.new(verts)
    from_bmesh("Rivets", body, uv=False)
    from_bmesh("Hull", lambda bm: quad(bm, 0.0, size=3.0, shift=-0.5), uv=False)
    return ["Rivets", "Hull"]


scene_case("400 rivets of 2 cm, 0.5 mm off a plate: each gone before its gap gives out", {"Rivets": [], "Hull": []}, rivets, UV_KIND="NONE", FLAT_DETAIL=True)


def crates_under_a_roof():
    from_bmesh("Crates", boxes(((0, 0, 0.5), (1.0, 1.0, 1.0)), ((2.5, 0, 0.5), (1.0, 1.0, 1.0))), uv=False)
    from_bmesh("Roof", lambda bm: quad(bm, 2.0, size=10.0, shift=-4.0), uv=False)
    bpy.data.objects["Roof"].location.y = -5.0
    return ["Crates", "Roof"]


scene_case("crates under a roof: their tops are in plain view from the side", {"Crates": [], "Roof": []}, crates_under_a_roof, UV_KIND="NONE", FLAT_DETAIL=True)


# ---- openings

def box_without(*names):
    def body(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((0, 0, 0.5)))
        doomed = [f for f in bm.faces if any(f.normal.dot(direction) > 0.9 for direction in names)]
        bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    return body


FRONT = mathutils.Vector((0, -1, 0))
BACK = mathutils.Vector((0, 1, 0))
LEFT = mathutils.Vector((-1, 0, 0))
RIGHT = mathutils.Vector((1, 0, 0))
DOWN = mathutils.Vector((0, 0, -1))
UP = mathutils.Vector((0, 0, 1))
case("a crate without its front: it nearly closes, so that is a hole", ["see_inside"], lambda: from_bmesh("Crate", box_without(FRONT), uv=False).name, UV_KIND="NONE")
case("the same, a kit piece a neighbor covers", [], lambda: from_bmesh("Crate", box_without(FRONT), uv=False).name, UV_KIND="NONE", KIT=True, notes=["see_inside"])
case("a shell with most of it left open, as the back of a kit's wall: a note", [], lambda: from_bmesh("Wall", box_without(BACK, UP, DOWN), uv=False).name, UV_KIND="NONE", notes=["open_side"])
case("a pipe, open at both ends: holes unless a neighbor covers them", ["see_inside"], lambda: from_bmesh("Pipe", box_without(UP, DOWN), uv=False).name, UV_KIND="NONE")
case("the same in a kit", [], lambda: from_bmesh("Pipe", box_without(UP, DOWN), uv=False).name, UV_KIND="NONE", KIT=["Pipe"], notes=["see_inside"])


def house_with_hole(hole):
    def body(bm):
        bmesh.ops.create_grid(bm, x_segments=int(10.0 / hole), y_segments=int(3.0 / hole), size=0.5, matrix=mathutils.Matrix.Translation((0, -3.0, 1.5)) @ mathutils.Matrix.Rotation(math.radians(90.0), 4, "X") @ mathutils.Matrix.Diagonal((10.0, 3.0, 1.0, 1.0)))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((0, 0, 1.5)) @ mathutils.Matrix.Diagonal((10.0, 6.0, 3.0, 1.0)))
        wall = [f for f in bm.faces if abs(f.calc_center_median().y + 3.0) < 1e-3 and f.calc_area() > 20.0]
        bmesh.ops.delete(bm, geom=wall, context="FACES_ONLY")
        grid = [f for f in bm.faces if abs(f.calc_center_median().y + 3.0) < 1e-3]
        target = min(grid, key=lambda f: (f.calc_center_median() - mathutils.Vector((1.0, -3.0, 1.5))).length)
        bmesh.ops.delete(bm, geom=[target], context="FACES_ONLY")
    return body


case("a hole of 28 cm in a 10 m house", ["see_inside"], lambda: from_bmesh("House", house_with_hole(0.28), uv=False).name, UV_KIND="NONE", FLAT_DETAIL=True)


def thin_panels_shed():
    def panel(bm, corners):
        verts = [bm.verts.new(c) for c in corners]
        bm.faces.new(verts)
    def body(bm):
        panel(bm, ((-2, -2, 0), (-2, -2, 3), (-2, 2, 3), (-2, 2, 0)))
        panel(bm, ((2, -2, 0), (2, 2, 0), (2, 2, 3), (2, -2, 3)))
        panel(bm, ((-2, 2, 0), (-2, 2, 3), (2, 2, 3), (2, 2, 0)))
        panel(bm, ((-2, -2, 3), (2, -2, 3), (2, 2, 3), (-2, 2, 3)))
        panel(bm, ((-2, -2, 0), (-2, 2, 0), (2, 2, 0), (2, -2, 0)))
    return from_bmesh("Shed", body, uv=False).name


case("a shed of separate panels, its front wall missing", ["see_inside"], thin_panels_shed, UV_KIND="NONE")


def ground_with_hole():
    def body(bm):
        bmesh.ops.create_grid(bm, x_segments=20, y_segments=20, size=10.0)
        for vert in bm.verts:
            vert.co.z = 0.3 * math.sin(vert.co.x) * math.cos(vert.co.y)
        doomed = [f for f in bm.faces if (f.calc_center_median().x ** 2 + f.calc_center_median().y ** 2) < 2.0]
        bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    obj = from_bmesh("Ground", body, uv=False)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj.name


case("hilly ground with a hole in it: right where something stands on it, so a note", [], ground_with_hole, UV_KIND="NONE", notes=["opening_in_sheet"])


def room_with_hole():
    def body(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((0, 0, 2)) @ mathutils.Matrix.Diagonal((6.0, 6.0, 4.0, 1.0)))
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        target = min(bm.faces, key=lambda f: (f.calc_center_median() - mathutils.Vector((3.0, 0.0, 2.0))).length)
        bmesh.ops.delete(bm, geom=[target], context="FACES_ONLY")
    return from_bmesh("Room", body, uv=False).name


case("a room seen from inside with a hole in its wall", ["see_inside"], room_with_hole, UV_KIND="NONE", SEEN_FROM_INSIDE=["Room"], FLAT_DETAIL=True)


# ---- UVs

def vertex_scramble():
    import random
    generator = random.Random(3)
    def body(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.5)
    obj = from_bmesh("Noise", body, uv=False)
    layer = obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        poly.use_smooth = True
    uvs = {v.index: (generator.random(), generator.random()) for v in obj.data.vertices}
    for loop in obj.data.loops:
        layer.data[loop.index].uv = uvs[loop.vertex_index]
    return obj.name


case("every vertex a UV at random: the edges run on and the faces fold", ["uv_scrambled"], vertex_scramble)


def mostly_blurred():
    obj = unwrap(from_bmesh("Blurred", cube, uv=False))
    layer = obj.data.uv_layers.active
    for poly in obj.data.polygons:
        if abs(poly.normal.z) > 0.9:
            continue
        uvs = [layer.data[i].uv.copy() for i in poly.loop_indices]
        center = sum(uvs, mathutils.Vector((0.0, 0.0))) / len(uvs)
        for loop_index, uv in zip(poly.loop_indices, uvs):
            layer.data[loop_index].uv = center + (uv - center) / 25.0
    return obj.name


case("a box blurred on its four sides: most of it sets no measure", ["uv_uneven_density"], mostly_blurred, UV_KIND="UNIQUE")
case("the same, nobody sees those sides", [], mostly_blurred, UV_KIND="UNIQUE", BLUR_OK=["Blurred"])


def in_a_node_group():
    obj = plank(False)()
    image = bpy.data.images.new("Art", 1024, 64)
    group = bpy.data.node_groups.new("Look", "ShaderNodeTree")
    node = group.nodes.new("ShaderNodeTexImage")
    node.image = image
    group.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    outputs = group.nodes.new("NodeGroupOutput")
    group.links.new(node.outputs[0], outputs.inputs[0])
    material = bpy.data.materials.new("Art")
    material.use_nodes = True
    holder = material.node_tree.nodes.new("ShaderNodeGroup")
    holder.node_tree = group
    material.node_tree.links.new(holder.outputs[0], material.node_tree.nodes["Principled BSDF"].inputs[0])
    bpy.data.objects[obj].data.materials.append(material)
    return obj


case("UV_KIND NONE, the texture inside a node group", ["uv_kind_none_with_texture"], in_a_node_group, UV_KIND="NONE")
case("a plank on a strip whose image the check can't read: said to be shared, a note", [], plank(False), UV_KIND="SHARED", notes=["uv_stretched"])


# ---- collision meshes

def turned(build, degrees):
    def scene():
        names = build()
        rotation = mathutils.Matrix.Rotation(math.radians(degrees), 4, "Z")
        for name in names:
            obj = bpy.data.objects[name]
            obj.data.transform(rotation)
            obj.data.update()
        return names
    return scene


for angle in (15, 30, 45, 70):
    scene_case(f"an arch closed by its collision mesh, turned {angle} degrees", {"Arch": [], "Arch_COL": ["collision_closes_opening"]},
               turned(model_and_collider("Arch", ARCH, (((0, 0, 1.5), (3.0, 0.5, 3.0)),)), angle), **SETTINGS)


GATE = (((-1.5, 0, 1.1), (0.1, 0.1, 2.2)), ((1.5, 0, 1.1), (0.1, 0.1, 2.2)), ((0, 0, 2.2), (3.1, 0.1, 0.1)))
scene_case("a gate 3 m wide between thin posts, closed by a thin box", {"Gate": [], "Gate_COL": ["collision_closes_opening"]}, model_and_collider("Gate", GATE, (((0, 0, 1.15), (3.1, 0.4, 2.3)),)), **SETTINGS)
GARDEN = (((-6, 0, 0.6), (6.0, 0.3, 1.2)), ((6, 0, 0.6), (6.0, 0.3, 1.2)))
scene_case("a garden wall with a 6 m gap, under one low box", {"Garden": [], "Garden_COL": ["collision_closes_opening"]}, model_and_collider("Garden", GARDEN, (((0, 0, 0.6), (18.0, 0.3, 1.2)),)), **SETTINGS)
LONG_WALL = (((-30.6, 0, 1.5), (60.0, 0.2, 3.0)), ((30.6, 0, 1.5), (60.0, 0.2, 3.0)))
scene_case("a 120 m wall with a 1.2 m gate, under one box", {"Wall": [], "Wall_COL": ["collision_closes_opening"]}, model_and_collider("Wall", LONG_WALL, (((0, 0, 1.5), (121.2, 0.2, 3.0)),)), **SETTINGS)
SLAB = ARCH + (((0, 0, 1.25), (2.0, 0.05, 2.5)),)
scene_case("an arch with a box per part, and a 5 cm slab across the way", {"Arch": [], "Arch_COL": ["collision_closes_opening"]}, model_and_collider("Arch", ARCH, SLAB), **SETTINGS)
WINDOW = (((0, 0, 0.45), (6.0, 0.3, 0.9)), ((0, 0, 2.75), (6.0, 0.3, 0.5)), ((-2.5, 0, 1.7), (1.0, 0.3, 1.6)), ((2.5, 0, 1.7), (1.0, 0.3, 1.6)))
scene_case("a window over a sill under one box: he can't walk through a window", {"Wall": [], "Wall_COL": []}, model_and_collider("Wall", WINDOW, (((0, 0, 1.5), (6.0, 0.3, 3.0)),)), **SETTINGS)
POSTS = tuple(((x * 0.4 - 3.0, 0, 1.1), (0.1, 0.1, 2.2)) for x in range(16))
scene_case("a palisade whose gaps no person fits, under one box", {"Fence": ["hidden_faces", "overlapping_coplanar_faces"], "Fence_COL": []}, model_and_collider("Fence", POSTS + (((0, 0, 2.2), (6.1, 0.1, 0.1)),), (((0, 0, 1.15), (6.2, 0.2, 2.3)),)), **SETTINGS)
L_SHAPE = (((0, -3, 1.5), (12.0, 6.0, 3.0)), ((-3, 3, 1.5), (6.0, 6.0, 3.0)))
scene_case("an L-shaped building under one box: he stops in its corner", {"Block": [], "Block_COL": ["collision_fills_space"]}, model_and_collider("Block", L_SHAPE, (((0, 0, 1.5), (12.0, 12.0, 3.0)),)), **SETTINGS)


def house_with_room():
    def body(bm):
        # Walls of 30 cm with a doorway, a slab under them, no roof to keep the scene plain: what counts is that a person walks in.
        for part in (((-3, 0, 1.5), (0.3, 6.0, 3.0)), ((3, 0, 1.5), (0.3, 6.0, 3.0)), ((0, 3, 1.5), (6.3, 0.3, 3.0)), ((-2, -3, 1.5), (2.3, 0.3, 3.0)), ((2, -3, 1.5), (2.3, 0.3, 3.0)), ((0, -3, 2.6), (1.7, 0.3, 0.8)), ((0, 0, 3.05), (6.3, 6.3, 0.1))):
            bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation(part[0]) @ mathutils.Matrix.Diagonal((*part[1], 1.0)))
    from_bmesh("House", body, uv=False)
    from_bmesh("House_COL", boxes(((0, 0, 1.55), (6.3, 6.3, 3.1))), uv=False)
    return ["House", "House_COL"]


scene_case("a room behind a door, under one solid box: he stops in the doorway", {"House": ["hidden_faces", "overlapping_coplanar_faces"], "House_COL": ["collision_fills_space"]}, house_with_room, **SETTINGS)


def box_over_fence():
    from_bmesh("Fence", boxes(((0, 0, 1), (20.0, 0.2, 2.0))), uv=False)
    from_bmesh("Fence_COL", boxes(((0, 0, 1), (20.0, 3.8, 2.0))), uv=False)
    return ["Fence", "Fence_COL"]


scene_case("a fence 20 cm thick with a collision box 3.8 m thick", {"Fence": [], "Fence_COL": ["collision_doesnt_fit"]}, box_over_fence, **SETTINGS)


def house_and_roof():
    from_bmesh("House", boxes(((0, 0, 1.5), (6.0, 6.0, 3.0))), uv=False)
    from_bmesh("Roof", boxes(((0, 0, 3.5), (6.0, 6.0, 1.0))), uv=False)
    from_bmesh("House_COL", boxes(((0, 0, 2.0), (6.0, 6.0, 4.0))), uv=False)
    return ["House", "Roof", "House_COL"]


scene_case("one collision mesh for a house and its roof", {"House": [], "Roof": [], "House_COL": []}, house_and_roof, **SETTINGS)


def open_box_collider():
    from_bmesh("Wall", boxes(((0, 0, 1.5), (20.0, 2.0, 3.0))), uv=False)
    def body(bm):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Translation((0, 0, 1.5)) @ mathutils.Matrix.Diagonal((20.0, 2.0, 3.0, 1.0)))
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.y < -0.9], context="FACES_ONLY")
    from_bmesh("Wall_COL", body, uv=False)
    return ["Wall", "Wall_COL"]


scene_case("a long wall's collision mesh missing its front face", {"Wall": [], "Wall_COL": ["collision_not_closed"]}, open_box_collider, **SETTINGS)


def mirrored_arch():
    def scene():
        names = model_and_collider("Arch", ARCH, ARCH)()
        for name in names:
            bpy.data.objects[name].scale = (-1.0, 1.0, 1.0)
        return names
    return scene


scene_case("a mirrored arch with a box per part: the normals still look out", {"Arch": ["transforms_not_applied"], "Arch_COL": ["transforms_not_applied"]}, mirrored_arch(), **SETTINGS)


# ---- numbers

def far_vertex(distance):
    def build():
        def body(bm):
            bmesh.ops.create_cube(bm, size=1.0)
            bm.verts.ensure_lookup_table()
            bm.verts[0].co.x = distance
        return from_bmesh("Crate", body, uv=False).name
    return build


case("a vertex at 1e25 m: told, not a crash", ["vertices_not_numbers"], far_vertex(1e25), UV_KIND="NONE")
case("a vertex at 1e8 m", ["vertices_not_numbers"], far_vertex(1e8), UV_KIND="NONE")


# ---- flat areas

def flat_grid_with(setup):
    def build():
        def body(bm):
            bmesh.ops.create_grid(bm, x_segments=60, y_segments=60, size=4.0)
        obj = from_bmesh("Floor", body, uv=False)
        setup(obj)
        return obj.name
    return build


def leftover_color(obj):
    attribute = obj.data.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    for item in attribute.data:
        item.color = (1.0, 1.0, 1.0, 1.0)


def painted_color(obj):
    attribute = obj.data.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    for k, item in enumerate(attribute.data):
        item.color = (k % 7 / 7.0, 0.5, 0.5, 1.0)


def all_sharp(obj):
    for edge in obj.data.edges:
        edge.use_edge_sharp = True


case("a flat floor of thousands of faces with a color attribute left at white", ["over_tessellated_flat_areas"], flat_grid_with(leftover_color), UV_KIND="NONE")
case("the same, its colors painted", [], flat_grid_with(painted_color), UV_KIND="NONE")
case("the same floor, every edge marked sharp", ["over_tessellated_flat_areas"], flat_grid_with(all_sharp), UV_KIND="NONE")


def facade_with_windows():
    """Holes need the vertices around them: each costs what a dissolve leaves."""
    def body(bm):
        bmesh.ops.create_grid(bm, x_segments=18, y_segments=3, size=1.0, matrix=mathutils.Matrix.Diagonal((9.0, 1.5, 1.0, 1.0)))
        windows = [f for f in bm.faces if abs(f.calc_center_median().y) < 0.4 and int((f.calc_center_median().x + 9.0) / 1.0) % 2 == 1]
        bmesh.ops.delete(bm, geom=windows, context="FACES_ONLY")
    return from_bmesh("Facade", body, uv=False).name


case("a facade of a row of windows: flat, and every vertex needed", [], facade_with_windows, UV_KIND="NONE", TWO_SIDED=["Facade"])


cut_path = script_path.replace("validate_mesh.py", "cut_hidden_faces.py")


def moving_part_survives_the_cut(keyed):
    clear()
    housing = from_bmesh("Housing", cube, uv=False)
    rod = from_bmesh("Rod", lambda bm: bmesh.ops.create_cube(bm, size=0.8), uv=False)
    if keyed:
        rod.keyframe_insert("location", frame=1)
        rod.location.x = 2.0
        rod.keyframe_insert("location", frame=20)
        rod.location.x = 0.0
    g = {"__file__": cut_path, "TARGETS": ["Housing", "Rod"]}
    exec(compile(open(cut_path).read(), cut_path, "exec"), g)
    deleted = g["result"]["deleted"]
    cases.append({"case": ("a rod that slides out keeps its faces in the cut" if keyed else "the same rod, sealed in for good, doesn't"), "expected": not keyed, "found": deleted, "ok": ("Rod" in deleted) == (not keyed)})


moving_part_survives_the_cut(True)
moving_part_survives_the_cut(False)


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
