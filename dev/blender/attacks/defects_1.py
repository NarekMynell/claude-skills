# Real defects that should fail. First batch: floating, poses, small covers, hems, rings, shallow patches, hats.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *


def raise_z(obj, dz):
    for v in obj.data.vertices:
        v.co.z += dz


def move(obj, offset):
    offset = Vector(offset)
    for v in obj.data.vertices:
        v.co += offset


# --- Floating ----------------------------------------------------------------------------------------------------------

@case("float_neck_and_head_group", "fail", "neck and head overlap each other and hang 9 cm above the torso")
def _():
    def extra(rig, parts):
        raise_z(parts["Neck"], 0.25)
        raise_z(parts["Head"], 0.25)
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"], "COLOR": "OBJECT"}}
    return person(extra)


@case("float_arm_saved_by_bracelet", "fail", "the whole arm hangs 12 cm from the shoulder; a bracelet set into it makes it 'cross' something")
def _():
    def extra(rig, parts):
        move(parts["Arm.L"], (0.15, 0.0, 0.02))
        b = rig.data.bones["forearm.L"]
        c = b.head_local.lerp(b.tail_local, 0.6) + Vector((0.15, 0, 0.02))
        on(paint(capsule("Bracelet", c - Vector((0.012, 0, 0)), c + Vector((0.012, 0, 0)), 0.05, 0.05, segments=12), BLUE), rig, "forearm.L")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "top"]}}
    return person(extra)


@case("float_head_inside_sword_bbox", "fail", "a head hanging 9 cm above the torso, inside the bounding box of a diagonal sword on the back")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Head"], do_unlink=True)
        bpy.data.objects.remove(parts["Neck"], do_unlink=True)
        on(paint(capsule("Head", (0, 0, 1.72), (0, 0, 1.78), 0.1, 0.1, segments=12), SKIN), rig, "head")
        on(paint(capsule("Sword", (-0.40, 0.11, 0.95), (0.40, 0.11, 2.0), 0.03, 0.02, segments=6), GRAY), rig, "chest")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


