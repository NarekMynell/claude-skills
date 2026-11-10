# Runs modeling/scripts/inspect_animation.py against walk cycles with known defects and checks each report.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <inspect_animation.py>
import os
import sys
import types

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gait  # noqa: E402
import mannequin  # noqa: E402
import partsbody  # noqa: E402
import quadruped  # noqa: E402

script_path = sys.argv[sys.argv.index("--") + 1]
script = open(script_path).read()
rig_path = os.path.join(os.path.dirname(script_path), "rig.py")
helpers_namespace = {"__file__": rig_path, "__name__": "rig_helpers"}
exec(compile(open(rig_path).read(), rig_path, "exec"), helpers_namespace)
helpers = types.SimpleNamespace(**helpers_namespace)


def run(**settings):
    namespace = {"__file__": script_path, "ARMATURE": "BodyRig"}
    namespace.update(settings)
    exec(compile(script, script_path, "exec"), namespace)
    return namespace["result"]


cases = []


def case(label, expected, walk=None, check=None, props=None, keys=None, at_least=False, parts=None, **settings):
    """expected: the issues the report must hold, exactly, or among others with at_least. keys: keys another clip.
    parts: adds other skinned meshes."""
    mannequin.clear()
    body, rig = mannequin.build()
    action = keys(rig) if keys else gait.key_walk(rig, rig_helpers=helpers, **(walk or {}))
    if props:
        props(rig)
        settings["PROPS"] = ["Prop"]
    if parts:
        parts(rig)
    report = run(ACTIONS=[action.name], **settings)
    entry = report["actions"][action.name]
    found = sorted(entry["issues"])
    ok = found == sorted(expected) and report["passed"] == (not expected)
    if at_least:
        ok = set(expected) <= set(found)
    detail = None
    if check:
        detail = check(entry["info"])
        ok = ok and detail is True
    cases.append({"case": label, "ok": ok, "expected": sorted(expected), "found": found, "issues": entry["issues"],
                  "info": entry["info"], "check": detail})


def speed_near(expected, key):
    def check(info):
        value = info.get(key)
        return True if value is not None and abs(value - expected) < 0.08 * expected else f"{key} = {value}, expected {expected}"
    return check


case("clean root-motion walk", [], check=speed_near(gait.SPEED, "root_speed_mps"))
case("clean in-place walk: the speed to move at", [], walk={"root": 0.0}, check=speed_near(gait.SPEED, "stride_speed_mps"))
case("root moves faster than the feet", ["foot_sliding"], walk={"root": 1.5})
case("feet below the ground", ["feet_below_ground"], walk={"feet_offset": -0.03})
case("arms swing with the same-side leg", ["same_side_arm_swing"], walk={"same_side_arms": True})
case("loop cut short", ["loop_seam"], walk={"end": 21})
case("loop cut short, not a loop", [], walk={"end": 21}, LOOP=False)
case("arm flips for one frame", ["joint_pops"], walk={"pop_frame": 12})
case("hands into the body", ["limbs_through_body"], walk={"arms_inward": (10, 13)})


def held_prop(rig):
    # A box that the left hand's mitten passes through on frames 6 to 9.
    bpy.ops.mesh.primitive_cube_add(size=0.12)
    prop = bpy.context.active_object
    prop.name = "Prop"
    for frame in range(0, gait.FRAMES + 1):
        bpy.context.scene.frame_set(frame)
        hand = rig.matrix_world @ rig.pose.bones["hand.L"].tail
        prop.location = hand if 6 <= frame <= 9 else hand + Vector((0.0, 0.0, 3.0))
        prop.keyframe_insert("location", frame=frame)


case("hand through a held prop", ["hand_through_prop"], props=held_prop)

def bag_on_the_arm(rig):
    # A bag skinned to the left forearm, at the wrist and clear of the body at rest; the arm brings it into the body.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.06, location=rig.matrix_world @ rig.data.bones["forearm.L"].tail_local)
    bag = bpy.context.active_object
    bag.name = "Bag"
    bpy.ops.object.transform_apply(location=True)
    group = bag.vertex_groups.new(name="forearm.L")
    group.add([v.index for v in bag.data.vertices], 1.0, "REPLACE")
    modifier = bag.modifiers.new("Armature", "ARMATURE")
    modifier.object = rig
    bag.parent = rig


case("a bag through the body", ["limbs_through_body"], walk={"arms_inward": (10, 13)}, props=None, at_least=True, parts=bag_on_the_arm,
     check=lambda info: True)

# Robotic motion: motion that is absent, whatever the style.
case("the body travels level, the trunk still", ["no_pelvis_motion", "trunk_still"], walk={"natural": False}, at_least=True)
case("straight legs swinging at a constant speed", ["stiff_knees", "linear_motion", "no_pelvis_motion", "trunk_still"],
     keys=gait.key_stiff_walk, at_least=True)
