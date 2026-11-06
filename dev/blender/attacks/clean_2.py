# Clean characters that should pass. Second batch: bodies, rigs, animals, accessories on the wrong sides of a joint.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import clean_1 as fp1
from defects_1 import raise_z, move, plane, open_lathe, fits_hat
from clean_1 import union, hair_shell, hood_shell
CASES.clear()


def ring_on(name, center, axis, r_out, r_in, half, segments=12):
    """A closed band around any axis."""
    center, axis = Vector(center), Vector(axis).normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    bm = bmesh.new()
    loops = []
    for r, h in ((r_in, -half), (r_out, -half), (r_out, half), (r_in, half)):
        loops.append([bm.verts.new(center + axis * h + (u * math.cos(2 * math.pi * s / segments) + v * math.sin(2 * math.pi * s / segments)) * r) for s in range(segments)])
    for i in range(4):
        a, b = loops[i], loops[(i + 1) % 4]
        for s in range(segments):
            bm.faces.new((a[s], a[(s + 1) % segments], b[(s + 1) % segments], b[s]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --- Accessories across a joint ------------------------------------------------------------------------------------------

@case("bracelet_on_lowpoly_arm", "pass", "a bracelet sunk into the forearm of a low-poly arm of one long quad per side")
def _():
    def extra(rig, parts):
        b = rig.data.bones["forearm.L"]
        axis = (b.tail_local - b.head_local).normalized()
        c = b.head_local.lerp(b.tail_local, 0.7)
        on(paint(ring_on("Bracelet", c, axis, 0.05, 0.03, 0.012), BLUE), rig, "forearm.L")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "front_left"], "CLOSEUPS": [{"label": "b", "center": list(c), "size": 0.3, "view": "front"}]}}
    return person(extra)


@case("bracelet_on_arm_with_rings_control", "pass", "the same bracelet on an arm with rings along it")
def _():
    def extra(rig, parts):
        b = rig.data.bones["forearm.L"]
        axis = (b.tail_local - b.head_local).normalized()
        c = b.head_local.lerp(b.tail_local, 0.7)
        on(paint(ring_on("Bracelet", c, axis, 0.05, 0.03, 0.012), BLUE), rig, "forearm.L")
        return {"WHOLE_PARTS": True}
    return person(extra, sections=6)


def jointed_arm_person(rig, parts):
    """Arms of two rigid parts each: a robot's or a doll's."""
    bones = rig.data.bones
    for side in ("L", "R"):
        bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
        s, e, w, h = bones[f"upper_arm.{side}"].head_local, bones[f"forearm.{side}"].head_local, bones[f"forearm.{side}"].tail_local, bones[f"hand.{side}"].tail_local
        on(paint(capsule(f"UpperArm.{side}", s, e, 0.05, 0.042, segments=12), GRAY), rig, f"upper_arm.{side}")
        on(paint(capsule(f"Forearm.{side}", e, w, 0.042, 0.033, segments=12), GRAY), rig, f"forearm.{side}")
        on(paint(capsule(f"Hand.{side}", w, h, 0.033, 0.03, segments=12), GRAY), rig, f"hand.{side}")


@case("bracelet_low_poly_on_hand_bone", "pass", "a low-poly bracelet on the hand bone, set into the end of a rigid forearm part: joint between them, its corners stick out, its sides dive in")
def _():
    def extra(rig, parts):
        jointed_arm_person(rig, parts)
        b = rig.data.bones["forearm.L"]
        axis = (b.tail_local - b.head_local).normalized()
        c = b.head_local.lerp(b.tail_local, 0.85)
        on(paint(ring_on("Bracelet", c, axis, 0.046, 0.02, 0.012, segments=5), BLUE), rig, "hand.L")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front"], "CLOSEUPS": [{"label": "b", "center": list(c), "size": 0.25, "view": "front"}]}}
    return person(extra)


@case("collar_on_neck_bone_low_poly_dips_into_chest", "pass", "a low-poly collar on the neck bone, resting on the shoulders: its corners stand out of the chest, its sides dip in")
def _():
    def extra(rig, parts):
        c = ring("Collar", 0.115, 0.05, 1.47, 1.50, segments=6, squash_y=0.72)
        on(paint(c, RED), rig, "neck")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


