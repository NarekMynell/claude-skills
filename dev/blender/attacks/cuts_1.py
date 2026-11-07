# The cut pipeline and the clip check: real defects that pass, and clean pipelines that fail or crash.
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
from defects_1 import raise_z, move, plane, open_lathe, fits_hat
from defects_2 import constrained_rig
CASES.clear()

PROOFS = tempfile.mkdtemp(prefix="proofs", dir=HERE)


def culling_render(name, **settings):
    shading = bpy.context.scene.display.shading
    saved = shading.show_backface_culling
    shading.show_backface_culling = True
    try:
        return render(name, **settings)
    finally:
        shading.show_backface_culling = saved


def pipeline(settings, proof, after_cut=None, **cut_settings):
    """whole parts -> cut -> final, as the guide says. Returns the three results."""
    settings = dict(settings)
    settings.pop("_render", None)
    settings.pop("WHOLE_PARTS", None)
    whole = check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, PROOF_NAME=proof, **settings)
    done = cut(TARGETS=settings["TARGETS"], ARMATURE=settings["ARMATURE"], **cut_settings)
    if after_cut:
        after_cut()
    final = check(PROOF_DIR=PROOFS, PROOF_NAME=proof, **settings)
    return whole, done, final


@case("cut_opens_midriff_long_quads", "pass", "a low-poly torso of long quads, trousers to above its middle, a crop top below its top: a visible belly band between them. Each quad's center and corners are covered: the cut has to keep the belly, and the render shows it does: daylight through the character")
def _():
    def extra(rig, parts):
        tr = lathe("Trousers", [(0.0, 0.78), (0.17, 0.80), (0.175, 1.0), (0.172, 1.175), (0.0, 1.178)], segments=16)
        for v in tr.data.vertices:
            v.co.y *= 0.72
        on(paint(tr, BLUE), rig, "hips", "spine")
        top = lathe("CropTop", [(0.0, 1.222), (0.178, 1.225), (0.185, 1.38), (0.12, 1.52), (0.0, 1.535)], segments=16)
        for v in top.data.vertices:
            v.co.y *= 0.72
        on(paint(top, RED), rig, "spine", "chest")
        for side in ("L", "R"):
            pass
        return {}
    settings = person(extra)
    whole, done, final = pipeline(settings, "midriff", SEE_THROUGH=[])
    print("  whole parts:", whole["passed"], short(whole))
    print("  cut:", done)
    culling_render("cut_opens_midriff", TARGETS=meshes(), VIEWS=["front", "left", "front_left"], CLOSEUPS=[{"label": "belly", "center": [0, 0, 1.2], "size": 0.5, "view": "front"}])
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="midriff")


@case("cut_control_uncut_midriff", "pass", "the same character, uncut: whole parts")
def _():
    def extra(rig, parts):
        tr = lathe("Trousers", [(0.0, 0.78), (0.17, 0.80), (0.175, 1.0), (0.172, 1.175), (0.0, 1.178)], segments=16)
        for v in tr.data.vertices:
            v.co.y *= 0.72
        on(paint(tr, BLUE), rig, "hips", "spine")
        top = lathe("CropTop", [(0.0, 1.222), (0.178, 1.225), (0.185, 1.38), (0.12, 1.52), (0.0, 1.535)], segments=16)
        for v in top.data.vertices:
            v.co.y *= 0.72
        on(paint(top, RED), rig, "spine", "chest")
        return {"WHOLE_PARTS": True}
    return person(extra)


def arm_through(rig, parts):
    bones = rig.data.bones
    bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
    on(paint(capsule("Arm.L", (-0.26, 0.0, 1.38), bones["hand.L"].tail_local, 0.045, 0.035, segments=8, sections=6), SKIN), rig, "upper_arm.L", "forearm.L", "hand.L")


