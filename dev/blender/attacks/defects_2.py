# Real defects that should fail. Second batch.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
from defects_1 import raise_z, move, plane, open_lathe, dense_leg, trouser, fits_hat, flap_hat, penguin_rig, penguin
CASES.clear()


@case("float_arms_saved_by_bracelets", "fail", "both arms hang 12 cm from the shoulders; a bracelet set into each makes them cross something")
def _():
    def extra(rig, parts):
        for side, sign in (("L", 1), ("R", -1)):
            move(parts[f"Arm.{side}"], (0.15 * sign, 0.0, 0.0))
            b = rig.data.bones[f"forearm.{side}"]
            axis = (b.tail_local - b.head_local).normalized()
            c = b.head_local.lerp(b.tail_local, 0.6) + Vector((0.15 * sign, 0, 0))
            on(paint(capsule(f"Bracelet.{side}", c - axis * 0.012, c + axis * 0.012, 0.052, 0.052, segments=12), BLUE), rig, f"forearm.{side}")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "top"]}}
    return person(extra)


@case("float_largest_part_cape_high", "fail", "a cape, the largest part, hangs 13 cm behind the back touching nothing, above the legs' reach")
def _():
    def extra(rig, parts):
        cape = paint(plane("Cape", -0.62, 0.62, 0.92, 1.62, 0.25), RED)
        on(cape, rig, "chest")
        print("AREAS", {k: round(sum(p.area for p in o.data.polygons), 3) for k, o in list(parts.items()) + [("Cape", cape)]})
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Cape"], "_render": {"VIEWS": ["back", "left", "front_left"]}}
    return person(extra)


@case("float_second_cape_control", "fail", "the same cape smaller than the torso (control: must fail)")
def _():
    def extra(rig, parts):
        on(paint(plane("Cape", -0.2, 0.2, 0.95, 1.5, 0.25), RED), rig, "chest")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Cape"]}
    return person(extra)


@case("float_small_gap_2cm_every_hand", "fail", "both hands hang 2.2 cm past the wrists, in the air: under 1.5% of the height")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            a, w = bones[f"upper_arm.{side}"].head_local, bones[f"forearm.{side}"].tail_local
            axis = (w - a).normalized()
            on(paint(capsule(f"Arm.{side}", a, w, 0.055, 0.035, segments=8), SKIN), rig, f"upper_arm.{side}", f"forearm.{side}")
            start = w + axis * (0.035 + 0.022 + 0.04)
            on(paint(capsule(f"Hand.{side}", start, start + axis * 0.05, 0.04, 0.03, segments=8), SKIN), rig, f"hand.{side}")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "front_left"], "CLOSEUPS": [{"label": "wrist", "center": list(bones["forearm.L"].tail_local), "size": 0.35, "view": "front"}]}}
    return person(extra)


@case("joint_gap_at_rest_then_flies_off_both", "fail", "arm parts rigid on the upper arm, hand parts 6 mm past them: bending the elbow leaves each hand in the air. The repo's loose_hand without the crossing at rest")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            a, b = bones[f"upper_arm.{side}"].head_local, bones[f"forearm.{side}"].tail_local
            axis = (b - a).normalized()
            on(paint(capsule(f"Arm.{side}", a, b, 0.055, 0.035, segments=8), SKIN), rig, f"upper_arm.{side}")
            start = b + axis * (0.035 + 0.006 + 0.04)
            on(paint(capsule(f"HandPart.{side}", start, start + axis * 0.05, 0.04, 0.03, segments=8), YELLOW), rig, f"hand.{side}")
        def after(report):
            apply_named_pose(rig, "arms_forward")
            render("joint_gap_arms_forward", VIEWS=["left", "front_left"], COLUMNS=2)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("joint_loose_hand_control", "fail", "the same with the parts crossing at rest (repo's own defect, control: must fail)")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            on(paint(capsule(f"Arm.{side}", bones[f"upper_arm.{side}"].head_local, bones[f"forearm.{side}"].tail_local, 0.055, 0.035, segments=8), SKIN), rig, f"upper_arm.{side}")
            on(paint(capsule(f"HandPart.{side}", bones[f"hand.{side}"].head_local, bones[f"hand.{side}"].tail_local, 0.04, 0.03, segments=8), YELLOW), rig, f"hand.{side}")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("joint_opens_on_one_side_still_crossing", "fail", "leg parts with flat ends set 1 cm into the thigh... the shin part's end pivots away: most of the joint gapes though one corner still crosses")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Leg.{side}"], do_unlink=True)
            hip, knee, ankle = bones[f"thigh.{side}"].head_local, bones[f"shin.{side}"].head_local, bones[f"shin.{side}"].tail_local
            # A thigh ending 8 cm above the knee joint, a shin starting 7 cm above it, at the side: rigid, and the pivot outside them.
            thigh_end = hip.lerp(knee, 0.85)
            on(paint(capsule(f"Thigh.{side}", hip, thigh_end, 0.075, 0.06, segments=10, rings=1), SKIN), rig, f"thigh.{side}")
            on(paint(capsule(f"Shin.{side}", thigh_end + Vector((0, 0, 0.02)) + (ankle - thigh_end).normalized() * 0.06, ankle, 0.058, 0.045, segments=10, rings=1), YELLOW), rig, f"shin.{side}")
        def after(report):
            apply_named_pose(rig, "squat")
            render("joint_opens_one_side_squat", VIEWS=["left", "front_left"], COLUMNS=2)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("pose_arm_inner_end_out_the_back_arms_forward", "fail", "the arm part reaches 10 cm inside the chest past the shoulder joint: with arms forward its inner end comes out of the back")
