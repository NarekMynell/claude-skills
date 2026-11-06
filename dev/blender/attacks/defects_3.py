# Real defects, third batch: helper bones, half shells, fused legs above the sample level, long tails, flipped parts.
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
import cuts_1 as cuts
from defects_1 import raise_z, move, plane, open_lathe, fits_hat, dense_leg, trouser
from defects_2 import constrained_rig, wide_hips
from clean_1 import union, hair_shell
from clean_2 import ring_on, horse_rig, horse, spider_rig, spider
from cuts_1 import culling_render, keys, run_clip
CASES.clear()


def add_helper_bones(rig, bones=("upper_arm", "thigh"), per=2):
    """Bones like a UE5 mannequin's upperarm_twist_01, upperarm_twist_02: extra children of the limb's bone."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    for side in ("L", "R"):
        for base in bones:
            parent = edit[f"{base}.{side}"]
            for k in range(per):
                b = edit.new(f"{base}_twist_{k + 1:02d}.{side}")
                b.head = parent.head.lerp(parent.tail, 0.3 + 0.3 * k)
                b.tail = parent.head.lerp(parent.tail, 0.5 + 0.3 * k)
                b.parent = parent
    bpy.ops.object.mode_set(mode="OBJECT")


@case("helpers_control_hand_in_the_hip", "fail", "a part on the hand bone in the hip at rest, and hands through wide hips in a pose (the repo's defects, control: must fail)")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        on(paint(capsule("Glove", (0.17, 0.0, 1.00), (0.25, 0.0, 0.95), 0.03, 0.03, segments=8), YELLOW), rig, "hand.L")
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True}
    return person(extra)


@case("helpers_hand_in_the_hip_rig_with_twist_bones", "fail", "the same defects on the same body; the rig also has two twist bones under each upper arm and thigh, as a UE5-style skeleton has: three children make the whole arm one 'hand'")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        on(paint(capsule("Glove", (0.17, 0.0, 1.00), (0.25, 0.0, 0.95), 0.03, 0.03, segments=8), YELLOW), rig, "hand.L")
        add_helper_bones(rig)
        def after(report):
            apply_named_pose(rig, "arms_down")
            render("helpers_arms_down", VIEWS=["front", "left"], COLUMNS=2)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True, "_after": after, "_render": {"VIEWS": ["front"]}}
    return person(extra)


@case("helpers_shin_through_belly_in_squat", "fail", "a fat belly and a squat: shins through it. Control without helpers below")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Torso"], do_unlink=True)
        t = capsule("Torso", (0, -0.12, 0.95), (0, 0, 1.36), 0.26, 0.17, segments=14, squash_y=1.0)
        on(paint(t, SKIN), rig, "hips", "spine", "chest")
        add_helper_bones(rig)
        def after(report):
            apply_named_pose(rig, "squat")
            render("helpers_squat", VIEWS=["left", "front_left"], COLUMNS=2)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True, "WAIST_BULGE": True, "_after": after}
    return person(extra, sections=6)


@case("helpers_shin_through_belly_control", "fail", "the same belly and squat with no helper bones (control: must fail)")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Torso"], do_unlink=True)
        t = capsule("Torso", (0, -0.12, 0.95), (0, 0, 1.36), 0.26, 0.17, segments=14, squash_y=1.0)
        on(paint(t, SKIN), rig, "hips", "spine", "chest")
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True, "WAIST_BULGE": True}
    return person(extra, sections=6)


def add_head_top_end(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    b = edit.new("HeadTop_End")
    b.head = edit["head"].tail.copy()
    b.tail = edit["head"].tail + Vector((0, 0, 0.08))
    b.parent = edit["head"]
    bpy.ops.object.mode_set(mode="OBJECT")


def arm_root_near_head(rig, parts):
    # The upper arm goes up through the head when arms are raised: long shoulders close to a big head.
    bpy.data.objects.remove(parts["Head"], do_unlink=True)
    on(paint(capsule("Head", (0, 0, 1.62), (0, 0, 1.68), 0.19, 0.19, segments=16), SKIN), rig, "head")


@case("mixamo_control_big_head_arms_up", "fail", "a head so big the raised arms go through it (control, plain rig: must fail)")
def _():
    def extra(rig, parts):
        arm_root_near_head(rig, parts)
        return {"WHOLE_PARTS": True}
    return person(extra, sections=6)


@case("mixamo_headtop_end_bone_big_head_arms_up", "fail", "the same on a rig with Mixamo's HeadTop_End: a center child of the head makes the head part of the 'trunk', and upper arms in the head a joint")
def _():
    def extra(rig, parts):
        arm_root_near_head(rig, parts)
        add_head_top_end(rig)
        def after(report):
            apply_named_pose(rig, "arms_up")
            render("mixamo_arms_up", VIEWS=["front", "front_left"], COLUMNS=2)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra, sections=6)


def half_shell(name, center, rx, ry, z0, z1, a0=-170, a1=-10, segments=16, rows=8):
    """A one-sided plate around the front: an arc from angle a0 to a1 in the XY plane, between two heights."""
    verts, faces = [], []
    for j in range(rows + 1):
        z = z0 + (z1 - z0) * j / rows
        for i in range(segments + 1):
            a = math.radians(a0 + (a1 - a0) * i / segments)
            verts.append((center[0] + rx * math.cos(a), center[1] + ry * math.sin(a), z))
    for j in range(rows):
        for i in range(segments):
            k = j * (segments + 1) + i
            faces.append((k, k + 1, k + segments + 2, k + segments + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def breastplate(rig, parts, poke):
    bpy.data.objects.remove(parts["Torso"], do_unlink=True)
    t = on(paint(capsule("Torso", (0, 0, 0.92), (0, 0, 1.36), 0.16, 0.17, segments=24, squash_y=0.68, sections=8, rings=6), SKIN), rig, "hips", "spine", "chest")
    plate = half_shell("Breastplate", (0, 0), 0.178, 0.135, 1.05, 1.38, a0=-150, a1=-30)
    on(paint(plate, GRAY), rig, "spine", "chest")
    if poke:
        bump(t, (0.04, -0.11, 1.22), 0.09, (0.0, -0.09, 0.0))


@case("half_shell_chest_through_breastplate", "fail", "a one-sided breastplate, open at the back: the chest comes through it. Inside tests need three looks along the axes to meet its back: from the chest, only one does")
def _():
    def extra(rig, parts):
        breastplate(rig, parts, True)
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Breastplate"], "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("half_shell_clean_control", "pass", "the same plate with the chest under it")
def _():
    def extra(rig, parts):
        breastplate(rig, parts, False)
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Breastplate"], "POSES": False}
    return person(extra)


@case("half_shell_shin_through_greave", "fail", "a one-sided greave on the shin, open at the back: the shin comes through it")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        leg = dense_leg(rig, segments=24, sections=20)
        g = half_shell("Greave", (0.10, 0), 0.075, 0.075, 0.12, 0.46, a0=-160, a1=-20)
        on(paint(g, GRAY), rig, "shin.L")
        bump(leg, (0.10, -0.06, 0.28), 0.08, (0.0, -0.07, 0.0))
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Greave"], "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


def fused_dog_legs_one_skin(height_of_web=True):
    """A one-skin dog whose front legs are one mass down to the knee; below that, two legs."""
    joints = {"pelvis": ((0, 0.28, 0.45), (0.11, 0.11), None), "belly": ((0, 0.05, 0.47), (0.12, 0.13), "pelvis"),
              "chest": ((0, -0.2, 0.48), (0.12, 0.12), "belly"), "neck": ((0, -0.34, 0.58), (0.06, 0.06), "chest"),
              "skull": ((0, -0.44, 0.66), (0.08, 0.08), "neck"), "nose": ((0, -0.55, 0.64), (0.04, 0.04), "skull"),
              "tail1": ((0, 0.43, 0.48), (0.03, 0.03), "pelvis"), "tail2": ((0, 0.55, 0.45), (0.02, 0.02), "tail1"),
              "tail3": ((0, 0.65, 0.40), (0.012, 0.012), "tail2")}
    bones = [("hips", "pelvis", "belly", None), ("spine", "belly", "chest", "hips"), ("neck", "neck", "skull", "spine"),
             ("head", "skull", "nose", "neck"), ("tail.01", "tail1", "tail2", "hips"), ("tail.02", "tail2", "tail3", "tail.01")]
    for end, y, parent, bone_parent in (("hind", 0.26, "pelvis", "hips"), ("fore", -0.2, "chest", "spine")):
        for side, x in (("L", 1), ("R", -1)):
            fused = end == "fore"
            joints.update({
                f"{end}_hip.{side}": ((0.03 * x if fused else 0.07 * x, y, 0.31), (0.05 if fused else 0.04, 0.05 if fused else 0.04), parent),
                f"{end}_knee.{side}": ((0.035 * x if fused else 0.09 * x, y, 0.2), (0.05 if fused else 0.035, 0.05 if fused else 0.035), f"{end}_hip.{side}"),
                f"{end}_ankle.{side}": ((0.09 * x, y, 0.05), (0.028, 0.028), f"{end}_knee.{side}"),
                f"{end}_toe.{side}": ((0.09 * x, y - 0.05, 0.028), (0.028, 0.028), f"{end}_ankle.{side}"),
            })
            bones += [(f"{end}_thigh.{side}", f"{end}_hip.{side}", f"{end}_knee.{side}", bone_parent),
                      (f"{end}_shin.{side}", f"{end}_knee.{side}", f"{end}_ankle.{side}", f"{end}_thigh.{side}"),
                      (f"{end}_paw.{side}", f"{end}_ankle.{side}", f"{end}_toe.{side}", f"{end}_shin.{side}")]
    path = os.path.join(SCRIPTS, "build_body.py")
    namespace = {"__file__": path, "NAME": "Dog", "JOINTS": joints, "BONES": bones, "SUBDIVISIONS": 0}
    exec(compile(open(path).read(), path, "exec"), namespace)
    return bpy.data.objects[namespace["result"]["mesh"]], bpy.data.objects[namespace["result"]["armature"]]


@case("fused_dog_front_legs_above_sample_level", "fail", "a one-skin dog whose front legs are one mass from the chest down past the knee: the check looks for separate legs at one height only")
def _():
    body, rig = fused_dog_legs_one_skin()
    paint(body, BROWN)
    return {"TARGETS": [body.name], "ARMATURE": rig.name, "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("dog_clean_control", "pass", "the repo's clean dog")
def _():
    body, rig = quadruped.build()
    return {"TARGETS": [body.name], "ARMATURE": rig.name}


@case("fused_legs_hidden_by_low_tail", "fail", "front legs fused at the check's level, and a tail hanging to that level: the tail's section makes up the count")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        for name in ("foreLeg.L", "foreLeg.R"):
            bpy.data.objects.remove(parts[name], do_unlink=True)
        for side in ("L", "R"):
            on(paint(capsule(f"foreLeg.{side}", bones[f"fore_thigh.{side}"].head_local, bones[f"fore_shin.{side}"].tail_local, 0.11, 0.095, segments=8), BROWN), rig, f"fore_thigh.{side}", f"fore_shin.{side}")
        bpy.data.objects.remove(parts["Tail"], do_unlink=True)
        on(paint(capsule("Tail", (0, 0.38, 0.48), (0, 0.66, 0.10), 0.03, 0.012, segments=6, rings=2), BROWN), rig, "tail.01", "tail.02")
        return {"WHOLE_PARTS": True, "ALLOW_CROSSING": ["foreLeg.L+foreLeg.R"], "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return animal(extra)


@case("fused_legs_control_no_tail", "fail", "the same fused legs with a short tail (control: must fail)")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        for name in ("foreLeg.L", "foreLeg.R"):
            bpy.data.objects.remove(parts[name], do_unlink=True)
        for side in ("L", "R"):
            on(paint(capsule(f"foreLeg.{side}", bones[f"fore_thigh.{side}"].head_local, bones[f"fore_shin.{side}"].tail_local, 0.11, 0.095, segments=8), BROWN), rig, f"fore_thigh.{side}", f"fore_shin.{side}")
        return {"WHOLE_PARTS": True, "ALLOW_CROSSING": ["foreLeg.L+foreLeg.R"]}
    return animal(extra)


@case("spider_no_coxa_two_legs_fused", "fail", "a spider on one body bone: two legs fused into one at the ground. One body bone makes all its legs one chain, and no separate-legs check runs")
def _():
    rig = spider_rig(coxa=False)
    spider(rig, coxa=False)
    # Bring the tips of two legs together.
    for side in ("L",):
        a, b = bpy.data.objects[f"Tar1.{side}"], bpy.data.objects[f"Tar2.{side}"]
        for o, sign in ((a, -1), (b, 1)):
            for v in o.data.vertices:
                if v.co.z < 0.07:
                    v.co.y = 0.0 + (v.co.y - v.co.y) + (-0.02 if sign < 0 else -0.02)
                    v.co.x = 0.34 + (v.co.x - 0.34) * 0.6
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "ALLOW_CROSSING": ["Tar1.L+Tar2.L"], "_render": {"VIEWS": ["front", "top", "left", "front_left"], "COLUMNS": 2}}


@case("long_tail_control_hand_through_nothing", "pass", "a horse with a long tail chain, tail set well clear of the barrel by its root")
def _():
    rig = horse_rig(tail_bones=10)
    horse(rig, tail_bones=10)
    bpy.data.objects.remove(bpy.data.objects["TailP"], do_unlink=True)
    # A tail starting past the barrel's end, each bone a section.
    obj = capsule("TailP", (0, 0.655, 0.93), (0, 1.15, 0.45), 0.035, 0.02, segments=8, sections=20)
    on(paint(obj, DARK), rig, *[f"tail.{k:02d}" for k in range(10)])
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


@case("long_tail_fused_front_legs", "fail", "the same horse, its front legs fused at the check's level: the trunk search walks down the tail, so the front legs make one chain and the check counts wrong")
def _():
    rig = horse_rig(tail_bones=10)
    horse(rig, tail_bones=10)
    bpy.data.objects.remove(bpy.data.objects["TailP"], do_unlink=True)
    obj = capsule("TailP", (0, 0.655, 0.93), (0, 1.15, 0.45), 0.035, 0.02, segments=8, sections=20)
    on(paint(obj, DARK), rig, *[f"tail.{k:02d}" for k in range(10)])
    for s in ("L", "R"):
        o = bpy.data.objects[f"foreLeg.{s}"]
        for v in o.data.vertices:
            v.co.x *= 0.45
    print("  chains:", [[b.name for b in c] for c in helpers.leg_chains(rig, helpers.map_roles(rig))])
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "ALLOW_CROSSING": ["foreLeg.L+foreLeg.R"], "_render": {"VIEWS": ["front", "left"]}}


@case("flipped_trouser_normals", "fail", "a trouser leg inside out: from outside the player sees the leg through it. Only what covers the head is checked for this")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        dense_leg(rig)
        t = trouser(rig)
        t.data.flip_normals()
        def after(report):
            v = _validate(["Trouser.L"])
            print("  validate_mesh on it:", v.get("passed"), {k: x for k, x in v.get("issues", {}).items()})
        return {"WHOLE_PARTS": True, "POSES": False, "_after": after, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


def _validate(names):
    path = SCRIPTS + "/validate_mesh.py"
    ns = {"__file__": path, "TARGETS": names}
    exec(compile(open(path).read(), path, "exec"), ns)
    return ns["result"]


@case("hair_cap_a_little_low_closed", "pass", "the repo's hair cap, whose bottom is 2.5 cm lower: past the head bone's base, it holds it, and its area is less than the head's")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hair", [(0.0, 1.63), (0.1, 1.63), (0.113, 1.67), (0.113, 1.71), (0.1, 1.78), (0.0, 1.81)], segments=16), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


@case("hair_cap_repo_control", "pass", "the repo's hair cap")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=16), DARK), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("bob_hair_on_one_skin_two_sided", "pass", "one skin with bob-length hair, open underneath, drawn two-sided: the hair holds the head bone's base")
def _():
    body, rig = mannequin.build()
    paint(body, SKIN)
    verts_z = [v.co.z for v in body.data.vertices]
    bm = bmesh.new()
    segs = 32
    rows = [(0.135, 1.52), (0.135, 1.60), (0.13, 1.68), (0.115, 1.74), (0.08, 1.785), (0.0, 1.80)]
    loops = []
    for r, z in rows:
        if r <= 0:
            loops.append(bm.verts.new((0, 0, z)))
        else:
            loops.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs), r * math.sin(2 * math.pi * s / segs), z)) for s in range(segs)])
    for a, b in zip(loops, loops[1:]):
        for s in range(segs):
            if isinstance(b, list):
                bm.faces.new((a[s], a[(s + 1) % segs], b[(s + 1) % segs], b[s]))
            else:
                bm.faces.new((a[s], a[(s + 1) % segs], b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    doomed = [f for f in bm.faces if f.calc_center_median().y < -0.03 and abs(f.calc_center_median().x) < 0.09 and f.calc_center_median().z < 1.70]
    bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    mesh = bpy.data.meshes.new("Hair")
    bm.to_mesh(mesh)
    bm.free()
    hair = bpy.data.objects.new("Hair", mesh)
    bpy.context.scene.collection.objects.link(hair)
    on(paint(hair, DARK), rig, "head")
    return {"TARGETS": ["Body", "Hair"], "ARMATURE": rig.name, "TWO_SIDED": ["Hair"], "ALLOW_HIDDEN": ["Body<Hair"], "SINGLE_LAYER": False, "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "back", "left", "front_left"], "COLUMNS": 2}}


if __name__ == "__main__":
    main()
