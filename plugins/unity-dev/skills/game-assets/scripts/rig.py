"""Shared helpers for the character and animation scripts in this folder; the other scripts load this file.

Maps an armature's bones to Unity Humanoid roles by name, checks the mapping against the bones' positions, and poses
bones by world-space direction, which works whatever each rig's bone rolls are.
Blender convention assumed: the character faces -Y, its left side is +X, up is +Z.
"""

import re

import bpy
from mathutils import Matrix, Vector

REQUIRED = (
    "Hips", "Spine", "Head",
    "LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
)
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")
SEGMENTS = ("Proximal", "Intermediate", "Distal")

# Name cores (lower case, without side markers and digits) per role, most specific first.
_LIMBS = (
    ("Shoulder", {"shoulder", "clavicle", "collar", "collarbone"}),
    ("LowerArm", {"forearm", "lowerarm", "elbow"}),
    ("UpperArm", {"upperarm", "uparm", "arm", "humerus"}),
    ("Hand", {"hand", "wrist"}),
    ("UpperLeg", {"upleg", "upperleg", "thigh", "femur"}),
    ("LowerLeg", {"lowerleg", "leg", "calf", "shin", "knee"}),
    ("Foot", {"foot", "ankle"}),
    ("Toes", {"toe", "toes", "toebase", "ball"}),
)
_CENTER = (
    ("Hips", {"hips", "pelvis", "hip"}),
    ("UpperChest", {"upperchest"}),
    ("Chest", {"chest"}),
    ("Spine", {"spine", "torso", "abdomen"}),
    ("Neck", {"neck"}),
    ("Head", {"head"}),
)
_FINGER_WORDS = {"thumb": "Thumb", "index": "Index", "middle": "Middle", "ring": "Ring", "pinky": "Little", "little": "Little"}
_SKIP_WORDS = {
    "end", "nub", "top", "tip", "ik", "fk", "pole", "target", "ctrl", "control", "mch", "org", "twist", "roll", "socket",
    "helper", "corrective", "meta", "metacarpal", "palm", "carpal", "jiggle", "dyn", "prop", "weapon", "attach", "eye",
    "jaw", "tongue", "teeth", "brow", "lid", "lip", "cheek", "breast", "hair", "cloth", "skirt", "cape", "tail",
}
_PREFIX = re.compile(r"^(mixamorig\d*[:_]|def[-_.]|cc_base_|bip\d*[ _])", re.IGNORECASE)


def words(name):
    """Splits a bone name into lower-case words: 'mixamorig:LeftHandThumb1' -> ['left', 'hand', 'thumb', '1']."""
    name = _PREFIX.sub("", name)
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r"([A-Za-z])(\d)", r"\1 \2", name)
    name = re.sub(r"(\d)([A-Za-z])", r"\1 \2", name)
    return re.sub(r"[^A-Za-z0-9]+", " ", name).lower().split()


def name_side(name):
    """'L', 'R' or None, from side markers in the name."""
    tokens = set(words(name))
    left, right = bool(tokens & {"l", "left"}), bool(tokens & {"r", "right"})
    return "L" if left and not right else "R" if right and not left else None


def _depth(bone):
    depth = 0
    while bone.parent:
        bone, depth = bone.parent, depth + 1
    return depth


def _classify(bone):
    tokens = words(bone.name)
    if not tokens or set(tokens) & _SKIP_WORDS:
        return None
    side = name_side(bone.name)
    core_words = [t for t in tokens if t not in {"l", "r", "left", "right"} and not t.isdigit()]
    finger = next((_FINGER_WORDS[t] for t in core_words if t in _FINGER_WORDS), None)
    if finger is None and "finger" in core_words:
        # MakeHuman's skeleton numbers the fingers from the thumb: finger1-1.L ... finger5-3.L.
        numbers = [t for t in tokens if t.isdigit()]
        if numbers and 1 <= int(numbers[0]) <= 5:
            finger = FINGERS[int(numbers[0]) - 1]
    if finger:
        return ("finger", side, finger) if side else None
    core = "".join(core_words)
    if side:
        return next((("limb", side, role) for role, cores in _LIMBS if core in cores), None)
    return next((("center", None, role) for role, cores in _CENTER if core in cores), None)