def _():
    def extra(rig, parts):
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            s, h = rig.data.bones[f"upper_arm.{side}"].head_local, rig.data.bones[f"hand.{side}"].tail_local
            on(paint(capsule(f"Arm.{side}", (s.x - 0.12 * sign, s.y, s.z), h, 0.045, 0.035, segments=8, sections=8), YELLOW), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        def after(report):
            apply_named_pose(rig, "arms_forward")
            render("pose_arm_inner_end_arms_forward", VIEWS=["back", "left", "back_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("pose_thigh_through_skirt_parts_body_dense", "fail", "a skirt weighted to the hips, on a body of parts with rings along the leg: in a squat each thigh goes through its front wall, knee out the other side")
def _():
    def extra(rig, parts):
        skirt = paint(open_lathe("Skirt", [(0.20, 0.62), (0.19, 0.80), (0.17, 0.96), (0.15, 1.04), (0.0, 1.10)], segments=20), RED)
        on(skirt, rig, "hips")
        def after(report):
            apply_named_pose(rig, "squat")
            render("pose_thigh_through_skirt_dense", VIEWS=["left", "front", "front_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True, "TWO_SIDED": ["Skirt"], "_after": after}
    return person(extra, sections=8)


@case("hem_shin_through_trouser_from_hem_up_v2", "fail", "the shin comes out through the front of the trouser leg, from the hem up to 20 cm above it, joined to the bare ankle")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
        leg = dense_leg(rig)
        trouser(rig)
        for v in leg.data.vertices:
            if 0.14 < v.co.z < 0.42 and v.co.y < -0.01:
                v.co.y -= 0.075 * min(1.0, (0.42 - v.co.z) / 0.04, (v.co.z - 0.14) / 0.05)
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left"], "CLOSEUPS": [{"label": "shin", "center": [0.1, -0.05, 0.3], "size": 0.5, "view": "front_left"}]}}
    return person(extra)


@case("hem_forearm_through_sleeve_from_cuff_up", "fail", "the forearm comes out through the sleeve from the cuff up, joined to the bare wrist")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
        a, b, w = bones["upper_arm.L"].head_local, bones["hand.L"].tail_local, bones["forearm.L"].tail_local
        arm = on(paint(capsule("Arm.L", a, b, 0.05, 0.035, segments=16, sections=16), SKIN), rig, "upper_arm.L", "forearm.L", "hand.L")
        end = a.lerp(w, 0.85)
        on(paint(capsule("Sleeve", a, end, 0.075, 0.052, segments=16, sections=12), RED), rig, "upper_arm.L", "forearm.L")
        axis = (b - a).normalized()
        length = (b - a).length
        up = Vector((math.sin(mannequin.A), 0, math.cos(mannequin.A)))
        for v in arm.data.vertices:
            t = (v.co - a).dot(axis) / length
            radial = (v.co - a) - axis * (v.co - a).dot(axis)
            if 0.35 < t < 0.78 and radial.length > 1e-4 and radial.normalized().dot(up) > 0.3:
                v.co += up * 0.05 * min(1.0, (t - 0.35) / 0.05, (0.78 - t) / 0.03)
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "top"], "CLOSEUPS": [{"label": "forearm", "center": list(end), "size": 0.45, "view": "front"}]}}
    return person(extra)


@case("hat_bunny_ears_through_hat", "fail", "long bunny ears set in the head come out through the crown: mostly outside, so an 'ornament'. The guide lists this for ALLOW_CROSSING")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), BROWN), rig, "head")
        for side, s in (("L", 1), ("R", -1)):
            on(paint(capsule(f"Ear.{side}", (0.05 * s, 0, 1.76), (0.09 * s, 0, 2.15), 0.025, 0.018, segments=8), SKIN), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("hat_long_horn_through_helmet", "fail", "a long horn set in the skull comes out through a closed helmet: mostly outside, so an 'ornament'")
def _():
    def extra(rig, parts):
        on(paint(lathe("Helmet", [(0.0, 1.62), (0.125, 1.62), (0.125, 1.75), (0.09, 1.82), (0.0, 1.84)], segments=20), GRAY), rig, "head")
        on(paint(capsule("Horn", (0.05, -0.02, 1.76), (0.14, -0.14, 2.15), 0.03, 0.006, segments=8), YELLOW), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}
    return person(extra)


@case("rig_hat_parented_to_armature_object", "fail", "a hat parented to the armature object, not to a bone: it stays where it is when the head moves. inside rig.py it has no bones at all")
def _():
    def extra(rig, parts):
        hat = paint(fits_hat(), BROWN)
        hat.parent = rig
        return {"WHOLE_PARTS": True, "ARMATURE": rig.name}
    return person(extra)


@case("rig_hat_weighted_to_chest", "fail", "a hat weighted to the chest: it never follows the head. No humanoid test pose nods the head")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), BROWN), rig, "chest")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("rig_hat_parented_to_body_mesh_left_out", "fail", "a too small hat parented to the head mesh, as hand modelers do: with no TARGETS it isn't gathered, and nothing says so")
def _():
    def extra(rig, parts):
        hat = paint(lathe("Cap", [(0.0, 1.66), (0.125, 1.66), (0.12, 1.70), (0.095, 1.74), (0.0, 1.76)], segments=16), BROWN)
        hat.parent = parts["Head"]
        s = {"WHOLE_PARTS": True, "ARMATURE": rig.name, "TARGETS": None}
        return s
    settings = person(extra)
    settings["TARGETS"] = None
    return settings


