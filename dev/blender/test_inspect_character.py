# Runs game-assets/scripts/inspect_character.py against test mannequins with known defects and checks each report.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <inspect_character.py>
import math
import os
import sys
import types

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mannequin  # noqa: E402
import partsbody  # noqa: E402
import quadruped  # noqa: E402

script_path = sys.argv[sys.argv.index("--") + 1]
script = open(script_path).read()
scratch = sys.argv[sys.argv.index("--") + 2]


def run(**settings):
    namespace = {"__file__": script_path}
    namespace.update(settings)
    exec(compile(script, script_path, "exec"), namespace)
    return namespace["result"]


def skin_to(obj, rig, bone):
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig
    obj.parent = rig


def add_sphere(name, center, radius, rig=None, bone=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=center)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.transform_apply(location=True)
    if rig:
        skin_to(obj, rig, bone)
    return obj


def add_tube(name, radius, low, high, rig=None, bone=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=high - low, location=(0, 0, (low + high) / 2), end_fill_type="NOTHING")
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.transform_apply(location=True)
    if rig:
        skin_to(obj, rig, bone)
    return obj


def vertices(body, test):
    return [v.index for v in body.data.vertices if test(body.matrix_world @ v.co)]


def rename_bones(rig, names):
    for old, new in names.items():
        rig.data.bones[old].name = new


MIXAMO = {"hips": "mixamorig:Hips", "spine": "mixamorig:Spine", "chest": "mixamorig:Spine1", "neck": "mixamorig:Neck", "head": "mixamorig:Head"}
UNREAL = {"hips": "pelvis", "spine": "spine_01", "chest": "spine_02", "neck": "neck_01", "head": "head"}
for side, word in (("L", "Left"), ("R", "Right")):
    MIXAMO.update({f"shoulder.{side}": f"mixamorig:{word}Shoulder", f"upper_arm.{side}": f"mixamorig:{word}Arm",
                   f"forearm.{side}": f"mixamorig:{word}ForeArm", f"hand.{side}": f"mixamorig:{word}Hand",
                   f"thigh.{side}": f"mixamorig:{word}UpLeg", f"shin.{side}": f"mixamorig:{word}Leg",
                   f"foot.{side}": f"mixamorig:{word}Foot", f"toe.{side}": f"mixamorig:{word}ToeBase"})
    s = side.lower()
    UNREAL.update({f"shoulder.{side}": f"clavicle_{s}", f"upper_arm.{side}": f"upperarm_{s}", f"forearm.{side}": f"lowerarm_{s}",
                   f"hand.{side}": f"hand_{s}", f"thigh.{side}": f"thigh_{s}", f"shin.{side}": f"calf_{s}",
                   f"foot.{side}": f"foot_{s}", f"toe.{side}": f"ball_{s}"})
    for finger, unreal in (("thumb", "thumb"), ("index", "index"), ("middle", "middle"), ("ring", "ring"), ("little", "pinky")):
        for k in (1, 2, 3):
            MIXAMO[f"{finger}.0{k}.{side}"] = f"mixamorig:{word}Hand{'Pinky' if finger == 'little' else finger.capitalize()}{k}"
            UNREAL[f"{finger}.0{k}.{side}"] = f"{unreal}_0{k}_{s}"

cases = []


def case(label, expected, build, at_least=False, **settings):
    mannequin.clear()
    build_settings = build() or {}
    settings = dict(build_settings, **settings)
    report = run(**settings)
    found = sorted(report["issues"])
    ok = found == sorted(expected) and report["passed"] == (not expected)
    if at_least:
        ok = set(expected) <= set(found)
    cases.append({"case": label, "ok": ok, "expected": sorted(expected), "found": found, "issues": report["issues"], "why": report["examples"].get("intersections")})


def clean():
    mannequin.build()


case("clean mannequin", [], clean, SYMMETRIC=["Body"])
case("clean, Mixamo bone names", [], lambda: rename_bones(mannequin.build()[1], MIXAMO))
case("clean, Unreal bone names", [], lambda: rename_bones(mannequin.build()[1], UNREAL))
case("no armature: rig checks skipped", [], lambda: mannequin.build(rigged=False) and None)
# The Skin modifier's hull also cuts into itself where the single leg meets the pelvis.
case("legs are one surface", ["fused_legs"], lambda: mannequin.build(variant="one_leg") and None, at_least=True)
case("swollen waist", ["waist_bulge"], lambda: mannequin.build(variant="waist") and None)
case("swollen waist on purpose", [], lambda: mannequin.build(variant="waist") and None, WAIST_BULGE=True)
case("thumbs next to the little fingers", ["left_finger_order", "right_finger_order"],
     lambda: mannequin.build(variant="thumb_back") and None)
case("hands mirrored: each is the other side's", ["left_hand_mirrored", "right_hand_mirrored"],
     lambda: mannequin.build(variant="mirrored_hand") and None)
def _swap():
    body, rig = mannequin.build()
    lefts = [b.name for b in rig.data.bones if b.name.endswith(".L")]
    rights = [b.name for b in rig.data.bones if b.name.endswith(".R")]
    rename_bones(rig, {n: n[:-2] + ".tmp" for n in lefts})
    rename_bones(rig, {n: n[:-2] + ".L" for n in rights})
    rename_bones(rig, {n[:-2] + ".tmp": n[:-2] + ".R" for n in lefts})


# The bones named for the left hand sit in the right hand, which is the left hand's mirror image.
case("left and right bone names swapped", ["left_hand_mirrored", "left_right_swapped", "opposite_side_weights", "right_hand_mirrored"], _swap, at_least=True)


def facing_back():
    body, rig = mannequin.build()
    turn = Matrix.Rotation(math.pi, 4, "Z")
    for obj in (rig, body):
        obj.matrix_world = turn @ obj.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (rig, body):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)


