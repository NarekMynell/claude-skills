"""Validates mesh objects for export to a game engine: what the player would see go wrong, and triangles paid for and never seen.

Run it as the game-assets guide's "Running the scripts" describes. Optional settings:
    TARGETS = ["Crate"]       object names; default: selected meshes, else all meshes
    TRIANGLE_BUDGET = 500     maximum triangles per object
    MERGE_DISTANCE = 1e-5     metres; vertices closer than this count as duplicates
    ZFIGHT_DISTANCE = 0.001   metres; overlapping faces facing the same way closer than this can z-fight, also across objects. 1 mm
                              holds to about 70 m with a 24-bit depth buffer and a 0.3 m near plane; a far camera needs more.
                              Facing opposite ways (a box on a floor, a thin sheet) only counts in `info`, since back faces are culled;
                              it matters for two-sided materials
    ZFIGHT_IGNORE = []        objects that never render together with the others
    COLLISION = ["Crate_COL"]  collision meshes, besides those named *_COL, *_Collider or UCX_*: they get no UV, shading or hidden-face
                              checks, nor z-fight with the others. They must be closed, or physics leaks, and stay within the model they
                              stand for: the one of the same name, or else all the rest of TARGETS
    CONVEX = ["Crate_COL"]    those of COLLISION used by a convex Mesh Collider: at most 255 triangles, and no dents
    FLAT_DETAIL = False       True when flat areas need their extra vertices. On its own for what has vertex colors, shape keys or a rig
    FACETED = False           True, or a list of objects, when the art shows flat facets on purpose: a low-poly look, a cut gem
    ROUND = False             True, or a list of objects, when the art shades over corners on purpose: one soft shape of few faces. What a rig bends counts as such
    KIT = False               True, or a list of objects, for kit pieces: their open ends and sides meet a neighbor, so an opening is only noted
    SEEN_FROM_INSIDE = ["Room"]  objects looked at from inside, such as a room or a sky dome: their normals point inward on purpose
    TWO_SIDED = ["Cape"]      objects drawn with both sides of their faces: an opening in them shows no hole
    LOWEST_VIEW = 0           degrees above the horizon: the lowest the camera looks from, for what an opening shows
    MOVES = ["Piston"]        parts that move in the game, besides those with keys of their own: what hides them at rest doesn't in play
    SEE_THROUGH = ["Glass"]   objects drawn transparent: what is inside them shows, so they hide nothing
    BLUR_OK = ["Cabinet"]     objects with a side nobody sees on few texels on purpose, under UV_KIND = "UNIQUE"
    RIG_HELPERS = "/abs/rig.py"  where rig.py is, when this file was sent as text and has no __file__ to find it by
    UV_KIND = "AUTO"          how the texture is laid on the mesh:
                              "UNIQUE": every face has its own texels, as a painted or baked texture needs. Overlaps are defects.
                              "SHARED": palette, atlas, trim sheet or tiling: faces share texels on purpose.
                              "NONE": drawn with a flat color or vertex colors: no UVs needed.
                              "AUTO" reads it from the layout, and `info` says what it read. A layout with heavy overlaps reads as
                              shared: set "UNIQUE" whenever a texture is baked or painted on this mesh. It also holds the layout to more:
                              nothing without texels, nothing pulled over 3 times one way, no part at under a quarter of the rest's texels
    TEXTURE_SIZE = 1024       pixels; checks the gap between UV islands of a unique layout, per material: `PADDING` pixels, or they bleed
                              at distance
    PADDING = 4               pixels; see the guide's UVs section for what a gap lasts
    LIGHTMAP_UV = "UVMap2"    the UV map used for lightmaps: inside 0-1, no overlaps at all, and no face without area
    PROOF_DIR = "/abs/docs/proofs"  writes this report to validate_mesh-<PROOF_NAME>.json there
    PROOF_NAME = "crate"      default: the first target's name, else "all"

Sets `result`: `passed`, and one entry per object with its `issues`, which fail, `notes`, which don't: harmless leftovers to clean up when
it's cheap, `examples` (where to look, world coordinates in metres) and `info`; `z_fighting_between_objects` lists face pairs between objects.
Modifiers are applied first, so the check sees what the exporter writes. LOD siblings (`_LOD0`, `_LOD1`) never count as z-fighting.
"""

import json
import math
import os
import re
import types
from collections import defaultdict

import bmesh
import bpy
import numpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

AREA_EPSILON = 1e-10
MAX_EXAMPLES = 3
PARALLEL_COS = math.cos(math.radians(10.0))
NORMAL_QUANTUM = 1e-3
PLANE_QUANTUM = 1e-4
OVERLAP_EPSILON = 1e-6
SEAM_COS = math.cos(math.radians(30.0))
MAX_FACES_FOR_ZFIGHT = 300000
# A person, for what a collision mesh closes off: wide, tall, and the step that is walked over.
PERSON_RADIUS = 0.3
PERSON_HEIGHT = 1.5
# A camera, for what z-fighting shows: its depth buffer, and how many pixels a metre covers on a 1080-line screen at 60 degrees, at one metre.
NEAR_PLANE = 0.3
DEPTH_BITS = 24
PIXELS_PER_DISTANCE = 935.0
PIXELS_SEEN = 3.0


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


def _too_little_to_see(area, surface):
    """Flicker nobody finds: under a hundredth of a small surface, and under a patch of 22 cm square on a large one. A poster or a rug shows well past that."""
    return area < min(0.05, 0.01 * surface)


def _overlap_limit(size):
    """How wide an overlap has to be to show: 1 mm, less on what is small and seen from close by. Float noise and a sliver no pixel covers don't count."""
    return min(0.001, 0.01 * max(size, 1e-6))


def _outline(face, axis_u, axis_v):
    """A face on a plane, as triangles: one that bends, as a wall with a notch for a door does, covers only what it covers."""
    polygon = [(v.co.dot(axis_u), v.co.dot(axis_v)) for v in face.verts]
    if len(polygon) == 3:
        return [polygon]
    return [[polygon[k] for k in triangle] for triangle in tessellate_polygon([[Vector((x, y, 0.0)) for x, y in polygon]])]


def _overlap_depths(first, second):
    """How deep pairs of triangles lie in each other on a plane: the least they overlap along the sides of either, as separating axes do. At
    most 0 when apart or only touching, so two floors that share a side line up and still count by how far they overlap."""
    depth = numpy.full(len(first), numpy.inf)
    for triangles in (first, second):
        for k in range(3):
            side = triangles[:, (k + 1) % 3] - triangles[:, k]
            axis = numpy.stack((-side[:, 1], side[:, 0]), axis=1)
            axis /= numpy.maximum(numpy.linalg.norm(axis, axis=1, keepdims=True), 1e-12)
            a = numpy.einsum("ijk,ik->ij", first, axis)
            b = numpy.einsum("ijk,ik->ij", second, axis)
            depth = numpy.minimum(depth, numpy.minimum(a.max(axis=1), b.max(axis=1)) - numpy.maximum(a.min(axis=1), b.min(axis=1)))
    return depth


def _triangle_overlap(first, second):
    """The area two triangles on a plane have in common, one clipped by the other."""
    a, b, c = second
    if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) < 0.0:
        second = (a, c, b)
    polygon = list(first)
    for k in range(3):
        px, py = second[k]
        qx, qy = second[(k + 1) % 3]
        kept = []
        for i, (x, y) in enumerate(polygon):
            nx, ny = polygon[(i + 1) % len(polygon)]
            here = (qx - px) * (y - py) - (qy - py) * (x - px)
            there = (qx - px) * (ny - py) - (qy - py) * (nx - px)
            if here >= 0.0:
                kept.append((x, y))
            if here * there < 0.0:
                t = here / (here - there)
                kept.append((x + (nx - x) * t, y + (ny - y) * t))
        polygon = kept
        if not polygon:
            return 0.0
    return abs(sum(polygon[i][0] * polygon[(i + 1) % len(polygon)][1] - polygon[(i + 1) % len(polygon)][0] * polygon[i][1] for i in range(len(polygon)))) / 2.0


def _close_pairs(low, high, margin=0.0):
    """Pairs of boxes on a plane nearer than `margin`, with no loop per pair: by a grid of cells as large as the larger boxes. The few far larger
    than the rest are tried against all, so one big floor among a thousand tiles doesn't make every cell big."""
    count = len(low)
    if count < 2:
        return numpy.zeros(0, dtype=numpy.int64), numpy.zeros(0, dtype=numpy.int64)
    sizes = (high - low).max(axis=1)
    usual = max(float(numpy.median(sizes)), 1e-9)
    large = numpy.nonzero(sizes > 8.0 * usual)[0]
    small = numpy.nonzero(sizes <= 8.0 * usual)[0]
    firsts, seconds = [], []
    if len(small) > 1:
        cell = max(float(sizes[small].max()) + margin, 1e-9)
        cells = numpy.floor(((low + high) / 2.0)[small] / cell).astype(numpy.int64)
        cells -= cells.min(axis=0) - 1
        width = int(cells[:, 1].max()) + 2
        keys = cells[:, 0] * width + cells[:, 1]
        order = numpy.argsort(keys, kind="stable")
        sorted_keys = keys[order]
        for offset in (0, 1, width - 1, width, width + 1):
            left = numpy.searchsorted(sorted_keys, keys + offset, side="left")
            right = numpy.searchsorted(sorted_keys, keys + offset, side="right")
            numbers = right - left
            if not numbers.any():
                continue
            a = numpy.repeat(numpy.arange(len(small)), numbers)
            starts = numpy.repeat(left, numbers)
            b = order[starts + (numpy.arange(len(a)) - numpy.repeat(numpy.cumsum(numbers) - numbers, numbers))]
            if offset == 0:
                keep = a < b
                a, b = a[keep], b[keep]
            firsts.append(small[a])
            seconds.append(small[b])
    for index in large.tolist():
        others = numpy.arange(count)
        others = others[(others != index) & ((sizes[others] <= 8.0 * usual) | (others > index))]
        firsts.append(numpy.full(len(others), index))
        seconds.append(others)
    if not firsts:
        return numpy.zeros(0, dtype=numpy.int64), numpy.zeros(0, dtype=numpy.int64)
    a, b = numpy.concatenate(firsts), numpy.concatenate(seconds)
    near = (low[a] < high[b] + margin).all(axis=1) & (low[b] < high[a] + margin).all(axis=1)
    return a[near], b[near]


def _inner_point(face):
    """A point inside a face, also one that bends around its middle, as a wall with a notch for a door does."""
    corners = [v.co for v in face.verts]
    if len(corners) == 3:
        return (corners[0] + corners[1] + corners[2]) / 3.0
    triangles = tessellate_polygon([corners])
    a, b, c = max(triangles, key=lambda t: (corners[t[1]] - corners[t[0]]).cross(corners[t[2]] - corners[t[0]]).length)
    return (corners[a] + corners[b] + corners[c]) / 3.0


def _coplanar_overlaps(faces, size):
    """Faces on one plane that lie on each other, facing the same way or opposite ways. Faces with the same corners are duplicates, counted apart."""
    buckets = defaultdict(list)
    normals = {}
    for face in faces:
        if face.calc_area() > AREA_EPSILON:
            key, canonical, sign = _canonical_plane(face)
            buckets[key].append((face, sign))
            normals.setdefault(key, canonical)

    same_facing = 0
    opposite_facing = 0
    examples = []
    same_area = 0.0
    limit = _overlap_limit(size)
    for key, members in buckets.items():
        if len(members) < 2:
            continue
        # Along a side of a face, so that a grid's cells line up with the axes and neighbors' boxes don't overlap.
        normal = normals[key]
        side = members[0][0].verts[1].co - members[0][0].verts[0].co
        side -= normal * side.dot(normal)
        axis_u = side.normalized() if side.length > 1e-9 else normal.orthogonal().normalized()
        axis_v = normal.cross(axis_u).normalized()
        triangles, owners = [], []
        for index, (face, _) in enumerate(members):
            for triangle in _outline(face, axis_u, axis_v):
                triangles.append(triangle)
                owners.append(index)
        points = numpy.array(triangles, dtype=numpy.float64)
        owners = numpy.array(owners)
        a, b = _close_pairs(points.min(axis=1), points.max(axis=1))
        keep = owners[a] != owners[b]
        a, b = a[keep], b[keep]
        if not len(a):
            continue
        overlapping = _overlap_depths(points[a], points[b]) > limit
        pairs = {(min(x, y), max(x, y)) for x, y in zip(owners[a[overlapping]].tolist(), owners[b[overlapping]].tolist())}
        for first, second in pairs:
            face_a, sign_a = members[first]
            face_b, sign_b = members[second]
            if {v.index for v in face_a.verts} == {v.index for v in face_b.verts}:
                continue
            if len(examples) < MAX_EXAMPLES:
                examples.append(face_a.calc_center_median())
            if sign_a == sign_b:
                same_facing += 1
                same_area += sum(_triangle_overlap(p, q) for p in _outline(face_a, axis_u, axis_v) for q in _outline(face_b, axis_u, axis_v))
            else:
                opposite_facing += 1
    return same_facing, opposite_facing, examples, same_area


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