@case("necklace_dips_into_chest_front_and_back", "pass", "a necklace on the neck bone, around the base of the neck, resting on the chest: it dips under the chest's surface at the front and the back")
def _():
    def extra(rig, parts):
        # A torus tilted slightly down at the front and the back: a saddle-shaped ring over the shoulders.
        bm = bmesh.new()
        seg, ring_seg = 24, 6
        loops = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            cx, cy = 0.105 * math.cos(a), 0.105 * math.sin(a)
            cz = 1.452 - 0.03 * math.cos(2 * a)
            loop = []
            for j in range(ring_seg):
                b = 2 * math.pi * j / ring_seg
                rad = 0.012
                loop.append(bm.verts.new((cx + rad * math.cos(b) * math.cos(a), cy + rad * math.cos(b) * math.sin(a), cz + rad * math.sin(b))))
            loops.append(loop)
        for i in range(seg):
            for j in range(ring_seg):
                bm.faces.new((loops[i][j], loops[i][(j + 1) % ring_seg], loops[(i + 1) % seg][(j + 1) % ring_seg], loops[(i + 1) % seg][j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new("Necklace")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("Necklace", mesh)
        bpy.context.scene.collection.objects.link(obj)
        on(paint(obj, YELLOW), rig, "neck")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


@case("wand_in_a_fist", "pass", "a thin wand held in a hand part: it goes through the fist, as a held thing does. Its area is smaller than the fist's")
def _():
    def extra(rig, parts):
        jointed_arm_person(rig, parts)
        bones = rig.data.bones
        w, h = bones["forearm.L"].tail_local, bones["hand.L"].tail_local
        c = w.lerp(h, 0.5)
        fist = capsule("Fist", c, c + Vector((0.0, 0.0, 0.001)), 0.05, 0.05, segments=12)
        on(paint(fist, SKIN), rig, "hand.L")
        on(paint(capsule("Wand", c + Vector((0, -0.28, 0)), c + Vector((0, 0.05, 0)), 0.006, 0.01, segments=6, rings=1), BROWN), rig, "hand.L")
        return {"WHOLE_PARTS": True, "POSES": False, "SYMMETRIC": ["Torso"], "_render": {"VIEWS": ["front", "left"], "CLOSEUPS": [{"label": "fist", "center": list(c), "size": 0.45, "view": "front_left"}]}}
    return person(extra)


@case("hinge_pin_through_robot_elbow", "pass", "a hinge pin through a robot's elbow, standing out on both sides of the joint: how a hinge looks")
def _():
    def extra(rig, parts):
        jointed_arm_person(rig, parts)
        for side, x in (("L", 1), ("R", -1)):
            e = rig.data.bones[f"forearm.{side}"].head_local
            on(paint(capsule(f"Pin.{side}", e + Vector((0, -0.06, 0)), e + Vector((0, 0.06, 0)), 0.012, 0.012, segments=8, rings=1), RED), rig, f"upper_arm.{side}")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left"], "CLOSEUPS": [{"label": "pin", "center": list(rig.data.bones["forearm.L"].head_local), "size": 0.25, "view": "front_left"}]}}
    return person(extra)


@case("chin_strap_low_poly", "pass", "a thin chin strap around the head on the head bone: it dips under the low-poly cheeks on both sides")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), BROWN), rig, "head")
        # A strap in the XZ plane, from the brim down under the chin.
        c = Vector((0, 0, 1.615))
        strap = ring_on("Strap", c, (0, 1, 0), 0.112, 0.098, 0.008, segments=10)
        on(paint(strap, DARK), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("belt_low_poly_on_rigid_torso_parts", "pass", "a low-poly belt on the hips bone, around a torso part weighted to the spine and chest only: joint between them, belt's corners out, sides in")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Torso"], do_unlink=True)
        on(paint(capsule("Torso", (0, 0, 1.10), (0, 0, 1.36), 0.15, 0.17, segments=12, squash_y=0.68), SKIN), rig, "spine", "chest")
        on(paint(capsule("Pelvis", (0, 0, 0.92), (0, 0, 1.0), 0.16, 0.15, segments=12, squash_y=0.68), BLUE), rig, "hips")
        on(paint(ring("Belt", 0.158, 0.08, 1.05, 1.09, segments=6, squash_y=0.68), BROWN), rig, "hips")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("crown_on_head_bone_child", "pass", "a closed crown on a socket bone that is a child of the head: fits and clears the head")
def _():
    rig = partsbody.person_rig()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    b = rig.data.edit_bones.new("hat_socket")
    b.head, b.tail = (0, 0, 1.75), (0, 0, 1.85)
    b.parent = rig.data.edit_bones["head"]
    b.use_deform = False
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = {o.name: o for o in partsbody.person(rig)}
    hat = paint(fits_hat(), BROWN)
    parent_to_bone(hat, rig, "hat_socket")
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


# --- Bodies --------------------------------------------------------------------------------------------------------------

@case("long_coat_on_body_of_parts", "pass", "a body of parts in a knee-length coat with legs clearly apart under it")
def _():
    def extra(rig, parts):
        coat = paint(open_lathe("Coat", [(0.24, 0.55), (0.22, 0.75), (0.2, 1.0), (0.2, 1.3), (0.15, 1.44), (0.0, 1.47)], segments=20), BROWN)
        for v in coat.data.vertices:
            v.co.y *= 0.75
        on(coat, rig, "hips", "spine", "chest", "thigh.L", "thigh.R")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Coat"], "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("short_tunic_on_body_of_parts", "pass", "a body of parts in a tunic to mid-thigh: legs apart below it, and the tunic isn't a long robe")
def _():
    def extra(rig, parts):
        tunic = paint(open_lathe("Tunic", [(0.22, 0.70), (0.2, 0.9), (0.2, 1.3), (0.15, 1.44), (0.0, 1.47)], segments=20), GREEN)
        for v in tunic.data.vertices:
            v.co.y *= 0.75
        on(tunic, rig, "hips", "spine", "chest")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Tunic"], "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("cape_to_the_calves_on_body_of_parts", "pass", "a body of parts with a cape behind the legs, down to the calves")
def _():
    def extra(rig, parts):
        cape = paint(plane("Cape", -0.22, 0.22, 0.28, 1.42, 0.135, nx=6, nz=8), RED)
        on(cape, rig, "chest", "spine", "hips")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Cape"], "POSES": False, "_render": {"VIEWS": ["front", "back", "left"]}}
    return person(extra)


@case("cape_to_the_calves_one_skin", "pass", "the same cape on one skin (control)")
def _():
    body, rig = mannequin.build()
    paint(body, SKIN)
    cape = paint(plane("Cape", -0.22, 0.22, 0.28, 1.42, 0.135, nx=6, nz=8), RED)
    on(cape, rig, "chest", "spine", "hips")
    return {"TARGETS": ["Body", "Cape"], "ARMATURE": rig.name, "TWO_SIDED": ["Cape"], "POSES": False, "SINGLE_LAYER": False}


def scaled_person(rig_scale=1.0):
    pass


def blob_rig():
    return make_rig("BlobRig", [
        ("hips", (0, 0, 0.32), (0, 0, 0.50), None), ("spine", (0, 0, 0.50), (0, 0, 0.68), "hips"), ("head", (0, 0, 0.68), (0, 0, 0.95), "spine"),
        ("upper_arm.L", (0.30, 0, 0.62), (0.42, 0, 0.55), "spine"), ("forearm.L", (0.42, 0, 0.55), (0.52, 0, 0.48), "upper_arm.L"), ("hand.L", (0.52, 0, 0.48), (0.58, 0, 0.44), "forearm.L"),
        ("upper_arm.R", (-0.30, 0, 0.62), (-0.42, 0, 0.55), "spine"), ("forearm.R", (-0.42, 0, 0.55), (-0.52, 0, 0.48), "upper_arm.R"), ("hand.R", (-0.52, 0, 0.48), (-0.58, 0, 0.44), "forearm.R"),
        ("thigh.L", (0.14, 0, 0.30), (0.14, 0, 0.18), "hips"), ("shin.L", (0.14, 0, 0.18), (0.14, 0, 0.06), "thigh.L"), ("foot.L", (0.14, 0, 0.06), (0.14, -0.14, 0.03), "shin.L"),
        ("thigh.R", (-0.14, 0, 0.30), (-0.14, 0, 0.18), "hips"), ("shin.R", (-0.14, 0, 0.18), (-0.14, 0, 0.06), "thigh.R"), ("foot.R", (-0.14, 0, 0.06), (-0.14, -0.14, 0.03), "shin.R"),
    ])


def blob_person(rig, bottom=0.16):
    r = 0.30
    on(paint(capsule("Blob", (0, 0, bottom + r), (0, 0, 0.72), r, 0.26, segments=16, sections=3), YELLOW), rig, "hips", "spine", "head")
    for s, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Arm.{s}", (0.27 * x, 0, 0.64), (0.58 * x, 0, 0.44), 0.05, 0.04, segments=8, sections=3), YELLOW), rig, f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}")
        on(paint(capsule(f"Leg.{s}", (0.14 * x, 0, 0.30), (0.14 * x, 0, 0.06), 0.07, 0.06, segments=8), DARK), rig, f"thigh.{s}", f"shin.{s}")
        on(paint(capsule(f"Foot.{s}", (0.14 * x, 0, 0.05), (0.14 * x, -0.14, 0.05), 0.05, 0.05, segments=8), DARK), rig, f"foot.{s}")