case("model faces +Y", ["left_right_swapped", "not_facing_minus_y", "opposite_side_weights"], facing_back, at_least=True)


def hair_in_head():
    body, rig = mannequin.build()
    add_sphere("Hair", (0.0, 0.01, 1.68), 0.1, rig, "head")
    return {"TARGETS": ["Body", "Hair"]}


# A cap that sits in the head and pokes nothing: what it costs is what the player never sees.
case("hair sunk into the head", ["sunk_into_body"], hair_in_head, at_least=True)


def layered_shirt(offset, low=1.05):
    """A shirt made like a real one: the body's torso surface, moved out along its normals, with the body's weights."""
    def build():
        body, rig = mannequin.build()
        shirt = body.copy()
        shirt.data = body.data.copy()
        shirt.name = "Shirt"
        bpy.context.scene.collection.objects.link(shirt)
        bm = bmesh.new()
        bm.from_mesh(shirt.data)
        # Above the hip creases: with the body's weights, a garment there pokes through in a squat, which the
        # "shirt through the hip crease" case checks.
        torso = lambda c: low < c.z < 1.38 and abs(c.x) < 0.16  # noqa: E731
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not torso(f.calc_center_median())], context="FACES")
        bm.normal_update()
        for vertex in bm.verts:
            vertex.co += vertex.normal * offset
        bm.to_mesh(shirt.data)
        bm.free()
        return {"TARGETS": ["Body", "Shirt"]}
    return build


# This shirt is cut straight at the armpits, so its sides stand open: a look in there meets its far wall. Two-sided, that's fine.
case("a one-sided shirt with open sides", ["see_inside"], layered_shirt(0.012), at_least=True, SINGLE_LAYER=False)
# No face of this low-poly body is covered all over in every pose, so nothing is wasted. "What parts hide of each other", below, is.
case("body kept under a loose shirt", [], layered_shirt(0.012), TWO_SIDED=["Shirt"])
case("body under a loose shirt, outfits swap", [], layered_shirt(0.012), SINGLE_LAYER=False, TWO_SIDED=["Shirt"])
case("body under a loose shirt, allowed", [], layered_shirt(0.012), ALLOW_HIDDEN=["Body<Shirt"], TWO_SIDED=["Shirt"])
case("shirt sunk into the body", ["sunk_into_body"], layered_shirt(-0.008), SINGLE_LAYER=False)
case("shirt over the hip creases pokes through in a squat", ["poke_through_in_poses"], layered_shirt(0.012, low=0.95), at_least=True, SINGLE_LAYER=False)


def opposite_weights():
    body, rig = mannequin.build()
    left_leg = vertices(body, lambda co: co.x > 0.08 and co.z < 0.6)
    body.vertex_groups["thigh.R"].add(left_leg[:20], 0.3, "REPLACE")


case("left leg weighted to the right thigh", ["opposite_side_weights", "stretched_in_poses"], opposite_weights)


def unweighted():
    body, rig = mannequin.build()
    crown = vertices(body, lambda co: co.z > 1.70)
    for group in body.vertex_groups:
        group.remove(crown)


case("unweighted vertices", ["unweighted_vertices"], unweighted)


def five_influences():
    body, rig = mannequin.build()
    target = vertices(body, lambda co: co.z > 1.0 and co.z < 1.2)[:3]
    for bone in ("hips", "spine", "chest", "neck", "head"):
        body.vertex_groups[bone].add(target, 0.2, "REPLACE")


case("five bone influences", ["over_four_influences"], five_influences)


def forearm_on_hips():
    body, rig = mannequin.build()
    forearm = vertices(body, lambda co: co.x > 0.42 and co.x < 0.55 and co.z > 0.9)
    for group in body.vertex_groups:
        group.remove(forearm)
    body.vertex_groups["hips"].add(forearm, 1.0, "REPLACE")


case("forearm weighted to the hips stretches in poses", ["stretched_in_poses"], forearm_on_hips, at_least=True)


def floating():
    body, rig = mannequin.build()
    rig.location.z += 0.05  # the body is its child


case("feet above the ground", ["not_on_ground"], floating)


def asymmetric():
    body, rig = mannequin.build()
    for index in vertices(body, lambda co: co.x > 0.05 and co.z > 1.0 and co.z < 1.4):
        body.data.vertices[index].co.y += 0.02


case("asymmetric body", ["asymmetric"], asymmetric, SYMMETRIC=["Body"])


def no_head_bone():
    body, rig = mannequin.build()
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    rig.data.edit_bones.remove(rig.data.edit_bones["head"])
    bpy.ops.object.mode_set(mode="OBJECT")


case("head bone missing", ["missing_humanoid_bones"], no_head_bone)


