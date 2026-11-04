# Keys a walk cycle on the test mannequin for the animation script tests. Feet are placed by two-bone IK: in place,
# the planted foot moves back at the walking speed; with root motion, the hips move forward and the planted foot stays.
# Arguments switch on one known defect each.
import math

import bpy
from mathutils import Matrix, Vector

FRAMES = 30          # one cycle at 30 fps: 1 s
STEP = 0.5           # metres from one foot's plant to the other's
SPEED = 2 * STEP     # metres per second: a stride (2 steps) per cycle
HIP_DROP = 0.05      # the hips sit lower than in the rest pose, so the planted leg can reach
LIFT = 0.07
ARM_SWING = math.radians(18)
BOB = 0.015          # the hips rise over the planted leg and sink between steps
SWAY = 0.012         # and lean over the planted foot
HIP_YAW = 5.0        # degrees each way; the shoulders turn against the hips


def _ik(hip, target, thigh, shin):
    """Knee position for a leg from hip to target, bending forward (-Y)."""
    to_target = target - hip
    distance = min(to_target.length, thigh + shin - 1e-4)
    along = to_target.normalized()
    cos_hip = (thigh ** 2 + distance ** 2 - shin ** 2) / (2 * thigh * distance)
    angle = math.acos(max(-1.0, min(1.0, cos_hip)))
    forward = Vector((0.0, -1.0, 0.0))
    bend = (forward - along * forward.dot(along)).normalized()
    return hip + (along * math.cos(angle) + bend * math.sin(angle)) * thigh


def _foot(phase):
    """Foot position relative to its hip, in place: (y, lift), for phase 0..1 (0 = heel strike in front)."""
    if phase < 0.5:
        u = phase / 0.5
        return -STEP / 2 + STEP * u, 0.0
    u = (phase - 0.5) / 0.5
    smooth = u * u * (3 - 2 * u)
    return STEP / 2 - STEP * smooth, LIFT * math.sin(math.pi * u)


def key_walk(rig, name="Walk", root=1.0, same_side_arms=False, feet_offset=0.0, end=FRAMES, pop_frame=None,
             arms_inward=None, rig_helpers=None, natural=True, limp=0.0):
    """root: 0 in place, 1 root motion that matches the stride, more than 1 root motion faster than the feet.
    arms_inward: (first, last) frames where the forearms point into the body, easing in and out over 4 frames.
    natural: False keeps the body level and the trunk still: legs and arms alone.
    limp: moves the right foot's timing away from half a cycle."""
    helpers = rig_helpers
    bones = rig.data.bones
    world = rig.matrix_world

    def rest(name):
        return world @ bones[name].head_local

    thigh = (rest("shin.L") - rest("thigh.L")).length
    shin = (rest("foot.L") - rest("shin.L")).length
    foot_dir = {s: (rest(f"toe.{s}") - rest(f"foot.{s}")).normalized() for s in "LR"}
    toe_dir = {s: (world @ bones[f"toe.{s}"].tail_local - rest(f"toe.{s}")).normalized() for s in "LR"}
    arm_dir = {s: (rest(f"forearm.{s}") - rest(f"upper_arm.{s}")).normalized() for s in "LR"}
    ankle_height = rest("foot.L").z + feet_offset

    action = bpy.data.actions.new(name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    scene = bpy.context.scene
    scene.render.fps = 30
    for frame in range(0, end + 1):
        t = frame / FRAMES
        for pose_bone in rig.pose.bones:
            pose_bone.matrix_basis.identity()
        bpy.context.view_layer.update()
        bob = -BOB * math.cos(4 * math.pi * t) if natural else 0.0  # lowest at each heel strike, when both feet are down
        sway = SWAY * math.sin(2 * math.pi * t) if natural else 0.0  # toward the left foot while it stands
        offset = Vector((sway, -SPEED * t * root, -HIP_DROP + bob))
        hips = rig.pose.bones["hips"]
        matrix = hips.matrix.copy()
        matrix.translation = matrix.translation + offset
        hips.matrix = matrix
        bpy.context.view_layer.update()
        if natural:
            # The left hip leads at the left heel strike, the trunk answers later and the other way, joint by joint.
            helpers.turn_bone(rig, "hips", (0.0, 0.0, 1.0), -HIP_YAW * math.cos(2 * math.pi * t))
            helpers.turn_bone(rig, "spine", (0.0, 0.0, 1.0), 1.1 * HIP_YAW * math.cos(2 * math.pi * (t - 0.04)))
            helpers.turn_bone(rig, "chest", (0.0, 0.0, 1.0), 1.1 * HIP_YAW * math.cos(2 * math.pi * (t - 0.08)))
            helpers.turn_bone(rig, "head", (0.0, 0.0, 1.0), -1.2 * HIP_YAW * math.cos(2 * math.pi * (t - 0.12)))
        for side, phase_shift in (("L", 0.0), ("R", 0.5 + limp)):
            y, lift = _foot((t + phase_shift) % 1.0)
            hip = world @ rig.pose.bones[f"thigh.{side}"].head
            # Relative to the hips the legs move as in place; root 1 keeps the planted foot still in the world.
            plant = Vector((rest(f"foot.{side}").x, y - SPEED * t * root, ankle_height + lift))
            knee = _ik(hip, plant, thigh, shin)
            helpers.point_bone(rig, f"thigh.{side}", knee - hip)
            helpers.point_bone(rig, f"shin.{side}", plant - knee)
            helpers.point_bone(rig, f"foot.{side}", foot_dir[side])
            helpers.point_bone(rig, f"toe.{side}", toe_dir[side])
        for side, sign in (("L", 1.0), ("R", -1.0)):
            # The left arm swings forward with the right leg: back at the left heel strike (t = 0).
            swing = -sign * ARM_SWING * math.cos(2 * math.pi * t)
            if same_side_arms:
                swing = -swing
            direction = arm_dir[side].copy()
            direction.rotate(Matrix.Rotation(-swing, 3, "X"))  # a negative turn about +X moves the hand to -Y
            helpers.point_bone(rig, f"upper_arm.{side}", direction)
            inward = 0.0
            if arms_inward:
                first, last = arms_inward
                inward = max(0.0, min(1.0, (frame - first + 4) / 4, (last + 4 - frame) / 4))
            target = Vector((-0.95 * sign, -0.05, -0.3)).normalized()
            trailing = direction.copy()
            if natural:
                # The forearm follows the upper arm late, bent a little at the elbow.
                late = -sign * ARM_SWING * math.cos(2 * math.pi * (t - 0.06))
                trailing = arm_dir[side].copy()
                trailing.rotate(Matrix.Rotation(-(late if not same_side_arms else -late) * 1.2 - math.radians(12), 3, "X"))
            helpers.point_bone(rig, f"forearm.{side}", trailing.slerp(target, inward))
        if frame == pop_frame:
            helpers.point_bone(rig, "upper_arm.L", Vector((0.2, 0.0, 1.0)))
        for pose_bone in rig.pose.bones:
            pose_bone.keyframe_insert("location", frame=frame)
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame)
    action.frame_range = (0, end)
    action.use_frame_range = True
    return action


