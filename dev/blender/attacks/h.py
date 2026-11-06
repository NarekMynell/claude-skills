# Harness for the attack cases: scenes built to fool inspect_character.py from both sides, by an adversarial review, kept as
# regression tests. Runs named cases headless and prints one line per case; dev/run-attack-tests.sh compares them with what is
# accepted.
import sys
sys.dont_write_bytecode = True  # nothing written next to the repo's modules
import json
import math
import os
import tempfile
import traceback
import types

import bmesh
import bpy
from mathutils import Matrix, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SCRIPTS = REPO + "/plugins/unity-dev/skills/game-assets/scripts"
P = SCRIPTS + "/inspect_character.py"
A = SCRIPTS + "/inspect_animation.py"
C = SCRIPTS + "/cut_hidden_faces.py"
R = SCRIPTS + "/render_views.py"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("ATTACK_OUT") or os.path.join(tempfile.gettempdir(), "unity-dev-attacks")

sys.path.insert(0, REPO + "/dev/blender")
import mannequin  # noqa: E402
import partsbody  # noqa: E402
import quadruped  # noqa: E402
import gait  # noqa: E402

_rn = {"__file__": SCRIPTS + "/rig.py", "__name__": "rig_helpers"}
exec(compile(open(SCRIPTS + "/rig.py").read(), SCRIPTS + "/rig.py", "exec"), _rn)
helpers = types.SimpleNamespace(**_rn)

capsule, lathe, ring, bump, attach, merge = partsbody.capsule, partsbody.lathe, partsbody.ring, partsbody.bump, partsbody.attach, partsbody.merge


def _exec(path, **settings):
    ns = {"__file__": path}
    ns.update(settings)
    exec(compile(open(path).read(), path, "exec"), ns)
    return ns["result"]


def check(**settings):
    return _exec(P, **settings)


def check_anim(**settings):
    return _exec(A, **settings)


def cut(**settings):
    return _exec(C, **settings)


def paint(obj, rgba, name=None):
    name = name or f"m{round(rgba[0]*255)}_{round(rgba[1]*255)}_{round(rgba[2]*255)}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    full = tuple(rgba) + ((1.0,) if len(rgba) == 3 else ())
    mat.diffuse_color = full
    if mat.node_tree:
        bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            bsdf.inputs["Base Color"].default_value = full
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


SKIN = (0.9, 0.7, 0.55)
RED = (0.8, 0.1, 0.1)
BLUE = (0.15, 0.25, 0.7)
GREEN = (0.15, 0.55, 0.2)
DARK = (0.12, 0.1, 0.1)
YELLOW = (0.9, 0.8, 0.2)
GRAY = (0.5, 0.5, 0.55)
BROWN = (0.4, 0.25, 0.1)


def paint_person(parts, color=SKIN):
    for o in parts.values():
        paint(o, color)


def render(name, targets=None, **settings):
    os.makedirs(OUT, exist_ok=True)
    defaults = {"OUTPUT_DIR": OUT, "NAME": name, "COLOR": "MATERIAL", "VIEWS": ["front", "back", "left", "front_left", "top", "bottom"], "COLUMNS": 3, "TILE": 512, "FLOOR": True, "CLOSEUPS": []}
    defaults.update(settings)
    if targets:
        defaults["TARGETS"] = targets
    r = _exec(R, **defaults)
    return r["sheet"]


def meshes():
    return [o.name for o in bpy.context.scene.objects if o.type == "MESH"]


def person(extra=None, skip=(), sections=1, merged=False, paint_skin=True):
    """The partsbody person. `extra(rig, parts)` may change it and return settings."""
    rig = partsbody.person_rig()
    parts = {o.name: o for o in partsbody.person(rig, skip, sections)}
    if paint_skin:
        paint_person(parts)
    settings = (extra(rig, parts) if extra else None) or {}
    names = meshes()
    if merged:
        partsbody.merge([bpy.data.objects[n] for n in names])
        names = ["Merged"]
    settings.setdefault("TARGETS", names)
    settings.setdefault("ARMATURE", rig.name)
    settings.setdefault("FINGERS", 5)
    return settings


def animal(extra=None, merged=False):
    rig = partsbody.animal_rig()
    parts = {o.name: o for o in partsbody.animal(rig)}
    paint_person(parts, BROWN)
    settings = (extra(rig, parts) if extra else None) or {}
    names = meshes()
    if merged:
        partsbody.merge([bpy.data.objects[n] for n in names])
        names = ["Merged"]
    settings.setdefault("TARGETS", names)
    settings.setdefault("ARMATURE", rig.name)
    return settings


def on(obj, rig, *bones):
    return attach(obj, rig, list(bones))


def make_rig(name, bones):
    """bones: list of (name, head, tail, parent)."""
    data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for bone_name, head, tail, parent in bones:
        b = data.edit_bones.new(bone_name)
        b.head, b.tail = Vector(head), Vector(tail)
        if parent:
            b.parent = made[parent]
        made[bone_name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def parent_to_bone(obj, rig, bone):
    """Rigid part on a bone, kept where it was built."""
    b = rig.data.bones[bone]
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_parent_inverse = (rig.matrix_world @ Matrix.Translation(b.tail_local) @ b.matrix_local.to_3x3().to_4x4()).inverted()
    return obj


def apply_named_pose(rig, name, humanoid=True):
    """Puts the rig in one of the check's test poses. For renders."""
    roles = helpers.map_roles(rig)
    poses = helpers.test_poses(roles) if humanoid else helpers.creature_poses(rig, roles)
    pose_roles = roles if humanoid else helpers.identity_roles(rig)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    helpers.apply_pose(rig, pose_roles, poses[name])
    bpy.context.view_layer.update()


def rest_rig(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


CASES = {}


def case(name, should, note=""):
    def deco(fn):
        CASES[name] = (fn, should, note)
        return fn
    return deco


def short(report):
    issues = report.get("issues", {})
    return {k: (v if not isinstance(v, (dict, list)) or len(str(v)) < 230 else str(v)[:230] + "...") for k, v in issues.items()}


def run_cases(selected=None, render_all=False):
    from time import time
    names = selected or list(CASES)
    results = []
    for name in names:
        fn, should, note = CASES[name]
        mannequin.clear()
        t = time()
        try:
            settings = fn() or {}
            after = settings.pop("_after", None)
            shot = settings.pop("_render", None)
            if render_all or (selected and shot is not None):
                try:
                    render(name, **(shot or {}))
                except Exception as e:
                    print("RENDER ERROR", name, e)
            report = check(**settings)
            if after:
                after(report)
            verdict = "PASS" if report["passed"] else "FAIL"
            correct = (verdict == "PASS") == (should == "pass")
            mark = "ok  " if correct else "WRONG"
            print(f"[{mark}] {name}: should {should}, check says {verdict} ({time() - t:.1f}s) {json.dumps(short(report), default=str)}")
            results.append({"case": name, "should": should, "verdict": verdict, "correct": correct, "issues": report["issues"], "examples": report.get("examples"), "info": report.get("info")})
        except Exception as e:
            print(f"[CRASH] {name}: {type(e).__name__}: {e}")
            traceback.print_exc(limit=4, file=sys.stdout)
            results.append({"case": name, "should": should, "verdict": "CRASH", "error": str(e)})
    return results


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    render_all = "--render" in args
    args = [a for a in args if a != "--render"]
    results = run_cases(args or None, render_all)
    tag = os.path.splitext(os.path.basename(sys.argv[sys.argv.index("--python") + 1]))[0]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{tag}.json"), "a") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    wrong = [r["case"] for r in results if not r.get("correct")]
    print("WRONG:", wrong)