case("a limp", ["uneven_steps"], walk={"limp": 0.2})
case("an idle that breathes", [], keys=gait.key_breathing_idle)
case("a frozen idle", ["frozen"], keys=lambda rig: gait.key_breathing_idle(rig, amount=0.0))
case("a machine is exempt", [], walk={"natural": False}, NATURAL=False)


def near(key, expected, tolerance):
    def check(info):
        value = info.get(key)
        return True if value is not None and abs(value - expected) <= tolerance else f"{key} = {value}, expected {expected}"
    return check


case("the natural walk's numbers are reported", [], check=near("froude", gait.SPEED ** 2 / (9.81 * 0.79), 0.04))
case("speed beyond what walking legs can carry", ["too_fast_for_a_walk"], MAX_WALK_FROUDE=0.1)
case("the game's speed asks for the right cadence", [], GAME_SPEED=gait.SPEED * 1.2, check=near("playback_rate", 1.2, 0.08))
case("the game's speed asks for a frantic cadence", ["playback_rate_out_of_range"], GAME_SPEED=gait.SPEED * 2.0)

# Four legs.
QUADRUPED_FEET = ["hind_paw.L", "fore_paw.L", "hind_paw.R", "fore_paw.R"]


def quadruped_case(label, expected, order, at_least=False, **settings):
    mannequin.clear()
    body, rig = quadruped.build()
    action = quadruped.key_walk(rig, helpers, **order)
    report = run(ACTIONS=[action.name], ARMATURE=rig.name, ROOT_BONE="hips", FEET=QUADRUPED_FEET, **settings)
    entry = report["actions"][action.name]
    found = sorted(entry["issues"])
    cases.append({"case": label, "ok": (set(expected) <= set(found) if at_least else set(expected) == set(found) and report["passed"] == (not expected)),
                  "expected": sorted(expected), "found": found, "issues": entry["issues"], "info": entry["info"], "check": None})


quadruped_case("a four-legged walk in lateral sequence", [], {})
quadruped_case("a walk that must be a walk", [], {}, GAIT="walk")
quadruped_case("a trot is a trot", [], {"offsets": quadruped.TROT, "stance": 0.6}, GAIT="trot")
quadruped_case("a trot where a walk was asked for", ["wrong_gait"], {"offsets": quadruped.TROT, "stance": 0.6}, GAIT="walk")
quadruped_case("feet in no order", ["irregular_footfall"], {"offsets": quadruped.IRREGULAR})
quadruped_case("a tail that hangs dead", ["secondary_still"], {"tail": False})
quadruped_case("a sliding paw", ["foot_sliding"], {"root": 1.3}, at_least=True)

# The receipt.
proofs = os.path.join(os.path.dirname(script_path), "..", "..", "..", "..", "..", "dev", "library-tests", "Logs", "proofs-test")
mannequin.clear()
_, receipt_rig = mannequin.build()
receipt_action = gait.key_walk(receipt_rig, rig_helpers=helpers)
run(ACTIONS=[receipt_action.name], PROOF_DIR=proofs, PROOF_NAME="walk")
receipt_path = os.path.join(proofs, f"inspect_animation-walk-{receipt_action.name}.json")
cases.append({"case": "writes one receipt per clip", "ok": os.path.exists(receipt_path), "expected": [], "found": [], "issues": {}, "info": {}, "check": None})


def dense_hair(rig):
    # Hair with far more triangles than the body: the body is still what holds the feet.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=96, radius=0.13, location=rig.matrix_world @ rig.data.bones["head"].tail_local)
    hair = bpy.context.active_object
    hair.name = "Hair"
    bpy.ops.object.transform_apply(location=True)
    hair.vertex_groups.new(name="head").add([v.index for v in hair.data.vertices], 1.0, "REPLACE")
    hair.modifiers.new("Armature", "ARMATURE").object = rig


mannequin.clear()
_, dense_rig = mannequin.build()
dense_action = gait.key_walk(dense_rig, rig_helpers=helpers, root=1.5)
dense_hair(dense_rig)
dense_entry = run(ACTIONS=[dense_action.name])["actions"][dense_action.name]
cases.append({"case": "a sliding clip with hair denser than the body", "ok": "foot_sliding" in dense_entry["issues"], "expected": ["foot_sliding"],
              "found": sorted(dense_entry["issues"]), "issues": dense_entry["issues"], "info": dense_entry["info"], "check": None})

mannequin.clear()
_, nofeet_rig = mannequin.build()
nofeet_action = gait.key_walk(nofeet_rig, rig_helpers=helpers)
bpy.data.objects["Body"].vertex_groups.clear()
nofeet_entry = run(ACTIONS=[nofeet_action.name], MESHES=["Body"])["actions"][nofeet_action.name]
cases.append({"case": "a walk nothing measured can't pass", "ok": "feet_not_measured" in nofeet_entry["issues"], "expected": ["feet_not_measured"],
              "found": sorted(nofeet_entry["issues"]), "issues": nofeet_entry["issues"], "info": nofeet_entry["info"], "check": None})