@case("blob_body_with_stub_legs", "pass", "a toy-like round body on two short stub legs, clearly apart (Fall Guys, Among Us)")
def _():
    rig = blob_rig()
    blob_person(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "FINGERS": 0, "WAIST_BULGE": True, "BONE_MAP": {}, "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("curvy_figure_widest_at_the_hips", "pass", "a figure with hips wider a little above the hip joints than at them: the widest point of hips isn't where the bone starts")
def _():
    body, rig = mannequin.build()
    for v in body.data.vertices:
        if 0.88 < v.co.z < 1.06:
            # Wide hips: widest around z = 0.96, with the waist and chest narrower.
            t = 1.0 - abs(v.co.z - 0.97) / 0.09
            v.co.x *= 1.0 + 0.28 * max(0.0, t)
    paint(body, SKIN)
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False, "_render": {"VIEWS": ["front", "left"]}}


@case("belt_with_dense_hair_on_body_of_parts", "pass", "a body of parts where the hair has the most faces, with a belt: 'body' is then the hair, the torso is measured by cross-section clusters, and the belt counts as the waist")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=64), DARK), rig, "head")
        on(paint(ring("Belt", 0.20, 0.14, 1.10, 1.14, squash_y=0.68), BROWN), rig, "spine", "hips")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