def _escapes(tree, point, direction):
    return tree.ray_cast(point, direction, 1000.0)[0] is None


def _cone(normal):
    tangent = normal.orthogonal().normalized()
    bitangent = normal.cross(tangent)
    return [normal] + [(normal + axis * 0.84).normalized() for axis in (tangent, -tangent, bitangent, -bitangent)]


def _closure(faces):
    """How far a surface closes around its own middle, as a share of all directions, and which way it looks: 1 for a closed surface looking out, -1 for one
    turned inside out, whatever its proportions; -5/6 for a crate without a lid turned inside out, and 0 for a flat sheet. A curtain, a backdrop or a
    half-pipe stays under -1/2: they are seen from the side they look to. By the solid angle each triangle takes up."""
    triangles = []
    for face in faces:
        corners = [v.co for v in face.verts]
        for k in range(1, len(corners) - 1):
            triangles.append((corners[0], corners[k], corners[k + 1]))
    if not triangles:
        return 0.0
    points = numpy.array(triangles, dtype=numpy.float64)
    relative = points - points.reshape(-1, 3).mean(axis=0)
    a, b, c = relative[:, 0], relative[:, 1], relative[:, 2]
    la, lb, lc = (numpy.maximum(numpy.linalg.norm(v, axis=1), 1e-12) for v in (a, b, c))
    top = numpy.einsum("ij,ij->i", a, numpy.cross(b, c))
    bottom = la * lb * lc + numpy.einsum("ij,ij->i", a, b) * lc + numpy.einsum("ij,ij->i", a, c) * lb + numpy.einsum("ij,ij->i", b, c) * la
    return float((2.0 * numpy.arctan2(top, bottom)).sum() / (4.0 * math.pi))


def _signed_volume(faces):
    """What a closed surface encloses, negative when it looks inward."""
    volume = 0.0
    for face in faces:
        corners = [v.co for v in face.verts]
        for k in range(1, len(corners) - 1):
            volume += corners[0].dot(corners[k].cross(corners[k + 1])) / 6.0
    return volume


def _inconsistent_normals(bm, seen_from_inside, size, matrix, cover):
    """Faces drawn inside out, which backface culling shows as holes. Neighbors are found by where they are, since hard edges split vertices and not the
    surface. Within a closed surface the few that disagree are wrong. All of one turned inward are a hollow where something covers their backs, and a defect
    where nothing does; an open surface that nearly closes the same. Where faces meet on one edge in threes neighbors tell nothing: there, a face that looks
    inward and shows its back to the outside. A flat sheet that faces down with its back to the sky is a floor drawn by nothing from where the camera is. What is
    seen from inside has only its neighbors to go by. What draws both sides isn't asked. `cover` holds the whole asset in the world: the bottom half of a buoy or a shell's
    lining has its back covered by another object."""
    bm.faces.index_update()
    bm.faces.ensure_lookup_table()
    original = [face.normal.copy() for face in bm.faces]
    centers = [face.calc_center_median() for face in bm.faces]
    welded = bm.copy()
    source = welded.faces.layers.int.new("source_face")
    for index, face in enumerate(welded.faces):
        face[source] = index
    bmesh.ops.remove_doubles(welded, verts=welded.verts[:], dist=max(1e-5, 1e-6 * size))
    bmesh.ops.recalc_face_normals(welded, faces=welded.faces[:])
    nudge = 1e-4 * min(1.0, size)
    tree = BVHTree.FromBMesh(bm)
    turned = matrix.to_3x3().inverted_safe().transposed()

    def back_shows(index):
        return _back_shows(cover, matrix @ centers[index], (turned @ original[index]).normalized(), nudge)

    wrong = set()
    for component in _connected_components(welded.faces[:]):
        counts = [len(edge.link_faces) for face in component for edge in face.edges]
        members = [face[source] for face in component]
        if max(counts) > 2:
            for index in members:
                normal = original[index]
                if normal.length < 0.5:
                    continue
                offset = normal * nudge
                if not any(_escapes(tree, centers[index] + offset, d) for d in _cone(normal)) and any(_escapes(tree, centers[index] - offset, d) for d in _cone(-normal)):
                    wrong.add(index)
            continue
        flipped = [face[source] for face in component if face.normal.dot(original[face[source]]) < 0]
        kept = [face[source] for face in component if face.normal.dot(original[face[source]]) >= 0]
        fewer = flipped if len(flipped) < len(kept) else kept
        if seen_from_inside:
            wrong.update(fewer)
        elif min(counts) == 2 and flipped and kept:
            wrong.update(fewer)
        elif min(counts) == 2:
            # All one way. Blender's guess at outward fails on thin concave shapes: the volume they enclose has the sign. Looking inward is right for a hollow in a solid,
            # or the lining of a pipe, and what covers their backs says so.
            if _signed_volume([bm.faces[i] for i in members]) < 0.0:
                wrong.update(i for i in members if back_shows(i))
        elif _closure([bm.faces[i] for i in members]) < -0.6:
            wrong.update(i for i in members if back_shows(i))
        else:
            wrong.update(i for i in fewer if back_shows(i))
        # A floor turned over: one flat part, facing down, nothing over it. The hull under a deck faces down too, and isn't flat.
        if not seen_from_inside and globals().get("LOWEST_VIEW", 0) >= 0:
            heights = [v.co.z for i in members for v in bm.faces[i].verts]
            xs = [v.co.x for i in members for v in bm.faces[i].verts]
            ys = [v.co.y for i in members for v in bm.faces[i].verts]
            if max(heights) - min(heights) <= 0.02 * max(max(xs) - min(xs), max(ys) - min(ys)):
                wrong.update(i for i in members if original[i].z < -0.7 and _escapes(cover, matrix @ centers[i] - (turned @ original[i]).normalized() * nudge, -(turned @ original[i]).normalized()))
    # A card drawn from both sides is two faces on the same corners, back to back: each covers the other's back.
    quantum = max(1e-5, 1e-6 * size)
    corners_of = defaultdict(list)
    for face in bm.faces:
        corners_of[frozenset(tuple(round(c / quantum) for c in v.co) for v in face.verts)].append(face.index)
    for faces in corners_of.values():
        if len(faces) > 1:
            wrong.difference_update(faces)
    welded.free()
    ordered = sorted(wrong)
    return len(ordered), [centers[i] for i in ordered[:MAX_EXAMPLES]]


def _back_shows(tree, center, normal, nudge):
    """Whether a camera can see a face from behind: a look from where nothing is in the way, and from above the horizon if the camera stays there."""
    if normal.length < 0.5:
        return False
    behind = center - normal * nudge
    floor = math.sin(math.radians(globals().get("LOWEST_VIEW", 0)))
    return any(direction.z >= floor - 1e-6 and _escapes(tree, behind, direction) for direction in _cone(-normal))


