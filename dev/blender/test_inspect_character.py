# Runs game-assets/scripts/inspect_character.py against test mannequins with known defects and checks each report.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <inspect_character.py>
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mannequin  # noqa: E402

script_path = sys.argv[sys.argv.index("--") + 1]
script = open(script_path).read()


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


def case(label, expected, build, **settings):
    mannequin.clear()
    build_settings = build() or {}
    settings = dict(build_settings, **settings)
    report = run(**settings)
    found = sorted(report["issues"])
    ok = found == sorted(expected) and report["passed"] == (not expected)
    cases.append({"case": label, "ok": ok, "expected": sorted(expected), "found": found, "issues": report["issues"]})


def clean():
    mannequin.build()


case("clean mannequin", [], clean, SYMMETRIC=["Body"])
case("clean, Mixamo bone names", [], lambda: rename_bones(mannequin.build()[1], MIXAMO))
case("clean, Unreal bone names", [], lambda: rename_bones(mannequin.build()[1], UNREAL))
case("no armature: rig checks skipped", [], lambda: mannequin.build(rigged=False) and None)
# The Skin modifier's hull also cuts into itself where the single leg meets the pelvis.
case("legs are one surface", ["fused_legs", "hidden_inside", "self_intersections"],
     lambda: mannequin.build(variant="one_leg", rigged=False) and None)
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
case("left and right bone names swapped", ["left_hand_mirrored", "left_right_swapped", "opposite_side_weights", "right_hand_mirrored"], _swap)


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


case("model faces +Y", ["left_right_swapped", "not_facing_minus_y", "opposite_side_weights"], facing_back)


def hair_in_head():
    body, rig = mannequin.build()
    add_sphere("Hair", (0.0, 0.01, 1.68), 0.1, rig, "head")
    return {"TARGETS": ["Body", "Hair"]}


case("hair cuts into the head", ["covered_faces", "parts_intersect", "sunk_into_body"], hair_in_head)


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


case("body kept under a loose shirt", ["covered_faces"], layered_shirt(0.012))
case("body under a loose shirt, outfits swap", [], layered_shirt(0.012), SINGLE_LAYER=False)
case("body under a loose shirt, allowed", [], layered_shirt(0.012), ALLOW_HIDDEN=["Body<Shirt"])
case("shirt sunk into the body", ["sunk_into_body"], layered_shirt(-0.008), SINGLE_LAYER=False)
case("shirt over the hip creases pokes through in a squat", ["poke_through_in_poses"], layered_shirt(0.012, low=0.95), SINGLE_LAYER=False)


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


case("forearm weighted to the hips stretches in poses", ["stretched_in_poses"], forearm_on_hips)


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

failed = [c for c in cases if not c["ok"]]
for c in cases:
    print("CASE", "ok  " if c["ok"] else "FAIL", c["case"], "expected", c["expected"], "found", c["found"])
    if not c["ok"]:
        print("     ", c["issues"])
if failed:
    raise AssertionError(f"{len(failed)} of {len(cases)} cases failed")
