# Second round on the cut pipeline and clips.
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
import cuts_1 as cuts
from defects_1 import raise_z, move, plane, open_lathe, fits_hat
from clean_1 import union
from cuts_1 import culling_render, keys, run_clip, pipeline
CASES.clear()
PROOFS = tempfile.mkdtemp(prefix="proofs", dir=HERE)
cuts.PROOFS = PROOFS


@case("cut_needs_two_passes", "pass", "eyes sunk into the head, set behind the neck's top: after the guide's three steps the final check reports covered faces the cut itself uncovered. One pass isn't a fixed point")
def _():
    def extra(rig, parts):
        for side, x in (("L", 0.04), ("R", -0.04)):
            on(paint(capsule(f"Eye.{side}", (x, -0.05, 1.66), (x, -0.05, 1.66001), 0.02, 0.02, segments=8, rings=3), DARK), rig, "head")
        return {}
    settings = person(extra)
    whole, done, final = pipeline(settings, "eyes2")
    print("  whole:", whole["passed"], "first cut:", done, "final:", final["passed"], short(final))
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="eyes2")


@case("cut_repeated_until_done_then_check", "pass", "the same, with the cut run again until it finds nothing: then the check")
def _():
    def extra(rig, parts):
        for side, x in (("L", 0.04), ("R", -0.04)):
            on(paint(capsule(f"Eye.{side}", (x, -0.05, 1.66), (x, -0.05, 1.66001), 0.02, 0.02, segments=8, rings=3), DARK), rig, "head")
        return {}
    settings = person(extra)
    plain = {k: settings[k] for k in ("TARGETS", "ARMATURE", "FINGERS")}
    check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, PROOF_NAME="eyes3", **plain)
    for k in range(6):
        done = cut(TARGETS=plain["TARGETS"], ARMATURE=plain["ARMATURE"])
        print(f"  cut {k}:", done["deleted"], "faces left in Eye.L:", len(bpy.data.objects["Eye.L"].data.polygons))
        if not done["deleted"]:
            break
    return dict(plain, PROOF_DIR=PROOFS, PROOF_NAME="eyes3")


def hat_variants(rig, parts):
    on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=16), DARK), rig, "head")
    on(paint(lathe("Cap", [(0.0, 1.70), (0.135, 1.70), (0.13, 1.78), (0.09, 1.825), (0.0, 1.84)], segments=16), RED), rig, "head")
    on(paint(lathe("SunHat", [(0.0, 1.72), (0.2, 1.72), (0.2, 1.725), (0.16, 1.73), (0.15, 1.88), (0.0, 1.92)], segments=16), YELLOW), rig, "head")
    return {"PART_GROUPS": {"hat": ["Cap", "SunHat"]}, "ALLOW_HIDDEN": ["Hair<Cap", "Hair<SunHat"]}


@case("variants_whole_parts_clean", "pass", "two hats that each fit, in PART_GROUPS, whole parts")
def _():
    settings = person(hat_variants)
    settings["WHOLE_PARTS"] = True
    return settings


@case("variants_cut_then_check", "pass", "the same character through the guide's cut: the tool has no PART_GROUPS, so one hat hides the other and its faces go")
def _():
    settings = person(hat_variants)
    groups, allow = settings["PART_GROUPS"], settings["ALLOW_HIDDEN"]
    plain = {"TARGETS": settings["TARGETS"], "ARMATURE": settings["ARMATURE"]}
    whole = check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, PROOF_NAME="hats", PART_GROUPS=groups, ALLOW_HIDDEN=allow, **plain)
    print("  whole:", whole["passed"], short(whole))
    before = len(bpy.data.objects["Cap"].data.polygons)
    done = cut(**plain)
    print("  cut:", done, "Cap faces", before, "->", len(bpy.data.objects["Cap"].data.polygons))
    bpy.data.objects["SunHat"].hide_render = True
    culling_render("variants_cut_cap_alone", TARGETS=[n for n in plain["TARGETS"] if n != "SunHat"], VIEWS=["front", "top", "front_left"], COLUMNS=3)
    bpy.data.objects["SunHat"].hide_render = False
    return dict(plain, PART_GROUPS=groups, ALLOW_HIDDEN=allow, PROOF_DIR=PROOFS, PROOF_NAME="hats")


