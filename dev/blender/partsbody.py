# A test character built from solid parts that overlap at the joints, as low-poly and toy-like characters are: torso, neck,
# head, arms, legs and feet on the mannequin's rig, and the same way for an animal. As separate objects or merged into one
# mesh; a build can change a part or add more. Weights are rigid along each part's bones, blended between neighbors.
import math

import bmesh
import bpy
from mathutils import Vector

import mannequin


def capsule(name, a, b, ra, rb, segments=10, rings=3, squash_y=1.0, sections=1):
    """A closed low-poly capsule from a to b, rounded at both ends. `sections` adds rings along its length."""
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    side = axis.orthogonal().normalized()
    other = axis.cross(side)
    bm = bmesh.new()
    profile = []
    for k in range(rings - 1, 0, -1):
        angle = k / rings * math.pi / 2
        profile.append((a - axis * (ra * math.sin(angle)), ra * math.cos(angle)))
    for k in range(sections):
        t = k / sections
        profile.append((a.lerp(b, t), ra + (rb - ra) * t))
    for k in range(0, rings):
        angle = k / rings * math.pi / 2
        profile.append((b + axis * (rb * math.sin(angle)), rb * math.cos(angle)))
    pole_low = bm.verts.new(a - axis * ra)
    pole_high = bm.verts.new(b + axis * rb)
    loops = []
    for center, radius in profile:
        loops.append([bm.verts.new(center + (side * math.cos(2 * math.pi * s / segments) + other * math.sin(2 * math.pi * s / segments)) * radius)
                      for s in range(segments)])
    for i in range(len(loops) - 1):
        for s in range(segments):
            bm.faces.new((loops[i][s], loops[i][(s + 1) % segments], loops[i + 1][(s + 1) % segments], loops[i + 1][s]))
    for s in range(segments):
        bm.faces.new((pole_low, loops[0][(s + 1) % segments], loops[0][s]))
        bm.faces.new((pole_high, loops[-1][s], loops[-1][(s + 1) % segments]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if squash_y != 1.0:
        for v in bm.verts:
            v.co.y *= squash_y
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def lathe(name, profile, center=(0.0, 0.0), segments=16):
    """A closed surface around a vertical axis: (radius, height) from the bottom up; the ends close at radius 0."""
    bm = bmesh.new()
    rings = []
    for radius, z in profile:
        if radius <= 0.0:
            rings.append(bm.verts.new((center[0], center[1], z)))
        else:
            rings.append([bm.verts.new((center[0] + radius * math.cos(2 * math.pi * s / segments), center[1] + radius * math.sin(2 * math.pi * s / segments), z))
                          for s in range(segments)])
    for lower, upper in zip(rings, rings[1:]):
        for s in range(segments):
            if isinstance(lower, list) and isinstance(upper, list):
                bm.faces.new((lower[s], lower[(s + 1) % segments], upper[(s + 1) % segments], upper[s]))
            elif isinstance(upper, list):
                bm.faces.new((lower, upper[s], upper[(s + 1) % segments]))
            else:
                bm.faces.new((lower[s], lower[(s + 1) % segments], upper))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def ring(name, radius, inner, low, high, center=(0.0, 0.0, 0.0), axis="Z", squash_y=1.0, segments=16):
    """A closed band around an axis: a belt, a bracelet, a collar. Radius outside, inner radius inside, between two heights
    along the axis measured from the center."""
    bm = bmesh.new()
    profile = [(inner, low), (radius, low), (radius, high), (inner, high)]
    loops = []
    for r, h in profile:
        loop = []
        for s in range(segments):
            angle = 2 * math.pi * s / segments
            u, v = r * math.cos(angle), r * math.sin(angle)
            offset = Vector((u, v, h)) if axis == "Z" else Vector((h, u, v))
            loop.append(bm.verts.new(Vector(center) + offset))
        loops.append(loop)
    for i in range(4):
        lower, upper = loops[i], loops[(i + 1) % 4]
        for s in range(segments):
            bm.faces.new((lower[s], lower[(s + 1) % segments], upper[(s + 1) % segments], upper[s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if squash_y != 1.0:
        for v in bm.verts:
            v.co.y *= squash_y
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def bump(obj, center, radius, push):
    """Pushes the vertices near a point: a knee that comes out through what covers it."""
    center, push = Vector(center), Vector(push)
    for v in obj.data.vertices:
        distance = (v.co - center).length
        if distance < radius:
            v.co += push * (1.0 - distance / radius)


def _segment_distance(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length


def attach(obj, rig, bones):
    """Weights a part to the nearest of its bones, blended with the next, and skins it."""
    segments = {n: (rig.data.bones[n].head_local, rig.data.bones[n].tail_local) for n in bones}
    for name in bones:
        obj.vertex_groups.new(name=name)
    for v in obj.data.vertices:
        ranked = sorted(bones, key=lambda n: _segment_distance(v.co, *segments[n]))[:2]
        strength = [max(_segment_distance(v.co, *segments[n]), 1e-4) ** -4 for n in ranked]
        total = sum(strength)
        for name, value in zip(ranked, strength):
            obj.vertex_groups[name].add([v.index], value / total, "REPLACE")
    obj.modifiers.new("Armature", "ARMATURE").object = rig
    obj.parent = rig
    return obj


def person_rig():
    body, rig = mannequin.build("Temp")
    bpy.data.objects.remove(body, do_unlink=True)
    return rig


def person(rig, skip=(), sections=1):
    """The parts of a person, overlapping where they join. Returns their objects."""
    bone = rig.data.bones
    built = []

    def add(name, obj_bones, *args, **kwargs):
        if name not in skip:
            built.append(attach(capsule(name, *args, sections=sections, **kwargs), rig, obj_bones))

    add("Torso", ["hips", "spine", "chest"], (0, 0, 0.92), (0, 0, 1.36), 0.16, 0.17, segments=12, squash_y=0.68)
    add("Neck", ["neck"], (0, 0, 1.42), (0, 0, 1.54), 0.05, 0.05, segments=8, rings=2)
    add("Head", ["head"], (0, 0, 1.62), (0, 0, 1.68), 0.105, 0.105, segments=12)
    for side in ("L", "R"):
        shoulder, hand = bone[f"upper_arm.{side}"].head_local, bone[f"hand.{side}"].tail_local
        add(f"Arm.{side}", [f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"], shoulder, hand, 0.055, 0.035, segments=8)
        hip, ankle = bone[f"thigh.{side}"].head_local, bone[f"shin.{side}"].tail_local
        add(f"Leg.{side}", [f"thigh.{side}", f"shin.{side}"], hip, ankle, 0.078, 0.045, segments=8)
        toe = bone[f"toe.{side}"].tail_local
        add(f"Foot.{side}", [f"foot.{side}", f"toe.{side}"], (ankle.x, ankle.y, 0.05), (toe.x, toe.y, 0.05), 0.05, 0.05, segments=8)
    return built


def merge(objects, name="Merged"):
    """Joins the objects into one mesh, with their weights, as a pipeline's assembly does."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    merged = bpy.context.active_object
    merged.name = name
    return merged


def animal_rig():
    """A four-legged rig facing -Y, with a tail."""
    data = bpy.data.armatures.new("AnimalRig")
    rig = bpy.data.objects.new("AnimalRig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}

    def bone(name, head, tail, parent=None):
        b = data.edit_bones.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        if parent:
            b.parent = made[parent]
        made[name] = b

    bone("hips", (0, 0.28, 0.47), (0, 0.05, 0.48))
    bone("spine", (0, 0.05, 0.48), (0, -0.2, 0.49), "hips")
    bone("neck", (0, -0.25, 0.53), (0, -0.36, 0.62), "spine")
    bone("head", (0, -0.36, 0.62), (0, -0.52, 0.62), "neck")
    bone("tail.01", (0, 0.40, 0.48), (0, 0.52, 0.46), "hips")
    bone("tail.02", (0, 0.52, 0.46), (0, 0.64, 0.42), "tail.01")
    for end, y, parent in (("hind", 0.26, "hips"), ("fore", -0.18, "spine")):
        for side, x in (("L", 0.09), ("R", -0.09)):
            bone(f"{end}_thigh.{side}", (x, y, 0.40), (x, y, 0.22), parent)
            bone(f"{end}_shin.{side}", (x, y, 0.22), (x, y, 0.05), f"{end}_thigh.{side}")
            bone(f"{end}_paw.{side}", (x, y, 0.05), (x, y - 0.06, 0.02), f"{end}_shin.{side}")
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def animal(rig, skip=()):
    """The parts of an animal, overlapping where they join."""
    bone = rig.data.bones
    built = []

    def add(name, obj_bones, *args, **kwargs):
        if name not in skip:
            built.append(attach(capsule(name, *args, **kwargs), rig, obj_bones))

    add("Trunk", ["hips", "spine"], (0, 0.30, 0.47), (0, -0.22, 0.49), 0.13, 0.13, segments=12)
    add("NeckPart", ["neck"], (0, -0.20, 0.50), (0, -0.36, 0.62), 0.06, 0.05, segments=8, rings=2)
    add("Skull", ["head"], (0, -0.38, 0.62), (0, -0.50, 0.62), 0.08, 0.05, segments=10)
    add("Tail", ["tail.01", "tail.02"], (0, 0.38, 0.48), (0, 0.64, 0.42), 0.03, 0.012, segments=6, rings=2)
    for side, x in (("L", 0.07), ("R", -0.07)):
        add(f"Ear.{side}", ["head"], (x, -0.40, 0.67), (x * 1.4, -0.40, 0.75), 0.022, 0.012, segments=6, rings=2)
    for end in ("hind", "fore"):
        for side in ("L", "R"):
            top, low = bone[f"{end}_thigh.{side}"].head_local, bone[f"{end}_shin.{side}"].tail_local
            add(f"{end}Leg.{side}", [f"{end}_thigh.{side}", f"{end}_shin.{side}"], top, low, 0.05, 0.028, segments=8)
            tip = bone[f"{end}_paw.{side}"].tail_local
            add(f"{end}Paw.{side}", [f"{end}_paw.{side}"], (low.x, low.y, 0.03), (tip.x, tip.y, 0.03), 0.03, 0.03, segments=8)
    return built