@case("blocky_character_legs_touching", "pass", "a blocky character: box legs side by side, touching at x = 0, as Minecraft or Roblox figures are")
def _():
    def box(name, lo, hi):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=[(a + b) / 2 for a, b in zip(lo, hi)])
        o = bpy.context.active_object
        o.name = name
        o.scale = [(b - a) for a, b in zip(lo, hi)]
        bpy.ops.object.transform_apply(location=True, scale=True, rotation=False)
        return o
    rig = make_rig("BlockRig", [
        ("hips", (0, 0, 0.75), (0, 0, 0.95), None), ("spine", (0, 0, 0.95), (0, 0, 1.2), "hips"), ("head", (0, 0, 1.5), (0, 0, 1.75), "spine"),
        ("upper_arm.L", (0.3, 0, 1.45), (0.55, 0, 1.45), "spine"), ("forearm.L", (0.55, 0, 1.45), (0.75, 0, 1.45), "upper_arm.L"), ("hand.L", (0.75, 0, 1.45), (0.85, 0, 1.45), "forearm.L"),
        ("upper_arm.R", (-0.3, 0, 1.45), (-0.55, 0, 1.45), "spine"), ("forearm.R", (-0.55, 0, 1.45), (-0.75, 0, 1.45), "upper_arm.R"), ("hand.R", (-0.75, 0, 1.45), (-0.85, 0, 1.45), "forearm.R"),
        ("thigh.L", (0.13, 0, 0.75), (0.13, 0, 0.40), "hips"), ("shin.L", (0.13, 0, 0.40), (0.13, 0, 0.05), "thigh.L"), ("foot.L", (0.13, 0, 0.05), (0.13, -0.1, 0.05), "shin.L"),
        ("thigh.R", (-0.13, 0, 0.75), (-0.13, 0, 0.40), "hips"), ("shin.R", (-0.13, 0, 0.40), (-0.13, 0, 0.05), "thigh.R"), ("foot.R", (-0.13, 0, 0.05), (-0.13, -0.1, 0.05), "shin.R"),
    ])
    on(paint(box("Torso", (-0.26, -0.13, 0.75), (0.26, 0.13, 1.5)), BLUE), rig, "hips", "spine")
    on(paint(box("Head", (-0.25, -0.25, 1.5), (0.25, 0.25, 2.0)), SKIN), rig, "head")
    for s, x in (("L", 1), ("R", -1)):
        lo, hi = (0.0, 0.26) if x > 0 else (-0.26, 0.0)
        on(paint(box(f"Leg.{s}", (lo, -0.13, 0.0), (hi, 0.13, 0.75)), DARK), rig, f"thigh.{s}", f"shin.{s}")
        lo, hi = (0.26, 0.85) if x > 0 else (-0.85, -0.26)
        on(paint(box(f"Arm.{s}", (lo, -0.13, 1.32), (hi, 0.13, 1.5)), SKIN), rig, f"upper_arm.{s}", f"forearm.{s}", f"hand.{s}")
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "FINGERS": 0, "_render": {"VIEWS": ["front", "left", "front_left"]}}