@case("clip_spike_through_back_one_surface", "fail", "a helmet with a rear spike in one surface: the head tilts back in a clip, the spike goes through the back and out the chest. Head and trunk are near, so neither check looks")
def _():
    def extra(rig, parts):
        helmet = lathe("Helmet", [(0.0, 1.62), (0.125, 1.62), (0.125, 1.75), (0.09, 1.82), (0.0, 1.84)], segments=20)
        spike = capsule("Spike", (0, 0.08, 1.70), (0, 0.42, 1.74), 0.03, 0.006, segments=8)
        on(paint(union("Helmet", [helmet, spike]), GRAY), rig, "head")
        return {"WHOLE_PARTS": True}
    settings = person(extra)
    rig = bpy.data.objects[settings["ARMATURE"]]
    head_turn = ("turn", (1, 0, 0), 62.0)
    action = keys(rig, {0: [], 10: [("head", head_turn)], 20: [("head", head_turn)]})
    run_clip(rig, action, "head back")
    culling_render("clip_spike_through_back", TARGETS=settings["TARGETS"], VIEWS=["left", "back", "front"], COLUMNS=3, FRAMES=[15])
    bpy.context.scene.frame_set(0)
    rig.animation_data.action = None
    rest_rig(rig)
    return settings


@case("clip_thigh_through_thigh_only", "fail", "a cross-step where only the thighs meet: the left thigh goes through the right thigh, knees and shins clear")
def _():
    def extra(rig, parts):
        for side in ("L", "R"):
            bpy.data.objects.remove(parts[f"Leg.{side}"], do_unlink=True)
            hip, ankle = rig.data.bones[f"thigh.{side}"].head_local, rig.data.bones[f"shin.{side}"].tail_local
            on(paint(capsule(f"Leg.{side}", hip, ankle, 0.082, 0.04, segments=12, sections=12), SKIN), rig, f"thigh.{side}", f"shin.{side}")
        return {"WHOLE_PARTS": True}
    settings = person(extra)
    rig = bpy.data.objects[settings["ARMATURE"]]
    steps = [("thigh.L", (-0.20, -0.55, -1.0)), ("shin.L", (0.6, -0.2, -1.0))]
    action = keys(rig, {0: [], 10: steps, 20: steps})
    run_clip(rig, action, "cross-step")
    culling_render("clip_thigh_through_thigh_only", TARGETS=settings["TARGETS"], VIEWS=["front", "left", "front_right"], COLUMNS=3, FRAMES=[15])
    bpy.context.scene.frame_set(0)
    rig.animation_data.action = None
    rest_rig(rig)
    return settings