@case("rig_curve_horn_through_head", "fail", "a spike modeled as a curve object goes right through the head: TARGETS drops anything that isn't a mesh, silently")
def _():
    def extra(rig, parts):
        curve = bpy.data.curves.new("Spike", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 0.015
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (-0.18, 0, 1.65, 1)
        spline.points[1].co = (0.18, 0, 1.65, 1)
        obj = bpy.data.objects.new("Spike", curve)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = rig
        return {"WHOLE_PARTS": True, "TARGETS": meshes() + ["Spike"]}
    return person(extra)


def constrained_rig(rig):
    """Control bones that drive the deform bones through Copy Transforms, as Rigify and many control rigs do."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    names = [b.name for b in edit]
    for name in names:
        b = edit[name]
        c = edit.new("ctrl_" + name)
        c.head, c.tail, c.roll = b.head, b.tail, b.roll
        c.use_deform = False
    for name in names:
        if edit[name].parent:
            edit["ctrl_" + name].parent = edit["ctrl_" + edit[name].parent.name]
    bpy.ops.object.mode_set(mode="OBJECT")
    for name in names:
        c = rig.pose.bones[name].constraints.new("COPY_TRANSFORMS")
        c.target = rig
        c.subtarget = "ctrl_" + name
    bpy.context.view_layer.update()


def wide_hips(rig, parts):
    bpy.data.objects.remove(parts["Torso"], do_unlink=True)
    on(paint(capsule("Torso", (0, 0, 0.92), (0, 0, 1.36), 0.34, 0.17, segments=12, squash_y=0.68), SKIN), rig, "hips", "spine", "chest")


@case("constraints_control_wide_hips_no_constraints", "fail", "the repo's 'a hand through the hip in a pose' (control: must fail)")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("constraints_poses_do_nothing", "fail", "the same defect, with deform bones driven by Copy Transforms from control bones: the poses move nothing, and info still lists them as checked")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        constrained_rig(rig)
        def after(report):
            print("  poses_checked:", report["info"].get("poses_checked"))
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("lowpoly_long_face_through_dented_sleeve", "fail", "a low-poly arm of one long quad per side; the sleeve dents in over it: the arm's face shows through the dent and no arm vertex is outside the sleeve")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        a, w = bones["upper_arm.L"].head_local, bones["forearm.L"].tail_local
        end = a.lerp(w, 0.85)
        parts["Arm.L"].data.name = "ArmMesh"
        sleeve = on(paint(capsule("Sleeve", a, end, 0.075, 0.052, segments=16, sections=14), RED), rig, "upper_arm.L", "forearm.L")
        axis = (end - a).normalized()
        length = (end - a).length
        up = Vector((math.sin(mannequin.A), 0, math.cos(mannequin.A)))
        for v in sleeve.data.vertices:
            t = (v.co - a).dot(axis) / length
            radial = (v.co - a) - axis * (v.co - a).dot(axis)
            if 0.3 < t < 0.7 and radial.length > 1e-4 and radial.normalized().dot(up) > 0.2:
                v.co -= radial.normalized() * 0.055 * min(1.0, (t - 0.3) / 0.08, (0.7 - t) / 0.08)
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "top"], "CLOSEUPS": [{"label": "dent", "center": list(a.lerp(end, 0.5)), "size": 0.45, "view": "front"}]}}
    return person(extra)


@case("lowpoly_sleeve_bite_then_pose_poke", "fail", "low-poly sleeve whose cuff bites the arm at rest; its faces are so large that the poke at the bent elbow lands on faces the rest pose already 'knows'")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
        a, h = bones["upper_arm.L"].head_local, bones["hand.L"].tail_local
        on(paint(capsule("Arm.L", a, h, 0.05, 0.04, segments=6, sections=2), SKIN), rig, "upper_arm.L", "forearm.L", "hand.L")
        w = bones["forearm.L"].tail_local
        on(paint(capsule("Sleeve", a, a.lerp(w, 0.8), 0.07, 0.036, segments=6, sections=2), RED), rig, "upper_arm.L", "forearm.L")
        def after(report):
            apply_named_pose(rig, "arms_forward")
            render("lowpoly_sleeve_pose", VIEWS=["left", "front_left", "top"], COLUMNS=3, CLOSEUPS=[])
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("lowpoly_sleeve_no_bite_control", "fail", "the same sleeve with no bite at rest and rings along it (control: must fail, the repo's own case)")
def _():
    def extra(rig, parts):
        bones = rig.data.bones
        bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
        a, h = bones["upper_arm.L"].head_local, bones["hand.L"].tail_local
        on(paint(capsule("Arm.L", a, h, 0.05, 0.035, segments=8, sections=6), SKIN), rig, "upper_arm.L", "forearm.L", "hand.L")
        w = bones["forearm.L"].tail_local
        on(paint(capsule("Sleeve", a, a.lerp(w, 0.85), 0.07, 0.05, segments=8, sections=6), RED), rig, "upper_arm.L", "forearm.L")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("foot_hovering_one_leg_short", "fail", "the right foot hangs 6 cm above the ground: the guide lists feet on the ground, and only the lowest point is measured")
def _():
    def extra(rig, parts):
        raise_z(parts["Foot.R"], 0.06)
        for v in parts["Leg.R"].data.vertices:
            if v.co.z < 0.2:
                v.co.z += 0.06
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


@case("paw_hovering", "fail", "one paw of a four-legged animal hangs 6 cm above the ground")
def _():
    def extra(rig, parts):
        raise_z(parts["hindPaw.R"], 0.06)
        for v in parts["hindLeg.R"].data.vertices:
            if v.co.z < 0.15:
                v.co.z += 0.06
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["back", "left"]}}
    return animal(extra)


@case("facing_back_no_toe_bones", "fail", "a person facing +Y with feet pointing back: without toe bones, facing isn't looked at")
def _():
    def extra(rig, parts):
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        edit = rig.data.edit_bones
        for name in ("toe.L", "toe.R"):
            edit.remove(edit[name])
        for b in edit:
            b.head.y, b.tail.y = -b.head.y, -b.tail.y
        bpy.ops.object.mode_set(mode="OBJECT")
        for o in parts.values():
            for v in o.data.vertices:
                v.co.y = -v.co.y
            o.data.flip_normals()
            o.data.update()
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front_left"]}}
    return person(extra)


@case("tall_pole_raises_every_threshold", "fail", "a standard bearer's pole 6 m tall: 1.5% of the height is 9 cm, so a hand hanging 7 cm off the wrist isn't floating, and 0.5% is 3 cm, so a head through a hat by 2.5 cm is a graze")
def _():
    def extra(rig, parts):
        on(paint(capsule("Pole", (0, 0.12, 0.95), (0, 0.12, 6.0), 0.02, 0.02, segments=6), BROWN), rig, "chest")
        on(paint(lathe("Cap", [(0.0, 1.66), (0.125, 1.66), (0.12, 1.70), (0.095, 1.74), (0.0, 1.76)], segments=16), BROWN), rig, "head")
        return {"WHOLE_PARTS": True, "COVERS_FROM_ABOVE": [], "POSES": False}
    return person(extra)


@case("hole_in_shirt_shows_skin", "fail", "one skin with a shirt; a face of the shirt is gone, so skin shows in a hole: the hole's own back isn't what the view meets")
def _():
    body, rig = mannequin.build()
    paint(body, SKIN)
    shirt = body.copy()
    shirt.data = body.data.copy()
    shirt.name = "Shirt"
    bpy.context.scene.collection.objects.link(shirt)
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    torso = lambda c: 1.05 < c.z < 1.38 and abs(c.x) < 0.16
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not torso(f.calc_center_median())], context="FACES")
    bm.normal_update()
    for vertex in bm.verts:
        vertex.co += vertex.normal * 0.012
    bm.faces.ensure_lookup_table()
    front = sorted(bm.faces, key=lambda f: (f.calc_center_median().y, abs(f.calc_center_median().z - 1.2)))
    area = [f for f in bm.faces if f.calc_center_median().y < -0.05 and abs(f.calc_center_median().z - 1.2) < 0.05 and abs(f.calc_center_median().x) < 0.06]
    print("  deleting", len(area), "faces of", len(bm.faces))
    bmesh.ops.delete(bm, geom=area, context="FACES_ONLY")
    bm.to_mesh(shirt.data)
    bm.free()
    paint(shirt, RED)
    return {"TARGETS": ["Body", "Shirt"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "_render": {"VIEWS": ["front", "front_left"]}}


@case("hole_control_hole_in_closed_part", "fail", "a hole in a closed torso with nothing behind it (control: must fail)")
def _():
    def extra(rig, parts):
        o = parts["Torso"]
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.faces.ensure_lookup_table()
        area = [f for f in bm.faces if f.calc_center_median().y < -0.05 and abs(f.calc_center_median().z - 1.15) < 0.25][:1]
        bmesh.ops.delete(bm, geom=area, context="FACES_ONLY")
        bm.to_mesh(o.data)
        bm.free()
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("zero_gap_coincident_shirt_zfights", "fail", "a shirt that lies exactly on the skin, offset 0.2 mm: z-fighting at any distance in a game")
def _():
    body, rig = mannequin.build()
    paint(body, SKIN)
    shirt = body.copy()
    shirt.data = body.data.copy()
    shirt.name = "Shirt"
    bpy.context.scene.collection.objects.link(shirt)
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    torso = lambda c: 1.05 < c.z < 1.38 and abs(c.x) < 0.16
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not torso(f.calc_center_median())], context="FACES")
    bm.normal_update()
    for vertex in bm.verts:
        vertex.co += vertex.normal * 0.0002
    bm.to_mesh(shirt.data)
    bm.free()
    paint(shirt, RED)
    return {"TARGETS": ["Body", "Shirt"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "POSES": False}


if __name__ == "__main__":
    main()