def map_roles(armature, overrides=None):
    """Unity Humanoid role -> bone name, from bone names, deform bones first. `overrides` wins."""
    bones = sorted(armature.data.bones, key=lambda b: (not b.use_deform, _depth(b), b.name))
    roles, chains = {}, {}
    for bone in bones:
        kind = _classify(bone)
        if kind is None:
            continue
        group, side, role = kind
        if group == "finger":
            chains.setdefault((side, role), []).append(bone)
        elif group == "center" and role == "Spine":
            chains.setdefault((None, "Spine"), []).append(bone)
        else:
            key = (("Left" if side == "L" else "Right") + role) if side else role
            roles.setdefault(key, bone.name)
    spine = sorted(chains.pop((None, "Spine"), []), key=_depth)
    for role, bone in zip(("Spine", "Chest", "UpperChest"), spine):
        if role == "Spine" or role not in roles:
            roles.setdefault(role, bone.name)
    for (side, finger), chain in chains.items():
        prefix = "Left" if side == "L" else "Right"
        for segment, bone in zip(SEGMENTS, sorted(chain, key=_depth)):
            roles[f"{prefix}{finger}{segment}"] = bone.name
    roles.update(overrides or {})
    return {role: name for role, name in roles.items() if name in armature.data.bones}


def head(armature, bone_name):
    return armature.matrix_world @ armature.data.bones[bone_name].head_local


def tail(armature, bone_name):
    return armature.matrix_world @ armature.data.bones[bone_name].tail_local


def is_ancestor(armature, ancestor, bone_name):
    bone = armature.data.bones[bone_name].parent
    while bone:
        if bone.name == ancestor:
            return True
        bone = bone.parent
    return False


def deforming_armature(mesh_object):
    for modifier in mesh_object.modifiers:
        if modifier.type == "ARMATURE" and modifier.object and modifier.show_viewport:
            return modifier.object
    return None


class PoseState:
    """Saves an armature's pose, action and pose position, and restores them on exit. Inside, the rig shows its pose
    without its action, so poses set by the caller stay."""

    def __init__(self, armature):
        self.armature = armature

    def __enter__(self):
        armature = self.armature
        self.basis = {pb.name: pb.matrix_basis.copy() for pb in armature.pose.bones}
        self.position = armature.data.pose_position
        animation = armature.animation_data
        self.action = animation.action if animation else None
        self.slot = getattr(animation, "action_slot", None) if animation else None
        if animation and animation.action:
            animation.action = None
        armature.data.pose_position = "POSE"
        bpy.context.view_layer.update()
        return self

    def reset(self):
        for pb in self.armature.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def __exit__(self, *exc):
        armature = self.armature
        for pb in armature.pose.bones:
            if pb.name in self.basis:
                pb.matrix_basis = self.basis[pb.name]
        if self.action is not None:
            armature.animation_data.action = self.action
            if self.slot is not None and hasattr(armature.animation_data, "action_slot"):
                try:
                    armature.animation_data.action_slot = self.slot
                except (TypeError, RuntimeError):
                    pass
        armature.data.pose_position = self.position
        bpy.context.view_layer.update()
        return False


def _rotate_about_head(armature, pose_bone, world_rotation):
    world3 = armature.matrix_world.to_3x3().normalized()
    local = (world3.inverted() @ world_rotation @ world3).to_4x4()
    matrix = pose_bone.matrix.copy()
    pivot = matrix.translation.copy()
    pose_bone.matrix = Matrix.Translation(pivot) @ local @ Matrix.Translation(-pivot) @ matrix
    bpy.context.view_layer.update()