class _Layout:
    """A UV map's faces as numbers: per triangle its area on the mesh, its area in UV and how stretched it is, its island, and overlaps. `aspects`
    gives a material's texture its shape: on a strip 8 times wider than tall, a plank mapped edge to edge isn't pulled at all."""

    SIZE = 512

    def __init__(self, bm, layer, images=None):
        self.layer = layer
        images = images or {}
        looks_down = globals().get("LOWEST_VIEW", 0) >= 0
        self.triangles = bm.calc_loop_triangles()
        self.surface = 0.0
        self.uv_area = 0.0
        self.collapsed = 0.0
        self.one_color = 0.0
        self.pulled = 0.0
        self.stretched = 0.0
        self.very_stretched = 0.0
        self.densities = []
        self.invalid = False
        low_u = low_v = math.inf
        high_u = high_v = -math.inf
        loops = beyond = at_origin = 0
        for triangle in self.triangles:
            points = [loop.vert.co for loop in triangle]
            uvs = [loop[layer].uv for loop in triangle]
            if not all(math.isfinite(uv.x) and math.isfinite(uv.y) for uv in uvs):
                self.invalid = True
                continue
            for uv in uvs:
                low_u, high_u = min(low_u, uv.x), max(high_u, uv.x)
                low_v, high_v = min(low_v, uv.y), max(high_v, uv.y)
                loops += 1
                beyond += uv.x < -0.05 or uv.y < -0.05 or uv.x > 1.05 or uv.y > 1.05
                at_origin += uv.x == 0.0 and uv.y == 0.0
            edge_a, edge_b = points[1] - points[0], points[2] - points[0]
            cross = edge_a.cross(edge_b)
            area = cross.length / 2.0
            uv_a, uv_b = uvs[1] - uvs[0], uvs[2] - uvs[0]
            uv_area = abs(uv_a.x * uv_b.y - uv_a.y * uv_b.x) / 2.0
            self.surface += area
            self.uv_area += uv_area
            if area <= AREA_EPSILON:
                continue
            # What faces down isn't looked at, so a crate's bottom may have few texels, or none.
            down = looks_down and triangle[0].face.normal.z < -0.7
            if uv_area <= 1e-12:
                # On a line of texels a texture smears. On one spot it is one color, as a palette or a solid pixel means it.
                reach = max(max(uv.x for uv in uvs) - min(uv.x for uv in uvs), max(uv.y for uv in uvs) - min(uv.y for uv in uvs))
                if down:
                    pass
                elif reach < 1.0 / self.SIZE:
                    self.one_color += area
                else:
                    self.collapsed += area
                continue
            # In pixels when the texture is known: a face on 4096 and one on 128 at one UV density are 32 times apart. Pulled along its own shape.
            width, height = images.get(triangle[0].face.material_index, (0, 0))
            self.densities.append((uv_area / area * (width * height if width and height else 1), area, down))
            if width and height and width != height:
                ratio = width / height
                uv_a, uv_b = Vector((uv_a.x * ratio, uv_a.y)), Vector((uv_b.x * ratio, uv_b.y))
            # How far the texture is pulled one way against the other: the two stretches of the map from the face to its UVs.
            axis_x = edge_a.normalized()
            axis_y = cross.normalized().cross(axis_x)
            ax, ay, bx, by = edge_a.dot(axis_x), edge_a.dot(axis_y), edge_b.dot(axis_x), edge_b.dot(axis_y)
            det = ax * by - ay * bx
            if abs(det) <= 1e-14:
                continue
            j00, j01 = (uv_a.x * by - uv_b.x * ay) / det, (uv_b.x * ax - uv_a.x * bx) / det
            j10, j11 = (uv_a.y * by - uv_b.y * ay) / det, (uv_b.y * ax - uv_a.y * bx) / det
            e, g, f = j00 * j00 + j10 * j10, j01 * j01 + j11 * j11, j00 * j01 + j10 * j11
            root = math.sqrt(max(0.0, (e - g) ** 2 + 4.0 * f * f))
            large, small = math.sqrt((e + g + root) / 2.0), math.sqrt(max(0.0, (e + g - root) / 2.0))
            pull = large / small if small > 1e-12 else math.inf
            if pull > 3.0:
                self.pulled += area
            if pull > 5.0:
                self.stretched += area
            if pull > 10.0:
                self.very_stretched += area
        self.extent = (low_u, high_u, low_v, high_v) if loops else (0.0, 0.0, 0.0, 0.0)
        self.never_unwrapped = loops > 0 and at_origin == loops
        # A vertex or two past the edge don't make a tiling texture.
        self.tiling = loops > 0 and beyond >= 0.05 * loops
        self.borders = []
        self.stacked_pairs = set()
        self.overlap_share = 0.0
        self.stacked_share = 0.0
        self.islands = 0
        self.span = 1.0

    def outside(self):
        low_u, high_u, low_v, high_v = self.extent
        return low_u < -1e-4 or low_v < -1e-4 or high_u > 1.0001 or high_v > 1.0001

    def thin_share(self):
        """How much of the surface has under a quarter of the texels per metre the sharpest tenth of it has: it shows blurred beside it. Against the sharpest,
        so that a box blurred on four of its six sides doesn't set the measure."""
        seen = sorted((d, a) for d, a, down in self.densities if not down)
        total = sum(a for _, a in seen)
        if not total:
            return 0.0
        running = 0.0
        sharp = seen[-1][0]
        for density, area in seen:
            running += area
            if running >= 0.9 * total:
                sharp = density
                break
        return sum(a for d, a in seen if d < sharp / 16.0) / max(self.surface, 1e-12)

    def runs_on(self, bm):
        """How the edges between faces carry their texture across: the share that does, and of those the share that folds, with both faces on one side of it.
        None running on, on a mesh whose faces are also pulled out of shape, is noise; and so is folding back and forth, as when each vertex has a UV at random."""
        joined = folded = total = 0
        layer = self.layer

        def turn(loop):
            first, second, third = loop[layer].uv, loop.link_loop_next[layer].uv, loop.link_loop_next.link_loop_next[layer].uv
            return (second.x - first.x) * (third.y - first.y) - (second.y - first.y) * (third.x - first.x)

        for edge in bm.edges:
            loops = edge.link_loops
            if len(loops) != 2:
                continue
            total += 1
            a, b = loops
            if (a[layer].uv - b.link_loop_next[layer].uv).length < 1e-5 and (a.link_loop_next[layer].uv - b[layer].uv).length < 1e-5:
                joined += 1
                if turn(a) * turn(b) < 0.0:
                    folded += 1
        return joined / max(total, 1), folded / max(joined, 1)

    def _label_islands(self, bm):
        """Faces that run on from each other in UV. A hard edge splits vertices and not the layout, so what joins them is where they are."""
        layer = self.layer
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        parent = list(range(len(bm.faces)))

        def find(item):
            while parent[item] != item:
                parent[item] = parent[parent[item]]
                item = parent[item]
            return item

        def rounded(vector, digits):
            return tuple(round(c, digits) for c in vector)

        edges = {}
        uses = defaultdict(int)
        for face in bm.faces:
            for loop in face.loops:
                a = (rounded(loop.vert.co, 5), rounded(loop[layer].uv, 5))
                b = (rounded(loop.link_loop_next.vert.co, 5), rounded(loop.link_loop_next[layer].uv, 5))
                key = (a, b) if a <= b else (b, a)
                first = edges.setdefault(key, face.index)
                uses[key] += 1
                parent[find(face.index)] = find(first)
        roots = {}
        label = [roots.setdefault(find(k), len(roots)) for k in range(len(parent))]
        self.islands = len(roots)
        # What bounds an island: the sides no other face runs on from.
        self.borders = []
        for key, number in uses.items():
            if number == 1:
                face = edges[key]
                self.borders.append((key[0][1], key[1][1], label[face], bm.faces[face].material_index))
        return label

    def rasterize(self, bm):
        """Draws the islands on a grid per material, whose faces can't show each other's texture: where two lie on each other, and how far
        apart they are. Islands that lie exactly on each other are mirrored or reused on purpose, and counted apart."""
        label = self._label_islands(bm)
        low_u, high_u, low_v, high_v = self.extent
        self.span = max(high_u - low_u, high_v - low_v, 1e-6)
        scale = self.SIZE / self.span
        by_material = defaultdict(list)
        for triangle in self.triangles:
            by_material[triangle[0].face.material_index].append(triangle)
        covered = overlap = stacked = 0
        self.stacked_pairs = set()
        for triangles in by_material.values():
            grid = numpy.full((self.SIZE, self.SIZE), -1, dtype=numpy.int32)
            faces = numpy.full((self.SIZE, self.SIZE), -1, dtype=numpy.int32)
            pairs = defaultdict(int)
            cells = defaultdict(int)
            for triangle in triangles:
                face = triangle[0].face.index
                island = label[face]
                uvs = [loop[self.layer].uv for loop in triangle]
                if not all(math.isfinite(uv.x) and math.isfinite(uv.y) for uv in uvs):
                    continue
                (ax, ay), (bx, by), (cx, cy) = [((uv.x - low_u) * scale, (uv.y - low_v) * scale) for uv in uvs]
                denominator = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
                if abs(denominator) < 1e-9:
                    continue
                x0, x1 = max(0, int(min(ax, bx, cx))), min(self.SIZE, int(max(ax, bx, cx)) + 1)
                y0, y1 = max(0, int(min(ay, by, cy))), min(self.SIZE, int(max(ay, by, cy)) + 1)
                if x0 >= x1 or y0 >= y1:
                    continue
                xs, ys = numpy.meshgrid(numpy.arange(x0, x1) + 0.5, numpy.arange(y0, y1) + 0.5, indexing="ij")
                w1 = ((bx - ax) * (ys - ay) - (by - ay) * (xs - ax)) / denominator
                w2 = ((xs - ax) * (cy - ay) - (ys - ay) * (cx - ax)) / denominator
                # Strictly inside: a cell's middle on the line between two triangles of a regular grid belongs to neither.
                inside = (w1 > 1e-6) & (w2 > 1e-6) & (w1 + w2 < 1.0 - 1e-6)
                if not inside.any():
                    continue
                part, part_faces = grid[x0:x1, y0:y1], faces[x0:x1, y0:y1]
                empty = inside & (part < 0)
                taken = inside & (part >= 0)
                if taken.any():
                    others, counts = numpy.unique(part[taken], return_counts=True)
                    for other, number in zip(others.tolist(), counts.tolist()):
                        if other != island:
                            pairs[(min(other, island), max(other, island))] += number
                    overlap += int(((part[taken] == island) & (part_faces[taken] != face)).sum())
                part[empty] = island
                part_faces[empty] = face
                cells[island] += int(inside.sum())
            covered += int((grid >= 0).sum())
            for (a, b), number in pairs.items():
                small, large = min(cells[a], cells[b]), max(cells[a], cells[b])
                if number >= 0.8 * small and small >= 0.8 * large:
                    stacked += number
                    self.stacked_pairs.add((a, b))
                else:
                    overlap += number
        covered = max(1, covered)
        self.overlap_share = overlap / covered
        self.stacked_share = stacked / covered

    def smallest_gap(self, padding, texture_size, images):
        """The narrowest gap under `padding` pixels between islands of one material, and how many sides lie that close; a side of an island against the other's,
        exactly, since no grid sees a gap of a few pixels on a large texture. In the pixels of the material's texture when it is known, wide or tall. Stacked
        islands are one, and each material has its own texture to bleed in."""
        closest = None
        close = 0
        stacked = self.stacked_pairs
        materials = defaultdict(list)
        for border in self.borders:
            materials[border[3]].append(border)
        for material, borders in materials.items():
            width, height = images.get(material, (0, 0))
            scale = numpy.array((width, height) if width and height else (texture_size, texture_size), dtype=numpy.float64)
            starts = numpy.array([b[0] for b in borders], dtype=numpy.float64) * scale
            ends = numpy.array([b[1] for b in borders], dtype=numpy.float64) * scale
            islands = numpy.array([b[2] for b in borders])
            a, b = _close_pairs(numpy.minimum(starts, ends), numpy.maximum(starts, ends), padding)
            keep = islands[a] != islands[b]
            a, b = a[keep], b[keep]
            if stacked and len(a):
                together = {(x, y) for x, y in stacked} | {(y, x) for x, y in stacked}
                keep = numpy.array([(x, y) not in together for x, y in zip(islands[a].tolist(), islands[b].tolist())])
                a, b = a[keep], b[keep]
            if not len(a):
                continue
            gaps = _segment_distances(starts[a], ends[a], starts[b], ends[b])
            near = gaps < padding
            close += int(near.sum())
            if near.any():
                closest = min(closest, float(gaps[near].min())) if closest is not None else float(gaps[near].min())
        return closest, close


def _segment_distances(p1, p2, q1, q2):
    """How far pairs of segments on a plane are from each other: the nearest of their ends to the other, and 0 if they cross."""

    def to_segment(points, a, b):
        side = b - a
        t = numpy.clip(numpy.einsum("ij,ij->i", points - a, side) / numpy.maximum(numpy.einsum("ij,ij->i", side, side), 1e-18), 0.0, 1.0)
        return numpy.linalg.norm(points - (a + side * t[:, None]), axis=1)

    def cross(a, b):
        return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]

    gaps = numpy.minimum.reduce([to_segment(p1, q1, q2), to_segment(p2, q1, q2), to_segment(q1, p1, p2), to_segment(q2, p1, p2)])
    crossing = (cross(q2 - q1, p1 - q1) * cross(q2 - q1, p2 - q1) < 0.0) & (cross(p2 - p1, q1 - p1) * cross(p2 - p1, q2 - p1) < 0.0)
    gaps[crossing] = 0.0
    return gaps


def _first_uv_layer(bm):
    """The map Unity reads as the texture's: the first in the file, whichever Blender shows as active."""
    layers = bm.loops.layers.uv
    return layers[0] if len(layers) else None


def _images(obj):
    """The texture each of an object's materials draws, by material slot: the image on its base color if it can tell, else the first image that leads
    somewhere, also inside node groups."""
    found = {}

    def walk(tree, depth=0):
        first = None
        for link in tree.links:
            if link.to_socket.name == "Base Color" and link.from_node.type == "TEX_IMAGE" and link.from_node.image:
                return link.from_node.image
        for node in tree.nodes:
            if node.type == "TEX_IMAGE" and node.image and any(output.is_linked for output in node.outputs):
                first = first or node.image
            elif node.type == "GROUP" and node.node_tree and depth < 8:
                first = first or walk(node.node_tree, depth + 1)
        return first

    for index, slot in enumerate(obj.material_slots):
        tree = slot.material.node_tree if slot.material else None
        image = walk(tree) if tree else None
        if image:
            found[index] = image
    return found