def low_head_bone(rig):
    """A head bone that starts at the top of the neck, as real rigs have it."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    edit["neck"].tail = (0, 0, 1.53)
    edit["head"].head = (0, 0, 1.53)
    bpy.ops.object.mode_set(mode="OBJECT")


@case("clip_nod_opens_cut_neck", "fail", "a head bone from the top of the neck. No test pose nods, so the cut removes the neck's top inside the head. A nod in a clip opens it, and the clip check looks for no openings")
def _():
    rig = partsbody.person_rig()
    low_head_bone(rig)
    parts = {o.name: o for o in partsbody.person(rig)}
    paint_person(parts)
    settings = {"TARGETS": meshes(), "ARMATURE": rig.name, "FINGERS": 5}
    whole, done, final = pipeline(settings, "nod")
    print("  whole:", whole["passed"], short(whole), "cut:", done, "final:", final["passed"], short(final))
    nod = ("turn", (1, 0, 0), -60.0)
    action = keys(rig, {0: [], 10: [("head", nod)], 20: [("head", nod)]})
    run_clip(rig, action, "nod")
    bpy.context.scene.frame_set(15)
    bpy.context.view_layer.update()
    character = helpers.Character([bpy.data.objects[n] for n in settings["TARGETS"]], rig)
    surfaces = character.gather()
    height = max(v.co.z for s in surfaces for v in s.bm.verts) - min(v.co.z for s in surfaces for v in s.bm.verts)
    sight = helpers.Sight(surfaces, height)
    print("  see_inside on the nod's frame:", {s.name: n for s in surfaces for n in [len(helpers.see_inside(s, sight, 0.0))] if n})
    helpers.free(surfaces)
    culling_render("clip_nod_opens_neck", TARGETS=settings["TARGETS"], VIEWS=["left", "back", "back_left"], COLUMNS=3, FRAMES=[15], CLOSEUPS=[{"label": "neck", "center": [0, 0, 1.5], "size": 0.35, "view": "back_left"}])
    bpy.context.scene.frame_set(0)
    rig.animation_data.action = None
    rest_rig(rig)
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="nod")


def trouser_leg(rig):
    hip, ankle = rig.data.bones["thigh.L"].head_local, rig.data.bones["shin.L"].tail_local
    end = hip.lerp(ankle, 0.85)
    return on(paint(capsule("Trouser", hip, end, 0.11, 0.075, segments=8, sections=6), BLUE), rig, "thigh.L", "shin.L")


@case("stale_receipt_knee_through_trouser_after_cut", "fail", "whole parts pass and leave a receipt; the leg then changes so the knee comes through the trousers, and is cut: the seam makes the check trust the old receipt")
def _():
    def extra(rig, parts):
        trouser_leg(rig)
        return {"POSES": False}
    settings = person(extra, sections=6)
    plain = {k: settings[k] for k in ("TARGETS", "ARMATURE", "FINGERS")}
    r = check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, PROOF_NAME="stale2", POSES=False, **plain)
    print("  first receipt:", r["passed"], short(r))
    rig = bpy.data.objects[plain["ARMATURE"]]
    knee = rig.data.bones["shin.L"].head_local
    partsbody.bump(bpy.data.objects["Leg.L"], (knee.x, knee.y - 0.05, knee.z), 0.09, (0.0, -0.05, 0.0))
    done = cut(TARGETS=plain["TARGETS"], ARMATURE=plain["ARMATURE"])
    print("  cut:", done)
    return dict(plain, POSES=False, PROOF_DIR=PROOFS, PROOF_NAME="stale2")


@case("stale_control_same_knee_whole_parts", "fail", "the same knee on the whole parts (control: must fail)")
def _():
    def extra(rig, parts):
        trouser_leg(rig)
        knee = rig.data.bones["shin.L"].head_local
        partsbody.bump(parts["Leg.L"], (knee.x, knee.y - 0.05, knee.z), 0.09, (0.0, -0.05, 0.0))
        return {"POSES": False, "WHOLE_PARTS": True}
    return person(extra, sections=6)


@case("parts_not_checked_no_cut_ever_made", "pass", "one skin with a hair cap whose open rim is set into the scalp; nothing was ever cut: the default run says to run the check on the parts before the cut")
def _():
    body, rig = mannequin.build()
    paint(body, SKIN)
    hair = open_lathe("Hair", [(0.075, 1.68), (0.088, 1.71), (0.08, 1.76), (0.05, 1.80), (0.0, 1.815)], segments=16)
    # Outward normals.
    bm = bmesh.new(); bm.from_mesh(hair.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(hair.data); bm.free()
    on(paint(hair, DARK), rig, "head")
    return {"TARGETS": ["Body", "Hair"], "ARMATURE": rig.name, "ALLOW_HIDDEN": ["Body<Hair"], "_render": {"VIEWS": ["front", "left"]}}


if __name__ == "__main__":
    main()
    shutil.rmtree(PROOFS, ignore_errors=True)