@case("stale_parts_receipt_vouches_for_a_later_defect", "fail", "whole parts pass and leave a receipt; then the arm is changed so it goes right through the chest, and cut: the old receipt covers it")
def _():
    settings = person()
    check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, PROOF_NAME="stale", POSES=True, **{k: settings[k] for k in ("TARGETS", "ARMATURE", "FINGERS")})
    rig = bpy.data.objects[settings["ARMATURE"]]
    parts = {n: bpy.data.objects[n] for n in settings["TARGETS"]}
    arm_through(rig, parts)
    names = meshes()
    cut(TARGETS=names, ARMATURE=rig.name)
    culling_render("stale_receipt_arm_through", TARGETS=names, VIEWS=["front", "back", "front_left"], COLUMNS=3)
    return {"TARGETS": names, "ARMATURE": rig.name, "FINGERS": 5, "PROOF_DIR": PROOFS, "PROOF_NAME": "stale"}


@case("stale_control_arm_through_whole_parts", "fail", "the same arm, whole parts (control: must fail)")
def _():
    settings = person(arm_through)
    settings["WHOLE_PARTS"] = True
    return settings


@case("other_characters_receipt", "fail", "a receipt of another character in the same folder, under the default name (the first target's): a poke through a cut seam passes")
def _():
    settings = person()
    check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, **{k: settings[k] for k in ("TARGETS", "ARMATURE", "FINGERS")})
    mannequin.clear()
    settings = person(arm_through)
    names = settings["TARGETS"]
    cut(TARGETS=names, ARMATURE=settings["ARMATURE"])
    return {"TARGETS": names, "ARMATURE": settings["ARMATURE"], "FINGERS": 5, "PROOF_DIR": PROOFS}


@case("cut_crash_part_fully_hidden", "pass", "eyes sunk wholly into the head: the cut removes them, the guide's third step then raises instead of reporting")
def _():
    def extra(rig, parts):
        for side, x in (("L", 0.04), ("R", -0.04)):
            on(paint(capsule(f"Eye.{side}", (x, -0.05, 1.66), (x, -0.05, 1.66001), 0.02, 0.02, segments=8, rings=3), DARK), rig, "head")
        return {}
    settings = person(extra)
    whole, done, final = pipeline(settings, "eyes")
    print("  cut:", done, "final:", final["passed"])
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="eyes")


def two_hats(rig, parts):
    hair = on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=16), DARK), rig, "head")
    on(paint(lathe("Cap", [(0.0, 1.70), (0.135, 1.70), (0.13, 1.78), (0.09, 1.825), (0.0, 1.84)], segments=16), RED), rig, "head")
    on(paint(lathe("SunHat", [(0.0, 1.72), (0.3, 1.72), (0.3, 1.725), (0.16, 1.73), (0.15, 1.88), (0.0, 1.92)], segments=16), YELLOW), rig, "head")
    return {"PART_GROUPS": {"hat": ["Cap", "SunHat"]}, "ALLOW_HIDDEN": ["Hair<Cap", "Hair<SunHat", "Cap<SunHat"]}


@case("cut_variants_the_tool_knows_no_groups", "fail", "two hats, one inside the other, in PART_GROUPS: they never appear together, and the cut has no PART_GROUPS: the Cap, hidden inside the SunHat, loses its faces")
def _():
    settings = person(two_hats)
    groups = settings["PART_GROUPS"]
    allow = settings["ALLOW_HIDDEN"]
    whole = check(WHOLE_PARTS=True, PROOF_DIR=PROOFS, PROOF_NAME="hats", TARGETS=settings["TARGETS"], ARMATURE=settings["ARMATURE"], PART_GROUPS=groups, ALLOW_HIDDEN=allow)
    print("  whole:", whole["passed"], short(whole))
    before = len(bpy.data.objects["Cap"].data.polygons)
    done = cut(TARGETS=settings["TARGETS"], ARMATURE=settings["ARMATURE"])
    print("  cut:", done, "Cap faces", before, "->", len(bpy.data.objects["Cap"].data.polygons))
    bpy.data.objects["SunHat"].hide_render = True
    return {"TARGETS": settings["TARGETS"], "ARMATURE": settings["ARMATURE"], "PART_GROUPS": groups, "ALLOW_HIDDEN": allow, "PROOF_DIR": PROOFS, "PROOF_NAME": "hats"}