@case("float_clean_control", "fail", "the same head hanging, with no sword (control: must fail)")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Head"], do_unlink=True)
        bpy.data.objects.remove(parts["Neck"], do_unlink=True)
        on(paint(capsule("Head", (0, 0, 1.72), (0, 0, 1.78), 0.1, 0.1, segments=12), SKIN), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


def plane(name, x0, x1, z0, z1, y, nx=4, nz=6):
    verts, faces = [], []
    for j in range(nz + 1):
        for i in range(nx + 1):
            verts.append((x0 + (x1 - x0) * i / nx, y, z0 + (z1 - z0) * j / nz))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


@case("float_largest_part_cape", "fail", "a cape, the largest part, hangs 13 cm behind the back touching nothing")
def _():
    def extra(rig, parts):
        cape = paint(plane("Cape", -0.5, 0.5, 0.45, 1.5, 0.25), RED)
        on(cape, rig, "chest")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Cape"], "_render": {"VIEWS": ["back", "left", "front_left"]}}
    return person(extra)


# --- A joint that opens, when the parts don't cross at rest -------------------------------------------------------------

@case("joint_gap_at_rest_then_flies_off", "fail", "a hand part 6 mm past the arm's end, arm rigid on the upper arm: bending the elbow takes the hand away (control of the repo's loose_hand, without the crossing)")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
        a, b = bones["upper_arm.L"].head_local, bones["forearm.L"].tail_local
        axis = (b - a).normalized()
        on(paint(capsule("Arm.L", a, b, 0.055, 0.035, segments=8), SKIN), rig, "upper_arm.L")
        start = b + axis * (0.035 + 0.006 + 0.04)
        on(paint(capsule("HandPart", start, start + axis * 0.05, 0.04, 0.03, segments=8), SKIN), rig, "hand.L")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front"]}}
    return person(extra)


# --- A part out the far side, in a pose ---------------------------------------------------------------------------------

@case("pose_thigh_top_out_of_the_back_in_squat", "fail", "the leg part runs 14 cm above the hip joint inside the torso: in a squat its top swings out through the back")
def _():
    def extra(rig, parts):
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Leg.{side}"], do_unlink=True)
            hip, ankle = rig.data.bones[f"thigh.{side}"].head_local, rig.data.bones[f"shin.{side}"].tail_local
            on(paint(capsule(f"Leg.{side}", hip + Vector((0, 0, 0.14)), ankle, 0.07, 0.045, segments=8, sections=6), SKIN), rig, f"thigh.{side}", f"shin.{side}")
        def after(report):
            apply_named_pose(bpy.data.objects[rig.name], "squat")
            render("pose_thigh_top_squat", VIEWS=["left", "back", "back_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("pose_arm_root_out_of_the_shoulder_arms_down", "fail", "the arm part starts near the spine, inside the chest: with arms down its inner end sticks up through the shoulder")
def _():
    def extra(rig, parts):
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            s, h = rig.data.bones[f"upper_arm.{side}"].head_local, rig.data.bones[f"hand.{side}"].tail_local
            on(paint(capsule(f"Arm.{side}", (0.03 * sign, 0, 1.42), h, 0.05, 0.035, segments=8, sections=8), SKIN), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        def after(report):
            apply_named_pose(rig, "arms_down")
            render("pose_arm_root_arms_down", VIEWS=["front", "left", "front_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


def open_lathe(name, profile, center=(0.0, 0.0), segments=16, close_top=True):
    bm = bmesh.new()
    rings = []
    for radius, z in profile:
        if radius <= 0.0:
            rings.append(bm.verts.new((center[0], center[1], z)))
        else:
            rings.append([bm.verts.new((center[0] + radius * math.cos(2 * math.pi * s / segments), center[1] + radius * math.sin(2 * math.pi * s / segments), z)) for s in range(segments)])
    for lower, upper in zip(rings, rings[1:]):
        for s in range(segments):
            if isinstance(lower, list) and isinstance(upper, list):
                bm.faces.new((lower[s], lower[(s + 1) % segments], upper[(s + 1) % segments], upper[s]))
            elif isinstance(upper, list):
                bm.faces.new((lower, upper[s], upper[(s + 1) % segments]))
            else:
                bm.faces.new((lower[s], lower[(s + 1) % segments], upper))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


@case("pose_thigh_through_skirt_parts_body", "fail", "a skirt weighted to the hips, on a body of parts: in a squat each thigh goes through its front wall")
def _():
    def extra(rig, parts):
        skirt = paint(open_lathe("Skirt", [(0.20, 0.62), (0.19, 0.80), (0.17, 0.96), (0.15, 1.04), (0.0, 1.10)], segments=20), RED)
        on(skirt, rig, "hips")
        def after(report):
            apply_named_pose(rig, "squat")
            render("pose_thigh_through_skirt_squat", VIEWS=["left", "front", "front_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True, "TWO_SIDED": ["Skirt"], "_after": after}
    return person(extra)


# --- Small covers -------------------------------------------------------------------------------------------------------

def dense_leg(rig, side="L", segments=16, sections=14, ra=0.078, rb=0.045):
    hip, ankle = rig.data.bones[f"thigh.{side}"].head_local, rig.data.bones[f"shin.{side}"].tail_local
    return on(paint(capsule(f"Leg.{side}", hip, ankle, ra, rb, segments=segments, sections=sections), SKIN), rig, f"thigh.{side}", f"shin.{side}")


@case("small_cover_knee_through_kneepad", "fail", "a knee comes out through the middle of a knee pad, by 2 cm: the pad is too small a share of the leg for the check to look")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        leg = dense_leg(rig)
        knee = rig.data.bones["shin.L"].head_local
        pad = capsule("Kneepad", (knee.x, knee.y - 0.05, knee.z - 0.03), (knee.x, knee.y - 0.05, knee.z + 0.03), 0.055, 0.055, segments=16)
        for v in pad.data.vertices:
            v.co.y = knee.y - 0.05 + (v.co.y - (knee.y - 0.05)) * 0.55
        on(paint(pad, BLUE), rig, "thigh.L", "shin.L")
        bump(leg, (knee.x, knee.y - 0.05, knee.z), 0.05, (0.0, -0.065, 0.0))
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"], "CLOSEUPS": [{"label": "knee", "center": [knee.x, knee.y - 0.06, knee.z], "size": 0.3, "view": "front_left"}]}}
    return person(extra)


@case("small_cover_kneepad_clean_control", "pass", "the same pad with the knee under it")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        dense_leg(rig)
        knee = rig.data.bones["shin.L"].head_local
        pad = capsule("Kneepad", (knee.x, knee.y - 0.05, knee.z - 0.03), (knee.x, knee.y - 0.05, knee.z + 0.03), 0.055, 0.055, segments=16)
        for v in pad.data.vertices:
            v.co.y = knee.y - 0.05 + (v.co.y - (knee.y - 0.05)) * 0.55
        on(paint(pad, BLUE), rig, "thigh.L", "shin.L")
        return {"WHOLE_PARTS": True, "POSES": False}
    return person(extra)


@case("small_cover_nose_through_mask", "fail", "the nose of a dense head comes out through a face mask")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Head"], do_unlink=True)
        head = on(paint(capsule("Head", (0, 0, 1.62), (0, 0, 1.68), 0.105, 0.105, segments=24, rings=8, sections=6), SKIN), rig, "head")
        mask = capsule("Mask", (-0.04, -0.075, 1.59), (0.04, -0.075, 1.59), 0.05, 0.05, segments=16, rings=5)
        on(paint(mask, DARK), rig, "head")
        bump(head, (0, -0.105, 1.60), 0.05, (0.0, -0.05, 0.0))
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left"], "CLOSEUPS": [{"label": "face", "center": [0, -0.1, 1.6], "size": 0.3, "view": "front_left"}]}}
    return person(extra)


# --- Hems, rings, shallow patches ---------------------------------------------------------------------------------------

def trouser(rig, side="L", segments=16, sections=14, ra=0.105, rb=0.075):
    hip, ankle = rig.data.bones[f"thigh.{side}"].head_local, rig.data.bones[f"shin.{side}"].tail_local
    end = hip.lerp(ankle, 0.85)
    return on(paint(capsule(f"Trouser.{side}", hip, end, ra, rb, segments=segments, sections=sections), BLUE), rig, f"thigh.{side}", f"shin.{side}")


@case("hem_shin_through_trouser_from_the_hem_up", "fail", "the shin comes out through the front of the trouser leg, from the hem up to 20 cm above it, joined to the bare ankle")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        leg = dense_leg(rig)
        trouser(rig)
        for v in leg.data.vertices:
            if v.co.z < 0.42 and v.co.y < -0.01:
                v.co.y -= 0.075 * min(1.0, (0.42 - v.co.z) / 0.04)
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"], "CLOSEUPS": [{"label": "shin", "center": [0.1, -0.05, 0.3], "size": 0.5, "view": "front_left"}]}}
    return person(extra)


@case("hem_clean_control", "pass", "the same trouser leg with the shin inside")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        dense_leg(rig)
        trouser(rig)
        return {"WHOLE_PARTS": True, "POSES": False}
    return person(extra)


@case("ring_knee_wider_than_trouser_all_around", "fail", "the knee is wider than the trouser leg all the way around: a band of skin shows between two lengths of trouser")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        leg = dense_leg(rig)
        trouser(rig)
        knee = rig.data.bones["shin.L"].head_local
        for v in leg.data.vertices:
            if abs(v.co.z - knee.z) < 0.05:
                d = Vector((v.co.x - knee.x, v.co.y - knee.y, 0))
                if d.length > 1e-4:
                    v.co.x = knee.x + d.x / d.length * 0.115
                    v.co.y = knee.y + d.y / d.length * 0.115
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("ring_elbow_wider_than_sleeve_all_around", "fail", "the elbow is wider than the sleeve all the way around")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
        bones = rig.data.bones
        a, b = bones["upper_arm.L"].head_local, bones["hand.L"].tail_local
        arm = on(paint(capsule("Arm.L", a, b, 0.05, 0.035, segments=16, sections=14), SKIN), rig, "upper_arm.L", "forearm.L", "hand.L")
        wrist = bones["forearm.L"].tail_local
        on(paint(capsule("Sleeve", a, a.lerp(wrist, 0.85), 0.075, 0.05, segments=16, sections=12), RED), rig, "upper_arm.L", "forearm.L")
        elbow = bones["forearm.L"].head_local
        axis = (b - a).normalized()
        for v in arm.data.vertices:
            along = (v.co - elbow).dot(axis)
            if abs(along) < 0.03:
                radial = (v.co - elbow) - axis * along
                if radial.length > 1e-4:
                    v.co = elbow + axis * along + radial.normalized() * 0.085
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "front_left", "top"]}}
    return person(extra)


@case("shallow_wide_thigh_patch_through_trouser", "fail", "skin comes out of the trousers by 7 mm over a patch 25 cm long and 8 cm wide: under the graze, plainly visible")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        hip, ankle = rig.data.bones["thigh.L"].head_local, rig.data.bones["shin.L"].tail_local
        leg = on(paint(capsule("Leg.L", hip, ankle, 0.078, 0.045, segments=32, sections=24), SKIN), rig, "thigh.L", "shin.L")
        tr = trouser(rig, segments=32, sections=24)
        tree_src = tr
        # Trouser radius at a height: follows the capsule's linear taper over 85% of the leg.
        axis = (hip.lerp(ankle, 0.85) - hip)
        for v in leg.data.vertices:
            t = (v.co - hip).dot(axis.normalized()) / axis.length
            if 0.25 < t < 0.60:
                center = hip + axis * t
                radial = v.co - center
                radial -= axis.normalized() * radial.dot(axis.normalized())
                if radial.length > 1e-4 and radial.normalized().y < -0.75:
                    r = 0.105 + (0.075 - 0.105) * t
                    v.co = center + radial.normalized() * (r + 0.007)
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"], "CLOSEUPS": [{"label": "thigh", "center": [0.1, -0.07, 0.62], "size": 0.5, "view": "front"}]}}
    return person(extra)


# --- Hats ---------------------------------------------------------------------------------------------------------------

def flap_hat(name="Ushanka"):
    hat = lathe(name, [(0.0, 1.66), (0.125, 1.66), (0.12, 1.70), (0.095, 1.74), (0.0, 1.76)], segments=16)
    # Two ear flaps pulled down from the band, in one mesh: the hat's lowest point is under the chin.
    for v in hat.data.vertices:
        if abs(v.co.z - 1.66) < 1e-4 and abs(v.co.y) < 0.03 and abs(v.co.x) > 0.1:
            v.co.z = 1.47
    return hat


@case("hat_head_through_crown_hat_with_ear_flaps", "fail", "the head comes 2.5 cm out through the crown of a hat whose ear flaps hang below the chin: 'starts above the hat's lowest point' makes the head an ornament")
def _():
    def extra(rig, parts):
        on(paint(flap_hat(), BROWN), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "top", "front_left"], "COLUMNS": 2}}
    return person(extra)


@case("hat_head_through_crown_same_hat_no_flaps_control", "fail", "the same crown without flaps (control: must fail)")
def _():
    def extra(rig, parts):
        on(paint(lathe("Cap", [(0.0, 1.66), (0.125, 1.66), (0.12, 1.70), (0.095, 1.74), (0.0, 1.76)], segments=16), BROWN), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


def fits_hat(name="Hat"):
    return lathe(name, [(0.0, 1.70), (0.2, 1.70), (0.2, 1.705), (0.13, 1.71), (0.125, 1.82), (0.0, 1.86)])


@case("hat_ear_through_hat_ornament", "fail", "animal ears set in the head come out through the crown: the guide says this needs ALLOW_CROSSING")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), BROWN), rig, "head")
        for side, s in (("L", 1), ("R", -1)):
            on(paint(capsule(f"Ear.{side}", (0.06 * s, 0, 1.74), (0.11 * s, 0, 1.97), 0.022, 0.012, segments=8), SKIN), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("hat_horn_through_helmet_ornament", "fail", "a horn set in the skull comes out through a closed helmet")
def _():
    def extra(rig, parts):
        on(paint(lathe("Helmet", [(0.0, 1.62), (0.125, 1.62), (0.125, 1.75), (0.09, 1.82), (0.0, 1.84)], segments=20), GRAY), rig, "head")
        on(paint(capsule("Horn", (0.05, -0.02, 1.74), (0.09, -0.08, 1.96), 0.03, 0.006, segments=8), YELLOW), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("hat_hair_quiff_through_crown", "fail", "a hair piece named Quiff comes through the crown: not a hair word, and it starts above the hat's lowest point")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hat", [(0.0, 1.69), (0.2, 1.69), (0.2, 1.695), (0.13, 1.70), (0.125, 1.77), (0.0, 1.80)]), BROWN), rig, "head")
        on(paint(lathe("Quiff", [(0.0, 1.72), (0.10, 1.72), (0.10, 1.80), (0.06, 1.88), (0.0, 1.90)], segments=16), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("hat_hair_same_named_hair_control", "fail", "the same, named Hair (control: must fail)")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hat", [(0.0, 1.69), (0.2, 1.69), (0.2, 1.695), (0.13, 1.70), (0.125, 1.77), (0.0, 1.80)]), BROWN), rig, "head")
        on(paint(lathe("Hair", [(0.0, 1.72), (0.10, 1.72), (0.10, 1.80), (0.06, 1.88), (0.0, 1.90)], segments=16), DARK), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("hat_hair_through_crown_merged", "fail", "the same in one merged mesh: no name to read, so 'Hair' is an ornament")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hat", [(0.0, 1.69), (0.2, 1.69), (0.2, 1.695), (0.13, 1.70), (0.125, 1.77), (0.0, 1.80)]), BROWN), rig, "head")
        on(paint(lathe("Hair", [(0.0, 1.72), (0.10, 1.72), (0.10, 1.80), (0.06, 1.88), (0.0, 1.90)], segments=16), DARK), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra, merged=True)


@case("hat_covers_off_head_through_crown", "fail", "COVERS_FROM_ABOVE=[] because the character also has a tiara: the head through the hat's crown is no longer seen")
def _():
    def extra(rig, parts):
        on(paint(lathe("Cap", [(0.0, 1.66), (0.125, 1.66), (0.12, 1.70), (0.095, 1.74), (0.0, 1.76)], segments=16), BROWN), rig, "head")
        return {"WHOLE_PARTS": True, "COVERS_FROM_ABOVE": []}
    return person(extra)


@case("hat_modular_head_variants_no_top", "fail", "a modular character: heads and hats are all variants, so the check finds no head to cover and no hat: HeadB comes through the crown")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Head"], do_unlink=True)
        on(paint(capsule("HeadA", (0, 0, 1.62), (0, 0, 1.68), 0.095, 0.095, segments=12), SKIN), rig, "head")
        on(paint(capsule("HeadB", (0, 0, 1.62), (0, 0, 1.70), 0.115, 0.115, segments=12), GREEN), rig, "head")
        on(paint(lathe("HatA", [(0.0, 1.68), (0.2, 1.68), (0.2, 1.685), (0.11, 1.69), (0.105, 1.76), (0.0, 1.79)]), BROWN), rig, "head")
        on(paint(fits_hat("HatB"), BROWN), rig, "head")
        return {"WHOLE_PARTS": True, "PART_GROUPS": {"head": ["HeadA", "HeadB"], "hat": ["HatB", "HatA"]}, "ALLOW_HIDDEN": ["HeadA<HatA", "HeadA<HatB", "HeadB<HatA", "HeadB<HatB"], "_render": {"VIEWS": ["front", "left"], "TARGETS": ["HeadB", "HatA", "Neck", "Torso"]}}
    return person(extra)


@case("hat_modular_control_head_fixed", "fail", "the same head and hat with the head not a variant (control: must fail)")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Head"], do_unlink=True)
        on(paint(capsule("HeadB", (0, 0, 1.62), (0, 0, 1.70), 0.115, 0.115, segments=12), GREEN), rig, "head")
        on(paint(lathe("HatA", [(0.0, 1.68), (0.2, 1.68), (0.2, 1.685), (0.11, 1.69), (0.105, 1.76), (0.0, 1.79)]), BROWN), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


def penguin_rig():
    return make_rig("BirdRig", [
        ("body", (0, 0, 0.12), (0, 0, 0.45), None),
        ("neck", (0, 0, 0.45), (0, 0, 0.55), "body"),
        ("skull", (0, 0, 0.55), (0, 0, 0.72), "neck"),
        ("flipper.L", (0.12, 0, 0.42), (0.17, 0, 0.22), "body"),
        ("flipper.R", (-0.12, 0, 0.42), (-0.17, 0, 0.22), "body"),
        ("leg.L", (0.06, 0, 0.14), (0.06, 0, 0.03), "body"),
        ("leg.R", (-0.06, 0, 0.14), (-0.06, 0, 0.03), "body"),
        ("foot.L", (0.06, 0, 0.03), (0.06, -0.08, 0.015), "leg.L"),
        ("foot.R", (-0.06, 0, 0.03), (-0.06, -0.08, 0.015), "leg.R"),
    ])


def penguin(rig):
    on(paint(capsule("Body", (0, 0, 0.22), (0, 0, 0.42), 0.14, 0.11, segments=16), DARK), rig, "body")
    on(paint(capsule("HeadPart", (0, 0, 0.60), (0, 0, 0.66), 0.085, 0.085, segments=16), DARK), rig, "skull")
    on(paint(capsule("Beak", (0, -0.07, 0.63), (0, -0.14, 0.62), 0.02, 0.008, segments=8), YELLOW), rig, "skull")
    for s, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Flipper.{s}", (0.125 * x, 0, 0.40), (0.175 * x, 0, 0.22), 0.03, 0.02, segments=8), DARK), rig, f"flipper.{s}")
        on(paint(capsule(f"Leg.{s}", (0.06 * x, 0, 0.14), (0.06 * x, 0, 0.03), 0.025, 0.02, segments=8), YELLOW), rig, f"leg.{s}")
        on(paint(capsule(f"Foot.{s}", (0.06 * x, 0, 0.02), (0.06 * x, -0.08, 0.02), 0.02, 0.02, segments=8), YELLOW), rig, f"foot.{s}")


@case("creature_penguin_clean_control", "pass", "a clean penguin of parts, head bone named skull")
def _():
    rig = penguin_rig()
    penguin(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("creature_skull_through_hat_bone_named_skull", "fail", "a penguin's head comes out of a small hat's crown; its head bone is named skull, so there is no head role and no hat")
def _():
    rig = penguin_rig()
    penguin(rig)
    on(paint(lathe("Hat", [(0.0, 0.70), (0.13, 0.70), (0.13, 0.705), (0.075, 0.71), (0.07, 0.725), (0.0, 0.735)], segments=20), RED), rig, "skull")
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}


@case("creature_skull_control_bone_named_head", "fail", "the same with the bone named head (control: must fail)")
def _():
    rig = penguin_rig()
    penguin(rig)
    rig.data.bones["skull"].name = "head"
    # The vertex groups follow the rename.
    on(paint(lathe("Hat", [(0.0, 0.70), (0.13, 0.70), (0.13, 0.705), (0.075, 0.71), (0.07, 0.725), (0.0, 0.735)], segments=20), RED), rig, "head")
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


@case("big_sword_through_torso_same_bone", "fail", "a greatsword on the chest bone comes through the torso and out of the belly: its area is larger than the torso's, so 'goes right through' isn't asked")
def _():
    def extra(rig, parts):
        s = capsule("Sword", (0.0, 0.28, 2.0), (0.0, -0.30, 0.55), 0.16, 0.10, segments=8)
        for v in s.data.vertices:
            v.co.x *= 1.0
        on(paint(s, GRAY), rig, "chest")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("small_sword_through_torso_control", "fail", "a smaller sword the same way (control: must fail)")
def _():
    def extra(rig, parts):
        on(paint(capsule("Sword", (0.0, 0.20, 1.75), (0.0, -0.20, 0.75), 0.03, 0.02, segments=8), GRAY), rig, "chest")
        return {"WHOLE_PARTS": True, "POSES": False}
    return person(extra)


if __name__ == '__main__':
    main()
