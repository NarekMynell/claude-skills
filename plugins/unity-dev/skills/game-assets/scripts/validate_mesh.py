"""Validates mesh objects for export to a game engine.

Run through the Blender MCP `execute_blender_code` tool. Optional settings, defined
before this code:
    TARGETS = ["Crate"]       object names; default: selected meshes, else all meshes
    TRIANGLE_BUDGET = 500     maximum triangles per object
    MERGE_DISTANCE = 1e-5     metres; vertices closer than this count as duplicates

Sets `result`: `passed`, and one entry per object with its non-zero issues and stats.
Modifiers are applied first, so the check sees what the exporter writes.
"""

from collections import defaultdict

import bmesh
import bpy

AREA_EPSILON = 1e-10
NORMAL_QUANTUM = 1e-3
PLANE_QUANTUM = 1e-4
OVERLAP_EPSILON = 1e-6


def _canonical_plane(face):
    normal = face.normal.normalized()
    sign = 1.0
    for component in normal:
        if abs(component) > NORMAL_QUANTUM:
            sign = 1.0 if component > 0 else -1.0
            break
    canonical = normal * sign
    distance = canonical.dot(face.verts[0].co)
    key = (
        round(canonical.x / NORMAL_QUANTUM),
        round(canonical.y / NORMAL_QUANTUM),
        round(canonical.z / NORMAL_QUANTUM),
        round(distance / PLANE_QUANTUM),
    )
    return key, canonical, sign


def _point_in_polygon(point, polygon):
    x, y = point
    inside = False
    count = len(polygon)
    for i in range(count):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % count]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _orientation(a, b, c):
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(value) <= OVERLAP_EPSILON:
        return 0
    return 1 if value > 0 else -1


