# Runs modeling/scripts/build_body.py: a cartoon figure, low and mid poly, must pass inspect_character.py, and a
# skeleton with two roots must be refused.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <build_body.py>
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mannequin  # noqa: E402

script_path = sys.argv[sys.argv.index("--") + 1]
inspect_path = os.path.join(os.path.dirname(script_path), "inspect_character.py")
problems = []


def run(path, **settings):
    namespace = {"__file__": path}
    namespace.update(settings)
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return namespace["result"]


# A cartoon figure about 3.5 heads tall: big head, short legs, mitten hands. Each thigh has a joint below the hip,
# so the hip crease has loops to fold with.
JOINTS = {"pelvis": ((0, 0, 0.45), (0.10, 0.07), None), "chest": ((0, 0, 0.62), (0.13, 0.09), "pelvis"),
          "neck": ((0, 0, 0.74), (0.045, 0.045), "chest"), "head": ((0, 0, 0.86), (0.13, 0.12), "neck"),
          "crown": ((0, 0, 0.98), (0.09, 0.085), "head")}
BONES = [("hips", "pelvis", "chest", None), ("spine", "chest", "neck", "hips"), ("neck", "neck", "head", "spine"),
         ("head", "head", "crown", "neck")]
for side, x in (("L", 1), ("R", -1)):
    JOINTS.update({
        f"hip.{side}": ((0.06 * x, 0, 0.35), (0.05, 0.05), "pelvis"),
        f"thigh.{side}": ((0.063 * x, 0, 0.29), (0.047, 0.047), f"hip.{side}"),
        f"knee.{side}": ((0.065 * x, 0, 0.21), (0.042, 0.042), f"thigh.{side}"),
        f"ankle.{side}": ((0.065 * x, 0, 0.06), (0.035, 0.035), f"knee.{side}"),
        f"toe.{side}": ((0.065 * x, -0.08, 0.03), (0.03, 0.03), f"ankle.{side}"),
        f"shoulder.{side}": ((0.15 * x, 0, 0.68), (0.04, 0.04), "chest"),
        f"elbow.{side}": ((0.26 * x, 0, 0.58), (0.032, 0.032), f"shoulder.{side}"),
        f"wrist.{side}": ((0.36 * x, 0, 0.49), (0.028, 0.028), f"elbow.{side}"),
        f"mitt.{side}": ((0.41 * x, 0, 0.445), (0.03, 0.025), f"wrist.{side}"),
    })
    BONES += [(f"upper_arm.{side}", f"shoulder.{side}", f"elbow.{side}", "spine"),
              (f"forearm.{side}", f"elbow.{side}", f"wrist.{side}", f"upper_arm.{side}"),
              (f"hand.{side}", f"wrist.{side}", f"mitt.{side}", f"forearm.{side}"),
              (f"thigh.{side}", f"hip.{side}", f"knee.{side}", "hips"),
              (f"shin.{side}", f"knee.{side}", f"ankle.{side}", f"thigh.{side}"),
              (f"foot.{side}", f"ankle.{side}", f"toe.{side}", f"shin.{side}")]

for levels in (0, 1):
    mannequin.clear()
    built = run(script_path, NAME="Toon", JOINTS=JOINTS, BONES=BONES, SUBDIVISIONS=levels)
    report = run(inspect_path, TARGETS=[built["mesh"]], SYMMETRIC=[built["mesh"]], FINGERS=0)
    if not report["passed"]:
        problems.append(f"subdivisions {levels}: {report['issues']}")

mannequin.clear()
broken = dict(JOINTS, chest=((0, 0, 0.62), (0.13, 0.09), None))
try:
    run(script_path, NAME="Broken", JOINTS=broken, BONES=BONES)
    problems.append("two roots were accepted")
except ValueError:
    pass

print("BUILD", json.dumps({"problems": problems}))
if problems:
    raise AssertionError("; ".join(problems))