def _uv_report(bm, obj):
    """The UV map as the kind of layout it is. Issues, notes and info."""
    issues, notes, info = {}, {}, {}
    kind = globals().get("UV_KIND", "AUTO")
    layer = _first_uv_layer(bm)
    images = _images(obj)
    if kind == "NONE":
        info["uv_kind"] = "none"
        if images:
            issues["uv_kind_none_with_texture"] = f"UV_KIND is NONE, and its material draws {next(iter(images.values())).name}: nothing here checks how that texture lies on it. Remove the setting"
        return issues, notes, info
    if layer is None:
        if images or kind == "UNIQUE" or (kind != "SHARED" and not obj.data.color_attributes):
            issues["no_uv_map"] = "no UV map, so no texture can show on it. If it is drawn with a flat color, set UV_KIND to NONE"
        info["uv_kind"] = "none" if kind != "UNIQUE" else "unique"
        return issues, notes, info
    sizes = {index: (image.size[0], image.size[1]) for index, image in images.items()}
    layout = _Layout(bm, layer, sizes)
    surface = max(layout.surface, 1e-12)
    if layout.invalid:
        issues["uv_invalid"] = "a UV coordinate isn't a number: the exporter writes garbage, and the file may not import"
    info["uv_area"] = round(layout.uv_area, 4)
    info["uv_extent"] = [round(c, 3) for c in layout.extent]
    if layout.densities:
        total = max(sum(a for _, a, _ in layout.densities), 1e-12)
        mean = sum(d * a for d, a, _ in layout.densities) / total
        spread = (sum(a * (d - mean) ** 2 for d, a, _ in layout.densities) / total) ** 0.5
        info["texel_density_spread"] = round(spread / max(mean, 1e-12), 3)
    keep_out = "If it is drawn with a flat color, set UV_KIND to NONE; if no pattern runs that way, as on a gradient or a trim column, to SHARED"
    collapsed = layout.collapsed / surface
    stretched = layout.stretched / surface
    if kind == "AUTO" and layout.never_unwrapped:
        info["uv_kind"] = "never unwrapped"
        issues["uv_never_unwrapped"] = "every UV sits at 0,0: this map was made and never laid out. If it is drawn with a flat color, set UV_KIND to NONE"
        return issues, notes, info
    # A palette, an atlas or tiling shares its texels by design: its faces can lie on each other and collapse into one color.
    palette = kind != "UNIQUE" and layout.uv_area < 0.02
    # Professional work has a third of its edges carrying the texture across at the very least, and under a third of them folding. A layout of a square per face has none running on, and keeps its faces alike.
    if not palette and layout.pulled / surface > 0.3:
        runs_on, folds = layout.runs_on(bm)
        info["uv_folds_share"] = round(folds, 4)
        if layout.pulled / surface > 0.5 and ((runs_on < 0.1 and info.get("texel_density_spread", 0.0) > 0.5) or folds > 0.35):
            issues["uv_scrambled"] = "the faces don't run on from each other in UV, or fold back and forth, and are pulled out of shape: a texture on it shows as noise. A wrong index in whatever wrote the UVs does this"
    shared = kind == "SHARED" or (kind == "AUTO" and (layout.tiling or palette or layout.uv_area > 1.3))
    if not shared:
        layout.rasterize(bm)
        info["uv_islands"] = layout.islands
        info["uv_overlap_share"] = round(layout.overlap_share, 4)
        if layout.stacked_share:
            info["uv_stacked_share"] = round(layout.stacked_share, 4)
        shared = kind == "AUTO" and layout.overlap_share >= 0.05
    if shared:
        info["uv_kind"] = "shared"
        # Read as shared, that doesn't take away what no texture survives: sides projected into lines, or streaks. A palette has no pattern to smear. Said to be shared,
        # as a gradient up a thin column of an atlas is, the author knows what runs which way: it is noted.
        if not palette:
            bucket = notes if kind == "SHARED" else issues
            if collapsed > 0.3:
                bucket["uv_collapsed"] = f"{collapsed:.0%} of the surface lies on a line in UV: the texture smears there, as on the sides of a box projected from above. {keep_out}"
            if layout.very_stretched / surface > 0.3:
                bucket["uv_stretched"] = f"{layout.very_stretched / surface:.0%} of the surface pulls the texture over 10 times more one way than the other: the pattern shows as streaks. {keep_out}"
        return issues, notes, info
    info["uv_kind"] = "unique"
    pulled = layout.pulled / surface
    thin = layout.thin_share()
    if kind == "UNIQUE":
        blank = collapsed + layout.one_color / surface
        if blank > 0.01:
            issues["uv_collapsed"] = f"{blank:.0%} of the surface has no UV area: the texture smears there, or shows one texel"
        if pulled > 0.1:
            issues["uv_stretched"] = f"{pulled:.0%} of the surface pulls the texture over 3 times more one way than the other: the pattern shows as streaks"
        if thin > 0.1 and obj.name not in globals().get("BLUR_OK", ()):
            issues["uv_uneven_density"] = f"{thin:.0%} of the surface has under a quarter of the texels per metre the sharpest of it has: it shows blurred beside it. If nobody sees that side, list it in BLUR_OK"
    else:
        if collapsed > 0.3:
            issues["uv_collapsed"] = f"{collapsed:.0%} of the surface lies on a line in UV: the texture smears there, one line of texels drawn across it. {keep_out}"
        elif collapsed > 0.0:
            notes["uv_collapsed_share"] = round(collapsed, 4)
        if stretched > 0.1:
            issues["uv_stretched"] = f"{stretched:.0%} of the surface pulls the texture over 5 times more one way than the other: the pattern shows as streaks. {keep_out}"
        elif pulled > 0.3:
            notes["uv_stretched_share"] = round(pulled, 4)
        if thin > 0.1:
            notes["uv_uneven_density"] = round(thin, 4)
    if layout.overlap_share >= 0.005:
        message = f"{layout.overlap_share:.1%} of the layout lies on another part of it: those faces show each other's texels"
        if kind == "UNIQUE":
            issues["uv_overlap"] = message
        else:
            notes["uv_overlap"] = message
    if kind == "UNIQUE" and layout.stacked_share >= 0.005:
        issues["uv_stacked_islands"] = f"{layout.stacked_share:.1%} of the layout is islands stacked exactly: right for mirrored parts, wrong for what is baked"
    if layout.outside():
        if kind == "UNIQUE":
            issues["uv_outside_0_1"] = f"it reaches {[round(c, 3) for c in layout.extent]}: past 0-1 a texture repeats, so those faces share another's texels"
        else:
            notes["uv_outside_0_1"] = [round(c, 3) for c in layout.extent]
    texture_size = globals().get("TEXTURE_SIZE")
    if texture_size:
        padding = globals().get("PADDING", 4)
        closest, close = layout.smallest_gap(padding, texture_size, sizes)
        if close:
            issues["uv_padding"] = f"the closest islands are {closest:.1f} px apart, {close} of their sides under {padding} px: colors bleed across at a distance"
    return issues, notes, info


def _lightmap_report(bm):
    name = globals().get("LIGHTMAP_UV")
    if not name:
        return {}
    layer = bm.loops.layers.uv.get(name)
    if layer is None:
        return {"no_lightmap_uv": f"no UV map named {name}"}
    issues = {}
    layout = _Layout(bm, layer)
    if layout.outside():
        issues["lightmap_uv_outside"] = f"extends to {[round(c, 3) for c in layout.extent]}, past 0-1"
    blank = layout.collapsed + layout.one_color
    if blank > 0.01 * max(layout.surface, 1e-12):
        issues["lightmap_uv_collapsed"] = f"{blank / max(layout.surface, 1e-12):.0%} of the surface has no area in it: those faces get one texel of light"
    layout.rasterize(bm)
    if layout.overlap_share + layout.stacked_share >= 0.002:
        issues["lightmap_uv_overlap"] = f"{layout.overlap_share + layout.stacked_share:.1%} of it lies on itself: light bakes wrong there"
    return issues


def _transform_report(obj):
    """Whether what the exporter writes keeps the object as modeled. One mesh placed many times, as a kit or a layout, can't be applied and
    doesn't need to be, and a child's rotation is how it is placed on its parent, such as a door on its hinge. A parent scaled unevenly shears
    whatever turns under it."""
    shared = obj.data.users > 1
    scale_ok = shared or all(abs(s - 1.0) < 1e-4 for s in obj.scale)
    world = obj.matrix_world.to_scale()
    if not shared and max(abs(c) for c in world) - min(abs(c) for c in world) > 1e-3 * max(abs(c) for c in world):
        scale_ok = False
    if shared or obj.parent is not None:
        return scale_ok, [round(s, 4) for s in obj.scale], [round(r, 4) for r in obj.rotation_euler]
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


def _flat_needed_triangles(bm, bent):
    """Triangles the flat areas would need at the least: each area, as far as UVs and materials run on, as a polygon of what must stay: the corners of its outline,
    and the vertices that faces outside it hang on, plus two for each hole. Dissolving them to count takes minutes on a grid of a few hundred cells. A face whose
    normals bend isn't flat to the eye, as with the loops that hold smooth shading to a box's edge."""
    layers = list(bm.loops.layers.uv)
    limit = math.cos(math.radians(0.1))

    def joins(edge):
        loops = edge.link_loops
        if len(loops) != 2 or edge.seam:
            return False
        a, b = loops
        if bent[a.face.index] > 1.0 or bent[b.face.index] > 1.0:
            return False
        if a.face.material_index != b.face.material_index or a.face.normal.dot(b.face.normal) < limit:
            return False
        return all((a[layer].uv - b.link_loop_next[layer].uv).length < 1e-5 and (a.link_loop_next[layer].uv - b[layer].uv).length < 1e-5 for layer in layers)

    kept = {edge.index for edge in bm.edges if not joins(edge)}
    # By where they are: a wall's top edge keeps the vertices a separate corrugated roof sits on.
    def at(vert):
        return tuple(round(c * 1e5) for c in vert.co)

    staying = defaultdict(set)
    for edge in bm.edges:
        if edge.index in kept:
            first, second = at(edge.verts[0]), at(edge.verts[1])
            staying[first].add(second)
            staying[second].add(first)
    seen = set()
    needed = 0
    for start in bm.faces:
        if start.index in seen:
            continue
        seen.add(start.index)
        stack = [start]
        outline = defaultdict(list)
        while stack:
            face = stack.pop()
            for edge in face.edges:
                if edge.index not in kept:
                    other = edge.link_faces[0] if edge.link_faces[1] is face else edge.link_faces[1]
                    if other.index not in seen:
                        seen.add(other.index)
                        stack.append(other)
                else:
                    for vert in edge.verts:
                        outline[vert].append(edge.other_vert(vert))
        corners = 0
        for vert, others in outline.items():
            if len(others) != 2 or len(staying[at(vert)]) != 2:
                corners += 1
                continue
            first, second = others[0].co - vert.co, others[1].co - vert.co
            if first.length < 1e-9 or second.length < 1e-9 or abs(first.normalized().dot(second.normalized())) < 0.99999:
                corners += 1
        # The loops of the outline: each one past the first is a hole.
        loops = 0
        unseen = set(outline)
        while unseen:
            loops += 1
            walk = [unseen.pop()]
            while walk:
                for other in outline[walk.pop()]:
                    if other in unseen:
                        unseen.remove(other)
                        walk.append(other)
        needed += max(corners + 2 * (loops - 1) - 2, 1)
    return needed


def _carries_color(mesh):
    """Whether vertex colors say anything: an attribute left over at one color doesn't."""
    for attribute in mesh.color_attributes:
        values = numpy.zeros(len(attribute.data) * 4, dtype=numpy.float32)
        attribute.data.foreach_get("color", values)
        if values.size and float(numpy.ptp(values.reshape(-1, 4), axis=0).max()) > 0.002:
            return True
    return False


def _evaluated_bmesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    bm = bmesh.new()
    bm.from_mesh(evaluated.to_mesh())
    evaluated.to_mesh_clear()
    bm.verts.index_update()
    bm.faces.index_update()
    bm.normal_update()
    return bm


def _where(obj, points):
    return [[round(c, 4) for c in obj.matrix_world @ p] for p in points[:MAX_EXAMPLES]]


def _shading_seams(bm, distance):
    """Edges cut in two between smooth faces that run on from each other: the surface shades as if cut there. Across a corner, as Edge Split
    leaves it, that is a hard edge, and on purpose."""
    quantum = max(distance, 1e-6)

    def key_of(edge):
        ends = sorted(tuple(round(c / quantum) for c in v.co) for v in edge.verts)
        return tuple(ends)

    edges = defaultdict(list)
    for edge in bm.edges:
        if len(edge.link_faces) == 1 and edge.link_faces[0].smooth:
            edges[key_of(edge)].append(edge)
    seams = 0
    for group in edges.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if group[i].link_faces[0].normal.dot(group[j].link_faces[0].normal) > SEAM_COS:
                    seams += 1
    return seams


def _not_finite_object(obj):
    return any(not all(math.isfinite(c) and abs(c) < 1e7 for c in vert.co) for vert in obj.data.vertices)


def _not_finite(bm):
    """Vertices no game can use: not numbers, or further off than single precision holds a surface together."""
    return sum(1 for vert in bm.verts if not all(math.isfinite(c) and abs(c) < 1e7 for c in vert.co))


def _labels(count, first, second):
    """Which group each of `count` items falls in, joined pair by pair, with no loop per pair."""
    labels = numpy.arange(count)
    while len(first):
        before = labels.copy()
        low = numpy.minimum(labels[first], labels[second])
        numpy.minimum.at(labels, first, low)
        numpy.minimum.at(labels, second, low)
        labels = labels[labels]
        if numpy.array_equal(labels, before):
            break
    return labels