def add_shell(name, profile, rig=None, bone=None, segments=24):
    """A lathe around the head's axis, open underneath like a hat or a hair cap: (radius, height) from the rim up."""
    mesh = bpy.data.meshes.new(name)
    verts, faces = [], []
    rings = [(r, z) for r, z in profile if r > 0.0]
    for r, z in rings:
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            verts.append((r * math.cos(angle), r * math.sin(angle), z))
    for k in range(len(rings) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((k * segments + i, k * segments + j, (k + 1) * segments + j, (k + 1) * segments + i))
    top = len(verts)
    verts.append((0.0, 0.0, profile[-1][1]))
    last = (len(rings) - 1) * segments
    for i in range(segments):
        faces.append((last + i, last + (i + 1) % segments, top))
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if rig:
        skin_to(obj, rig, bone)
    return obj


HAIR = [(0.135, 1.66), (0.135, 1.73), (0.1, 1.80), (0.0, 1.825)]
HAT_FITS = [(0.22, 1.70), (0.15, 1.705), (0.145, 1.82), (0.0, 1.87)]
# Crown top below the head's top: the head comes up through it.
HAT_TOO_SMALL = [(0.2, 1.64), (0.115, 1.645), (0.11, 1.69), (0.0, 1.70)]
# A crown narrower than the head, tall enough: the head comes out through its walls.
HAT_NARROW = [(0.2, 1.62), (0.06, 1.625), (0.06, 1.76), (0.0, 1.80)]
# Grazes the head's corners by 2 mm under the brim: nobody can see that.
HAT_SNUG = [(0.2, 1.70), (0.105, 1.705), (0.1, 1.76), (0.0, 1.80)]
HAT_OVER_BALD_HEAD = [(0.2, 1.70), (0.12, 1.705), (0.115, 1.79), (0.0, 1.815)]  # clears the head, not the hair
COVERED = ["Body<Hair", "Body<Hat", "Body<HatFits", "Body<HatSmall", "Body<HatBald", "Hair<Hat", "Hair<HatFits", "Hair<HatSmall", "Hair<HatBald"]


def hat_on_head(profile):
    def build():
        body, rig = mannequin.build()
        add_shell("Hat", profile, rig, "head")
        return {"TARGETS": ["Body", "Hat"], "ALLOW_HIDDEN": COVERED}
    return build


case("a hat that clears the head", [], hat_on_head(HAT_FITS))
case("a snug hat, grazing under its brim", [], hat_on_head(HAT_SNUG))
case("the head comes up through the hat's crown", ["parts_intersect", "shows_through_from_above"], hat_on_head(HAT_TOO_SMALL), at_least=True)
case("the head comes out through the crown's walls", ["shows_through_from_above"], hat_on_head(HAT_NARROW), at_least=True)


def hair_and_hats():
    body, rig = mannequin.build()
    add_shell("Hair", HAIR, rig, "head")
    add_shell("HatFits", HAT_FITS, rig, "head")
    add_shell("HatSmall", HAT_SNUG, rig, "head")
    return {"TARGETS": ["Body", "Hair", "HatFits", "HatSmall"], "ALLOW_HIDDEN": COVERED}


# Its brim sticks out of the hair, and the hair covers the rest of it: nothing comes through, and the hat is lost.
case("a hat lost in the hair, with its brim out", ["variant_swallowed", "shows_through_from_above"], hair_and_hats,
     PART_GROUPS={"hair": ["Hair"], "hat": ["HatFits", "HatSmall"]})


def hair_and_bald_hat():
    body, rig = mannequin.build()
    add_shell("Hair", HAIR, rig, "head")
    add_shell("HatFits", HAT_FITS, rig, "head")
    add_shell("HatBald", HAT_OVER_BALD_HEAD, rig, "head")
    return {"TARGETS": ["Body", "Hair", "HatFits", "HatBald"], "ALLOW_HIDDEN": COVERED}


case("a clash the game can show", ["variants_clash", "shows_through_from_above"], hair_and_bald_hat, PART_GROUPS={"hair": ["Hair"], "hat": ["HatFits", "HatBald"]})
case("a clash the game never shows", [], hair_and_bald_hat, PART_GROUPS={"hair": ["Hair"], "hat": ["HatFits", "HatBald"]},
     NEVER_TOGETHER=["Hair+HatBald"])


# Defects that cut no surface: only a look from above finds them.
def hat_lost_in_hair(hat_second):
    def build():
        body, rig = mannequin.build()
        add_shell("Hair", HAIR, rig, "head")
        add_shell("HatFits", HAT_FITS, rig, "head")
        add_shell("HatInside", [(0.125, 1.70), (0.12, 1.75), (0.08, 1.80), (0.0, 1.815)], rig, "head")
        names = ["HatFits", "HatInside"] if hat_second else ["HatInside", "HatFits"]
        return {"TARGETS": ["Body", "Hair", "HatFits", "HatInside"], "ALLOW_HIDDEN": COVERED + ["Body<HatInside", "Hair<HatInside"],
                "PART_GROUPS": {"hair": ["Hair"], "hat": names}, "POSES": False}
    return build


case("a hat swallowed by the hair, second in its group", ["shows_through_from_above", "variant_swallowed"], hat_lost_in_hair(True))
# First in its group, the plain hidden-face check sees it too.
case("a hat swallowed by the hair, first in its group", ["covered_faces", "shows_through_from_above", "variant_swallowed"], hat_lost_in_hair(False))


def open_crown():
    body, rig = mannequin.build()
    # A ring of a crown with no top: the head stands 5 cm out of it, touching nothing.
    mesh = bpy.data.meshes.new("Hat")
    verts, faces = [], []
    rings = [(0.2, 1.68), (0.13, 1.685), (0.125, 1.74)]
    for r, z in rings:
        for i in range(24):
            angle = 2 * math.pi * i / 24
            verts.append((r * math.cos(angle), r * math.sin(angle), z))
    for k in range(len(rings) - 1):
        for i in range(24):
            j = (i + 1) % 24
            faces.append((k * 24 + i, k * 24 + j, (k + 1) * 24 + j, (k + 1) * 24 + i))
    mesh.from_pydata(verts, [], faces)
    hat = bpy.data.objects.new("Hat", mesh)
    bpy.context.scene.collection.objects.link(hat)
    skin_to(hat, rig, "head")
    return {"TARGETS": ["Body", "Hat"], "ALLOW_HIDDEN": COVERED}


case("the head out of an open crown, touching nothing", ["shows_through_from_above", "open_part"], open_crown, at_least=True)
# One-sided, its far wall vanishes from above; drawn two-sided, it's a tiara.
case("a one-sided band: its far side vanishes from above", ["see_inside", "see_inside_in_poses"], open_crown, OPEN_ON_TOP=["Hat"])
case("an open crown that is meant to be: a two-sided tiara", [], open_crown, OPEN_ON_TOP=["Hat"], TWO_SIDED=["Hat"])


def renamed_open_crown(name):
    def build():
        settings = open_crown()
        bpy.data.objects["Hat"].name = name
        settings["TARGETS"] = ["Body", name]
        settings["ALLOW_HIDDEN"] = COVERED + [f"Body<{name}"]
        return settings
    return build


# By shape, not by name.
case("an open crown named Fedora", ["shows_through_from_above", "open_part"], renamed_open_crown("Fedora"), at_least=True)


def bald_spot():
    body, rig = mannequin.build()
    # Hair with its top missing: from above, the head shows.
    add_shell("Hair", HAIR, rig, "head")
    hair = bpy.data.objects["Hair"]
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > 1.78], context="FACES_ONLY")
    bm.to_mesh(hair.data)
    bm.free()
    return {"TARGETS": ["Body", "Hair"], "ALLOW_HIDDEN": COVERED}