def parented_bag(rig):
    # A rigid bag parented to the forearm's bone, in the body when the arm comes in.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.06)
    bag = bpy.context.active_object
    bag.name = "Bag"
    bag.parent = rig
    bag.parent_type = "BONE"
    bag.parent_bone = "forearm.L"


case("a bag parented to a bone, through the body", ["limbs_through_body"], walk={"arms_inward": (10, 13)}, at_least=True, parts=parented_bag)


# Bodies built from parts: separate objects hold the feet, and joints are no collisions.
def parts_walk(label, expected, merged=False, at_least=False, extra=None, **walk):
    mannequin.clear()
    armature = partsbody.person_rig()
    parts = partsbody.person(armature)
    if extra:
        parts = extra(armature, {p.name: p for p in parts}) or parts
    if merged:
        partsbody.merge([o for o in bpy.context.scene.objects if o.type == "MESH"])
    action = gait.key_walk(armature, rig_helpers=helpers, **walk)
    report = run(ACTIONS=[action.name], ARMATURE=armature.name)
    entry = report["actions"][action.name]
    found = sorted(entry["issues"])
    ok = set(expected) <= set(found) if at_least else found == sorted(expected)
    cases.append({"case": f"{label} ({'one mesh' if merged else 'objects'})", "ok": ok, "expected": sorted(expected), "found": found, "issues": entry["issues"], "info": entry["info"], "check": None})


def loose_hand(armature, parts):
    # The arm's part follows the upper arm alone: when the elbow moves, the hand part leaves it.
    bpy.data.objects.remove(parts["Arm.L"], do_unlink=True)
    bones = armature.data.bones
    partsbody.attach(partsbody.capsule("Arm.L", bones["upper_arm.L"].head_local, bones["forearm.L"].tail_local, 0.055, 0.035, segments=8), armature, ["upper_arm.L"])
    partsbody.attach(partsbody.capsule("HandPart", bones["hand.L"].head_local, bones["hand.L"].tail_local, 0.04, 0.03, segments=8), armature, ["hand.L"])


for merged in (False, True):
    parts_walk("a clean walk of a body of parts", [], merged)
    parts_walk("a body of parts sliding on both feet", ["foot_sliding"], merged, root=1.5)
    parts_walk("hands into the body of parts", ["limbs_through_body"], merged, at_least=True, arms_inward=(10, 13))
    parts_walk("a joint that comes apart in the clip", ["joint_opens"], merged, at_least=True, extra=loose_hand, arms_inward=(10, 13))


def animal_walk(label, expected, merged=False, at_least=False, extra=None, **order):
    mannequin.clear()
    armature = partsbody.animal_rig()
    parts = {p.name: p for p in partsbody.animal(armature)}
    if extra:
        extra(armature, parts)
    if merged:
        partsbody.merge([o for o in bpy.context.scene.objects if o.type == "MESH"])
    action = quadruped.key_walk(armature, helpers, **order)
    report = run(ACTIONS=[action.name], ARMATURE=armature.name, ROOT_BONE="hips", FEET=QUADRUPED_FEET)
    entry = report["actions"][action.name]
    found = sorted(entry["issues"])
    ok = set(expected) <= set(found) if at_least else found == sorted(expected)
    cases.append({"case": f"{label} ({'one mesh' if merged else 'objects'})", "ok": ok, "expected": sorted(expected), "found": found, "issues": entry["issues"], "info": entry["info"], "check": None})


def low_tail(armature, parts):
    # A tail that hangs into the hind legs: no joint connects them.
    bpy.data.objects.remove(parts["Tail"], do_unlink=True)
    partsbody.attach(partsbody.capsule("Tail", (0, 0.38, 0.48), (0, 0.27, 0.14), 0.04, 0.03, segments=6, rings=2), armature, ["tail.01", "tail.02"])
    for side, x in (("L", 0.02), ("R", -0.02)):
        partsbody.bump(parts[f"hindLeg.{side}"], (x, 0.26, 0.25), 0.09, (-x * 4.0, 0.0, 0.0))


for merged in (False, True):
    animal_walk("an animal of parts walks", [], merged)
    animal_walk("an animal of parts, sliding", ["foot_sliding"], merged, at_least=True, root=1.3)
    animal_walk("a tail through the hind legs", ["limbs_through_body"], merged, at_least=True, extra=low_tail)

failed = [c for c in cases if not c["ok"]]
for c in cases:
    print("CASE", "ok  " if c["ok"] else "FAIL", c["case"], "expected", c["expected"], "found", c["found"])
    if not c["ok"]:
        print("     ", c["issues"], c["check"], c["info"])
if failed:
    raise AssertionError(f"{len(failed)} of {len(cases)} cases failed")