class _Shading:
    """How the surface shades, from the normals the exporter writes, however they were made. Neighbors are found by where they are: hard edges split vertices."""

    def __init__(self, obj):
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        try:
            loops, polygons = len(mesh.loops), len(mesh.polygons)
            self.polygons = polygons
            if not polygons:
                return
            corner_vertex = numpy.zeros(loops, dtype=numpy.int32)
            mesh.loops.foreach_get("vertex_index", corner_vertex)
            corner_normal = numpy.zeros(loops * 3, dtype=numpy.float32)
            mesh.corner_normals.foreach_get("vector", corner_normal)
            corner_normal = corner_normal.reshape(-1, 3)
            face_normal = numpy.zeros(polygons * 3, dtype=numpy.float32)
            mesh.polygon_normals.foreach_get("vector", face_normal)
            face_normal = face_normal.reshape(-1, 3)
            self.area = numpy.zeros(polygons, dtype=numpy.float32)
            mesh.polygons.foreach_get("area", self.area)
            self.down = face_normal[:, 2] < -0.7 if globals().get("LOWEST_VIEW", 0) >= 0 else numpy.zeros(polygons, dtype=bool)
            first, count = numpy.zeros(polygons, dtype=numpy.int32), numpy.zeros(polygons, dtype=numpy.int32)
            mesh.polygons.foreach_get("loop_start", first)
            mesh.polygons.foreach_get("loop_total", count)
            position = numpy.zeros(len(mesh.vertices) * 3, dtype=numpy.float64)
            mesh.vertices.foreach_get("co", position)
            position = position.reshape(-1, 3)
        finally:
            evaluated.to_mesh_clear()
        self.face_of = numpy.repeat(numpy.arange(polygons), count)
        next_corner = first[self.face_of] + (numpy.arange(loops) - first[self.face_of] + 1) % count[self.face_of]
        self.corner_position = position[corner_vertex]
        self.size = float((position.max(axis=0) - position.min(axis=0)).max()) if len(position) else 1.0
        self.bent = numpy.zeros(polygons)
        numpy.maximum.at(self.bent, self.face_of, numpy.degrees(numpy.arccos(numpy.clip((corner_normal * face_normal[self.face_of]).sum(axis=1), -1.0, 1.0))))
        where = numpy.unique(numpy.round(position / max(1e-5, 1e-6 * self.size)).astype(numpy.int64), axis=0, return_inverse=True)[1].ravel()
        start_at, end_at = where[corner_vertex], where[corner_vertex[next_corner]]
        low, high = numpy.minimum(start_at, end_at), numpy.maximum(start_at, end_at)
        keys = low * (int(where.max()) + 2) + high
        order = numpy.argsort(keys, kind="stable")
        ordered = keys[order]
        runs = numpy.concatenate(([0], numpy.nonzero(numpy.diff(ordered))[0] + 1))
        lengths = numpy.diff(numpy.concatenate((runs, [len(ordered)])))
        pairs = runs[(lengths == 2) & (low[order[runs]] != high[order[runs]])]
        a, b = order[pairs], order[pairs + 1]
        self.face_a, self.face_b = self.face_of[a], self.face_of[b]
        self.angle = numpy.degrees(numpy.arccos(numpy.clip((face_normal[self.face_a] * face_normal[self.face_b]).sum(axis=1), -1.0, 1.0)))
        # The other face's corners at this edge's two ends.
        same = start_at[b] == start_at[a]
        at_start = numpy.where(same, b, next_corner[b])
        at_end = numpy.where(same, next_corner[b], b)
        apart = (corner_normal[a] * corner_normal[at_start]).sum(axis=1), (corner_normal[next_corner[a]] * corner_normal[at_end]).sum(axis=1)
        self.apart = numpy.degrees(numpy.arccos(numpy.clip(numpy.minimum(*apart), -1.0, 1.0)))
        self.length = numpy.maximum(numpy.linalg.norm(position[corner_vertex[a]] - position[corner_vertex[next_corner[a]]], axis=1), 1e-9)
        self.islands = _labels(polygons, self.face_a, self.face_b)
        self.open_corners = order[runs[lengths == 1]]

    def _sizes(self, labels):
        """Per label, how far what carries it reaches, and its area."""
        count = int(labels.max()) + 1
        low = numpy.full((count, 3), numpy.inf)
        high = numpy.full((count, 3), -numpy.inf)
        numpy.minimum.at(low, labels[self.face_of], self.corner_position)
        numpy.maximum.at(high, labels[self.face_of], self.corner_position)
        area = numpy.zeros(count)
        numpy.add.at(area, labels, self.area)
        return high - low, area

    def _share_shown(self, shown):
        """The largest share of a part of the object that shows the defect: one crate on a yard of one mesh is as bad as a crate alone. A part too small to find doesn't count."""
        reach, area = self._sizes(self.islands)
        shown_area = numpy.zeros(len(area))
        numpy.add.at(shown_area, self.islands[shown], self.area[shown])
        large = reach.max(axis=1) >= 0.02 * self.size
        share = shown_area / numpy.maximum(area, 1e-12)
        return float(share[large].max()) if large.any() else 0.0

    def over_corners(self):
        """Flat faces whose normals bend: the shading runs across them. Where large faces turn a corner and shade as one, as on a box shaded smooth; or a little on a panel beside
        narrow faces, as on a bevel shaded smooth without weighted normals. Large for the whole object, or for a part of it that is hard-surface, as a crate on a yard of one mesh
        is, or 40 boxes merged: on most of its area on a few flat planes. Leaves and rocks shade soft on purpose, and a thin beam or a stem has no width to show it."""
        reach_of_island, _ = self._sizes(self.islands)
        size_of_island = reach_of_island.max(axis=1)
        flat = self.angle < 1.0
        regions = _labels(self.polygons, self.face_a[flat], self.face_b[flat])
        reach, area = self._sizes(regions)
        width = area / numpy.maximum(numpy.linalg.norm(reach, axis=1), 1e-9)
        # What is hard-surface: the eight largest planes of a part hold most of it.
        island_of_region = numpy.zeros(len(area), dtype=numpy.int64)
        island_of_region[regions] = self.islands
        planes = defaultdict(list)
        for index in numpy.nonzero(area > 0.0)[0].tolist():
            planes[int(island_of_region[index])].append(float(area[index]))
        hard = numpy.zeros(len(size_of_island), dtype=bool)
        for island, sizes in planes.items():
            hard[island] = sum(sorted(sizes)[-8:]) >= 0.6 * sum(sizes)
        # Closed: a leaf card isn't what this is about.
        hard &= size_of_island >= 0.02 * self.size
        hard[numpy.unique(self.islands[self.face_of[self.open_corners]])] = False
        measure = numpy.where(hard, numpy.minimum(size_of_island, self.size), self.size)
        size_of_face = measure[self.islands]
        far_a, far_b = self.area[self.face_a] / self.length, self.area[self.face_b] / self.length
        size_at = size_of_face[self.face_a]
        corners = (self.angle > 55.0) & (self.apart < 5.0) & (numpy.maximum(far_a, far_b) >= 0.05 * size_at) & (numpy.minimum(far_a, far_b) >= 0.02 * size_at)
        shown = numpy.zeros(self.polygons, dtype=bool)
        shown[self.face_a[corners]] = True
        shown[self.face_b[corners]] = True
        # The flat bottom of a boulder bends at its rim, and nobody looks at it.
        shown &= ~self.down
        neighbor = numpy.zeros(len(area))
        numpy.maximum.at(neighbor, regions[self.face_a[~flat]], width[regions[self.face_b[~flat]]])
        numpy.maximum.at(neighbor, regions[self.face_b[~flat]], width[regions[self.face_a[~flat]]])
        bent_area = numpy.zeros(len(area))
        mask = (self.bent >= 5.0) & ~self.down
        numpy.add.at(bent_area, regions[mask], self.area[mask])
        size_of_region = numpy.zeros(len(area))
        numpy.maximum.at(size_of_region, regions, size_of_face)
        panel = (bent_area / numpy.maximum(area, 1e-12) >= 0.5) & (width >= 0.1 * size_of_region) & (neighbor <= width / 3.0)
        all_shown = shown | panel[regions]
        whole = float(self.area[all_shown].sum() / max(float(self.area.sum()), 1e-12))
        shown_area = numpy.zeros(len(size_of_island))
        numpy.add.at(shown_area, self.islands[all_shown], self.area[all_shown])
        _, area_of_island = self._sizes(self.islands)
        share = shown_area / numpy.maximum(area_of_island, 1e-12)
        # On its own a part counts when it can be told apart: a crate on a yard, and not a chip off a rock. Forty small boxes count together.
        large = hard & (size_of_island >= 0.05 * self.size)
        return max(whole, float(share[large].max()) if large.any() else 0.0)

    def flat_curves(self):
        """Faces turning one after the other, each shaded flat: a run of ten or more, of faces of like width. One crease is a ridge; a flat top ringed by chamfers isn't a curve either."""
        far_a, far_b = self.area[self.face_a] / self.length, self.area[self.face_b] / self.length
        alike = numpy.maximum(far_a, far_b) <= 3.0 * numpy.maximum(numpy.minimum(far_a, far_b), 1e-9)
        facets = (self.angle > 1.5) & (self.angle < 40.0) & (self.apart > 0.7 * self.angle) & alike
        runs = _labels(self.polygons, self.face_a[facets], self.face_b[facets])
        sizes = numpy.bincount(runs, minlength=self.polygons)
        return self._share_shown(sizes[runs] >= 10)


def _shading_report(obj):
    """What shades wrong, and how far each face's normals bend from its own. Of 254 professional objects, what fails is low-poly on purpose."""
    issues = {}
    shading = _Shading(obj)
    # A far level of detail is seen too small for shading to tell, and is cut down to few faces on purpose.
    if not shading.polygons or (_lod_level(obj.name) or 0) >= 1:
        return issues, shading.bent if shading.polygons else numpy.zeros(0)
    # A body that bends is shaded round however few its faces; so is what the art wants as one soft shape.
    round_on_purpose = globals().get("ROUND", False)
    if round_on_purpose is not True and obj.name not in (round_on_purpose or ()) and not any(m.type == "ARMATURE" for m in obj.modifiers):
        share = shading.over_corners()
        if share >= 0.1:
            issues["smooth_across_corners"] = f"the normals bend across {share:.0%} of a flat surface, so it shades as one with what it turns into: it reads as a balloon with dark corners. Mark those edges sharp, shade by angle, or weight the normals; or set ROUND if the art means one soft shape"
    faceted = globals().get("FACETED", False)
    if faceted is not True and obj.name not in (faceted or ()):
        share = shading.flat_curves()
        if share >= 0.25:
            issues["flat_shaded_curves"] = f"{share:.0%} of a surface curves and shades flat: every face shows. Shade it smooth, with sharp edges at its corners, or set FACETED if the art means it"
    return issues, shading.bent