def point_bone(armature, bone_name, direction):
    """Turns a pose bone so that it points along `direction` (world space), around its head."""
    pose_bone = armature.pose.bones[bone_name]
    current = (armature.matrix_world.to_3x3() @ pose_bone.matrix.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    target = Vector(direction).normalized()
    _rotate_about_head(armature, pose_bone, current.rotation_difference(target).to_matrix())


def turn_bone(armature, bone_name, axis, degrees):
    """Rotates a pose bone around a world-space axis through its head."""
    import math
    rotation = Matrix.Rotation(math.radians(degrees), 3, Vector(axis).normalized())
    _rotate_about_head(armature, armature.pose.bones[bone_name], rotation)


def _both(role, direction, right=None):
    """Left and right entries; the right side mirrors the left unless given."""
    return [("Left" + role, direction), ("Right" + role, right or (-direction[0], direction[1], direction[2]))]


_LIMB_POSES = {
    "arms_down": _both("UpperArm", (0.25, 0.0, -1.0)) + _both("LowerArm", (0.2, -0.1, -1.0)),
    "arms_up": _both("UpperArm", (0.35, 0.0, 1.0)) + _both("LowerArm", (0.25, 0.0, 1.0)),
    "arms_forward": _both("UpperArm", (0.15, -1.0, -0.15)) + _both("LowerArm", (-0.5, -0.85, 0.15)),
    "squat": _both("UpperLeg", (0.2, -1.0, -0.25)) + _both("LowerLeg", (0.05, 0.3, -1.0)),
    "stride": _both("UpperLeg", (0.05, -0.6, -1.0), right=(-0.05, 0.45, -1.0))
    + _both("LowerLeg", (0.0, 0.2, -1.0), right=(0.0, 0.8, -1.0)),
}


def test_poses(roles):
    """The deformation test poses this rig supports: name -> list of (role, target). A target is a world direction
    to point the bone along, ("turn", axis, degrees), or ("curl", side, degrees) toward the palm."""
    poses = {}
    for name, steps in _LIMB_POSES.items():
        steps = [step for step in steps if step[0] in roles]
        if steps:
            poses[name] = steps
    turns = [(role, ("turn", (0.0, 0.0, 1.0), degrees)) for role, degrees in (("Spine", 20), ("Chest", 15), ("Head", 40)) if role in roles]
    if turns:
        poses["twist"] = turns
    curl = [
        (f"{side}{finger}{segment}", ("curl", side, 35 if finger == "Thumb" else 60))
        for side in ("Left", "Right") for finger in FINGERS for segment in SEGMENTS
        if f"{side}{finger}{segment}" in roles
    ]
    if curl:
        poses["fists"] = curl
    return poses


def apply_pose(armature, roles, steps):
    """Applies one test pose from `test_poses`, parents before children."""
    def depth(step):
        return _depth(armature.data.bones[roles[step[0]]])

    for role, target in sorted(steps, key=depth):
        bone = roles[role]
        if isinstance(target[0], str) and target[0] == "turn":
            turn_bone(armature, bone, target[1], target[2])
        elif isinstance(target[0], str) and target[0] == "curl":
            palm = palm_normal(armature, roles, target[1])
            pose_bone = armature.pose.bones[bone]
            direction = (armature.matrix_world.to_3x3() @ pose_bone.matrix.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
            if palm is None or abs(direction.dot(palm)) > 0.95:
                continue
            turn_bone(armature, bone, direction.cross(palm), target[2])
        else:
            point_bone(armature, bone, target)


def palm_normal(armature, roles, side):
    """World direction the palm faces, from the finger roots, or None without index and little fingers."""
    hand = roles.get(f"{side}Hand")
    index = roles.get(f"{side}IndexProximal")
    little = roles.get(f"{side}LittleProximal") or roles.get(f"{side}RingProximal")
    if not (hand and index and little):
        return None
    along = (head(armature, roles.get(f"{side}MiddleProximal", index)) - head(armature, hand)).normalized()
    across = head(armature, index) - head(armature, little)
    normal = along.cross(across).normalized()
    # For a left hand with fingers along +X and the index in front (-Y) of the little finger, along x across is -Z:
    # palm down. A right hand gives the opposite sign for the same palm direction.
    return normal if side == "Left" else -normal