# --- Rigs -----------------------------------------------------------------------------------------------------------------

def add_twist_bones(body, rig):
    """Unreal-style twist bones: children of the limb bones, each holding the half of the limb next to the joint."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    made = []
    for side in ("L", "R"):
        for base in ("upper_arm", "forearm", "thigh", "shin"):
            parent = edit[f"{base}.{side}"]
            b = edit.new(f"{base}_twist_01.{side}")
            mid = (parent.head + parent.tail) / 2
            b.head, b.tail, b.roll = mid, parent.tail, parent.roll
            b.parent = parent
            made.append((f"{base}_twist_01.{side}", f"{base}.{side}", mid.copy(), parent.tail.copy()))
    bpy.ops.object.mode_set(mode="OBJECT")
    # Move the weight of each limb's outer half to its twist bone.
    for twist, base, mid, tail in made:
        axis = (tail - mid)
        group = body.vertex_groups.new(name=twist)
        src = body.vertex_groups[base]
        for v in body.data.vertices:
            try:
                w = src.weight(v.index)
            except RuntimeError:
                continue
            t = (v.co - mid).dot(axis) / axis.length_squared
            if t > 0.0:
                group.add([v.index], w, "REPLACE")
                src.remove([v.index])


@case("rig_with_twist_bones_one_skin", "pass", "the clean mannequin with Unreal-style twist bones: a child of the upper arm and a child of the forearm are no joint apart, so the fold of an elbow reads as a poke")
def _():
    body, rig = mannequin.build()
    paint(body, SKIN)
    add_twist_bones(body, rig)
    return {"TARGETS": ["Body"], "ARMATURE": rig.name}


@case("rig_no_twist_control", "pass", "the same mannequin without them (control)")
def _():
    body, rig = mannequin.build()
    return {"TARGETS": ["Body"], "ARMATURE": rig.name}


def twist_person_parts(extra_thigh=False):
    rig = partsbody.person_rig()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    for side in ("L", "R"):
        for base in ("thigh", "upper_arm", "forearm", "shin"):
            parent = edit[f"{base}.{side}"]
            b = edit.new(f"{base}_twist_01.{side}")
            b.head, b.tail, b.roll = (parent.head + parent.tail) / 2, parent.tail, parent.roll
            b.parent = parent
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


@case("rig_with_twist_bones_parts", "pass", "a body of parts on a rig with twist bones, each part weighted to them")
def _():
    rig = twist_person_parts()
    built = []
    bone = rig.data.bones
    def add(name, obj_bones, *args, **kwargs):
        built.append(attach(paint(capsule(name, *args, **kwargs), SKIN), rig, obj_bones))
    add("Torso", ["hips", "spine", "chest"], (0, 0, 0.92), (0, 0, 1.36), 0.16, 0.17, segments=12, squash_y=0.68, sections=3)
    add("Neck", ["neck"], (0, 0, 1.42), (0, 0, 1.54), 0.05, 0.05, segments=8, rings=2)
    add("Head", ["head"], (0, 0, 1.62), (0, 0, 1.68), 0.105, 0.105, segments=12)
    for side in ("L", "R"):
        shoulder, hand = bone[f"upper_arm.{side}"].head_local, bone[f"hand.{side}"].tail_local
        add(f"Arm.{side}", [f"upper_arm.{side}", f"upper_arm_twist_01.{side}", f"forearm.{side}", f"forearm_twist_01.{side}", f"hand.{side}"], shoulder, hand, 0.055, 0.035, segments=8, sections=8)
        hip, ankle = bone[f"thigh.{side}"].head_local, bone[f"shin.{side}"].tail_local
        add(f"Leg.{side}", [f"thigh.{side}", f"thigh_twist_01.{side}", f"shin.{side}", f"shin_twist_01.{side}"], hip, ankle, 0.078, 0.045, segments=8, sections=8)
        toe = bone[f"toe.{side}"].tail_local
        add(f"Foot.{side}", [f"foot.{side}", f"toe.{side}"], (ankle.x, ankle.y, 0.05), (toe.x, toe.y, 0.05), 0.05, 0.05, segments=8)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


def horse_rig(tail_bones=2, scapula=False):
    bones = [("hips", (0, 0.40, 0.95), (0, 0.10, 0.97), None), ("spine", (0, 0.10, 0.97), (0, -0.30, 1.0), "hips"), ("neck", (0, -0.30, 1.05), (0, -0.55, 1.35), "spine"), ("head", (0, -0.55, 1.35), (0, -0.80, 1.25), "neck")]
    z = 0.95
    y = 0.55
    for k in range(tail_bones):
        name = f"tail.{k:02d}"
        ny, nz = y + 0.06, z - 0.5 / max(tail_bones, 1)
        bones.append((name, (0, y, z), (0, ny, nz), f"tail.{k - 1:02d}" if k else "hips"))
        y, z = ny, nz
    for end, ly, parent in (("hind", 0.38, "hips"), ("fore", -0.28, "spine")):
        for side, x in (("L", 0.13), ("R", -0.13)):
            top = parent
            if scapula:
                bones.append((f"{end}_scapula.{side}", (x, ly, 1.02), (x, ly, 0.82), parent))
                top = f"{end}_scapula.{side}"
                bones.append((f"{end}_upper.{side}", (x, ly, 0.82), (x, ly, 0.56), top))
            else:
                bones.append((f"{end}_upper.{side}", (x, ly, 0.82), (x, ly, 0.56), top))
            bones.append((f"{end}_lower.{side}", (x, ly, 0.56), (x, ly, 0.28), f"{end}_upper.{side}"))
            bones.append((f"{end}_cannon.{side}", (x, ly, 0.28), (x, ly, 0.07), f"{end}_lower.{side}"))
            bones.append((f"{end}_hoof.{side}", (x, ly, 0.07), (x, ly - 0.07, 0.02), f"{end}_cannon.{side}"))
    return make_rig("HorseRig", bones)


def horse(rig, tail_len=0.5, tail_hang=True, scapula=False, tail_bones=2):
    on(paint(capsule("Barrel", (0, 0.42, 0.95), (0, -0.32, 1.0), 0.22, 0.22, segments=16, sections=3), BROWN), rig, "hips", "spine")
    on(paint(capsule("NeckP", (0, -0.28, 1.05), (0, -0.55, 1.35), 0.10, 0.07, segments=10, sections=2), BROWN), rig, "neck")
    on(paint(capsule("HeadP", (0, -0.56, 1.35), (0, -0.80, 1.25), 0.075, 0.05, segments=10, sections=2), BROWN), rig, "head")
    for s, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Ear.{s}", (0.04 * x, -0.56, 1.40), (0.05 * x, -0.56, 1.50), 0.018, 0.008, segments=6), BROWN), rig, "head")
    for end, y in (("hind", 0.38), ("fore", -0.28)):
        for s, x in (("L", 0.13), ("R", -0.13)):
            names = [f"{end}_upper.{s}", f"{end}_lower.{s}", f"{end}_cannon.{s}"]
            if scapula:
                names = [f"{end}_scapula.{s}"] + names
            on(paint(capsule(f"{end}Leg.{s}", (x, y, 0.92), (x, y, 0.07), 0.075, 0.028, segments=8, sections=6), BROWN), rig, *names)
            on(paint(capsule(f"{end}Hoof.{s}", (x, y, 0.035), (x, y - 0.05, 0.035), 0.035, 0.035, segments=8), DARK), rig, f"{end}_hoof.{s}")
    tails = [f"tail.{k:02d}" for k in range(tail_bones)]
    on(paint(capsule("TailP", (0, 0.57, 0.97), (0, 0.55 + 0.06 * tail_bones, 0.95 - 0.5), 0.035, 0.02, segments=8, sections=max(tail_bones, 2) * 2), DARK), rig, *tails)


@case("horse_clean", "pass", "a clean horse of parts, tail hanging behind the hind legs")
def _():
    rig = horse_rig()
    horse(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front", "back", "front_left"], "COLUMNS": 2}}


@case("horse_with_scapula_bones", "pass", "the same horse on a rig with a scapula bone at the top of each leg, carrying part of it: the leg's next bone is then two steps from the trunk")
def _():
    rig = horse_rig(scapula=True)
    horse(rig, scapula=True)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


@case("horse_long_tail_chain", "pass", "the same horse with a long tail chain of 10 bones: the trunk search walks down the tail instead of the spine")
def _():
    rig = horse_rig(tail_bones=10)
    horse(rig, tail_bones=10)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "back"]}}


def bird_rig():
    return make_rig("BirdRig", [
        ("root", (0, 0.05, 0.30), (0, -0.08, 0.34), None), ("neck", (0, -0.08, 0.34), (0, -0.13, 0.42), "root"), ("skull", (0, -0.13, 0.42), (0, -0.20, 0.44), "neck"),
        ("tail", (0, 0.10, 0.28), (0, 0.28, 0.24), "root"),
        ("wing.L", (0.075, -0.05, 0.36), (0.10, 0.05, 0.34), "root"), ("wing2.L", (0.10, 0.05, 0.34), (0.095, 0.17, 0.30), "wing.L"),
        ("wing.R", (-0.075, -0.05, 0.36), (-0.10, 0.05, 0.34), "root"), ("wing2.R", (-0.10, 0.05, 0.34), (-0.095, 0.17, 0.30), "wing.R"),
        ("thigh.L", (0.04, 0.02, 0.24), (0.04, 0.0, 0.13), "root"), ("shin.L", (0.04, 0.0, 0.13), (0.04, 0.0, 0.03), "thigh.L"), ("toe.L", (0.04, 0.0, 0.03), (0.04, -0.06, 0.01), "shin.L"),
        ("thigh.R", (-0.04, 0.02, 0.24), (-0.04, 0.0, 0.13), "root"), ("shin.R", (-0.04, 0.0, 0.13), (-0.04, 0.0, 0.03), "thigh.R"), ("toe.R", (-0.04, 0.0, 0.03), (-0.04, -0.06, 0.01), "shin.R"),
    ])


def bird(rig):
    on(paint(capsule("BodyP", (0, 0.06, 0.29), (0, -0.07, 0.33), 0.085, 0.085, segments=12, sections=2), BLUE), rig, "root")
    on(paint(capsule("HeadP", (0, -0.13, 0.43), (0, -0.14, 0.44), 0.05, 0.05, segments=12), BLUE), rig, "skull", "neck")
    on(paint(capsule("Beak", (0, -0.17, 0.43), (0, -0.23, 0.42), 0.02, 0.005, segments=8), YELLOW), rig, "skull")
    tail = capsule("TailP", (0, 0.10, 0.28), (0, 0.28, 0.24), 0.04, 0.03, segments=8)
    for v in tail.data.vertices:
        v.co.z = 0.26 + (v.co.z - 0.26) * 0.3
    on(paint(tail, BLUE), rig, "tail")
    for s, x in (("L", 1), ("R", -1)):
        wing = capsule(f"Wing.{s}", (0.075 * x, -0.05, 0.36), (0.095 * x, 0.17, 0.30), 0.045, 0.02, segments=8, sections=4)
        for v in wing.data.vertices:
            v.co.x = (0.085 * x) + (v.co.x - 0.085 * x) * 0.3
        on(paint(wing, GREEN), rig, f"wing.{s}", f"wing2.{s}")
        on(paint(capsule(f"Leg.{s}", (0.04 * x, 0.02, 0.24), (0.04 * x, 0.0, 0.03), 0.018, 0.012, segments=8, sections=4), YELLOW), rig, f"thigh.{s}", f"shin.{s}")
        on(paint(capsule(f"Foot.{s}", (0.04 * x, 0.0, 0.012), (0.04 * x, -0.06, 0.012), 0.012, 0.012, segments=8), YELLOW), rig, f"toe.{s}")


@case("bird_wings_folded", "pass", "a small bird with its wings folded along its body, as a perched bird: 'bend to the side' pushes one wing tip through the body")
def _():
    rig = bird_rig()
    bird(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front", "top", "front_left"], "COLUMNS": 2}}


def spider_rig(coxa=True):
    bones = [("body", (0, 0.12, 0.16), (0, -0.05, 0.16), None)]
    for side, sx in (("L", 1), ("R", -1)):
        for i, ang in enumerate((55, 20, -20, -55)):
            a = math.radians(ang)
            dx, dy = math.cos(a) * sx, -math.sin(a)
            base = Vector((0.05 * dx, -0.02 + 0.05 * dy, 0.16))
            knee = base + Vector((dx, dy, 0)) * 0.13 + Vector((0, 0, 0.09))
            shin = base + Vector((dx, dy, 0)) * 0.26 + Vector((0, 0, 0.02))
            tip = base + Vector((dx, dy, 0)) * 0.31 + Vector((0, 0, -0.16))
            parent = "body"
            if coxa:
                c = base + Vector((dx, dy, 0)) * 0.03
                bones.append((f"coxa{i}.{side}", base, c, parent))
                parent = f"coxa{i}.{side}"
                base = c
            bones.append((f"femur{i}.{side}", base, knee, parent))
            bones.append((f"tibia{i}.{side}", knee, shin, f"femur{i}.{side}"))
            bones.append((f"tarsus{i}.{side}", shin, tip, f"tibia{i}.{side}"))
    return make_rig("SpiderRig", bones)


def spider(rig, coxa=True, fused=False):
    on(paint(capsule("Thorax", (0, 0.0, 0.16), (0, -0.05, 0.16), 0.07, 0.06, segments=12), DARK), rig, "body")
    on(paint(capsule("Abdomen", (0, 0.14, 0.17), (0, 0.04, 0.16), 0.1, 0.06, segments=12), DARK), rig, "body")
    b = rig.data.bones
    for side in ("L", "R"):
        for i in range(4):
            start = b[f"femur{i}.{side}"].head_local if not coxa else b[f"coxa{i}.{side}"].head_local
            knee, sh, tip = b[f"tibia{i}.{side}"].head_local, b[f"tarsus{i}.{side}"].head_local, b[f"tarsus{i}.{side}"].tail_local
            names = [f"femur{i}.{side}", f"tibia{i}.{side}", f"tarsus{i}.{side}"]
            on(paint(capsule(f"Fem{i}.{side}", start, knee, 0.016, 0.014, segments=6, rings=1), BROWN), rig, f"femur{i}.{side}")
            on(paint(capsule(f"Tib{i}.{side}", knee, sh, 0.014, 0.012, segments=6, rings=1), BROWN), rig, f"tibia{i}.{side}")
            on(paint(capsule(f"Tar{i}.{side}", sh, tip, 0.012, 0.006, segments=6, rings=1), BROWN), rig, f"tarsus{i}.{side}")


@case("spider_with_coxa", "pass", "a clean spider of parts, short coxa bones")
def _():
    rig = spider_rig()
    spider(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "top", "left", "front_left"], "COLUMNS": 2}}


@case("spider_no_coxa", "pass", "the same spider with no coxa bones: one body bone, eight legs off it")
def _():
    rig = spider_rig(coxa=False)
    spider(rig, coxa=False)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


def tortoise_rig():
    bones = [("root", (0, 0.10, 0.12), (0, -0.10, 0.12), None), ("neck", (0, -0.18, 0.14), (0, -0.28, 0.17), "root"), ("head", (0, -0.28, 0.17), (0, -0.36, 0.18), "neck"),
             ("tail", (0, 0.22, 0.09), (0, 0.30, 0.06), "root")]
    for end, y in (("fore", -0.12), ("hind", 0.14)):
        for side, x in (("L", 0.13), ("R", -0.13)):
            bones.append((f"{end}_upper.{side}", (x * 0.8, y, 0.10), (x * 1.15, y, 0.06), "root"))
            bones.append((f"{end}_lower.{side}", (x * 1.15, y, 0.06), (x * 1.15, y, 0.015), f"{end}_upper.{side}"))
    return make_rig("TortoiseRig", bones)


def tortoise(rig):
    shell = lathe("Shell", [(0.0, 0.035), (0.20, 0.035), (0.23, 0.07), (0.20, 0.15), (0.10, 0.205), (0.0, 0.22)], segments=20)
    for v in shell.data.vertices:
        v.co.y *= 1.2
    on(paint(shell, GREEN), rig, "root")
    on(paint(capsule("NeckP", (0, -0.15, 0.13), (0, -0.28, 0.17), 0.04, 0.035, segments=8), YELLOW), rig, "neck")
    on(paint(capsule("HeadP", (0, -0.29, 0.17), (0, -0.35, 0.18), 0.04, 0.03, segments=8), YELLOW), rig, "head")
    on(paint(capsule("TailP", (0, 0.22, 0.08), (0, 0.32, 0.05), 0.02, 0.008, segments=6), YELLOW), rig, "tail")
    for end, y in (("fore", -0.12), ("hind", 0.14)):
        for s, x in (("L", 0.13), ("R", -0.13)):
            on(paint(capsule(f"{end}Leg.{s}", (x * 0.8, y, 0.10), (x * 1.15, y, 0.045), 0.04, 0.04, segments=8, sections=2), YELLOW), rig, f"{end}_upper.{s}", f"{end}_lower.{s}")


@case("tortoise", "pass", "a tortoise: short legs under a shell, whose rim hangs lower than the check's level on the legs")
def _():
    rig = tortoise_rig()
    tortoise(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front", "bottom", "front_left"], "COLUMNS": 2}}


if __name__ == "__main__":
    main()
