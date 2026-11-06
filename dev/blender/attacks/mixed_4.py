# Fourth round: a hero built by the guide's rules, animals with gear, nicks, slivers, a tall pole, near-pairs with a Mixamo head.
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
import clean_3 as fp3
import defects_3 as fn3
import cuts_1 as cuts
from defects_1 import raise_z, move, plane, open_lathe, fits_hat
from clean_1 import union, hair_shell, hood_shell
from clean_2 import ring_on, horse_rig, horse
from clean_3 import subdivided_mannequin, union_person
from defects_3 import add_head_top_end, add_helper_bones
from cuts_1 import culling_render, keys, run_clip, pipeline
CASES.clear()
PROOFS = tempfile.mkdtemp(prefix="proofs", dir=HERE)
cuts.PROOFS = PROOFS


def hero_by_the_guide(rig):
    """Worn parts are layers on the limb's bones; only the limb's end stays under them. Hair above the head bone's base."""
    b = rig.data.bones
    made = []

    def add(name, color, bones, *args, **kwargs):
        made.append(on(paint(capsule(name, *args, **kwargs), color), rig, *bones))

    add("Tunic", GREEN, ["hips", "spine", "chest"], (0, 0, 0.95), (0, 0, 1.36), 0.17, 0.175, segments=12, squash_y=0.72, sections=3)
    add("Neck", SKIN, ["neck"], (0, 0, 1.42), (0, 0, 1.54), 0.05, 0.05, segments=8, rings=2)
    add("Head", SKIN, ["head"], (0, 0, 1.62), (0, 0, 1.68), 0.105, 0.105, segments=12)
    add("Nose", SKIN, ["head"], (0, -0.09, 1.63), (0, -0.125, 1.62), 0.022, 0.018, segments=6, rings=2)
    for side, x in (("L", 1), ("R", -1)):
        add(f"Ear.{side}", SKIN, ["head"], (0.09 * x, 0, 1.64), (0.135 * x, 0, 1.66), 0.025, 0.018, segments=6, rings=2)
        add(f"Eye.{side}", DARK, ["head"], (0.04 * x, -0.092, 1.66), (0.04 * x, -0.0925, 1.66), 0.014, 0.014, segments=8)
        s, e, w, h = (b[f"upper_arm.{side}"].head_local, b[f"forearm.{side}"].head_local, b[f"forearm.{side}"].tail_local, b[f"hand.{side}"].tail_local)
        add(f"Sleeve.{side}", GREEN, [f"upper_arm.{side}", f"forearm.{side}"], s, s.lerp(w, 0.8), 0.062, 0.05, segments=10, sections=6)
        start = s.lerp(w, 0.72)
        add(f"ForearmEnd.{side}", SKIN, [f"forearm.{side}", f"hand.{side}"], start, h, 0.036, 0.03, segments=10, sections=3)
        hip, knee, ankle = b[f"thigh.{side}"].head_local, b[f"shin.{side}"].head_local, b[f"shin.{side}"].tail_local
        add(f"Trouser.{side}", BLUE, [f"thigh.{side}", f"shin.{side}"], hip + Vector((0, 0, 0.03)), hip.lerp(ankle, 0.8), 0.088, 0.062, segments=10, sections=6)
        add(f"Boot.{side}", BROWN, [f"shin.{side}"], (ankle.x, ankle.y, 0.25), (ankle.x, ankle.y, 0.09), 0.07, 0.058, segments=10, sections=2)
        toe = b[f"toe.{side}"].tail_local
        add(f"Foot.{side}", BROWN, [f"foot.{side}", f"toe.{side}"], (ankle.x, ankle.y, 0.05), (toe.x, toe.y, 0.05), 0.05, 0.05, segments=8)
        add(f"Pad.{side}", GRAY, [f"upper_arm.{side}"], s + Vector((-0.01 * x, 0, 0.012)), s + Vector((0.035 * x, 0, -0.012)), 0.075, 0.07, segments=10)
    on(paint(ring("Belt", 0.186, 0.12, 1.03, 1.07, squash_y=0.72, segments=16), BROWN), rig, "hips", "spine")
    on(paint(capsule("Pouch", (0.165, -0.06, 1.0), (0.165, -0.06, 1.03), 0.04, 0.04, segments=8), BROWN), rig, "hips")
    on(paint(lathe("Hair", [(0.0, 1.645), (0.1, 1.645), (0.113, 1.68), (0.113, 1.72), (0.09, 1.78), (0.0, 1.805)], segments=16), DARK), rig, "head")
    on(paint(capsule("Quiver", (-0.08, 0.145, 1.42), (0.08, 0.145, 1.02), 0.045, 0.04, segments=8), BROWN), rig, "chest")
    return made


@case("hero_by_the_guide_whole_parts", "pass", "a low-poly hero of parts, built by the guide: worn parts over limb ends, belt, pouch, shoulder pads, hair above the head bone's base, quiver")
def _():
    rig = partsbody.person_rig()
    hero_by_the_guide(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "FINGERS": 5, "SYMMETRIC": ["Tunic"], "_render": {"VIEWS": ["front", "back", "left", "front_left"], "COLUMNS": 2}}


