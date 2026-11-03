# Runs game-assets/scripts/inspect_animation.py against walk cycles with known defects and checks each report.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <inspect_animation.py>
import os
import sys
import types

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gait  # noqa: E402
import mannequin  # noqa: E402

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


def case(label, expected, walk=None, check=None, props=None, **settings):
    mannequin.clear()
    body, rig = mannequin.build()
    action = gait.key_walk(rig, rig_helpers=helpers, **(walk or {}))
    if props:
        props(rig)
        settings["PROPS"] = ["Prop"]
    report = run(ACTIONS=[action.name], **settings)
    entry = report["actions"][action.name]
    found = sorted(entry["issues"])
    ok = found == sorted(expected) and report["passed"] == (not expected)
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

failed = [c for c in cases if not c["ok"]]
for c in cases:
    print("CASE", "ok  " if c["ok"] else "FAIL", c["case"], "expected", c["expected"], "found", c["found"])
    if not c["ok"]:
        print("     ", c["issues"], c["check"], c["info"])
if failed:
    raise AssertionError(f"{len(failed)} of {len(cases)} cases failed")