def key_stiff_walk(rig, name="Stiff", frames=FRAMES):
    """The walk code tends to write first: straight legs and arms swinging about the hips at a constant speed, keyed at
    the extremes with linear interpolation, everything on the same beat, nothing else moving. For checks that must
    call it robotic."""
    action = bpy.data.actions.new(name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    bpy.context.scene.render.fps = 30
    swing = math.radians(22)
    for frame in range(0, frames + 1):
        t = frame / frames
        # A triangle wave: constant speed, then an instant turn.
        wave = 4 * abs(((t + 0.25) % 1.0) - 0.5) - 1
        for pose_bone in rig.pose.bones:
            pose_bone.matrix_basis.identity()
            pose_bone.rotation_mode = "QUATERNION"
        for side, sign in (("L", 1.0), ("R", -1.0)):
            for bone, amount in ((f"thigh.{side}", sign), (f"upper_arm.{side}", -sign)):
                rig.pose.bones[bone].rotation_quaternion = Matrix.Rotation(swing * wave * amount, 4, "X").to_quaternion()
        bpy.context.view_layer.update()
        for pose_bone in rig.pose.bones:
            pose_bone.keyframe_insert("location", frame=frame)
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame)
    action.frame_range = (0, frames)
    action.use_frame_range = True
    return action


def key_breathing_idle(rig, name="Idle", frames=60, amount=2.5):
    """An idle: the chest rises and falls, the weight shifts. amount 0 freezes it."""
    action = bpy.data.actions.new(name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action
    for frame in range(0, frames + 1):
        t = frame / frames
        for pose_bone in rig.pose.bones:
            pose_bone.matrix_basis.identity()
            pose_bone.rotation_mode = "QUATERNION"
        rig.pose.bones["chest"].rotation_quaternion = Matrix.Rotation(math.radians(amount) * math.sin(2 * math.pi * t), 4, "X").to_quaternion()
        rig.pose.bones["spine"].rotation_quaternion = Matrix.Rotation(math.radians(amount) * math.sin(2 * math.pi * (t - 0.1)), 4, "Y").to_quaternion()
        for pose_bone in rig.pose.bones:
            pose_bone.keyframe_insert("location", frame=frame)
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame)
    action.frame_range = (0, frames)
    action.use_frame_range = True
    return action