@case("hero_by_the_guide_pipeline", "pass", "the same hero through the guide's three steps: whole parts, cut, check")
def _():
    rig = partsbody.person_rig()
    hero_by_the_guide(rig)
    settings = {"TARGETS": meshes(), "ARMATURE": rig.name, "FINGERS": 5, "SYMMETRIC": ["Tunic"]}
    whole, done, final = pipeline(settings, "hero")
    print("  whole:", whole["passed"], short(whole))
    print("  cut:", done)
    print("  final:", final["passed"], short(final))
    k = 0
    while k < 6:
        again = cut(TARGETS=settings["TARGETS"], ARMATURE=rig.name)
        k += 1
        if not again["deleted"]:
            break
        print("  cut again:", again["deleted"])
    culling_render("hero_after_cut", TARGETS=settings["TARGETS"], VIEWS=["front", "back", "left", "front_left", "top"])
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="hero")


@case("person_with_rings_pipeline", "pass", "the clean person with rings along its limbs through the guide's three steps")
def _():
    settings = person(sections=4)
    whole, done, final = pipeline(settings, "ringed")
    print("  whole:", whole["passed"], "cut:", done, "final:", final["passed"], short(final))
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="ringed")


@case("animal_with_rings_pipeline", "pass", "the clean animal through the guide's three steps")
def _():
    settings = animal()
    whole, done, final = pipeline(settings, "pet")
    print("  whole:", whole["passed"], short(whole), "cut:", done, "final:", final["passed"], short(final))
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="pet")


def nick(body, sign):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    tree = helpers.BVHTree.FromBMesh(bm)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    best = None
    for v in bm.verts:
        if 0.12 < abs(v.co.x) < 0.3 and 1.15 < v.co.z < 1.45 and v.co.x * sign > 0:
            d = Vector((-sign, 0, -0.35)).normalized()
            hit = tree.ray_cast(v.co + d * 1e-4, d, 0.2)
            if hit[0] is not None and hit[3] > 2e-3 and hit[1].dot(d) < 0 and v not in bm.faces[hit[2]].verts:
                if best is None or hit[3] < best[1]:
                    best = (v.index, hit[3], d.copy())
    index, dist, d = best
    body.data.vertices[index].co += d * (dist + 0.002)
    bm.free()
    return index, round(dist, 4)


@case("nick_one", "pass", "a one-skin body with one 2 mm nick at one armpit")
def _():
    body, rig = mannequin.build()
    print("  nick", nick(body, 1))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False}


@case("nick_two", "pass", "the same with a nick at each armpit: each as small as before, their extent half a metre")
def _():
    body, rig = mannequin.build()
    print("  nicks", nick(body, 1), nick(body, -1))
    def after(report):
        print("  examples:", report.get("examples", {}).get("intersections"))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False, "_after": after}


def stretched_lengths(body, rig):
    """How long were the edges the check calls stretched? Same loop as _poses_report."""
    roles = helpers.map_roles(rig)
    character = helpers.Character([body], rig)
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    rest = character.gather()
    lengths = [[e.calc_length() for e in s.bm.edges] for s in rest]
    helpers.free(rest)
    rig.data.pose_position = "POSE"
    out = []
    with helpers.PoseState(rig) as state:
        for name, steps in helpers.test_poses(roles).items():
            state.reset()
            helpers.apply_pose(rig, roles, steps)
            parts = character.gather()
            for part, ls in zip(parts, lengths):
                for edge, r in zip(part.bm.edges, ls):
                    if r > 1e-6:
                        q = edge.calc_length() / r
                        if q > 2.0 or q < 0.2:
                            out.append((name, round(r * 1000, 2), round(q, 2)))
            helpers.free(parts)
    return out


@case("stretch_union_rest_lengths", "pass", "a boolean union: how long are the edges reported as stretched?")
def _():
    body, rig = union_person()
    print("  stretched (pose, rest length mm, ratio):", stretched_lengths(body, rig))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name}


@case("stretch_dense_rest_lengths", "pass", "the mannequin subdivided twice, opposite-side weights cleaned: how long are the edges reported as stretched?")
def _():
    body, rig = subdivided_mannequin(2)
    mannequin.clean_weights(body, rig)
    print("  stretched (pose, rest length mm, ratio):", sorted(stretched_lengths(body, rig), key=lambda e: e[1])[:30])
    def after(report):
        pass
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "FINGERS": 5}


def knee_poke(rig, parts, depth):
    bpy.data.objects.remove(parts["Leg.L"], do_unlink=True)
    from defects_1 import dense_leg, trouser
    leg = dense_leg(rig)
    trouser(rig)
    knee = rig.data.bones["shin.L"].head_local
    bump(leg, (knee.x, knee.y - 0.05, knee.z), 0.07, (0.0, -depth, 0.0))