case("the head through a hole in the hair", ["shows_through_from_above", "open_part"], bald_spot, at_least=True)


def side_hole():
    body, rig = mannequin.build()
    hat = add_shell("Hat", HAT_FITS, rig, "head", segments=24)
    bm = bmesh.new()
    bm.from_mesh(hat.data)
    bm.faces.ensure_lookup_table()
    # One face out of the crown's side, halfway up.
    crown = [f for f in bm.faces if 1.72 < f.calc_center_median().z < 1.80]
    bmesh.ops.delete(bm, geom=[crown[0]], context="FACES_ONLY")
    bm.to_mesh(hat.data)
    bm.free()
    return {"TARGETS": ["Body", "Hat"], "ALLOW_HIDDEN": COVERED}


case("a hole in the side of a hat", ["open_part"], side_hole, at_least=True)


def flipped_hat():
    body, rig = mannequin.build()
    hat = add_shell("Hat", HAT_FITS, rig, "head")
    hat.data.flip_normals()
    return {"TARGETS": ["Body", "Hat"], "ALLOW_HIDDEN": COVERED + ["Hat", "Hat<Body"]}


case("a hat inside out", ["inside_out"], flipped_hat, at_least=True)


def hat_left_out():
    body, rig = mannequin.build()
    add_shell("Hat", HAT_TOO_SMALL, rig, "head")
    return {"TARGETS": ["Body"]}


case("a hat on the rig, left out of TARGETS", ["parts_left_out"], hat_left_out)


def parented_hat(profile):
    def build():
        body, rig = mannequin.build()
        hat = add_shell("Hat", profile)
        hat.parent = rig
        hat.parent_type = "BONE"
        hat.parent_bone = "head"
        # Keep it where it was built: a bone parent works from the bone's tail, in the bone's orientation.
        bone = rig.data.bones["head"]
        hat.matrix_parent_inverse = (rig.matrix_world @ Matrix.Translation(bone.tail_local) @ bone.matrix_local.to_3x3().to_4x4()).inverted()
        return {"ARMATURE": rig.name, "ALLOW_HIDDEN": COVERED}
    return build


case("a too-small hat parented to a bone, no TARGETS", ["parts_intersect", "shows_through_from_above"], parented_hat(HAT_TOO_SMALL), at_least=True)
case("a fitting hat parented to a bone is fine, not 'not skinned'", [], parented_hat(HAT_FITS))


def one_mesh_hat():
    body, rig = mannequin.build()
    add_shell("Hat", HAT_TOO_SMALL, rig, "head")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.data.objects["Hat"].select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    return {"TARGETS": ["Body"], "ALLOW_HIDDEN": ["Body"]}


case("the same defect inside one mesh", ["self_intersections", "shows_through_from_above"], one_mesh_hat, at_least=True)


# --- Characters built from parts that overlap at the joints -----------------------------------------------------------

proof_dir = os.path.join(scratch, "proofs")


def parts_build(extra=None, skip=(), sections=1, merged=False):
    """Builds the person, lets `extra` change it, and returns its settings. `extra` gets the rig and the parts by name."""
    def build():
        rig = partsbody.person_rig()
        parts = {o.name: o for o in partsbody.person(rig, skip, sections)}
        settings = (extra(rig, parts) if extra else None) or {}
        names = [o.name for o in bpy.context.scene.objects if o.type == "MESH"]
        if merged:
            partsbody.merge([bpy.data.objects[n] for n in names])
            names = ["Merged"]
        settings.setdefault("TARGETS", names)
        settings.setdefault("ARMATURE", rig.name)
        settings.setdefault("FINGERS", 5)
        return settings
    return build


def both(label, expected, extra=None, at_least=False, skip=(), sections=1, **settings):
    """The same character as separate objects and as one merged mesh, on its whole parts: defects must show in each. In one
    mesh, parts that poke each other report as the mesh cutting itself."""
    settings.setdefault("WHOLE_PARTS", True)
    case(f"{label} (objects)", expected, parts_build(extra, skip, sections), at_least=at_least, **settings)
    merged_expected = ["self_intersections" if name == "parts_intersect" else name for name in expected]
    case(f"{label} (one mesh)", merged_expected, parts_build(extra, skip, sections, merged=True), at_least=at_least, **settings)


both("a clean body of parts", [])
case("its whole parts still cost what is hidden", ["hidden_inside"], parts_build(merged=True))
case("the same as objects: what parts hide of each other", ["covered_faces", "sunk_into_body"], parts_build(), at_least=True)


def wearing(*made):
    def extra(rig, parts):
        for make in made:
            make(rig, parts)
    return extra


def on_bone(obj, rig, bones):
    return partsbody.attach(obj, rig, bones)