def keys(rig, frames, name="Clip"):
    """frames: {frame: [(bone, target)]}, with target a direction, or ("turn", axis, degrees). Keys every bone on each frame."""
    action = bpy.data.actions.new(name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    bpy.context.scene.render.fps = 30
    roles = helpers.identity_roles(rig)
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    for frame, steps in sorted(frames.items()):
        for pb in rig.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        helpers.apply_pose(rig, roles, steps)
        for pb in rig.pose.bones:
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
    action.frame_range = (min(frames), max(frames))
    action.use_frame_range = True
    return action


def run_clip(rig, action, label, **settings):
    report = check_anim(ARMATURE=rig.name, ACTIONS=[action.name], NATURAL=False, GROUND=None, LOOP=False, **settings)
    entry = report["actions"][action.name]
    print(f"  clip {label}:", json.dumps(entry["issues"], default=str)[:300])
    return entry


@case("clip_hole_after_cut_no_actions", "fail", "cut against the test poses, as the guide allows when no clip goes further: a side kick then opens the hole where the leg's top was. The clip check doesn't look for openings")
def _():
    settings = person(merged=True)
    rig = bpy.data.objects[settings["ARMATURE"]]
    whole, done, final = pipeline(settings, "kick")
    print("  whole:", whole["passed"], "cut:", done, "final:", final["passed"], short(final))
    action = keys(rig, {0: [("thigh.L", (0.25, 0, -1.0))], 10: [("thigh.L", (1.0, 0.0, -0.05)), ("shin.L", (1.0, 0.0, -0.05))], 20: [("thigh.L", (1.0, 0.0, -0.05)), ("shin.L", (1.0, 0.0, -0.05))]})
    entry = run_clip(rig, action, "side kick")
    bpy.context.scene.frame_set(15)
    bpy.context.view_layer.update()
    # What the same helper finds if asked, on the frame of the kick.
    character = helpers.Character([bpy.data.objects["Merged"]], rig)
    surfaces = character.gather()
    height = max(v.co.z for s in surfaces for v in s.bm.verts) - min(v.co.z for s in surfaces for v in s.bm.verts)
    sight = helpers.Sight(surfaces, height)
    found = {s.name: len(helpers.see_inside(s, sight, 0.0)) for s in surfaces}
    print("  see_inside on the kick's frame:", {k: v for k, v in found.items() if v})
    helpers.free(surfaces)
    culling_render("clip_hole_after_cut_kick", TARGETS=["Merged"], VIEWS=["front", "back", "front_left", "top"], COLUMNS=2, FRAMES=[15], CLOSEUPS=[{"label": "hip", "center": [0.15, 0, 0.9], "size": 0.5, "view": "front_left"}])
    bpy.context.scene.frame_set(0)
    def after(r):
        print("  verdict is the clip's:", "PASS" if not entry["issues"] else entry["issues"])
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="kick", POSES=True, _after=after)


@case("clip_near_pair_spike_through_back", "fail", "a helmet with a rear spike: the head tilts back in a clip and the spike goes through the back and out the chest. Head and trunk are 'near', so the clip check doesn't look")
def _():
    def extra(rig, parts):
        helmet = lathe("Helmet", [(0.0, 1.62), (0.125, 1.62), (0.125, 1.75), (0.09, 1.82), (0.0, 1.84)], segments=20)
        on(paint(helmet, GRAY), rig, "head")
        on(paint(capsule("Spike", (0, 0.08, 1.70), (0, 0.42, 1.74), 0.03, 0.006, segments=8), DARK), rig, "head")
        return {"WHOLE_PARTS": True}
    settings = person(extra)
    rig = bpy.data.objects[settings["ARMATURE"]]
    head_turn = ("turn", (1, 0, 0), 55.0)
    action = keys(rig, {0: [], 10: [("head", head_turn)], 20: [("head", head_turn)]})
    run_clip(rig, action, "head back")
    culling_render("clip_spike_through_back", TARGETS=settings["TARGETS"], VIEWS=["left", "back"], COLUMNS=2, FRAMES=[15])
    bpy.context.scene.frame_set(0)
    settings["POSES"] = True
    return settings