@case("pole_control_knee_through_trousers", "fail", "a knee 2.5 cm through a trouser leg (control: must fail)")
def _():
    def extra(rig, parts):
        knee_poke(rig, parts, 0.075)
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


@case("pole_knee_through_trousers_with_6m_pole", "fail", "the same knee, on a standard bearer with a 6 m pole: the graze is 0.5% of the height, 3 cm")
def _():
    def extra(rig, parts):
        knee_poke(rig, parts, 0.075)
        on(paint(capsule("Pole", (0, 0.13, 0.95), (0, 0.13, 6.0), 0.02, 0.02, segments=6), BROWN), rig, "chest")
        return {"WHOLE_PARTS": True, "POSES": False}
    return person(extra)


@case("pole_hand_hanging_with_6m_pole", "fail", "a head hanging 8 cm above the body, with the same pole: 1.5% of the height is 9 cm")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Head"], do_unlink=True)
        bpy.data.objects.remove(parts["Neck"], do_unlink=True)
        on(paint(capsule("Head", (0, 0, 1.71), (0, 0, 1.77), 0.1, 0.1, segments=12), SKIN), rig, "head")
        on(paint(capsule("Pole", (0.25, 0.13, 0.95), (0.25, 0.13, 6.0), 0.02, 0.02, segments=6), BROWN), rig, "chest")
        return {"WHOLE_PARTS": True, "POSES": False, "SYMMETRIC": ["Torso"]}
    return person(extra)


def arm_root_up_head(rig, parts):
    for side, sign in (("L", 1), ("R", -1)):
        bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
        s, h = rig.data.bones[f"upper_arm.{side}"].head_local, rig.data.bones[f"hand.{side}"].tail_local
        on(paint(capsule(f"Arm.{side}", (0.06 * sign, 0, 1.42), h, 0.05, 0.035, segments=8, sections=8), YELLOW), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
    bpy.data.objects.remove(parts["Torso"], do_unlink=True)
    on(paint(capsule("Torso", (0, 0, 0.92), (0, 0, 1.36), 0.16, 0.17, segments=12, squash_y=0.95), SKIN), rig, "hips", "spine", "chest")


@case("mixamo_control_arm_root_into_head", "fail", "the arm's inner end swings up into the head when the arms come down (control, plain rig: must fail)")
def _():
    def extra(rig, parts):
        arm_root_up_head(rig, parts)
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("mixamo_headtop_end_arm_root_into_head", "fail", "the same on a rig with Mixamo's HeadTop_End bone: the head is now part of the trunk, and an upper arm in the head is a joint")
def _():
    def extra(rig, parts):
        arm_root_up_head(rig, parts)
        add_head_top_end(rig)
        def after(report):
            apply_named_pose(rig, "arms_down")
            render("mixamo_arm_root_arms_down", VIEWS=["front", "left"], COLUMNS=2)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


def long_tail_animal(count):
    rig = horse_rig(tail_bones=count)
    horse(rig, tail_bones=count)
    bpy.data.objects.remove(bpy.data.objects["TailP"], do_unlink=True)
    y1 = 0.55 + 0.06 * count
    obj = capsule("TailP", (0, 0.655, 0.93), (0, y1, 0.45), 0.03, 0.015, segments=8, sections=count * 2)
    on(paint(obj, DARK), rig, *[f"tail.{k:02d}" for k in range(count)])
    return rig


for count in (3, 8, 10, 11, 12, 14):
    def make(count=count):
        def build():
            rig = long_tail_animal(count)
            print(f"  tail {count}: trunk", sorted(helpers.trunk_bones(rig, helpers.map_roles(rig)))[:6], "chains", [c[0].name for c in helpers.leg_chains(rig, helpers.map_roles(rig))])
            return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left"]}}
        return build
    case(f"long_tail_{count}_bones", "pass", "a horse whose tail has this many bones")(make())


@case("hood_clear_of_arms_open_part", "pass", "a two-sided hood with a face opening, clear of the arms, weighted to the head")
def _():
    def extra(rig, parts):
        bm_hood = hood_shell("Hood", r=0.128)
        # Trim what would reach the arms: shoulders stay inside the hood's radius.
        for v in bm_hood.data.vertices:
            if v.co.z < 1.52:
                d = (v.co.x ** 2 + v.co.y ** 2) ** 0.5
                k = 0.125 / max(d, 1e-6)
                v.co.x *= k
                v.co.y *= k
                v.co.z = 1.46 + (v.co.z - 1.42) * 0.5
        on(paint(bm_hood, GREEN), rig, "head")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Hood"], "POSES": False, "_render": {"VIEWS": ["front", "back", "left", "front_left", "top"]}}
    return person(extra)


if __name__ == "__main__":
    main()
    shutil.rmtree(PROOFS, ignore_errors=True)
else:
    shutil.rmtree(PROOFS, ignore_errors=True)