def validate_object(obj, triangle_budget, merge_distance, flat_detail=False, collision=False, convex=False, cover=None):
    bm = _evaluated_bmesh(obj)
    triangles = sum(len(face.verts) - 2 for face in bm.faces)
    if _not_finite(bm):
        report = {"name": obj.name, "issues": {"vertices_not_numbers": f"{_not_finite(bm)} vertices aren't numbers, or lie thousands of kilometres off: nothing else can be read"}, "notes": {}, "info": {"triangles": triangles, "vertices": len(bm.verts)}}
        bm.free()
        return report

    vertex_sets = defaultdict(list)
    for face in bm.faces:
        vertex_sets[frozenset(v.index for v in face.verts)].append(face)
    size = max(obj.dimensions) if max(obj.dimensions) > 0.0 else 1.0
    # A collision mesh is what it encloses: its boxes may overlap, as nobody sees them.
    same_facing, opposite_facing, overlap_examples, overlap_area = (0, 0, [], 0.0) if collision else _coplanar_overlaps(bm.faces[:], size)
    surface = sum(face.calc_area() for face in bm.faces)
    little_stacked = same_facing if same_facing and _too_little_to_see(overlap_area, surface) else 0
    same_facing -= little_stacked
    applied, scale, rotation = _transform_report(obj)
    doubles = bmesh.ops.find_doubles(bm, verts=bm.verts[:], dist=merge_distance)["targetmap"]
    open_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)

    flipped_faces, flipped_where = _inconsistent_normals(bm, obj.name in globals().get("SEEN_FROM_INSIDE", ()), size, obj.matrix_world, cover or _tree_of([obj])) if bm.faces and obj.name not in globals().get("TWO_SIDED", ()) else (0, [])
    # What the player sees, or what costs for nothing. A leftover that nothing shows goes in notes.
    issues = {
        "no_faces": "it has no faces: nothing is drawn" if not bm.faces else None,
        "duplicate_faces": 0 if collision else sum(len(faces) - 1 for faces in vertex_sets.values() if len(faces) > 1),
        "overlapping_coplanar_faces": same_facing,
        "inconsistent_normals": flipped_faces,
        "transforms_not_applied": not applied,
        "over_triangle_budget": triangle_budget is not None and triangles > triangle_budget,
    }
    notes = {
        "non_manifold_edges": sum(1 for edge in bm.edges if len(edge.link_faces) > 2),
        "loose_vertices": sum(1 for vert in bm.verts if not vert.link_edges),
        "loose_edges": sum(1 for edge in bm.edges if not edge.link_faces),
        "zero_area_faces": sum(1 for face in bm.faces if face.calc_area() <= AREA_EPSILON),
        "zero_length_edges": sum(1 for edge in bm.edges if edge.calc_length() < merge_distance),
        "duplicate_vertices": len(doubles),
    }
    info = {
        "triangles": triangles,
        "vertices": len(bm.verts),
        "ngons": sum(1 for face in bm.faces if len(face.verts) > 4),
        "boundary_edges": open_edges,
        "material_slots": len(obj.material_slots),
        "dimensions_m": [round(d, 4) for d in obj.dimensions],
        "scale": scale,
        "rotation": rotation,
    }
    if opposite_facing:
        info["back_to_back_coplanar_faces"] = opposite_facing
    if little_stacked:
        notes["stacked_faces"] = f"{little_stacked} pairs, {overlap_area:.3f} m2 of {surface:.2f}: too little to see"
    if collision:
        # A sheet to walk on is fine as it is, also over a hill or a bowl. What nearly closes leaks.
        if open_edges and abs(_closure(bm.faces[:])) > 0.7:
            issues["collision_not_closed"] = f"{open_edges} open edges in what encloses a volume: whatever gets behind them passes through"
        if convex:
            if triangles > 255:
                issues["convex_over_255"] = f"{triangles} triangles: Unity makes do with a hull of at most 255, which isn't this shape"
            dents = _dents(bm)
            if dents:
                issues["convex_with_dents"] = f"{dents} vertices lie inside the hull: a convex collider fills them in, and the player stands on air there"
    else:
        if len(doubles) and not obj.data.has_custom_normals:
            seams = _shading_seams(bm, merge_distance)
            if seams:
                issues["shading_seam"] = f"{seams} edges are cut in two across smooth faces that run on from each other: the surface shades as if cut there. Merge by distance"
        uv_issues, uv_notes, uv_info = _uv_report(bm, obj)
        issues.update(uv_issues)
        notes.update(uv_notes)
        info.update(uv_info)
        issues.update(_lightmap_report(bm))
        shading_issues, bent = _shading_report(obj)
        issues.update(shading_issues)
        extra = max(0, triangles - _flat_needed_triangles(bm, bent))
        info["flat_area_extra_triangles"] = extra
        # Flat areas carry what they can't show as shape: vertex colors, or they bend.
        carries = _carries_color(obj.data) or bool(obj.data.shape_keys) or any(m.type == "ARMATURE" for m in obj.modifiers)
        if not flat_detail and not carries and extra >= max(20, 0.5 * triangles):
            issues["over_tessellated_flat_areas"] = extra
    examples = {
        "inconsistent_normals": flipped_where,
        "duplicate_faces": [faces[1].calc_center_median() for faces in vertex_sets.values() if len(faces) > 1],
        "overlapping_coplanar_faces": overlap_examples,
        "non_manifold_edges": [(e.verts[0].co + e.verts[1].co) / 2 for e in bm.edges if len(e.link_faces) > 2],
        "loose_vertices": [v.co for v in bm.verts if not v.link_edges],
        "loose_edges": [(e.verts[0].co + e.verts[1].co) / 2 for e in bm.edges if not e.link_faces],
        "zero_area_faces": [f.calc_center_median() for f in bm.faces if f.calc_area() <= AREA_EPSILON],
    }
    examples = {key: _where(obj, points) for key, points in examples.items() if (issues.get(key) or notes.get(key)) and points}
    bm.free()
    report = {"name": obj.name, "issues": {k: v for k, v in issues.items() if v}, "notes": {k: v for k, v in notes.items() if v}, "info": info}
    if examples:
        report["examples"] = examples
    return report


def _dents(bm):
    """Vertices of a collision mesh that lie inside its convex hull by more than a millimetre."""
    copy = bm.copy()
    hull = bmesh.ops.convex_hull(copy, input=copy.verts[:])
    planes = [(face.normal.copy(), face.verts[0].co.copy()) for face in hull["geom"] if isinstance(face, bmesh.types.BMFace)]
    copy.free()
    if not planes:
        return 0
    return sum(1 for vert in bm.verts if all(normal.dot(vert.co - point) < -0.001 for normal, point in planes))