def _segments_cross(p1, p2, q1, q2):
    d1 = _orientation(q1, q2, p1)
    d2 = _orientation(q1, q2, p2)
    d3 = _orientation(p1, p2, q1)
    d4 = _orientation(p1, p2, q2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _polygons_overlap(a, b):
    if _point_in_polygon(a["center"], b["polygon"]) or _point_in_polygon(b["center"], a["polygon"]):
        return True
    poly_a, poly_b = a["polygon"], b["polygon"]
    for i in range(len(poly_a)):
        for j in range(len(poly_b)):
            if _segments_cross(poly_a[i], poly_a[(i + 1) % len(poly_a)], poly_b[j], poly_b[(j + 1) % len(poly_b)]):
                return True
    return False


def _coplanar_overlaps(faces):
    buckets = defaultdict(list)
    normals = {}
    for face in faces:
        if face.calc_area() > AREA_EPSILON:
            key, canonical, sign = _canonical_plane(face)
            buckets[key].append((face, sign))
            normals.setdefault(key, canonical)

    same_facing = 0
    opposite_facing = 0
    for key, members in buckets.items():
        if len(members) < 2:
            continue
        axis_u = normals[key].orthogonal().normalized()
        axis_v = normals[key].cross(axis_u).normalized()
        shapes = []
        for face, sign in members:
            polygon = [(v.co.dot(axis_u), v.co.dot(axis_v)) for v in face.verts]
            center = face.calc_center_median()
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            shapes.append({
                "verts": frozenset(face.verts),
                "sign": sign,
                "polygon": polygon,
                "center": (center.dot(axis_u), center.dot(axis_v)),
                "box": (min(xs), max(xs), min(ys), max(ys)),
            })
        shapes.sort(key=lambda shape: shape["box"][0])
        active = []
        for shape in shapes:
            min_x, max_x, min_y, max_y = shape["box"]
            active = [other for other in active if other["box"][1] > min_x + OVERLAP_EPSILON]
            for other in active:
                if other["box"][2] >= max_y - OVERLAP_EPSILON or min_y >= other["box"][3] - OVERLAP_EPSILON:
                    continue
                if other["verts"] == shape["verts"] or not _polygons_overlap(shape, other):
                    continue
                if other["sign"] == shape["sign"]:
                    same_facing += 1
                else:
                    opposite_facing += 1
            active.append(shape)
    return same_facing, opposite_facing


def _connected_components(faces):
    unvisited = set(faces)
    components = []
    while unvisited:
        stack = [unvisited.pop()]
        component = []
        while stack:
            face = stack.pop()
            component.append(face)
            for edge in face.edges:
                for neighbour in edge.link_faces:
                    if neighbour in unvisited:
                        unvisited.remove(neighbour)
                        stack.append(neighbour)
        components.append(component)
    return components


def _inconsistent_normals(bm):
    bm.faces.index_update()
    original = [face.normal.copy() for face in bm.faces]
    corrected = bm.copy()
    corrected.faces.index_update()
    bmesh.ops.recalc_face_normals(corrected, faces=corrected.faces[:])
    total = 0
    for component in _connected_components(corrected.faces[:]):
        flipped = sum(1 for face in component if face.normal.dot(original[face.index]) < 0)
        closed = all(len(edge.link_faces) == 2 for face in component for edge in face.edges)
        total += flipped if closed else min(flipped, len(component) - flipped)
    corrected.free()
    return total


def _uv_report(bm):
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        return {"no_uv_map": True}, {}
    degenerate = 0
    outside = 0
    densities = []
    for face in bm.faces:
        uvs = [loop[uv_layer].uv for loop in face.loops]
        outside += sum(1 for uv in uvs if not (0.0 <= uv.x <= 1.0 and 0.0 <= uv.y <= 1.0))
        area_3d = face.calc_area()
        if area_3d <= AREA_EPSILON:
            continue
        area_uv = 0.0
        for i in range(1, len(uvs) - 1):
            first = uvs[i] - uvs[0]
            second = uvs[i + 1] - uvs[0]
            area_uv += abs(first.x * second.y - first.y * second.x) * 0.5
        if area_uv <= AREA_EPSILON:
            degenerate += 1
        else:
            densities.append(area_uv / area_3d)
    info = {"uv_loops_outside_0_1": outside}
    if len(densities) > 1:
        mean = sum(densities) / len(densities)
        deviation = (sum((d - mean) ** 2 for d in densities) / len(densities)) ** 0.5
        info["texel_density_spread"] = round(deviation / mean, 3)
    return {"degenerate_uv_faces": degenerate}, info


def _transform_report(obj):
    scale_ok = all(abs(s - 1.0) < 1e-4 for s in obj.scale)
    if obj.rotation_mode == "QUATERNION":
        rotation = list(obj.rotation_quaternion)
        rotation_ok = abs(rotation[0] - 1.0) < 1e-4 and all(abs(r) < 1e-4 for r in rotation[1:])
    elif obj.rotation_mode == "AXIS_ANGLE":
        rotation = list(obj.rotation_axis_angle)
        rotation_ok = abs(rotation[0]) < 1e-4
    else:
        rotation = list(obj.rotation_euler)
        rotation_ok = all(abs(r) < 1e-4 for r in rotation)
    return scale_ok and rotation_ok, [round(s, 4) for s in obj.scale], [round(r, 4) for r in rotation]


def validate_object(obj, triangle_budget, merge_distance):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    bm = bmesh.new()
    bm.from_mesh(evaluated.to_mesh())
    evaluated.to_mesh_clear()
    bm.verts.index_update()
    bm.normal_update()

    vertex_sets = defaultdict(int)
    for face in bm.faces:
        vertex_sets[frozenset(v.index for v in face.verts)] += 1
    same_facing, opposite_facing = _coplanar_overlaps(bm.faces[:])
    triangles = sum(len(face.verts) - 2 for face in bm.faces)
    applied, scale, rotation = _transform_report(obj)
    uv_issues, uv_info = _uv_report(bm)

    issues = {
        "duplicate_vertices": len(bmesh.ops.find_doubles(bm, verts=bm.verts[:], dist=merge_distance)["targetmap"]),
        "duplicate_faces": sum(count - 1 for count in vertex_sets.values() if count > 1),
        "overlapping_coplanar_faces": same_facing,
        "back_to_back_coplanar_faces": opposite_facing,
        "non_manifold_edges": sum(1 for edge in bm.edges if len(edge.link_faces) > 2),
        "loose_vertices": sum(1 for vert in bm.verts if not vert.link_edges),
        "loose_edges": sum(1 for edge in bm.edges if not edge.link_faces),
        "zero_area_faces": sum(1 for face in bm.faces if face.calc_area() <= AREA_EPSILON),
        "zero_length_edges": sum(1 for edge in bm.edges if edge.calc_length() < merge_distance),
        "inconsistent_normals": _inconsistent_normals(bm),
        "transforms_not_applied": not applied,
        "over_triangle_budget": triangle_budget is not None and triangles > triangle_budget,
    }
    issues.update(uv_issues)
    info = {
        "triangles": triangles,
        "vertices": len(bm.verts),
        "ngons": sum(1 for face in bm.faces if len(face.verts) > 4),
        "boundary_edges": sum(1 for edge in bm.edges if len(edge.link_faces) == 1),
        "material_slots": len(obj.material_slots),
        "dimensions_m": [round(d, 4) for d in obj.dimensions],
        "scale": scale,
        "rotation": rotation,
    }
    info.update(uv_info)
    bm.free()
    return {"name": obj.name, "issues": {k: v for k, v in issues.items() if v}, "info": info}


def validate(targets=None, triangle_budget=None, merge_distance=1e-5):
    missing = []
    if targets:
        objects = []
        for name in targets:
            obj = bpy.data.objects.get(name)
            if obj is None:
                missing.append(name)
            else:
                objects.append(obj)
    else:
        objects = [o for o in bpy.context.selected_objects if o.type == "MESH"]
        objects = objects or [o for o in bpy.context.scene.objects if o.type == "MESH"]
    reports = [validate_object(o, triangle_budget, merge_distance) for o in objects if o.type == "MESH"]
    passed = not missing and all(not report["issues"] for report in reports)
    report = {"passed": passed, "objects": reports}
    if missing:
        report["missing_objects"] = missing
    return report


result = validate(
    globals().get("TARGETS"),
    globals().get("TRIANGLE_BUDGET"),
    globals().get("MERGE_DISTANCE", 1e-5),
)