def ears_and_nose(rig, parts):
    on_bone(partsbody.capsule("Ear.L", (0.09, 0, 1.64), (0.15, 0, 1.68), 0.025, 0.018, segments=6, rings=2), rig, ["head"])
    on_bone(partsbody.capsule("Ear.R", (-0.09, 0, 1.64), (-0.15, 0, 1.68), 0.025, 0.018, segments=6, rings=2), rig, ["head"])
    on_bone(partsbody.capsule("Nose", (0, -0.09, 1.63), (0, -0.13, 1.62), 0.025, 0.02, segments=6, rings=2), rig, ["head"])


def sunk_eyes(rig, parts):
    for side, x in (("L", 0.04), ("R", -0.04)):
        on_bone(partsbody.capsule(f"Eye.{side}", (x, -0.085, 1.66), (x, -0.085, 1.66001), 0.022, 0.022, segments=8, rings=3), rig, ["head"])


def belt_and_anklet(rig, parts):
    on_bone(partsbody.ring("Belt", 0.172, 0.14, 0.98, 1.04, squash_y=0.68), rig, ["hips", "spine"])
    on_bone(partsbody.ring("Anklet", 0.066, 0.03, -0.015, 0.015, center=(0.10, 0.0, 0.25)), rig, ["shin.L"])


def hair_cap(rig, parts):
    on_bone(partsbody.lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)]), rig, ["head"])


def clear_hat(rig, parts):
    on_bone(partsbody.lathe("Hat", [(0.0, 1.70), (0.2, 1.70), (0.2, 1.705), (0.13, 1.71), (0.125, 1.82), (0.0, 1.86)]), rig, ["head"])


def sunk_rim_hat(rig, parts):
    # The band of the hat is narrower than the head where it sits: its lower edge bites into the forehead all around.
    on_bone(partsbody.lathe("Hat", [(0.0, 1.655), (0.09, 1.655), (0.125, 1.70), (0.12, 1.82), (0.0, 1.86)]), rig, ["head"])


def bobble(rig, parts):
    clear_hat(rig, parts)
    on_bone(partsbody.capsule("Bobble", (0, 0, 1.87), (0, 0, 1.875), 0.03, 0.03, segments=8), rig, ["head"])


def side_horn(rig, parts):
    on_bone(partsbody.capsule("Horn", (0.07, -0.02, 1.70), (0.15, -0.04, 1.80), 0.03, 0.008, segments=6), rig, ["head"])


def top_antenna(rig, parts):
    on_bone(partsbody.capsule("Antenna", (0, 0, 1.76), (0, 0, 1.90), 0.012, 0.008, segments=6), rig, ["head"])


def sleeve(rig, parts):
    shoulder, wrist = rig.data.bones["upper_arm.L"].head_local, rig.data.bones["forearm.L"].tail_local
    end = shoulder.lerp(wrist, 0.85)
    on_bone(partsbody.capsule("Sleeve", shoulder, end, 0.085, 0.05, segments=8, sections=4), rig, ["upper_arm.L", "forearm.L"])


def trouser_leg(rig, parts):
    hip, ankle = rig.data.bones["thigh.L"].head_local, rig.data.bones["shin.L"].tail_local
    end = hip.lerp(ankle, 0.85)
    on_bone(partsbody.capsule("Trouser", hip, end, 0.11, 0.075, segments=8, sections=6), rig, ["thigh.L", "shin.L"])


both("ears and a nose set into the head", [], wearing(ears_and_nose))
both("eyes sunk deep into the head", [], wearing(sunk_eyes))
both("a belt and an anklet sunk in", [], wearing(belt_and_anklet))
both("a hair cap set into the head", [], wearing(hair_cap))
both("a hat clear of the head", [], wearing(clear_hat))
both("a hat whose band bites into the forehead", [], wearing(sunk_rim_hat))
both("a bobble on a hat", [], wearing(bobble))
both("a horn to one side", [], wearing(side_horn))
both("an antenna on top", [], wearing(top_antenna))
# With the whole limb kept under them they poke at a deep bend, truly; these two look at the cuff and the hem at rest.
both("a sleeve with the hand coming out of its cuff", [], wearing(sleeve), sections=4, POSES=False)
both("a trouser leg with the foot coming out of its hem", [], wearing(trouser_leg), sections=6, POSES=False)
both("a whole limb kept under a wide sleeve, with the elbow folded", [], wearing(sleeve), sections=4)


def narrow_sleeve(rig, parts):
    shoulder, wrist = rig.data.bones["upper_arm.L"].head_local, rig.data.bones["forearm.L"].tail_local
    on_bone(partsbody.capsule("Sleeve", shoulder, shoulder.lerp(wrist, 0.85), 0.07, 0.042, segments=8, sections=4), rig, ["upper_arm.L", "forearm.L"])


both("a whole limb kept under a narrow sleeve pokes when the elbow folds", ["poke_through_in_poses"], wearing(narrow_sleeve), sections=4)


def thighs_cross_in_the_pelvis(rig, parts):
    for name in ("Leg.L", "Leg.R", "Torso"):
        bpy.data.objects.remove(parts[name], do_unlink=True)
    on_bone(partsbody.capsule("Torso", (0, 0, 0.90), (0, 0, 1.36), 0.16, 0.17, segments=12, squash_y=0.68), rig, ["hips", "spine", "chest"])
    for side, sign in (("L", 1), ("R", -1)):
        on_bone(partsbody.capsule(f"Thigh.{side}", (-0.03 * sign, 0, 0.93), (0.13 * sign, 0, 0.50), 0.035, 0.035, segments=8), rig, [f"thigh.{side}"])
        on_bone(partsbody.capsule(f"Shin.{side}", (0.13 * sign, 0, 0.52), (0.10 * sign, 0, 0.09), 0.04, 0.035, segments=8), rig, [f"shin.{side}"])


both("thighs that cross only inside the pelvis", [], thighs_cross_in_the_pelvis, POSES=False)