def _box(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    return [min(p[k] for p in points) for k in range(3)], [max(p[k] for p in points) for k in range(3)]


def _collision_groups(collision, visible):
    """Which model each collision mesh stands for: the one of its name, Crate for Crate_COL and for UCX_Crate_01, else all that is visible.
    Several together are one shape."""
    groups = defaultdict(list)
    names = {o.name: o for o in visible}
    for obj in collision:
        base = re.sub(r"(^UCX_|_(COL|Collider)\d*(\.\d+)?$)", "", obj.name)
        base = re.sub(r"_\d+$", "", base) if base not in names else base
        groups[base if base in names else None].append(obj)
    return [(names.get(base), members) for base, members in groups.items()]


def _tree_of(objects):
    """All of some objects' faces in one tree, in the world."""
    coords, polygons = [], []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        offset = len(coords)
        matrix = obj.matrix_world
        coords.extend(matrix @ v.co for v in mesh.vertices)
        # Mirrored in the game, its faces still look outward.
        turn = -1 if matrix.determinant() < 0.0 else 1
        polygons.extend([offset + k for k in p.vertices][::turn] for p in mesh.polygons)
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(coords, polygons) if polygons else None


def _closed_off(models, members):
    """What a collision mesh closes that the model leaves open on the ground, where a person fits: `PERSON_RADIUS` wide, `PERSON_HEIGHT` tall, stepping over what is under half a
    metre. Places are taken along the mesh's own length and width, however it stands, so a long thin wall is walked along and not sampled past. Places inside a shell, with
    only backs around them, don't count: that is the hollow behind a wall that only has a front. Returns where the mesh blocks a way through the model, clear both ways with
    the model to both sides, as a door or a gap in a fence has at any angle, and how many square metres the mesh fills that a person can walk to from outside it."""
    model = _tree_of(models)
    solid = _tree_of(members)
    if model is None or solid is None:
        return [], 0.0, 1.0
    low, high = _box(models)
    bottom = low[2] - 0.01
    points = numpy.array([list(obj.matrix_world @ v.co) for obj in members for v in obj.data.vertices])
    middle_xy = points[:, :2].mean(axis=0)
    centered = points[:, :2] - middle_xy
    axes = numpy.linalg.svd(centered.T @ centered)[0]
    along = centered @ axes
    # With a margin all round, to walk in from.
    start = along.min(axis=0) - 0.75
    reach_of = along.max(axis=0) - along.min(axis=0) + 1.5
    steps = numpy.full(2, 0.25)
    while numpy.prod(numpy.ceil(reach_of / steps)) > 4000.0:
        steps *= 1.25
    counts = numpy.ceil(reach_of / steps).astype(int)
    cell = reach_of / counts
    up = Vector((0.0, 0.0, 1.0))
    ways = [Vector((math.cos(k * math.pi / 8.0), math.sin(k * math.pi / 8.0), 0.0)) for k in range(16)]
    reach = max(high[k] - low[k] for k in range(3)) + 1.0

    def body_fits(x, y, floor):
        """Nothing within a person's reach, from the step up to the head."""
        return not any(model.find_nearest_range(Vector((x, y, floor + 0.5 + PERSON_RADIUS + k * (PERSON_HEIGHT - 0.5 - 2.0 * PERSON_RADIUS))), PERSON_RADIUS) for k in (0.0, 1.0))

    free = {}
    inside = {}
    for i in range(int(counts[0])):
        for j in range(int(counts[1])):
            place = middle_xy + axes @ (start + (numpy.array((i, j)) + 0.5) * cell)
            x, y = float(place[0]), float(place[1])
            # Up through what is underfoot: a slab or a sill is stepped onto, and the inside of a solid wall is no room however high it goes.
            floor, ceiling, at, in_solid = bottom, math.inf, bottom, False
            for _ in range(12):
                hit = model.ray_cast(Vector((x, y, at)), up, high[2] - at + PERSON_HEIGHT)
                if hit[0] is None:
                    break
                at = hit[0].z + 0.001
                from_behind = hit[1].dot(up) > 0.0
                if in_solid:
                    if from_behind:
                        in_solid = False
                        floor = at
                        if hit[0].z - bottom >= 0.5:
                            ceiling = floor
                            break
                elif hit[0].z - bottom >= 0.5:
                    ceiling = hit[0].z
                    break
                elif from_behind:
                    floor = at
                else:
                    in_solid = True
            if in_solid or ceiling - floor < PERSON_HEIGHT:
                continue
            probe = Vector((x, y, floor + 0.5))
            chest = Vector((x, y, floor + 0.75 * PERSON_HEIGHT))
            # Clear all round, whatever stands there: a line up runs along a post's sides, and rays pass either side of a thin bar.
            if not body_fits(x, y, floor):
                continue
            hits = [model.ray_cast(chest, way, reach) for way in ways]
            if any(hit[0] is not None and hit[1].dot(way) > 0.0 for hit, way in zip(hits, ways)):
                continue  # a back in sight: the inside of a shell
            free[i, j] = (chest, hits, floor)
            nearest = solid.find_nearest(probe)
            inside[i, j] = nearest[0] is not None and nearest[1].dot(probe - nearest[0]) < 0.0
    through = []

    def person_passes(floor, x, y, way):
        """A whole body along a line, both ways, as far as the model goes: a sill stops it, and a gap between posts, where thin rays each find their way."""
        for sign in (1.0, -1.0):
            step = 0.1
            while step < reach:
                at = Vector((x, y, 0.0)) + way * (sign * step)
                if not (low[0] <= at.x <= high[0] and low[1] <= at.y <= high[1]) and step > 2.0 * PERSON_RADIUS:
                    break
                if not body_fits(at.x, at.y, floor):
                    return False
                step += 0.1
        return True

    for (chest, hits, floor) in free.values():
        if through:
            break
        for k in range(8):
            sides = [any(hits[(k + turn + shift) % 16][0] is not None for shift in (-1, 0, 1)) for turn in (4, 12)]
            if hits[k][0] is None and hits[k + 8][0] is None and all(sides) and person_passes(floor, chest.x, chest.y, ways[k]):
                # As far as the model reaches along the way: what lies beyond it isn't this door's.
                span = min((high[a] - chest[a]) / ways[k][a] if ways[k][a] > 1e-6 else (low[a] - chest[a]) / ways[k][a] if ways[k][a] < -1e-6 else math.inf for a in (0, 1))
                back = min((low[a] - chest[a]) / ways[k][a] if ways[k][a] > 1e-6 else (high[a] - chest[a]) / ways[k][a] if ways[k][a] < -1e-6 else math.inf for a in (0, 1))
                blocked = solid.ray_cast(chest, ways[k], max(span, 0.0) + 0.05)[0] is not None or solid.ray_cast(chest, -ways[k], max(-back, 0.0) + 0.05)[0] is not None
                if blocked:
                    through.append([round(c, 3) for c in chest])
                    break
    # What can be walked to from outside the mesh, and how much of it the mesh fills.
    reached = {key for key in free if not inside[key]}
    stack = list(reached)
    while stack:
        i, j = stack.pop()
        chest = free[i, j][0]
        for other in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if other in free and other not in reached:
                towards = free[other][0] - chest
                if model.ray_cast(chest, towards.normalized(), towards.length)[0] is None:
                    reached.add(other)
                    stack.append(other)
    area_of_cell = float(cell[0] * cell[1])
    footprint = float((along.max(axis=0) - along.min(axis=0)).prod())
    return through, area_of_cell * sum(1 for key in reached if inside[key]), max(footprint, 1e-6)


def _collision_fit(collision, visible, by_name):
    """A collision mesh past its model is a wall nobody sees; one away from it, or that misses what stands at walking height, lets the player through; one that fills what
    the model leaves open stops him at air. Smaller on purpose, as a tree's trunk is, is noted: its crown is above his head, and only a look can tell the rest."""
    for model, members in _collision_groups(collision, visible):
        models = [model] if model else visible
        low, high = _box(models)
        low_c, high_c = _box(members)
        def beyond(low, high):
            # Per side, a quarter of the model that way and at least a hand's width. Below the model nobody sees it: a floor's collision mesh may be thick.
            return max(max(low[k] - low_c[k] - max(0.25, 0.25 * (high[k] - low[k])) for k in (0, 1)), max(high_c[k] - high[k] - max(0.25, 0.25 * (high[k] - low[k])) for k in range(3)))
        if beyond(low, high) > 0.0 and model is not None:
            # It may stand for more than the mesh of its name: a house and its roof.
            all_low, all_high = _box(visible)
            if beyond(all_low, all_high) <= 0.0:
                models, low, high = visible, all_low, all_high
        size = max(high[k] - low[k] for k in range(3))
        past = max(max(low[k] - low_c[k] for k in (0, 1)), max(high_c[k] - high[k] for k in range(3)))
        apart = any(high_c[k] + 0.01 < low[k] or high[k] + 0.01 < low_c[k] for k in range(3))
        past_limit = beyond(low, high) > 0.0
        short = max(high[k] - low[k] - (high_c[k] - low_c[k]) for k in (0, 1))
        low_top = high[2] - high_c[2]
        # With an open side a mesh has no inside to fill anything with: that is told as such.
        leaks = any("collision_not_closed" in by_name[obj.name]["issues"] for obj in members)
        through, filled, footprint = ([], 0.0, 1.0) if apart or past_limit or leaks else _closed_off(visible, members)
        open_share = 0.0 if apart or past_limit else _left_open(models, members, low[2])
        for obj in members:
            entry = by_name[obj.name]
            entry["info"]["collision_past_model_m"] = round(past, 3)
            if apart:
                entry["issues"]["collision_doesnt_fit"] = "it doesn't touch the model: the player walks through the model, and hits air"
            elif past_limit:
                entry["issues"]["collision_doesnt_fit"] = f"it reaches {past:.2f} m past the model, which is {size:.2f} m: the player stops at nothing"
            elif through:
                entry["issues"]["collision_closes_opening"] = f"a person fits through the model at {through[0]} and the collision mesh closes it: the player stops at air. Leave the opening out of the mesh"
            elif filled >= max(2.0, 0.15 * footprint):
                entry["issues"]["collision_fills_space"] = f"{filled:.1f} m2 a person can walk to are filled in by the mesh, a corner of a yard or the room behind a door: the player stops at air. Follow the model's outline"
            elif open_share > 0.5:
                entry["notes"]["collision_leaves_model_open"] = f"{open_share:.0%} of what stands at walking height has no collision on it: right for leaves and grass, a hole for a wall"
            elif short > max(0.25, 0.5 * size):
                entry["notes"]["collision_smaller_than_model"] = f"{short:.2f} m narrower than the model: right for a tree's trunk, a hole for a wall"
            elif low_top > max(0.25, 0.3 * (high[2] - low[2])):
                entry["notes"]["collision_lower_than_model"] = f"its top is {low_top:.2f} m under the model's: what jumps or flies passes over it there"
            if 0.25 <= filled < max(2.0, 0.15 * footprint):
                entry["notes"]["collision_fills_recess"] = f"{filled:.1f} m2 a person can walk to are filled in by the mesh: the player stops short of what he sees"


def _left_open(models, members, ground):
    """How much of a model's surface at walking height is far from its collision mesh. A wall a third covered is walked through; a tree has its trunk there."""
    solid = _tree_of(members)
    if solid is None:
        return 0.0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    total = open_area = 0.0
    for obj in models:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        for triangle in mesh.loop_triangles[:20000]:
            a, b, c = (matrix @ mesh.vertices[k].co for k in triangle.vertices)
            area = (b - a).cross(c - a).length / 2.0
            steps = max(1, min(8, int(math.sqrt(area) / 0.25)))
            part = area / (steps * (steps + 1) / 2.0)
            for i in range(steps):
                for j in range(steps - i):
                    point = a + (b - a) * ((i + 0.33) / steps) + (c - a) * ((j + 0.33) / steps)
                    if not 0.2 <= point.z - ground <= 1.7:
                        continue
                    total += part
                    nearest = solid.find_nearest(point, 0.3)
                    if nearest[0] is None:
                        open_area += part
        evaluated.to_mesh_clear()
    return open_area / total if total else 0.0


def _moves(obj):
    """Whether an object moves on its own in the game: keys on it or on what carries it, or the MOVES setting."""
    current = obj
    while current is not None:
        if current.name in globals().get("MOVES", ()) or (current.animation_data and current.animation_data.action):
            return True
        current = current.parent
    return False


def _open_loops(bm, edges):
    """The edges given, each with the open edges it runs on into: one list per opening."""
    bm.edges.ensure_lookup_table()
    loops = []
    seen = set()
    for start in edges:
        if start in seen:
            continue
        seen.add(start)
        stack = [bm.edges[start]]
        members = []
        while stack:
            edge = stack.pop()
            members.append(edge)
            for vert in edge.verts:
                for other in vert.link_edges:
                    if other.index not in seen and len(other.link_faces) == 1:
                        seen.add(other.index)
                        stack.append(other)
        loops.append(members)
    return loops


def _openings(surface, edges, size, closure):
    """Which openings the edges that show a surface's inside belong to: holes, or tops, that fail, and what only a note can say of them. A gap under 3% of the asset and
    under 10 cm, such as the end of a thin pole, nobody finds. A whole side left open, as on a kit's wall or the back of a stair, is right if a neighbor covers it, and only
    the project knows: the render shows it. Unless what has it nearly closes: that is a crate without its front, or a slit down a pillar."""
    holes, small, sides = [], 0, 0
    for members in _open_loops(surface.bm, edges):
        points = numpy.array([list(v.co) for edge in members for v in edge.verts])
        extent = float((points.max(axis=0) - points.min(axis=0)).max())
        if extent < min(0.03 * size, 0.1):
            small += len(members)
            continue
        # The plane the opening lies in, if it does: its normal is the direction it opens to. A bin's open top looks up; the rim of a shell open on several sides lies in no plane.
        centered = points - points.mean(axis=0)
        axes, spread, _ = numpy.linalg.svd(centered.T @ centered)
        looks_up = abs(float(axes[2, 2])) >= 0.7 and float(spread[2]) < 0.05 * float(spread[0])
        if extent > 0.4 * size and not looks_up and abs(closure) < 0.75:
            sides += len(members)
            continue
        holes.extend(members)
    return holes, small, sides


def _cavities(surfaces, see_through, allowed, size):
    """Faces in a sealed hollow: a closed surface all turned inward with its back covered all round, as the inside of a thick-walled room nobody can enter, and what stands
    in it. A look from outside never gets there, and each of those faces sees the others, so that alone can't tell."""
    hidden = set()
    covers = [s for s in surfaces if s.owner not in see_through]
    if not covers:
        return hidden
    coords, polygons = [], []
    for surface in covers:
        offset = len(coords)
        coords.extend(v.co.copy() for v in surface.bm.verts)
        polygons.extend([offset + v.index for v in face.verts] for face in surface.bm.faces)
    tree = BVHTree.FromPolygons(coords, polygons)
    nudge = 1e-4 * min(1.0, size)
    up = Vector((0.0, 0.0, 1.0))
    for surface in covers:
        if len(surface.bm.faces) < 4 or any(len(edge.link_faces) != 2 for edge in surface.bm.edges) or _closure(surface.bm.faces[:]) > -0.7:
            continue
        if any(_back_shows(tree, face.calc_center_median(), face.normal, nudge) for face in surface.bm.faces):
            continue
        own = BVHTree.FromBMesh(surface.bm)
        for other in surfaces:
            if other.owner in allowed:
                continue
            if other is surface:
                hidden.update((other.name, face.index) for face in other.bm.faces)
                continue
            # In the hollow when a look up from it meets the hollow's own face, turned toward it.
            point = other.bm.verts[0].co
            hit = own.ray_cast(point, up)
            if hit[0] is not None and hit[1].dot(up) < 0.0 and own.ray_cast(point, -up)[0] is not None:
                hidden.update((other.name, face.index) for face in other.bm.faces)
    return hidden


def _hidden_report(meshes, reports):
    """What a look from outside gets wrong and what it never gets: faces nobody can see, inside or under the rest of the asset, and openings that
    show the inside of a surface. LOD levels are never on screen together, so each is judged with what isn't a level."""
    rigid = [o for o in meshes if not any(m.type == "ARMATURE" for m in o.modifiers)]
    if not rigid:
        return
    path = globals().get("RIG_HELPERS") or os.path.join(os.path.dirname(globals()["__file__"]), "rig.py")
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    rig = types.SimpleNamespace(**namespace)
    levels = sorted({_lod_level(o.name) for o in rigid} - {None}) or [None]
    counts = defaultdict(int)
    where = defaultdict(list)
    holes = defaultdict(list)
    small_gaps = defaultdict(int)
    open_sides = defaultdict(int)
    sheet_holes = defaultdict(int)
    two_sided = set(globals().get("TWO_SIDED", ()))
    from_inside = set(globals().get("SEEN_FROM_INSIDE", ()))
    see_through = set(globals().get("SEE_THROUGH", ()))
    kit = globals().get("KIT", False)
    moving = {o.name for o in rigid if _moves(o)}
    # One mesh placed many times: a face hidden in this copy shows in the next, and cutting it cuts them all.
    placed_again = {o.name for o in rigid if o.data.users > 1}
    lowest = globals().get("LOWEST_VIEW", 0)
    for level in levels:
        together = [o for o in rigid if _lod_level(o.name) in (None, level)]
        surfaces = rig.Character(together).gather()
        if not surfaces:
            continue
        try:
            points = [v.co for s in surfaces for v in s.bm.verts]
            size = max(max(p[k] for p in points) - min(p[k] for p in points) for k in range(3))
            # As far as the asset reaches: a small thing sealed in the middle of a crate is as hidden as a large one.
            hidden = set(rig.hidden_faces(surfaces, see_through | moving, 2.0 * max(size, 1e-3), moving | placed_again, spacing=0.025 * max(size, 1e-3), wide=True))
            hidden |= _cavities(surfaces, see_through | moving, moving | placed_again, size)
            by_name = {s.name: s for s in surfaces}
            for name, face in hidden:
                surface = by_name[name]
                if _lod_level(surface.owner) is None and level != levels[0]:
                    continue
                counts[surface.owner] += len(surface.bm.faces[face].verts) - 2
                if len(where[surface.owner]) < MAX_EXAMPLES:
                    where[surface.owner].append([round(c, 4) for c in surface.bm.faces[face].calc_center_median()])
            sight = rig.Sight([s for s in surfaces if s.owner not in see_through], max(size, 1e-3))
            # Of the object and of all there is: a shed of separate panels closes as one.
            everything = abs(_closure([face for s in surfaces for face in s.bm.faces]))
            closures = {owner: max(everything, abs(_closure([face for s in surfaces if s.owner == owner for face in s.bm.faces]))) for owner in {s.owner for s in surfaces}}
            for surface in surfaces:
                if surface.owner in two_sided or surface.owner in see_through or (_lod_level(surface.owner) is None and level != levels[0]):
                    continue
                outline = [edge.index for edge in surface.bm.edges if len(edge.link_faces) == 1]
                faces_up = surface.bm.faces and lowest >= 0 and min(face.normal.z for face in surface.bm.faces) > 0.0
                if surface.owner in from_inside or faces_up:
                    # Ground faces up all over: it has no inside to look into, and nobody looks at its far edge from below it. A room is looked at from where a look
                    # from outside can't tell. Either way an opening shows sky, or nothing: past its outer edge, it is the player's to see.
                    loops = _open_loops(surface.bm, outline)
                    if faces_up:
                        loops.sort(key=lambda edges: -max(e.calc_length() for e in edges) - len(edges))
                        loops = loops[1:]
                    inner = [edge.index for members in loops for edge in members]
                    if faces_up:
                        if inner:
                            sheet_holes[surface.owner] += len(inner)
                        continue
                    found, small, sides = _openings(surface, inner, size, 1.0)
                else:
                    found, small, sides = _openings(surface, rig.see_inside(surface, sight, lowest, any_surface=True), size, closures[surface.owner])
                for edge in found:
                    holes[surface.owner].append([round(c, 4) for c in (edge.verts[0].co + edge.verts[1].co) / 2])
                small_gaps[surface.owner] += small
                open_sides[surface.owner] += sides
        finally:
            rig.free(surfaces)
    for report in reports:
        name = report["name"]
        if holes.get(name):
            bucket = report["notes"] if kit is True or name in (kit or ()) else report["issues"]
            bucket["see_inside"] = f"{len(holes[name])} open edges show the inside of the surface, where culling draws nothing: a hole. Close it, list it in TWO_SIDED if both sides are drawn, or in KIT if a neighbor covers it"
            report.setdefault("examples", {})["see_inside"] = holes[name][:MAX_EXAMPLES]
        if sheet_holes.get(name):
            report["notes"]["opening_in_sheet"] = f"{sheet_holes[name]} open edges around openings inside a sheet: right where something stands on it, a hole in the ground where nothing does"
        if small_gaps.get(name):
            report["notes"]["small_gaps"] = f"{small_gaps[name]} open edges around gaps too small to find"
        if open_sides.get(name):
            report["notes"]["open_side"] = f"{open_sides[name]} open edges around a whole side left open, which shows empty from there: right only if a neighbor covers it"
        count = counts.get(name, 0)
        if not count:
            continue
        report["info"]["hidden_triangles"] = count
        # A few faces inside cost less than finding them does, and professional work leaves up to a tenth there. Whole parts inside are more.
        if count >= max(12, 0.1 * report["info"]["triangles"]):
            report["issues"]["hidden_faces"] = f"{count} of {report['info']['triangles']} triangles can't be seen from anywhere: delete them. If a part moves out in play, list it in MOVES"
            report.setdefault("examples", {})["hidden_faces"] = where[name]


def _lod_level(name):
    match = re.match(r"^.*_LOD(\d+)$", name)
    return int(match.group(1)) if match else None


def _lod_base(name):
    match = re.match(r"^(.*)_LOD\d+$", name)
    return match.group(1) if match else None


def _z_fighting(objects, distance, ignore):
    """Parallel faces that lie over each other closer than `distance`: between objects, or within one object when not exactly on one plane (that
    case has its own count). By how far their outlines overlap on one plane: a floor over another by a metre of ten shows stripes there."""
    meshes = []
    sizes = []
    for obj in objects:
        if obj.name in ignore:
            continue
        bm = _evaluated_bmesh(obj)
        bm.transform(obj.matrix_world)
        if obj.matrix_world.determinant() < 0.0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])  # mirrored in the game, its faces still look outward
        bm.normal_update()
        meshes.append((obj.name, bm))
        sizes.append(max(obj.dimensions) if max(obj.dimensions) > 0.0 else 1.0)
    surfaces = {name: sum(face.calc_area() for face in bm.faces) for name, bm in meshes}
    points, polygons, owners = [], [], []
    for index, (name, bm) in enumerate(meshes):
        offset = len(points)
        points.extend(v.co.copy() for v in bm.verts)
        for face in bm.faces:
            polygons.append([offset + v.index for v in face.verts])
            owners.append((index, face))
    pairs = {}
    two_sided = set(globals().get("TWO_SIDED", ()))
    if polygons and len(polygons) <= MAX_FACES_FOR_ZFIGHT:
        tree = BVHTree.FromPolygons(points, polygons)
        for index, (mesh_index, face) in enumerate(owners):
            if face.calc_area() <= AREA_EPSILON:
                continue
            normal = face.normal
            corners = set(polygons[index])
            center = face.calc_center_median()
            radius = max((v.co - center).length for v in face.verts)
            inner = None
            for _, other_normal, other, _ in tree.find_nearest_range(center, radius + distance):
                if other is None or other <= index or (index, other) in pairs:
                    continue
                if corners & set(polygons[other]) or abs(normal.dot(other_normal)) < PARALLEL_COS:
                    continue
                other_mesh, other_face = owners[other]
                if other_face.calc_area() <= AREA_EPSILON:
                    continue
                names = (meshes[mesh_index][0], meshes[other_mesh][0])
                same_object = other_mesh == mesh_index
                if inner is None:
                    inner = _inner_point(face)
                other_inner = _inner_point(other_face)
                gap = min(abs(normal.dot(other_inner - inner)), abs(other_normal.dot(other_inner - inner)))
                # Exactly on one plane, within one object, is what the count of stacked faces is for.
                if gap > distance or (same_object and gap <= 1e-6 and _canonical_plane(face)[0] == _canonical_plane(other_face)[0]):
                    continue
                if not same_object:
                    levels = (_lod_level(names[0]), _lod_level(names[1]))
                    if None not in levels and levels[0] != levels[1]:
                        continue  # never on screen together
                    if _lod_base(names[0]) and _lod_base(names[0]) == _lod_base(names[1]):
                        continue
                axis_u = normal.orthogonal().normalized()
                axis_v = normal.cross(axis_u).normalized()
                first = _outline(face, axis_u, axis_v)
                second = _outline(other_face, axis_u, axis_v)
                a, b = numpy.repeat(numpy.arange(len(first)), len(second)), numpy.tile(numpy.arange(len(second)), len(first))
                wide = float(_overlap_depths(numpy.array(first, dtype=numpy.float64)[a], numpy.array(second, dtype=numpy.float64)[b]).max())
                if wide <= _overlap_limit(min(sizes[mesh_index], sizes[other_mesh])):
                    continue
                facing = "z_fighting" if normal.dot(other_normal) > 0 or names[0] in two_sided or names[1] in two_sided else "back_to_back"
                area = sum(_triangle_overlap(p, q) for p in first for q in second)
                pairs[(index, other)] = (facing, names, [round(c, 4) for c in inner], round(gap * 1000, 2), area, index if face.calc_area() < other_face.calc_area() else other)
    for _, bm in meshes:
        bm.free()
    pairs = _patches_that_show(pairs, polygons, points)
    return list(pairs.values()), surfaces, len(polygons) > MAX_FACES_FOR_ZFIGHT