@case("clip_joint_flies_off_no_crossing_at_rest", "fail", "the hand part that doesn't cross the arm at rest: in a clip the elbow bends and the hand stays in the air, 20 cm off")
def _():
    settings = person(fn2.CASES and None) if False else None
    rig = partsbody.person_rig()
    parts = {o.name: o for o in partsbody.person(rig)}
    paint_person(parts)
    bones = rig.data.bones
    for side in ("L", "R"):
        bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
        a, b = bones[f"upper_arm.{side}"].head_local, bones[f"forearm.{side}"].tail_local
        axis = (b - a).normalized()
        on(paint(capsule(f"Arm.{side}", a, b, 0.055, 0.035, segments=8), SKIN), rig, f"upper_arm.{side}")
        start = b + axis * (0.035 + 0.006 + 0.04)
        on(paint(capsule(f"HandPart.{side}", start, start + axis * 0.05, 0.04, 0.03, segments=8), YELLOW), rig, f"hand.{side}")
    action = keys(rig, {0: [], 10: [("forearm.L", (0.1, -0.6, 0.8)), ("forearm.R", (-0.1, -0.6, 0.8))], 20: [("forearm.L", (0.1, -0.6, 0.8)), ("forearm.R", (-0.1, -0.6, 0.8))]})
    run_clip(rig, action, "elbow")
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


@case("clip_thigh_through_thigh_mirrored", "fail", "a cross-step: the left thigh goes through the right thigh. Bones on one joint's two sides 'brush', so it's never reported")
def _():
    settings = person(sections=8)
    rig = bpy.data.objects[settings["ARMATURE"]]
    steps = [("thigh.L", (-0.30, 0.0, -1.0)), ("shin.L", (0.45, -0.6, -1.0))]
    action = keys(rig, {0: [], 10: steps, 20: steps})
    run_clip(rig, action, "cross-step")
    culling_render("clip_thigh_through_thigh", TARGETS=settings["TARGETS"], VIEWS=["front", "left"], COLUMNS=2, FRAMES=[15])
    bpy.context.scene.frame_set(0)
    settings["WHOLE_PARTS"] = True
    return settings


@case("clip_variants_flagged_no_part_groups", "pass", "a clean walk of a character with two sleeve variants: they never appear together, and the clip check has no PART_GROUPS")
def _():
    def extra(rig, parts):
        b = rig.data.bones
        a, w = b["upper_arm.L"].head_local, b["forearm.L"].tail_local
        on(paint(capsule("SleeveA", a, a.lerp(w, 0.85), 0.085, 0.052, segments=8, sections=6), RED), rig, "upper_arm.L", "forearm.L")
        on(paint(capsule("SleeveB", a, a.lerp(w, 0.45), 0.09, 0.07, segments=8, sections=3), BLUE), rig, "upper_arm.L")
        a, w = b["upper_arm.R"].head_local, b["forearm.R"].tail_local
        on(paint(capsule("SleeveAR", a, a.lerp(w, 0.85), 0.085, 0.052, segments=8, sections=6), RED), rig, "upper_arm.R", "forearm.R")
        on(paint(capsule("SleeveBR", a, a.lerp(w, 0.45), 0.09, 0.07, segments=8, sections=3), BLUE), rig, "upper_arm.R")
        return {"WHOLE_PARTS": True, "PART_GROUPS": {"sleeveL": ["SleeveA", "SleeveB"], "sleeveR": ["SleeveAR", "SleeveBR"]}, "NEVER_TOGETHER": ["SleeveA+SleeveBR", "SleeveB+SleeveAR"], "POSES": False}
    settings = person(extra, sections=4)
    rig = bpy.data.objects[settings["ARMATURE"]]
    steps = [("forearm.L", (0.1, -0.6, 0.8)), ("forearm.R", (-0.1, -0.6, 0.8))]
    action = keys(rig, {0: [], 10: steps, 20: steps})
    entry = run_clip(rig, action, "elbows bend")
    def after(r):
        r["issues"].update({"clip": entry["issues"]} if entry["issues"] else {})
        r["passed"] = not r["issues"]
    return dict(settings, _after=after)


@case("clip_constraints_clean_control", "pass", "a clean body of parts on a rig driven by control bones: clip keyed on the control bones works")
def _():
    settings = person()
    rig = bpy.data.objects[settings["ARMATURE"]]
    constrained_rig(rig)
    settings["WHOLE_PARTS"] = True
    return settings


if __name__ == "__main__":
    main()
    shutil.rmtree(PROOFS, ignore_errors=True)
else:
    shutil.rmtree(PROOFS, ignore_errors=True)