def fingers_in_a_palm(rig, parts):
    bones = rig.data.bones
    for side in ("L", "R"):
        bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
        on_bone(partsbody.capsule(f"Arm.{side}", bones[f"upper_arm.{side}"].head_local, bones[f"forearm.{side}"].tail_local, 0.055, 0.035, segments=8, sections=4), rig, [f"upper_arm.{side}", f"forearm.{side}"])
        on_bone(partsbody.capsule(f"Palm.{side}", bones[f"hand.{side}"].head_local, bones[f"hand.{side}"].tail_local, 0.032, 0.03, segments=8), rig, [f"hand.{side}"])
        for finger in ("thumb", "index", "middle", "ring", "little"):
            base, tip = bones[f"{finger}.01.{side}"].head_local, bones[f"{finger}.03.{side}"].tail_local
            on_bone(partsbody.capsule(f"{finger}.{side}", base, tip, 0.008, 0.006, segments=6, rings=2, sections=3), rig, [f"{finger}.0{k}.{side}" for k in (1, 2, 3)])


both("fingers set into a palm", [], fingers_in_a_palm)


def hair_cards(rig, parts):
    # Crossing strips, rooted in the scalp: transparent, one part.
    mesh = bpy.data.meshes.new("Cards")
    verts, faces = [], []
    for k in range(6):
        angle = k * math.pi / 6
        dx, dy = 0.12 * math.cos(angle), 0.12 * math.sin(angle)
        base = len(verts)
        verts += [(-dx, -dy, 1.74), (dx, dy, 1.74), (dx, dy, 1.84), (-dx, -dy, 1.84)]
        faces.append((base, base + 1, base + 2, base + 3))
    mesh.from_pydata(verts, [], faces)
    cards = bpy.data.objects.new("Cards", mesh)
    bpy.context.scene.collection.objects.link(cards)
    on_bone(cards, rig, ["head"])


case("hair cards that cross each other and the scalp", [], parts_build(wearing(hair_cards)), WHOLE_PARTS=True, SEE_THROUGH=["Cards"])


# What must still fail on a body of parts.
def head_through_hat(rig, parts):
    on_bone(partsbody.lathe("Hat", [(0.0, 1.70), (0.2, 1.70), (0.2, 1.705), (0.13, 1.71), (0.125, 1.74), (0.0, 1.76)]), rig, ["head"])


def hair_through_hat(rig, parts):
    on_bone(partsbody.lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.80), (0.0, 1.83)]), rig, ["head"])
    on_bone(partsbody.lathe("Hat", [(0.0, 1.71), (0.2, 1.71), (0.2, 1.715), (0.13, 1.72), (0.125, 1.78), (0.0, 1.80)]), rig, ["head"])


def knee_through_trousers(rig, parts):
    trouser_leg(rig, parts)
    bones = rig.data.bones
    knee = bones["shin.L"].head_local
    partsbody.bump(parts["Leg.L"], (knee.x, knee.y - 0.05, knee.z), 0.09, (0.0, -0.05, 0.0))


def elbow_through_sleeve(rig, parts):
    sleeve(rig, parts)
    elbow = rig.data.bones["forearm.L"].head_local
    partsbody.bump(parts["Arm.L"], (elbow.x, elbow.y + 0.04, elbow.z), 0.07, (0.0, 0.05, 0.0))


def arm_out_the_back(rig, parts):
    bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
    bones = rig.data.bones
    on_bone(partsbody.capsule("Arm.L", (-0.26, 0.0, 1.38), bones["hand.L"].tail_local, 0.045, 0.035, segments=8, sections=6), rig, ["upper_arm.L", "forearm.L", "hand.L"])


def legs_fused(rig, parts):
    for name in ("Leg.L", "Leg.R"):
        bpy.data.objects.remove(parts[name], do_unlink=True)
    bones = rig.data.bones
    for side in ("L", "R"):
        on_bone(partsbody.capsule(f"Leg.{side}", bones[f"thigh.{side}"].head_local, bones[f"shin.{side}"].tail_local, 0.115, 0.05, segments=8), rig, [f"thigh.{side}", f"shin.{side}"])


def spike_through_head(rig, parts):
    on_bone(partsbody.capsule("Spike", (-0.16, 0.0, 1.65), (0.16, 0.0, 1.65), 0.015, 0.015, segments=6, rings=2), rig, ["head"])


def hand_part_in_the_hip(rig, parts):
    on_bone(partsbody.capsule("Glove", (0.17, 0.0, 1.00), (0.25, 0.0, 0.95), 0.03, 0.03, segments=8), rig, ["hand.L"])


both("the head through a hat", ["parts_intersect", "shows_through_from_above"], wearing(head_through_hat), at_least=True)
both("hair through a hat", ["parts_intersect", "shows_through_from_above"], wearing(hair_through_hat), at_least=True)
both("a knee through trousers", ["parts_intersect"], wearing(knee_through_trousers), at_least=True, sections=6)
both("an elbow through a sleeve", ["parts_intersect"], wearing(elbow_through_sleeve), at_least=True, sections=4)
both("an arm out of the back", ["parts_intersect"], wearing(arm_out_the_back), at_least=True)
both("legs fused below the pelvis", ["parts_intersect"], wearing(legs_fused), at_least=True)
both("a spike through the head", ["parts_intersect"], wearing(spike_through_head), at_least=True)
both("a hand in the hip at rest", ["parts_intersect"], wearing(hand_part_in_the_hip), at_least=True)
case("a spike through the head, on purpose", [], parts_build(wearing(spike_through_head)), WHOLE_PARTS=True, ALLOW_CROSSING=["Spike+Head"])


def wide_hips_at_the_arms(rig, parts):
    # Arms that join the torso at rest, whose hands go into its wide hips when they come down.
    bpy.data.objects.remove(parts["Torso"], do_unlink=True)
    on_bone(partsbody.capsule("Torso", (0, 0, 0.92), (0, 0, 1.36), 0.34, 0.17, segments=12, squash_y=0.68), rig, ["hips", "spine", "chest"])


