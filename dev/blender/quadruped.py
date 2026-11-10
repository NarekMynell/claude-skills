# A test animal for the animation script tests: built by modeling/scripts/build_body.py, facing -Y, left at +X, with a
# walk whose paws are placed by two-bone IK. Offsets choose the gait: when each paw lands, as a share of the cycle.
import math
import os

import bpy
from mathutils import Matrix, Vector

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "plugins", "modeling", "scripts"))
FRAMES = 40
STEP = 0.3
LIFT = 0.05
WALK = {"hind.L": 0.0, "fore.L": 0.25, "hind.R": 0.5, "fore.R": 0.75}
TROT = {"hind.L": 0.0, "fore.R": 0.0, "fore.L": 0.5, "hind.R": 0.5}
IRREGULAR = {"hind.L": 0.0, "fore.L": 0.08, "hind.R": 0.2, "fore.R": 0.33}


def build(name="Animal"):
    joints = {"pelvis": ((0, 0.28, 0.45), (0.11, 0.11), None), "belly": ((0, 0.05, 0.47), (0.12, 0.13), "pelvis"),
              "chest": ((0, -0.2, 0.48), (0.12, 0.12), "belly"), "neck": ((0, -0.34, 0.58), (0.06, 0.06), "chest"),
              "skull": ((0, -0.44, 0.66), (0.08, 0.08), "neck"), "nose": ((0, -0.55, 0.64), (0.04, 0.04), "skull"),
              "tail1": ((0, 0.43, 0.48), (0.03, 0.03), "pelvis"), "tail2": ((0, 0.55, 0.45), (0.02, 0.02), "tail1"),
              "tail3": ((0, 0.65, 0.40), (0.012, 0.012), "tail2")}
    bones = [("hips", "pelvis", "belly", None), ("spine", "belly", "chest", "hips"), ("neck", "neck", "skull", "spine"),
             ("head", "skull", "nose", "neck"), ("tail.01", "tail1", "tail2", "hips"), ("tail.02", "tail2", "tail3", "tail.01")]
    for end, y, parent, bone_parent in (("hind", 0.26, "pelvis", "hips"), ("fore", -0.2, "chest", "spine")):
        for side, x in (("L", 1), ("R", -1)):
            joints.update({
                f"{end}_hip.{side}": ((0.07 * x, y, 0.31), (0.04, 0.04), parent),
                f"{end}_knee.{side}": ((0.09 * x, y, 0.2), (0.035, 0.035), f"{end}_hip.{side}"),
                f"{end}_ankle.{side}": ((0.09 * x, y, 0.05), (0.028, 0.028), f"{end}_knee.{side}"),
                f"{end}_toe.{side}": ((0.09 * x, y - 0.05, 0.028), (0.028, 0.028), f"{end}_ankle.{side}"),
            })
            bones += [(f"{end}_thigh.{side}", f"{end}_hip.{side}", f"{end}_knee.{side}", bone_parent),
                      (f"{end}_shin.{side}", f"{end}_knee.{side}", f"{end}_ankle.{side}", f"{end}_thigh.{side}"),
                      (f"{end}_paw.{side}", f"{end}_ankle.{side}", f"{end}_toe.{side}", f"{end}_shin.{side}")]
    path = os.path.join(SCRIPTS, "build_body.py")
    namespace = {"__file__": path, "NAME": name, "JOINTS": joints, "BONES": bones, "SUBDIVISIONS": 0}
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return bpy.data.objects[namespace["result"]["mesh"]], bpy.data.objects[namespace["result"]["armature"]]


def _ik(hip, target, thigh, shin, bend_toward):
    to_target = target - hip
    distance = min(to_target.length, thigh + shin - 1e-4)
    along = to_target.normalized()
    cos_hip = (thigh ** 2 + distance ** 2 - shin ** 2) / (2 * thigh * distance)
    angle = math.acos(max(-1.0, min(1.0, cos_hip)))
    bend = (bend_toward - along * bend_toward.dot(along)).normalized()
    return hip + (along * math.cos(angle) + bend * math.sin(angle)) * thigh


def key_walk(rig, helpers, name="Walk", offsets=None, stance=0.7, root=1.0, tail=True):
    """stance: the share of the cycle a paw stays down. root: 1 moves the body at the speed of the paws."""
    offsets = offsets or WALK
    bones = rig.data.bones
    world = rig.matrix_world

    def rest(bone):
        return world @ bones[bone].head_local

    paw_direction = {leg: (world @ bones[f"{leg.split('.')[0]}_paw.{leg.split('.')[1]}"].tail_local - rest(f"{leg.split('.')[0]}_paw.{leg.split('.')[1]}")).normalized()
                     for leg in offsets}
    # A paw stays down for `stance` of the cycle while it passes under the body: the body covers STEP in that time.
    cycle_travel = STEP / stance * root

    action = bpy.data.actions.new(name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    bpy.context.scene.render.fps = 30
    for frame in range(0, FRAMES + 1):
        t = frame / FRAMES
        for pose_bone in rig.pose.bones:
            pose_bone.matrix_basis.identity()
            pose_bone.rotation_mode = "QUATERNION"
        bpy.context.view_layer.update()
        hips = rig.pose.bones["hips"]
        matrix = hips.matrix.copy()
        matrix.translation += Vector((0.0, -cycle_travel * t, -0.02 + 0.006 * math.sin(4 * math.pi * t)))
        hips.matrix = matrix
        bpy.context.view_layer.update()
        helpers.turn_bone(rig, "spine", (0.0, 0.0, 1.0), 4.0 * math.sin(2 * math.pi * (t - 0.05)))
        helpers.turn_bone(rig, "neck", (0.0, 0.0, 1.0), -5.0 * math.sin(2 * math.pi * (t - 0.12)))
        if tail:
            helpers.turn_bone(rig, "tail.01", (0.0, 0.0, 1.0), 12.0 * math.sin(2 * math.pi * (t - 0.1)))
            helpers.turn_bone(rig, "tail.02", (0.0, 0.0, 1.0), 16.0 * math.sin(2 * math.pi * (t - 0.2)))
        for leg, offset in offsets.items():
            end, side = leg.split(".")
            phase = (t - offset) % 1.0
            # At phase 0 the paw lands in front, and stays on the ground while the body passes over it.
            if phase < stance:
                along = -STEP / 2 + STEP * phase / stance
                lift = 0.0
            else:
                u = (phase - stance) / (1.0 - stance)
                along = STEP / 2 - STEP * u * u * (3 - 2 * u)
                lift = LIFT * math.sin(math.pi * u)
            hip = world @ rig.pose.bones[f"{end}_thigh.{side}"].head
            base = rest(f"{end}_paw.{side}")
            plant = Vector((base.x, base.y + along - cycle_travel * t, base.z + lift))
            thigh = bones[f"{end}_thigh.{side}"].length
            shin = bones[f"{end}_shin.{side}"].length
            bend = Vector((0.0, -1.0, 0.0)) if end == "fore" else Vector((0.0, 1.0, 0.0))
            knee = _ik(hip, plant, thigh, shin, bend)
            helpers.point_bone(rig, f"{end}_thigh.{side}", knee - hip)
            helpers.point_bone(rig, f"{end}_shin.{side}", plant - knee)
            helpers.point_bone(rig, f"{end}_paw.{side}", paw_direction[leg])
        for pose_bone in rig.pose.bones:
            pose_bone.keyframe_insert("location", frame=frame)
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame)
    action.frame_range = (0, FRAMES)
    action.use_frame_range = True
    return action