def _patches_that_show(pairs, polygons, points):
    """Which of the overlapping faces flicker where someone sees it. A gap holds until the depth buffer runs out, further off the wider it is, and out
    there the patch has to cover a few pixels: a lens's layers or a jacket's seams are gone by then, a floor over a floor isn't, however many small
    faces it is made of. Exactly on one plane there is no distance it holds to."""
    parent = {key: key for key in pairs}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    # By where corners are: a floor of quads with hard edges shares no vertex, and is one patch.
    at_corner = {}
    for key, pair in pairs.items():
        if pair[0] != "z_fighting":
            continue
        # Through the smaller of the two: 400 rivets on one plate are 400 patches.
        for corner in polygons[pair[5]]:
            at = tuple(round(c * 1e4) for c in points[corner])
            parent[find(key)] = find(at_corner.setdefault(at, key))
    patches = defaultdict(list)
    for key, pair in pairs.items():
        if pair[0] == "z_fighting":
            patches[find(key)].append(key)
    kept = {key: pair for key, pair in pairs.items() if pair[0] != "z_fighting"}
    for members in patches.values():
        area = sum(pairs[key][4] for key in members)
        gap = sum(pairs[key][3] for key in members) / len(members) / 1000.0
        holds_to = math.sqrt(gap * NEAR_PLANE * 2.0 ** DEPTH_BITS)
        if math.sqrt(area) > PIXELS_SEEN * holds_to / PIXELS_PER_DISTANCE:
            kept.update((key, pairs[key]) for key in members)
    return kept


def validate(targets=None, triangle_budget=None, merge_distance=1e-5, zfight_distance=0.001, zfight_ignore=(), flat_detail=False):
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
    meshes = [o for o in objects if o.type == "MESH"]
    collision = set(globals().get("COLLISION", ())) | {o.name for o in meshes if re.search(r"(^UCX_|_COL\d*(\.\d+)?$|_Collider\d*(\.\d+)?$)", o.name)}
    convex = set(globals().get("CONVEX", ()))
    # What covers what: all that is drawn together. Levels of detail aren't, and neither does glass cover anything.
    see_through = set(globals().get("SEE_THROUGH", ()))
    covers = {}

    def cover_of(obj):
        if obj.name in collision or _not_finite_object(obj):
            return None
        level = _lod_level(obj.name)
        if level not in covers:
            together = [o for o in meshes if o.name not in collision and o.name not in see_through and _lod_level(o.name) in (None, level) and not _not_finite_object(o)]
            covers[level] = _tree_of(together) if together else None
        return covers[level]

    reports = [validate_object(o, triangle_budget, merge_distance, flat_detail, o.name in collision, o.name in convex, cover_of(o)) for o in meshes]
    by_name = {r["name"]: r for r in reports}
    clean_meshes = [o for o in meshes if "vertices_not_numbers" not in by_name[o.name]["issues"]]
    visible = [o for o in clean_meshes if o.name not in collision]
    colliders = [o for o in clean_meshes if o.name in collision]
    if visible and colliders:
        _collision_fit(colliders, visible, by_name)
    between = []
    found, surfaces, too_many = _z_fighting(visible, zfight_distance, set(zfight_ignore))
    if too_many:
        for o in visible:
            by_name[o.name]["notes"]["z_fighting_not_checked"] = f"over {MAX_FACES_FOR_ZFIGHT} faces together: check its parts one by one"
    fights = defaultdict(list)
    for facing, names, location, gap_mm, area, _ in found:
        if facing == "z_fighting":
            fights[names].append((location, gap_mm, area))
        else:
            for name in set(names):
                by_name[name]["info"][facing] = by_name[name]["info"].get(facing, 0) + 1
    for names, entries in fights.items():
        area = sum(entry[2] for entry in entries)
        little = _too_little_to_see(area, min(surfaces[names[0]], surfaces[names[1]]))
        for name in set(names):
            entry = by_name[name]
            if little:
                entry["notes"]["z_fighting"] = entry["notes"].get("z_fighting", 0) + len(entries)
                continue
            entry["issues"]["z_fighting"] = entry["issues"].get("z_fighting", 0) + len(entries)
            examples = entry.setdefault("examples", {}).setdefault("z_fighting", [])
            for location, gap_mm, _ in entries[:MAX_EXAMPLES - len(examples)]:
                examples.append({"at": location, "gap_mm": gap_mm, "with": names[1] if names[0] == name else names[0]})
        if names[0] != names[1] and not little:
            for location, gap_mm, _ in entries:
                if len(between) < 10:
                    between.append({"objects": list(names), "at": location, "gap_mm": gap_mm, "kind": "z_fighting"})
    if globals().get("__file__") or globals().get("RIG_HELPERS"):
        _hidden_report(visible, [by_name[o.name] for o in visible])
    else:
        for o in visible:
            by_name[o.name]["issues"]["hidden_faces_not_checked"] = "faces nobody can see, and holes, weren't looked for: run it by its path, with __file__ set, or set RIG_HELPERS to where rig.py is on that machine"
    passed = not missing and bool(meshes) and all(not report["issues"] for report in reports)
    report = {"passed": passed, "objects": reports}
    if not meshes:
        report["nothing_checked"] = "no mesh among the targets"
    if between:
        report["z_fighting_between_objects"] = between
    if missing:
        report["missing_objects"] = missing
    return report


result = validate(
    globals().get("TARGETS"),
    globals().get("TRIANGLE_BUDGET"),
    globals().get("MERGE_DISTANCE", 1e-5),
    globals().get("ZFIGHT_DISTANCE", 0.001),
    globals().get("ZFIGHT_IGNORE", ()),
    globals().get("FLAT_DETAIL", False),
)

if globals().get("PROOF_DIR"):
    os.makedirs(globals()["PROOF_DIR"], exist_ok=True)
    proof_name = globals().get("PROOF_NAME") or (globals().get("TARGETS") or ["all"])[0]
    with open(os.path.join(globals()["PROOF_DIR"], f"validate_mesh-{proof_name}.json"), "w") as proof_file:
        json.dump(result, proof_file, indent=1, default=str)