both("a hand through the hip in a pose", ["poke_through_in_poses"], wearing(wide_hips_at_the_arms), at_least=True)


def loose_hand(rig, parts):
    # The arm's whole part follows the upper arm: at the elbow's bend, the hand part leaves it.
    bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
    bones = rig.data.bones
    on_bone(partsbody.capsule("Arm.L", bones["upper_arm.L"].head_local, bones["forearm.L"].tail_local, 0.055, 0.035, segments=8), rig, ["upper_arm.L"])
    on_bone(partsbody.capsule("HandPart", bones["hand.L"].head_local, bones["hand.L"].tail_local, 0.04, 0.03, segments=8), rig, ["hand.L"])


case("a joint that comes apart in a pose", ["joint_opens_in_poses"], parts_build(wearing(loose_hand)), at_least=True, WHOLE_PARTS=True)


def wide_one_skin():
    body, rig = mannequin.build()
    for vertex in body.data.vertices:
        if 0.75 < vertex.co.z < 1.0:
            vertex.co.x *= 2.6


case("one skin: a hand through the hip in a pose", ["poke_through_in_poses"], wide_one_skin, at_least=True)


# Cutting what is hidden: the tool, the holes it must not leave, the receipts.
def cut_tool(**settings):
    path = os.path.join(os.path.dirname(script_path), "cut_hidden_faces.py")
    namespace = {"__file__": path}
    namespace.update(settings)
    exec(compile(open(path).read(), path, "exec"), namespace)
    return namespace["result"]


def cut_flow(merged):
    def flow():
        settings = parts_build(merged=merged)()
        check = {k: settings[k] for k in ("TARGETS", "ARMATURE", "FINGERS")}
        whole = run(WHOLE_PARTS=True, PROOF_DIR=proof_dir, PROOF_NAME="cutflow", **check)
        result = cut_tool(TARGETS=check["TARGETS"], ARMATURE=check["ARMATURE"])
        final = run(PROOF_DIR=proof_dir, PROOF_NAME="cutflow", **check)
        return whole, result, final
    return flow


for merged in (False, True):
    mannequin.clear()
    whole, result, final = cut_flow(merged)()
    saved = result["triangles_before"] - result["triangles_after"]
    ok = whole["passed"] and final["passed"] and saved > 0.05 * result["triangles_before"]
    cases.append({"case": f"whole parts pass, the cut saves triangles, the result passes ({'one mesh' if merged else 'objects'})", "ok": ok, "expected": [], "found": sorted(final["issues"]),
                  "issues": {"whole": whole["issues"], "final": final["issues"], "cut": result}})

for name in os.listdir(proof_dir):
    os.remove(os.path.join(proof_dir, name))
mannequin.clear()
settings = parts_build(merged=True)()
cut_tool(TARGETS=settings["TARGETS"], ARMATURE=settings["ARMATURE"])
report = run(PROOF_DIR=proof_dir, PROOF_NAME="nocheck", **settings)
cases.append({"case": "cut, with no check of the whole parts", "ok": "parts_not_checked_before_cut" in report["issues"], "expected": ["parts_not_checked_before_cut"], "found": sorted(report["issues"]), "issues": report["issues"]})


def cut_at_rest_only(obj):
    """Deletes what is hidden in the rest pose alone, as a careless pipeline does: bends open what it removed."""
    path = os.path.join(os.path.dirname(script_path), "rig.py")
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    exec(compile(open(path).read(), path, "exec"), namespace)
    helpers = types.SimpleNamespace(**namespace)
    armature = helpers.deforming_armature(obj)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    surfaces = helpers.Character([obj], armature).gather()
    doomed = set()
    for a in surfaces:
        for b in surfaces:
            if a is not b:
                for index in helpers.under(a, b):
                    doomed.add(a.source[index])
    helpers.free(surfaces)
    armature.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in doomed], context="FACES")
    bm.to_mesh(obj.data)
    bm.free()


def careless_cut():
    settings = parts_build(merged=True)()
    run(WHOLE_PARTS=True, PROOF_DIR=proof_dir, PROOF_NAME="careless", POSES=False, **settings)
    cut_at_rest_only(bpy.data.objects["Merged"])
    return dict(settings, PROOF_DIR=proof_dir, PROOF_NAME="careless")


case("a cut at rest alone: bends open what it removed", ["see_inside_in_poses"], careless_cut, at_least=True)


def cut_by_centers(obj):
    """Deletes every face whose center is inside another part, also those that still show: holes at the seams."""
    path = os.path.join(os.path.dirname(script_path), "rig.py")
    namespace = {"__file__": path, "__name__": "rig_helpers"}
    exec(compile(open(path).read(), path, "exec"), namespace)
    helpers = types.SimpleNamespace(**namespace)
    armature = helpers.deforming_armature(obj)
    armature.data.pose_position = "REST"
    bpy.context.view_layer.update()
    surfaces = helpers.Character([obj], armature).gather()
    doomed = set()
    for a in surfaces:
        for b in surfaces:
            if a is not b:
                for face in a.bm.faces:
                    if helpers.inside(b, face.calc_center_median()):
                        doomed.add(a.source[face.index])
    helpers.free(surfaces)
    armature.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in doomed], context="FACES")
    bm.to_mesh(obj.data)
    bm.free()


def rough_cut():
    settings = parts_build(merged=True)()
    run(WHOLE_PARTS=True, PROOF_DIR=proof_dir, PROOF_NAME="rough", POSES=False, **settings)
    cut_by_centers(bpy.data.objects["Merged"])
    return dict(settings, PROOF_DIR=proof_dir, PROOF_NAME="rough", POSES=False)


case("a cut by face centers: holes at the seams", ["see_inside"], rough_cut, at_least=True)


def floating_head(rig, parts):
    for name in ("Head", "Neck"):
        bpy.data.objects.remove(parts[name], do_unlink=True)
    on_bone(partsbody.capsule("Head", (0, 0, 1.72), (0, 0, 1.78), 0.1, 0.1, segments=12), rig, ["head"])


both("a head hanging above the body", ["floating_part"], wearing(floating_head), at_least=True)
case("a halo hanging above the head, on purpose", [], parts_build(lambda rig, parts: on_bone(partsbody.ring("Halo", 0.11, 0.09, -0.005, 0.005, center=(0, 0, 1.93)), rig, ["head"]) and None), WHOLE_PARTS=True, ALLOW_FLOATING=["Halo"], OPEN_ON_TOP=["Halo"])


# A statue: no rig, no joints, only what shows.
def statue(extra=None):
    def build():
        names = []
        for name, args, kwargs in (("Torso", ((0, 0, 0.92), (0, 0, 1.36), 0.16, 0.17), {"segments": 12, "squash_y": 0.68}),
                                   ("Head", ((0, 0, 1.55), (0, 0, 1.68), 0.1, 0.1), {"segments": 12}),
                                   ("Leg.L", ((0.09, 0, 0.90), (0.09, 0, 0.05), 0.07, 0.05), {"segments": 8}),
                                   ("Leg.R", ((-0.09, 0, 0.90), (-0.09, 0, 0.05), 0.07, 0.05), {"segments": 8})):
            names.append(partsbody.capsule(name, *args, **kwargs).name)
        if extra:
            names.append(extra())
        return {"TARGETS": names}
    return build


case("a statue of parts", [], statue(), WHOLE_PARTS=True)
case("a statue with a spike through it", ["parts_intersect"], at_least=True, build=statue(lambda: partsbody.capsule("Spike", (-0.3, 0, 1.15), (0.3, 0, 1.15), 0.01, 0.01, segments=6, rings=2).name), WHOLE_PARTS=True)


# Animals: any number of legs, no Humanoid bones.
def animal_build(extra=None, merged=False):
    def build():
        rig = partsbody.animal_rig()
        parts = {o.name: o for o in partsbody.animal(rig)}
        settings = (extra(rig, parts) if extra else None) or {}
        names = [o.name for o in bpy.context.scene.objects if o.type == "MESH"]
        if merged:
            partsbody.merge([bpy.data.objects[n] for n in names])
            names = ["Merged"]
        settings.setdefault("TARGETS", names)
        settings.setdefault("ARMATURE", rig.name)
        return settings
    return build


def animal_both(label, expected, extra=None, at_least=False, **settings):
    settings.setdefault("WHOLE_PARTS", True)
    case(f"{label} (objects)", expected, animal_build(extra), at_least=at_least, **settings)
    merged_expected = ["self_intersections" if name == "parts_intersect" else name for name in expected]
    case(f"{label} (one mesh)", merged_expected, animal_build(extra, merged=True), at_least=at_least, **settings)


animal_both("a clean animal of parts", [])


def animal_skeleton_first():
    body, rig = quadruped.build()
    return {"TARGETS": [body.name], "ARMATURE": rig.name, "SYMMETRIC": [body.name]}


case("a clean animal of one skin", [], animal_skeleton_first)


def fat_belly(rig, parts):
    bpy.data.objects.remove(parts["Trunk"], do_unlink=True)
    on_bone(partsbody.capsule("Trunk", (0, 0.30, 0.40), (0, -0.22, 0.40), 0.21, 0.21, segments=12), rig, ["hips", "spine"])


animal_both("a shin through the belly when a leg folds", ["poke_through_in_poses"], wearing(fat_belly), at_least=True)


def animal_hat(rig, parts):
    on_bone(partsbody.lathe("Hat", [(0.0, 0.64), (0.09, 0.64), (0.09, 0.645), (0.05, 0.65), (0.045, 0.665), (0.0, 0.672)], center=(0.0, -0.44)), rig, ["head"])


animal_both("a skull through a small hat", ["parts_intersect", "shows_through_from_above"], wearing(animal_hat), at_least=True)


def fused_animal_legs(rig, parts):
    for name in ("foreLeg.L", "foreLeg.R"):
        bpy.data.objects.remove(parts[name], do_unlink=True)
    bones = rig.data.bones
    for side in ("L", "R"):
        on_bone(partsbody.capsule(f"foreLeg.{side}", bones[f"fore_thigh.{side}"].head_local, bones[f"fore_shin.{side}"].tail_local, 0.11, 0.095, segments=8), rig, [f"fore_thigh.{side}", f"fore_shin.{side}"])


animal_both("front legs cut each other", ["parts_intersect"], wearing(fused_animal_legs), at_least=True)

# The receipt.
proofs = os.path.join(os.path.dirname(script_path), "..", "..", "..", "..", "..", "dev", "library-tests", "Logs", "proofs-test")
mannequin.clear()
mannequin.build()
receipt_report = run(SYMMETRIC=["Body"], PROOF_DIR=proofs, PROOF_NAME="mannequin", POSES=False)
receipt = os.path.join(proofs, "inspect_character-mannequin.json")
ok = os.path.exists(receipt) and open(receipt).read().lstrip("{ \n").startswith('"passed": ' + str(receipt_report["passed"]).lower())
cases.append({"case": "writes its receipt", "ok": ok, "expected": [], "found": [], "issues": {}})

failed = [c for c in cases if not c["ok"]]
for c in cases:
    print("CASE", "ok  " if c["ok"] else "FAIL", c["case"], "expected", c["expected"], "found", c["found"])
    if not c["ok"]:
        print("     ", c["issues"], c.get("why"))
print("TOTAL", len(cases), "cases,", len(failed), "failed")
if failed:
    raise AssertionError(f"{len(failed)} of {len(cases)} cases failed")
