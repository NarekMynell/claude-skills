"""Shared helpers for the character and animation scripts in this folder; the other scripts load this file.

The rig: maps an armature's bones to Unity Humanoid roles by name, reads any skeleton's trunk and legs, and poses bones by
world-space direction, which works whatever each rig's bone rolls are.

The surfaces: a character as connected surfaces, which bones carry each, where surfaces cross, what shows from outside, and
which crossings are defects. Two surfaces crossing is no defect by itself: a leg that enters a torso and stays there is how a
body built from parts joins. A defect is what the player can see go wrong:
    - surfaces no joint connects cut each other (a hand in a hip, two legs fused below the pelvis);
    - a part comes out the other side of what it enters (an arm out of the back);
    - a surface that runs under another shows through it (a knee through trousers, a head through a hat);
    - a joint comes apart, or a cut opening shows, when the body moves.

Blender convention assumed: the character faces -Y, its left side is +X, up is +Z.
"""

import hashlib
import math
import re

import bmesh
import bpy
import numpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

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
_FACE_WORDS = {"jaw", "tongue", "teeth", "tooth", "eye", "eyes", "lid", "brow", "lip", "mouth"}
_PREFIX = re.compile(r"^(.*:|mixamorig\d*_|def[-_.]|cc_base_|bip\d*[ _])", re.IGNORECASE)  # a namespace, or a tool's own mark


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
    _fill_from_chain(armature, roles)
    roles.update(overrides or {})
    return {role: name for role, name in roles.items() if name in armature.data.bones}


def _fill_from_chain(armature, roles):
    """Names differ between tools, the chain of a limb doesn't: a clavicle called so makes the bone called shoulder the upper arm."""
    bones = armature.data.bones
    for side in ("Left", "Right"):
        for upper, lower, end in (("UpperArm", "LowerArm", "Hand"), ("UpperLeg", "LowerLeg", "Foot")):
            if side + lower not in roles and side + end in roles and bones[roles[side + end]].parent:
                roles[side + lower] = bones[roles[side + end]].parent.name
            if side + upper not in roles and side + lower in roles and bones[roles[side + lower]].parent:
                roles[side + upper] = bones[roles[side + lower]].parent.name
        collar = roles.get(side + "Shoulder")
        if collar and collar == roles.get(side + "UpperArm"):
            parent = bones[collar].parent
            if parent is not None and name_side(parent.name):
                roles[side + "Shoulder"] = parent.name
            else:
                del roles[side + "Shoulder"]


def head(armature, bone_name):
    return armature.matrix_world @ armature.data.bones[bone_name].head_local


_LIMB_ENDS = {}


def _limb_ends(armature):
    """Where each bone really ends, at rest in the armature's space. A bone made in Blender ends at its tail. An imported FBX's
    bones have tails that point anywhere, because the file stores joints: there, a bone ends where the bones it carries start."""
    data = armature.data
    # Another armature can take the place and the name of one that was removed: its bones tell them apart.
    key = (data.as_pointer(), len(data.bones), tuple(data.bones[-1].head_local), tuple(data.bones[-1].tail_local)) if data.bones else None
    if key in _LIMB_ENDS:
        return _LIMB_ENDS[key]

    def apart(bone):
        return [c for c in bone.children if (c.head_local - bone.head_local).length > 1e-6]

    singles = [b for b in data.bones if len(apart(b)) == 1]
    follow = sum(1 for b in singles if (apart(b)[0].head_local - b.tail_local).length <= 0.25 * (apart(b)[0].head_local - b.head_local).length)
    tails_hold = follow * 2 >= len(singles)
    ends = {}
    for bone in sorted(data.bones, key=_depth):
        children = apart(bone)
        if not children:
            parent = bone.parent
            axis = bone.tail_local - bone.head_local
            if tails_hold or parent is None:
                ends[bone.name] = bone.tail_local.copy()
            else:
                # The end of a chain has nothing to end at: it goes on as the bone before it did, and no further than half of it.
                before = bone.head_local - parent.head_local
                reach = min(axis.length, 0.5 * before.length) if before.length > 1e-6 else axis.length
                ends[bone.name] = bone.head_local + (before.normalized() * reach if before.length > 1e-6 else axis)
            continue
        if any((c.head_local - bone.tail_local).length <= 0.1 * (c.head_local - bone.head_local).length for c in children):
            ends[bone.name] = bone.tail_local.copy()
            continue
        far = max((c.head_local - bone.head_local).length for c in children)
        carried = [c.head_local for c in children if (c.head_local - bone.head_local).length > 0.6 * far]
        ends[bone.name] = sum(carried, Vector()) / len(carried)
    _LIMB_ENDS[key] = ends
    return ends


def tail(armature, bone_name):
    """Where a bone ends at rest, in world space."""
    return armature.matrix_world @ _limb_ends(armature)[bone_name]


def posed_tail(armature, bone_name):
    """Where a bone ends in the current pose, in world space."""
    bone = armature.data.bones[bone_name]
    return armature.matrix_world @ armature.pose.bones[bone_name].matrix @ bone.matrix_local.inverted() @ _limb_ends(armature)[bone_name]


def limb_length(armature, bone_name):
    """How long a bone really is, in metres."""
    return (tail(armature, bone_name) - head(armature, bone_name)).length


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
    without its action, so poses set by the caller stay. With `mute_constraints`, its bones follow the caller alone."""

    def __init__(self, armature, mute_constraints=False):
        self.armature = armature
        self.mute_constraints = mute_constraints

    def __enter__(self):
        armature = self.armature
        self.basis = {pb.name: pb.matrix_basis.copy() for pb in armature.pose.bones}
        self.position = armature.data.pose_position
        # IK and copy constraints would hold the bones where they are, and every test pose would show the rest pose.
        self.muted = [c for pb in armature.pose.bones for c in pb.constraints if not c.mute] if self.mute_constraints else []
        for constraint in self.muted:
            constraint.mute = True
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
        for constraint in self.muted:
            constraint.mute = False
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
    current = (posed_tail(armature, bone_name) - armature.matrix_world @ pose_bone.head).normalized()
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
    "arms_forward": _both("UpperArm", (0.15, -1.0, -0.15)) + _both("LowerArm", (0.85, -0.45, 0.1)),
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
            direction = (posed_tail(armature, bone) - armature.matrix_world @ armature.pose.bones[bone].head).normalized()
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


# --- Any skeleton ----------------------------------------------------------------------------------------------------


def is_humanoid(armature, roles):
    """Whether a rig is a person's: enough of the Humanoid bones, standing upright. A four-legged rig with human bone names
    isn't one."""
    if sum(1 for role in REQUIRED if role in roles) < 8:
        return False
    if "Hips" in roles and "Head" in roles:
        hips, top = head(armature, roles["Hips"]), head(armature, roles["Head"])
        return top.z - hips.z > abs(top.y - hips.y)
    return True


def _center_chain(armature):
    """The chain down the middle of the skeleton, from the root to the end of its largest branch."""
    data = armature.data.bones
    roots = [b for b in data if b.parent is None]
    if not roots:
        return []
    size = max(max(abs(c) for c in b.head_local) for b in data) or 1.0
    bone = max(roots, key=lambda b: len(b.children_recursive))
    chain = []
    while bone is not None:
        chain.append(bone)
        center = [c for c in bone.children if abs(c.head_local.x) < 0.02 * size and name_side(c.name) is None]
        bone = max(center, key=lambda c: len(c.children_recursive)) if center else None
    # Tiny end bones, such as Mixamo's HeadTop_End, carry nothing.
    while len(chain) > 2 and limb_length(armature, chain[-1].name) < 0.4 * limb_length(armature, chain[-2].name) and not chain[-1].children:
        chain.pop()
    return chain


def head_bone(armature, roles=None):
    """The head: the Humanoid role, else the end of the center chain, whatever it is called."""
    roles = roles or {}
    if "Head" in roles:
        return roles["Head"]
    chain = _center_chain(armature)
    return chain[-1].name if len(chain) >= 3 else None


def trunk_bones(armature, roles=None):
    """The center chain up to, but not including, the head, with the collar bones."""
    roles = roles or {}
    trunk = {roles[r] for r in ("Hips", "Spine", "Chest", "UpperChest", "Neck", "LeftShoulder", "RightShoulder") if r in roles}
    chain = _center_chain(armature)
    top = head_bone(armature, roles)
    trunk.update(b.name for b in chain if b.name != top)
    for bone in chain:
        for child in bone.children:
            if child not in chain and len(child.children) == 1 and limb_length(armature, child.name) < 0.6 * limb_length(armature, child.children[0].name):
                trunk.add(child.name)
    trunk.discard(top)
    return trunk


def leg_chains(armature, roles=None):
    """The chains of bones that reach the ground, from where each leaves the trunk: a person's two, an animal's four, a
    spider's eight, a snake's none."""
    trunk = trunk_bones(armature, roles)
    top = head_bone(armature, roles)
    deform = [b for b in armature.data.bones if b.use_deform]
    if not deform:
        return []
    heights = {b.name: min(head(armature, b.name).z, tail(armature, b.name).z) for b in deform}
    low = min(heights.values())
    high = max(max(head(armature, b.name).z, tail(armature, b.name).z) for b in deform)
    chains = {}
    for bone in deform:
        if bone.name in trunk or bone.name == top or any(c.use_deform for c in bone.children) or heights[bone.name] > low + 0.15 * (high - low):
            continue
        path = [bone]
        while path[0].parent is not None and path[0].parent.name not in trunk:
            path.insert(0, path[0].parent)
        if path[0].parent is None or len(path) < 2:
            continue
        if path[0].name not in chains or len(path) > len(chains[path[0].name]):
            chains[path[0].name] = path
    return list(chains.values())


def creature_poses(armature, roles=None):
    """Bends for any skeleton that isn't a Humanoid: legs forward, back and folded, and the trunk, neck and tail to the side,
    up and down. They stay small, and a wing or a fin stays where it is: no one knows how this body moves until its clips do.
    Name -> list of (bone, target), for `apply_pose` with `identity_roles`."""
    legs = leg_chains(armature, roles)
    in_legs = {b.name for chain in legs for b in chain}
    top = head_bone(armature, roles)
    # What is in the head moves on its own: a jaw, a tongue, the eyes. And so does what is too small to carry the body.
    in_head = {b.name for b in armature.data.bones[top].children_recursive} if top else set()
    in_head |= {b.name for b in armature.data.bones if set(words(b.name)) & _FACE_WORDS}
    heads = [head(armature, b.name) for b in armature.data.bones]
    span = max(max(p[k] for p in heads) - min(p[k] for p in heads) for k in range(3)) if heads else 0.0
    others = [b.name for b in armature.data.bones if b.use_deform and b.parent is not None and b.name not in in_legs and b.name not in in_head
              and name_side(b.name) is None and limb_length(armature, b.name) >= 0.015 * span]
    side, up = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    poses = {}
    if legs:
        poses["legs_forward"] = [(chain[0].name, ("turn", side, -15.0)) for chain in legs]
        poses["legs_back"] = [(chain[0].name, ("turn", side, 15.0)) for chain in legs]
        poses["legs_folded"] = [(bone.name, ("turn", side, degrees)) for chain in legs for bone, degrees in zip(chain, (-20.0, 40.0, -20.0))]
    if others:
        # A long chain adds up: a snake bends about a quarter turn in all.
        each = min(15.0, 90.0 / len(others))
        poses["bend_side"] = [(name, ("turn", up, each)) for name in others]
        poses["bend_up"] = [(name, ("turn", side, each)) for name in others]
        poses["bend_down"] = [(name, ("turn", side, -each)) for name in others]
    return poses


def identity_roles(armature):
    return {b.name: b.name for b in armature.data.bones}


class Joints:
    """How bones and surfaces connect. A helper bone counts as the bone it sits on: a twist bone is its limb. The trunk counts
    as one thing, and so does a hand with its fingers: they fold into themselves without anything going through."""

    def __init__(self, armature, surfaces, roles=None):
        self.armature = armature
        self.node = {}
        self.up = {}
        self.carried = {}
        if armature is None:
            return
        for surface in surfaces:
            for bone in surface.bones:
                self.carried.setdefault(bone, set()).add(surface.name)
        data = armature.data.bones
        roles = roles or {}
        trunk = trunk_bones(armature, roles)
        for bone in data:
            self.node[bone.name] = "trunk" if bone.name in trunk else bone.name
        for bone in data:
            parent = bone.parent
            if parent is not None and not bone.children and bone.name not in trunk and _sits_on(armature, bone, parent):
                self.node[bone.name] = self.node[parent.name]
        hands = [roles[r] for r in ("LeftHand", "RightHand") if r in roles]
        if not hands and not is_humanoid(armature, roles):
            hands = [b.name for b in data if b.name not in trunk and _is_hand_like(armature, b)]
        for name in hands:
            for child in data[name].children_recursive:
                self.node[child.name] = self.node[name]
        carried = set(self.carried)
        for bone in data:
            node = self.node[bone.name]
            parent = bone.parent
            while parent is not None and (self.node[parent.name] == node or (parent.name not in carried and parent.name not in trunk)):
                parent = parent.parent
            if parent is not None:
                self.up[node] = self.node[parent.name]

    def near(self, a, b):
        """The same bone, or bones one joint connects."""
        if a is None or b is None or not self.node:
            return True
        na, nb = self.node.get(a, a), self.node.get(b, b)
        return na == nb or self.up.get(na) == nb or self.up.get(nb) == na

    def mirrored(self, a, b):
        """The two sides' bones on one joint: thighs brush each other."""
        if a is None or b is None or not self.node:
            return False
        parent = self.up.get(self.node.get(a, a))
        return parent is not None and parent == self.up.get(self.node.get(b, b)) and {name_side(a), name_side(b)} == {"L", "R"}

    def line(self, name):
        """Where a bone is now, start and end, in world space."""
        if self.armature.data.pose_position == "REST":
            return head(self.armature, name), tail(self.armature, name)
        return self.armature.matrix_world @ self.armature.pose.bones[name].head, posed_tail(self.armature, name)

    def entry(self, a, b):
        """Whether one of two surfaces hangs from the other on the rig: (the one that hangs, the bone of it nearest the other),
        else None. Bones that carry nothing don't count as a step."""
        for low, high in ((a, b), (b, a)):
            for name in sorted(low.bones):
                bone = self.armature.data.bones.get(name)
                if bone is None:
                    continue
                entry, parent = name, bone.parent
                while parent is not None:
                    if parent.name in high.bones:
                        return low, entry
                    if parent.name in low.bones:
                        entry = parent.name
                    elif parent.name in self.carried:
                        break
                    parent = parent.parent
        return None

    def goes_back_in(self, low, high, entry):
        """Whether the bones of a hanging part leave what it hangs from and then go back in: an elbow out and a wrist in. A limb that
        stays inside from its root and comes out once, as a tortoise's leg does, doesn't."""
        for name in low.bones:
            chain = []
            bone = self.armature.data.bones.get(name)
            while bone is not None and bone.name != entry:
                chain.insert(0, bone.name)
                bone = bone.parent
            if bone is None:
                continue
            chain.insert(0, entry)
            points = [self.line(link)[0] for link in chain] + [self.line(name)[1]]
            out = False
            for point in points:
                if not inside(high, point):
                    out = True
                elif out:
                    return True
        return False

    def far_end(self, fine, entry):
        """The vertices at the far end of a part from the bone it hangs by: on the bone furthest down the chain, the furthest
        along it."""
        def steps(name):
            count, bone = 0, self.armature.data.bones.get(name)
            while bone is not None and bone.name != entry:
                count, bone = count + 1, bone.parent
            return count if bone is not None else -1

        carried = [i for i, name in enumerate(fine.bone) if name]
        if not carried:
            return []
        deepest = max(steps(fine.bone[i]) for i in carried)
        last = [i for i in carried if steps(fine.bone[i]) == deepest]
        start, end = self.line(fine.bone[last[0]])
        axis = (end - start).normalized()
        along = sorted(last, key=lambda i: (fine.bm.verts[i].co - start).dot(axis))
        return along[-max(1, len(along) // 5):]

    def at_joint(self, high, bone, entry):
        """Whether a crossing on a bone of the hanging part is where it joins `high`: on the bone that hangs from it, or further
        along with every joint from there to here inside it. A limb that stays inside what it enters still enters once."""
        if bone is None or self.node.get(bone, bone) == self.node.get(entry, entry):
            return True
        link = self.armature.data.bones.get(bone)
        chain = []
        while link is not None and link.name != entry:
            chain.append(link.name)
            link = link.parent
        return link is not None and all(inside(high, self.line(name)[0]) for name in chain)


def _sits_on(armature, bone, parent):
    """Whether a childless bone is a helper on its parent, such as a twist bone: it starts along the parent, not at its end."""
    axis = _limb_ends(armature)[parent.name] - parent.head_local
    if axis.length <= 1e-6:
        return True
    return (bone.head_local - parent.head_local).dot(axis.normalized()) < 0.9 * axis.length


def _is_hand_like(armature, bone):
    """Three or more short chains from one bone: fingers on a hand, toes on a paw."""
    if len(bone.children) < 3:
        return False
    for child in bone.children:
        chain = [child] + list(child.children_recursive)
        if any(len(link.children) > 1 for link in chain) or sum(limb_length(armature, link.name) for link in chain) > limb_length(armature, bone.name):
            return False
    return True


# --- Surfaces --------------------------------------------------------------------------------------------------------


def _fibonacci(count):
    """Directions spread evenly over the sphere."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    directions = []
    for i in range(count):
        z = 1.0 - 2.0 * (i + 0.5) / count
        radius = math.sqrt(max(0.0, 1.0 - z * z))
        directions.append(Vector((radius * math.cos(i * golden), radius * math.sin(i * golden), z)))
    return directions


DIRECTIONS = _fibonacci(96)
FINE_DIRECTIONS = _fibonacci(256)
_AXES = [Vector(axis) for axis in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]


class Surface:
    """One connected surface of an object, evaluated (modifiers and pose applied) in world space."""

    def __init__(self, owner, name, bm, face_bone, vertex_bone, source):
        self.owner = owner  # the object's name
        self.name = name  # the object's name, when it holds one surface
        self.bm = bm
        self.face_bone = face_bone  # per face, the bone that carries it most, or None
        self.vertex_bone = vertex_bone  # per vertex, the same
        self.source = source  # per face, its index in the object's evaluated mesh
        self.bones = {b for b in face_bone if b}
        bm.normal_update()
        for sequence in (bm.verts, bm.edges, bm.faces):
            sequence.ensure_lookup_table()
            sequence.index_update()
        self.tree = BVHTree.FromBMesh(bm)
        self.area = sum(f.calc_area() for f in bm.faces)
        self.lowest = min((v.co.z for v in bm.verts), default=0.0)
        self.highest = max((v.co.z for v in bm.verts), default=0.0)
        self.fine = {}

    def free(self):
        for sampled in self.fine.values():
            sampled.free()
        self.bm.free()

    def bone_at(self, face, points):
        """The bone that carries a face where these points are: a long face can span two bones."""
        center = sum(points, Vector()) / len(points)
        nearest = min(self.bm.faces[face].verts, key=lambda v: (v.co - center).length_squared)
        return self.vertex_bone[nearest.index]

    def sampled(self, spacing):
        """This surface with no edge longer than `spacing`: a low-poly part has too few vertices to tell where it is."""
        if spacing not in self.fine:
            self.fine[spacing] = _Sampled(self, spacing)
        return self.fine[spacing]


class _Sampled:
    def __init__(self, surface, spacing):
        self.surface = surface
        bm = surface.bm.copy()
        for _ in range(6):
            bm.edges.ensure_lookup_table()
            long_edges = [e for e in bm.edges if e.calc_length() > spacing]
            if not long_edges:
                break
            bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
        bm.normal_update()
        for sequence in (bm.verts, bm.edges, bm.faces):
            sequence.ensure_lookup_table()
            sequence.index_update()
        self.bm = bm
        self.area = [sum(f.calc_area() / len(f.verts) for f in v.link_faces) for v in bm.verts]
        self.face = [surface.tree.find_nearest(v.co)[2] for v in bm.verts]
        self.bone = [surface.bone_at(f, [v.co]) if f is not None else None for f, v in zip(self.face, bm.verts)]

    def free(self):
        self.bm.free()

    def area_of(self, verts):
        return sum(self.area[i] for i in verts)


def _carrying_bones(obj, bm, armature):
    """Per face and per vertex, the deform bone with the most weight."""
    if obj.parent_type == "BONE" and obj.parent_bone:
        return [obj.parent_bone] * len(bm.faces), [obj.parent_bone] * len(bm.verts)
    layer = bm.verts.layers.deform.active
    if layer is None or armature is None:
        return [None] * len(bm.faces), [None] * len(bm.verts)
    bones = armature.data.bones
    names = {g.index: g.name for g in obj.vertex_groups if g.name in bones and bones[g.name].use_deform}

    def strongest(verts):
        totals = {}
        for vertex in verts:
            for group, weight in vertex[layer].items():
                name = names.get(group)
                if name:
                    totals[name] = totals.get(name, 0.0) + weight
        return max(totals, key=totals.get) if totals else None

    return [strongest(face.verts) for face in bm.faces], [strongest((vertex,)) for vertex in bm.verts]


def _islands(bm):
    seen, islands = set(), []
    for start in bm.faces:
        if start.index in seen:
            continue
        stack, faces = [start], []
        seen.add(start.index)
        while stack:
            face = stack.pop()
            faces.append(face.index)
            for vertex in face.verts:
                for other in vertex.link_faces:
                    if other.index not in seen:
                        seen.add(other.index)
                        stack.append(other)
        islands.append(sorted(faces))
    return islands


def _island_names(owner, islands, bones):
    """One name per island: the largest keeps the object's, the others add the bone that carries them."""
    largest = max(range(len(islands)), key=lambda k: len(islands[k]))
    names, used = [], {}
    for k, faces in enumerate(islands):
        if k == largest:
            names.append(owner)
            continue
        carried = [bones[i] for i in faces if bones[i]]
        label = max(sorted(set(carried)), key=carried.count) if carried else str(k + 1)
        used[label] = used.get(label, 0) + 1
        names.append(f"{owner}[{label}]" if used[label] == 1 else f"{owner}[{label}.{used[label]}]")
    return names


def _copy_island(bm, faces):
    copy = bmesh.new()
    mapped, kept = {}, []
    for index in faces:
        face = bm.faces[index]
        verts = []
        for vertex in face.verts:
            if vertex.index not in mapped:
                mapped[vertex.index] = copy.verts.new(vertex.co)
            verts.append(mapped[vertex.index])
        try:
            copy.faces.new(verts)
            kept.append(index)
        except ValueError:
            pass  # a duplicate face: validate_mesh reports it
    return copy, kept, list(mapped)


class Character:
    """Gathers a character's surfaces, in whatever pose the rig is in now. An object with several islands splits into one
    surface per island; one listed in `whole` stays one surface: hair cards are many strips and one part."""

    def __init__(self, objects, armature=None, whole=()):
        self.objects = objects
        self.armature = armature
        self.whole = set(whole)
        self.layout = {}

    def gather(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        surfaces = []
        for obj in self.objects:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            bm = bmesh.new()
            if mesh is not None:
                bm.from_mesh(mesh)
            evaluated.to_mesh_clear()
            if not bm.faces:
                bm.free()
                continue
            bm.transform(obj.matrix_world)
            if obj.matrix_world.determinant() < 0.0:
                bmesh.ops.reverse_faces(bm, faces=bm.faces[:])  # a mirrored child: its faces still look outward
            for sequence in (bm.verts, bm.faces):
                sequence.ensure_lookup_table()
                sequence.index_update()
            # The same parts in every pose, unless a modifier changes them with it: a Mirror merges what comes close.
            key = (obj.name, len(bm.verts), len(bm.faces))
            if key not in self.layout:
                face_bones, vertex_bones = _carrying_bones(obj, bm, self.armature)
                islands = [list(range(len(bm.faces)))] if obj.name in self.whole else _islands(bm)
                self.layout[key] = (face_bones, vertex_bones, islands, _island_names(obj.name, islands, face_bones))
            face_bones, vertex_bones, islands, names = self.layout[key]
            if len(islands) == 1:
                surfaces.append(Surface(obj.name, names[0], bm, face_bones, vertex_bones, islands[0]))
                continue
            for faces, name in zip(islands, names):
                copy, kept, verts = _copy_island(bm, faces)
                surfaces.append(Surface(obj.name, name, copy, [face_bones[i] for i in kept], [vertex_bones[i] for i in verts], kept))
            bm.free()
        return surfaces


def free(surfaces):
    for surface in surfaces:
        surface.free()


def geometry_key(objects):
    """A fingerprint of the objects' meshes: whether what was checked is still what is there."""
    digest = hashlib.md5()
    for obj in sorted((o for o in objects if o.type == "MESH"), key=lambda o: o.name):
        digest.update(obj.name.encode())
        for vertex in obj.data.vertices:
            digest.update(("%.4f %.4f %.4f;" % tuple(vertex.co)).encode())
    return digest.hexdigest()


def appearing_together(surfaces, groups, never_together=()):
    """Each variant with the first of every other group it can appear with: what can be on screen at once. The character alone
    when it has no variants."""
    first = [p for p in surfaces if p.owner not in {name for names in groups.values() for name in names[1:]}]
    sets = [first]
    for group, names in groups.items():
        for name in names[1:]:
            others = [p for p in first if p.owner not in groups[group]
                      and f"{p.owner}+{name}" not in never_together and f"{name}+{p.owner}" not in never_together]
            sets.append(others + [p for p in surfaces if p.owner == name])
    return sets


def crossings(surfaces):
    """Face pairs that cut through each other: within a surface, {index: pairs}, and between two, {(i, j): pairs}.
    Faces of one surface that share a vertex only touch there."""
    within, between = {}, {}
    for i, a in enumerate(surfaces):
        faces = a.bm.faces
        pairs = {tuple(sorted(p)) for p in a.tree.overlap(a.tree)
                 if p[0] != p[1] and not {v.index for v in faces[p[0]].verts} & {v.index for v in faces[p[1]].verts}}
        if pairs:
            within[i] = sorted(pairs)
        for j in range(i + 1, len(surfaces)):
            found = a.tree.overlap(surfaces[j].tree)
            if found:
                between[(i, j)] = found
    return within, between


def _triangles(face):
    corners = [v.co for v in face.verts]
    return [(corners[0], corners[k], corners[k + 1]) for k in range(1, len(corners) - 1)]


def _in_triangle(point, a, b, c, margin=-1e-6):
    v0, v1, v2 = c - a, b - a, point - a
    d00, d01, d02, d11, d12 = v0.dot(v0), v0.dot(v1), v0.dot(v2), v1.dot(v1), v1.dot(v2)
    denominator = d00 * d11 - d01 * d01
    if abs(denominator) < 1e-18:
        return False
    u = (d11 * d02 - d01 * d12) / denominator
    v = (d00 * d12 - d01 * d02) / denominator
    return u >= margin and v >= margin and u + v <= 1.0 - margin


def _crossing_edges(face, other, margin=-1e-6):
    """The edges of a face that pass through another, as (start, end, where)."""
    found = []
    corners = [v.co for v in face.verts]
    for p, q in zip(corners, corners[1:] + corners[:1]):
        for a, b, c in _triangles(other):
            normal = (b - a).cross(c - a)
            dp, dq = normal.dot(p - a), normal.dot(q - a)
            # A corner on the other's plane, as of two boxes that touch, is no crossing, whichever side rounding puts it on.
            if dp * dq < 0.0 and min(abs(dp), abs(dq)) > 1e-5 * normal.length:
                point = p.lerp(q, dp / (dp - dq))
                if _in_triangle(point, a, b, c, margin):
                    found.append((p, q, point))
    return found


def _edges_through(face, other):
    return [point for _, _, point in _crossing_edges(face, other)]


def crossing_points(a, face_a, b, face_b):
    """Where two faces cut each other."""
    fa, fb = a.bm.faces[face_a], b.bm.faces[face_b]
    points = _edges_through(fa, fb) + _edges_through(fb, fa)
    return points or [(fa.calc_center_median() + fb.calc_center_median()) / 2]


def _really_cross(a, face_a, b, face_b):
    """Whether two faces cut each other, and don't only touch. An edge through the inside of the other face does. An edge that meets its rim
    may be two boxes meeting at a corner, or mirrored parts whose edges meet exactly: there, it has to go from outside the other surface to
    inside it."""
    fa, fb = a.bm.faces[face_a], b.bm.faces[face_b]
    if _crossing_edges(fa, fb, 1e-4) or _crossing_edges(fb, fa, 1e-4):
        return True
    for edges, other in ((_crossing_edges(fa, fb), b), (_crossing_edges(fb, fa), a)):
        for p, q, point in edges:
            step = (q - p).normalized() * min(0.05 * (q - p).length, 0.01)
            if _deep_inside(other, point - step) != _deep_inside(other, point + step):
                return True
    return False


def _deep_inside(surface, point):
    return surface.tree.find_nearest(point)[3] > 1e-4 and inside(surface, point)


def extent(points):
    """The size of a set of points: its longest side."""
    if not points:
        return 0.0
    return max(max(p[k] for p in points) - min(p[k] for p in points) for k in range(3))


class Ring:
    """One connected line where two surfaces cross: per pair of faces, the points where they cross."""

    def __init__(self, details):
        self.details = details  # (face of a, face of b, points)
        self.points = [p for _, _, points in details for p in points]

    def flipped(self):
        return Ring([(y, x, points) for x, y, points in self.details])


def rings_of(a, b, found, tolerance):
    """The separate lines of a crossing: its face pairs, grouped where their points run on from each other."""
    # Boxes that touch face to face overlap and don't cross: no edge of one goes through the other.
    details = [(pair, crossing_points(a, pair[0], b, pair[1])) for pair in found if _really_cross(a, pair[0], b, pair[1])]
    if not details:
        return []
    count = len(details)
    tree = KDTree(sum(len(points) for _, points in details))
    index = 0
    owner = []
    for k, (_, points) in enumerate(details):
        for point in points:
            tree.insert(point, index)
            owner.append(k)
            index += 1
    tree.balance()
    parent = list(range(count))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for k, (_, points) in enumerate(details):
        for point in points:
            for _, other, _ in tree.find_range(point, tolerance):
                parent[find(k)] = find(owner[other])
    groups = {}
    for k in range(count):
        groups.setdefault(find(k), []).append(k)
    return [Ring([(details[k][0][0], details[k][0][1], details[k][1]) for k in members]) for members in groups.values()]


class Sight:
    """What can be seen from outside, among the surfaces that appear together."""

    def __init__(self, surfaces, height):
        coords, polygons, self.owners = [], [], []
        for surface in surfaces:
            offset = len(coords)
            coords.extend(v.co.copy() for v in surface.bm.verts)
            for face in surface.bm.faces:
                polygons.append([offset + v.index for v in face.verts])
                self.owners.append(surface)
        self.tree = BVHTree.FromPolygons(coords, polygons) if polygons else None
        self.height = max(height, 0.001)
        self.bottom = min((c.z for c in coords), default=0.0)
        self.reach = 3.0 * self.height
        self.margin = 0.002 * self.height

    def visible(self, point):
        """Whether a look from some side reaches the point with nothing in front of it."""
        if self.tree is None:
            return True
        for direction in DIRECTIONS:
            hit = self.tree.ray_cast(point + direction * self.reach, -direction, self.reach)
            if hit[0] is None or hit[3] >= self.reach - self.margin:
                return True
        return False


def _along_edge(edge, spacing):
    start, end = edge.verts[0].co, edge.verts[1].co
    count = max(1, int(edge.calc_length() / spacing))
    return [start.lerp(end, (k + 0.5) / count) for k in range(count)]


def see_inside(surface, sight, lowest_view=0.0, any_surface=False):
    """Open edges past which a look from outside meets the surface's own back: a hole into its inside, which backface culling
    shows as a gap. Up to where the camera can go: `lowest_view` is in degrees above the horizon. An edge low on the asset that opens
    downward is the bottom a rock or a brick leaves off where the ground takes over, and only from below the ground would it show.
    `any_surface`: the back met may be another part's too, as in a shed of separate panels; on a body that is a look under a garment."""
    found = []
    nudge = 0.001 * sight.height
    floor = math.sin(math.radians(lowest_view))
    views = [d for d in FINE_DIRECTIONS if d.z >= floor]
    spacing = 0.015 * sight.height
    for edge in surface.bm.edges:
        if len(edge.link_faces) != 1:
            continue
        face = edge.link_faces[0]
        outward = (edge.verts[1].co - edge.verts[0].co).cross(face.normal)
        if outward.length < 1e-9:
            continue
        outward.normalize()
        if outward.dot((edge.verts[0].co + edge.verts[1].co) / 2 - face.calc_center_median()) < 0.0:
            outward = -outward
        if outward.z < -0.5 and lowest_view >= 0.0 and (edge.verts[0].co.z + edge.verts[1].co.z) / 2 < sight.bottom + 0.2 * sight.height:
            continue
        if any(_shows_back(surface, point + outward * nudge, face.normal, views, sight, any_surface) for point in _along_edge(edge, spacing)):
            found.append(edge.index)
    return found


def _shows_back(surface, point, normal, views, sight, any_surface=False):
    for direction in views:
        if normal.dot(direction) < 0.34:
            continue  # along the surface, a sliver; from behind it, no look from outside
        hit = sight.tree.ray_cast(point + direction * sight.reach, -direction, 2.0 * sight.reach)
        # Past the edge, and on to its far wall: a look along the gap under a loose garment isn't a look inside.
        if hit[0] is not None and hit[3] >= sight.reach + 0.03 * sight.height and hit[1].dot(-direction) > 0.0 and (any_surface or sight.owners[hit[2]] is surface):
            return True
    return False


def cone(normal):
    """The outward directions a face is looked at from."""
    tangent = normal.orthogonal().normalized()
    bitangent = normal.cross(tangent)
    return [normal] + [(normal + axis * 0.84).normalized() for axis in (tangent, -tangent, bitangent, -bitangent)]


def wide_cone(normal):
    """The same, close to along the face."""
    tangent = normal.orthogonal().normalized()
    bitangent = normal.cross(tangent)
    return [(normal + axis * 2.75).normalized() for axis in (tangent, -tangent, bitangent, -bitangent, (tangent + bitangent).normalized(), (tangent - bitangent).normalized(), (bitangent - tangent).normalized(), -(tangent + bitangent).normalized())]


def _face_samples(face, spacing):
    """Points over a face, about `spacing` apart, and along its edges: a long face can show in the middle with its corners and
    center covered, and a sliver of it along one edge."""
    center = face.calc_center_median()
    points = [center] + [v.co.lerp(center, 0.02) for v in face.verts]
    corners = [v.co for v in face.verts]
    for p, q in zip(corners, corners[1:] + corners[:1]):
        steps = int((p - q).length / spacing)
        points.extend(p.lerp(q, k / (steps + 1)).lerp(center, 0.02) for k in range(1, steps + 1))
    for a, b, c in _triangles(face):
        longest = max((a - b).length, (b - c).length, (c - a).length)
        steps = int(longest / spacing)
        for i in range(1, steps):
            for j in range(1, steps - i):
                points.append(a + (b - a) * (i / steps) + (c - a) * (j / steps))
    return points


def hidden_faces(surfaces, see_through, reach, allowed=(), among=None, spacing=None, wide=False):
    """Faces nobody can see: all over them, the outward directions run into the back of a surface. Returns {(surface name,
    face): cover surface name}, for all faces or those in `among`. `allowed` lists objects, and "Object<Cover" pairs, whose
    hidden faces are intended. `wide` looks from the side as well: under a roof a crate's top is in plain view."""
    coords, polygons, owners = [], [], []
    for surface in surfaces:
        if surface.owner in see_through:
            continue
        offset = len(coords)
        coords.extend(v.co.copy() for v in surface.bm.verts)
        for face in surface.bm.faces:
            polygons.append([offset + v.index for v in face.verts])
            owners.append((surface, face.index))
    if not polygons:
        return {}
    tree = BVHTree.FromPolygons(coords, polygons)
    spacing = spacing or reach * 0.05
    hidden = {}
    for surface in surfaces:
        if surface.owner in allowed:
            continue
        for face in surface.bm.faces:
            key = (surface.name, face.index)
            if (among is not None and key not in among) or face.normal.length < 0.5:
                continue
            directions = cone(face.normal)
            if wide:
                directions = directions + wide_cone(face.normal)
            cover = None
            for point in _face_samples(face, spacing):
                # Far from the origin a small step vanishes in single precision, and a face hits itself.
                nudge = 1e-5 + 1e-6 * max(abs(point.x), abs(point.y), abs(point.z))
                cover_here = _cover_of(tree, owners, point + face.normal * nudge, directions, surface, face.index, reach, nudge)
                if cover_here is None or f"{surface.owner}<{cover_here.owner}" in allowed:
                    cover = None
                    break
                cover = cover or cover_here
            if cover is not None:
                hidden[key] = cover.name
    return hidden


def _cover_of(tree, owners, origin, directions, surface, face, reach, nudge=1e-5):
    cover = None
    for direction in directions:
        location, normal, index, _ = tree.ray_cast(origin, direction, reach)
        if location is not None and owners[index] == (surface, face):
            location, normal, index, _ = tree.ray_cast(location + direction * nudge, direction, reach)
        if location is None or normal.dot(direction) <= 0.0:
            return None
        cover = cover or owners[index][0]
    return cover


def under(surface, cover, faces=None):
    """Faces of a surface whose outward directions all run into the back of the cover: they sit inside or under it."""
    found = set()
    for index in (range(len(surface.bm.faces)) if faces is None else faces):
        face = surface.bm.faces[index]
        normal = face.normal
        if normal.length < 0.5:
            continue
        origin = face.calc_center_median() + normal * 1e-5
        for direction in cone(normal):
            location, hit_normal, _, _ = cover.tree.ray_cast(origin, direction, 100.0)
            if location is None or hit_normal.dot(direction) <= 0.0:
                break
        else:
            found.add(index)
    return found


def inside(surface, point):
    """Whether a surface encloses a point: looks along the axes meet its back, or nothing where it is open or cut, and never
    its front."""
    backs = 0
    for axis in _AXES:
        location, normal, _, _ = surface.tree.ray_cast(point, axis, 100.0)
        if location is not None:
            if normal.dot(axis) <= 0.0:
                return False
            backs += 1
    return backs >= 3


def open_edges_inside(surface, other):
    """Whether an open edge of the surface sits inside the other: where a rim is sunk, or faces were cut away."""
    for edge in surface.bm.edges:
        if len(edge.link_faces) == 1 and inside(other, (edge.verts[0].co + edge.verts[1].co) / 2):
            return True
    return False


# --- The judgement ---------------------------------------------------------------------------------------------------


def rim_height(cover):
    """Above this, what comes out of something on the head has come through its crown, not from under its rim."""
    boundary = [edge for edge in cover.bm.edges if len(edge.link_faces) == 1]
    zs = [v.co.z for v in cover.bm.verts]
    low, high = min(zs), max(zs)
    rim = min((min(v.co.z for v in edge.verts) for edge in boundary), default=low)
    return max(rim, low) + 0.25 * (high - low)


class Judge:
    """Decides which crossings show as defects. The same judgement at rest and in any pose: the geometry of the moment tells.

    Bones say what a crossing is. Surfaces on the same bones are layers or attachments; surfaces a joint connects meet at that
    joint; any others have no reason to touch. Geometry says whether it's wrong: a part that enters what it joins goes in once
    and stays; a layer doesn't come out through a wall of what covers it, only at its openings."""

    def __init__(self, joints, scale, tops=(), skull=None, see_through=(), skip=None):
        self.joints = joints
        self.scale = max(scale, 0.001)  # the character's height, without what it carries
        self.tops = set(tops)  # names of the surfaces that cover the head
        self.skull = skull  # name of the surface that is the head
        self.skull_owner = None
        self.head = None  # the head's surface in the pose now
        self.judge_layers = True
        self.see_through = see_through
        self.skip = skip
        self.graze = 0.005 * self.scale  # less than this can't be seen at any game distance
        self.spacing = 0.03 * self.scale
        self.tolerance = 0.004 * self.scale
        self.pieces_cache = {}

    def fresh(self):
        """Forgets what it worked out about the last pose's surfaces."""
        self.pieces_cache = {}

    def rings(self, a, b, found, sight):
        """The lines of a crossing that are big enough to see, and that something outside can see."""
        rings = []
        for ring in rings_of(a, b, found, self.tolerance):
            if extent(ring.points) >= self.graze and any(sight.visible(p) for p in ring.points):
                rings.append(ring)
        return rings

    def kind(self, a, b, ring):
        """What a line of a crossing is: "same" (layers or attachments on the same bones, or no rig to tell), "joint" or "apart"."""
        if not (a.bones and b.bones):
            return "same"
        pairs = [(a.bone_at(x, points), b.bone_at(y, points)) for x, y, points in ring.details]
        close = sum(1 for x, y in pairs if self.joints.near(x, y)) * 2 >= len(pairs)
        if a.bones & b.bones:
            return "same" if close else "apart"
        hanging = self.joints.entry(a, b)
        if hanging is not None:
            low, entry = hanging
            high = b if low is a else a
            carried = {x if low is a else y for x, y in pairs} - {None}
            if any(self.joints.at_joint(high, bone, entry) for bone in carried):
                return "joint"
        # A part between them, such as a neck between head and torso, can be sunk in both: at that joint, not far from it.
        if close:
            center = sum(ring.points, Vector()) / len(ring.points)
            for bone in {x for pair in pairs for x in pair} - {None}:
                if (center - self.joints.line(bone)[0]).length <= 1.5 * limb_length(self.joints.armature, bone):
                    return "joint"
        return "apart"

    def outer(self, surface, cover, region=None):
        """The parts of a surface outside the cover: sets of sampled vertices, joined by edges that don't pass through the
        cover. Those too small to see are left out. Returns them, the vertices under the cover, and the sample. `region` keeps
        only what these bones carry."""
        key = (surface.name, cover.name, None if region is None else tuple(sorted(region)))
        if key in self.pieces_cache:
            return self.pieces_cache[key]
        fine = surface.sampled(self.spacing)
        verts = fine.bm.verts
        members = set(range(len(verts))) if region is None else {i for i in range(len(verts)) if fine.bone[i] in region}
        outside = {i for i in members if not self._covered(verts[i], cover)}
        groups, left = [], set(outside)
        while left:
            stack = [left.pop()]
            group = set(stack)
            while stack:
                vertex = verts[stack.pop()]
                for edge in vertex.link_edges:
                    other = edge.other_vert(vertex)
                    if other.index not in left:
                        continue
                    along = other.co - vertex.co
                    if cover.tree.ray_cast(vertex.co, along.normalized(), along.length)[0] is None:
                        left.remove(other.index)
                        group.add(other.index)
                        stack.append(other.index)
            groups.append(group)
        seen = []
        for group in groups:
            depth = max(cover.tree.find_nearest(verts[i].co)[3] for i in group)
            # Wide and shallow still shows. On the cover's own surface, as a ring of hair exactly on a cap's rim, nothing has come out.
            if depth >= self.graze or (depth >= 0.1 * self.graze and extent([verts[i].co for i in group]) >= 10.0 * self.graze):
                seen.append(group)
        result = (seen, members - outside, fine, members)
        self.pieces_cache[key] = result
        return result

    @staticmethod
    def _covered(vertex, cover):
        """Whether a vertex is under the cover: enclosed by it, or looking out at its back, as under a half shell."""
        if inside(cover, vertex.co):
            return True
        normal = vertex.normal
        if normal.length < 0.5:
            return False
        location, hit_normal, _, _ = cover.tree.ray_cast(vertex.co + normal * 1e-5, normal, 100.0)
        return location is not None and hit_normal.dot(normal) > 0.0

    def _rings_around(self, group, fine, rings, outer=None):
        """The rings a piece ends at: those whose nearest outside vertex belongs to it, at some point along them."""
        others = [other for other in (outer or []) if other is not group]
        coords = [(fine.bm.verts[i].co, True) for i in group] + [(fine.bm.verts[i].co, False) for other in others for i in other]
        tree = KDTree(len(coords))
        for k, (co, _) in enumerate(coords):
            tree.insert(co, k)
        tree.balance()
        reach = 2.0 * self.spacing
        found = []
        for ring in rings:
            for point in ring.points:
                _, index, distance = tree.find(point)
                if distance <= reach and coords[index][1]:
                    found.append(ring)
                    break
        return found

    def _axes(self, surface, ring=None):
        """The lines a surface can be worn around: its bones where the ring is, or its long axis with no rig."""
        lines = []
        if self.joints.armature is not None and surface.bones:
            names = {surface.bone_at(x, points) for x, _, points in ring.details} if ring else surface.bones
            lines = [self.joints.line(name) for name in names if name]
        return lines or [_long_axis([v.co for v in surface.bm.verts])]

    def _is_cuff(self, surface, ring):
        """Whether a ring goes around the surface like a cuff or a hem: all the way around one of its bones, or around its long
        axis with no rig, and no longer along it than twice across it."""
        for start, end in self._axes(surface, ring):
            around, along, across = _around_line(ring.points, start, end)
            if around and along <= 2.0 * max(across, 1e-6):
                return True
        return False

    def _wraps(self, surface, other):
        """Whether the whole surface is a ring around one of its bones, and the smaller of the two: a necklace on a chest, a belt.
        A limb goes around its bone too, but it is long."""
        if surface.area > other.area or self.joints.armature is None or not surface.bones:
            return False
        coords = [v.co for v in surface.bm.verts]
        for name in surface.bones:
            start, end = self.joints.line(name)
            around, along, across = _around_line(coords, start, end)
            if not around or along > 2.0 * max(across, 1e-6):
                continue
            axis = (end - start).normalized()
            radii = [((p - start) - axis * (p - start).dot(axis)).length for p in coords]
            if max(radii) <= 4.0 * max(min(radii), 1e-6):  # at about one distance all around: a bent arm isn't that
                return True
        return False

    def _at_opening(self, cover, ring):
        """Whether a ring runs along an open edge of the cover: the surface comes out at an opening, not through a wall."""
        samples = [p for edge in cover.bm.edges if len(edge.link_faces) == 1 for p in _along_edge(edge, self.spacing)]
        if not samples:
            return False
        tree = KDTree(len(samples))
        for k, co in enumerate(samples):
            tree.insert(co, k)
        tree.balance()
        limit = min(0.02 * self.scale, 0.25 * extent(ring.points))
        return all(tree.find(p)[2] <= limit for p in ring.points)

    def _stands_on_head(self, surface):
        """Whether a part crosses the head itself: rabbit ears through a hat do, a feather in the hat's band doesn't."""
        return self.head is not None and surface is not self.head and bool(surface.tree.overlap(self.head.tree))

    @staticmethod
    def _covers(surface, cover):
        """Whether one thing on the head is over the other: higher, and at least as wide, as a sun hat over hair."""
        def outline(part):
            xs, ys = [v.co.x for v in part.bm.verts], [v.co.y for v in part.bm.verts]
            return (max(xs) - min(xs)) * (max(ys) - min(ys))
        return surface.highest >= cover.highest and outline(surface) >= outline(cover)

    def _through_top(self, surface, cover, outer, fine, members, share, rings):
        """Whether something under what covers the head comes through it: a piece above its rim, away from where the surface
        leaves it at the bottom. A feather on a hat isn't under it, and a sun hat over hair is the one that covers."""
        if surface.name != self.skull:
            on_top = share < 0.75 and surface.lowest >= cover.lowest - 0.02 * self.scale and not self._stands_on_head(surface)
            if on_top or (surface.name in self.tops and self._covers(surface, cover)):
                return False
        lowest = min(members, key=lambda i: fine.bm.verts[i].co.z)
        rim = rim_height(cover)
        down = Vector((0.0, 0.0, -1.0))
        for piece in outer:
            if lowest in piece or min(fine.bm.verts[i].co.z for i in piece) <= rim:
                continue
            # On top of the cover, not beside it: hair that bulges out past a cap's band hasn't come through the cap.
            if not any(cover.tree.ray_cast(fine.bm.verts[i].co, down, 10.0)[0] is not None for i in piece):
                continue
            if not all(self._at_opening(cover, ring) for ring in self._rings_around(piece, fine, rings, outer)):
                return True
        return False

    def _layers(self, surface, cover, rings):
        """Why a surface on the same bones as the cover shows wrong, or None."""
        region = surface.bones & cover.bones if surface.bones and cover.bones else None
        outer, covered, fine, members = self.outer(surface, cover, region)
        total = fine.area_of(members)
        if total <= 0.0:
            return None
        share = fine.area_of(covered) / total
        if cover.name in self.tops and self._through_top(surface, cover, outer, fine, members, share, rings):
            return f"{surface.name} comes through {cover.name}"
        # A body under what it wears shows through it. A small part in a large one, such as an eye in a head, doesn't; nor does a
        # ring on what it sits on, such as a belt on a tunic. What covers the head has its own rule, above.
        cover_total = cover.area if region is None else sum(f.calc_area() for f in cover.bm.faces if cover.face_bone[f.index] in surface.bones)
        # And the cover has to be big enough to wear: a tooth set in a jaw isn't worn by it.
        if cover.name not in self.tops and 0.1 * total <= cover_total <= total / 0.33 and cover.area >= 0.01 * surface.area and not self._wraps(surface, cover):
            for piece in outer:
                area = fine.area_of(piece)
                if area >= total - area:
                    continue
                around = self._rings_around(piece, fine, rings, outer)
                if not around:
                    continue
                # One end, as a hand comes out of a cuff. A knee wider than the trouser leg has a line above it and one below.
                if self._one_place(around) and all(self._is_cuff(surface, ring) or self._at_opening(cover, ring) for ring in around):
                    continue
                return f"{surface.name} runs under {cover.name} and shows through it"
        # What goes through is the smaller of the two: a body doesn't go through a tooth set in it.
        if len(outer) >= 2 and surface.area <= cover.area and not self._worn(surface, cover, outer, fine, rings):
            return f"{surface.name} goes right through {cover.name}"
        return None

    def _one_place(self, rings):
        """Whether lines of a crossing lie in one place: both faces of a thin disc, not a line above a knee and one below it."""
        centers = [sum(ring.points, Vector()) / len(ring.points) for ring in rings]
        return all((c - centers[0]).length <= 2.0 * self.spacing for c in centers)

    def _worn(self, surface, cover, outer, fine, rings):
        """Whether one of two surfaces on the same bones that pass through each other is worn around the other, which is fine: a
        belt, a bracelet, a sleeve with an arm in it, a necklace that dips into a chest."""
        if self.joints.armature is None or not surface.bones:
            return surface.area > cover.area  # no bones to go around: what is larger than what it passes through wears it
        if self._wraps(surface, cover) or self._wraps(cover, surface):
            return True
        around = [ring for piece in outer for ring in self._rings_around(piece, fine, rings, outer)]
        return bool(around) and all(self._is_cuff(surface, ring) for ring in around)

    def _joint(self, a, b):
        """A part that joins another goes in by its root and stays: its far end doesn't come out, or end up inside. A ring on the
        next bone, such as a collar, sits around what it meets instead."""
        if self._wraps(a, b) or self._wraps(b, a):
            return None
        hanging = self.joints.entry(a, b) if self.joints.armature is not None else None
        if hanging is not None:
            low, entry = hanging
            high = b if low is a else a
            if self.joints.goes_back_in(low, high, entry):
                return f"{low.name} leaves {high.name} and goes back into it"
            if len(low.bones) >= 2:  # a limb: an ear on the head's bone has no far end along that bone
                _, covered, fine, _ = self.outer(low, high)
                far = self.joints.far_end(fine, entry)
                if far and sum(1 for i in far if i in covered) * 2 > len(far):
                    return f"{low.name} ends inside {high.name}"
        for surface, cover in ((a, b), (b, a)):
            outer = self.outer(surface, cover)
            if len(outer[0]) >= 2 and not self._folding_end(surface, cover, hanging, outer):
                return f"{surface.name} comes out the other side of {cover.name}"
        return None

    def _folding_end(self, surface, cover, hanging, outer):
        """Whether what shows past the other part is only the round end of a limb segment at its own joint, as at a bent elbow. On
        the trunk, what comes out is something coming out."""
        if hanging is None:
            return False
        trunk = "trunk"
        if any(self.joints.node.get(name) == trunk for name in (surface.bones | cover.bones)):
            return False
        joint = self.joints.line(hanging[1])[0]
        reach = limb_length(self.joints.armature, hanging[1])
        groups, _, fine, _ = outer
        ends = 0
        for group in groups:
            if max((fine.bm.verts[i].co - joint).length for i in group) > reach:
                ends += 1
        return ends < 2

    def pair(self, a, b, found, sight):
        """Why a crossing between two surfaces shows as a defect, as (why, where, how many faces), or None. And whether a joint
        holds them."""
        if self.skip and self.skip(a, b):
            return None, False
        if a.owner in self.see_through or b.owner in self.see_through:
            # Hair cards grow from the head and cross each other. Up through what covers the head, they still show.
            cards, cover = (a, b) if a.owner in self.see_through else (b, a)
            if cover.name in self.tops:
                rings = self.rings(a, b, found, sight)
                if rings:
                    region = cards.bones & cover.bones if cards.bones and cover.bones else None
                    outer, covered, fine, members = self.outer(cards, cover, region)
                    if self._through_top(cards, cover, outer, fine, members, 1.0, [r if cards is a else r.flipped() for r in rings]):
                        return (f"{cards.name} comes through {cover.name}", rings[0].points[0], sum(len(r.details) for r in rings)), False
            return None, False
        # One object's islands on one bone are one part, as long as it isn't the character itself: chunks of hair, a hat's brim.
        if a.owner == b.owner and len(a.bones | b.bones) <= 1 and self.skull_owner != a.owner:
            return None, False
        rings = self.rings(a, b, found, sight)
        if not rings:
            return None, False
        kinds = [(ring, self.kind(a, b, ring)) for ring in rings]
        apart = [ring for ring, kind in kinds if kind == "apart"]
        if apart:
            return (f"{a.name} and {b.name} cut each other, and no joint connects them", apart[0].points[0], sum(len(r.details) for r in apart)), False
        count = sum(len(r.details) for r in rings)
        at = rings[0].points[0]
        joined = [ring for ring, kind in kinds if kind == "joint"]
        if joined:
            why = self._joint(a, b)
            if why:
                return (why, at, count), True
        same = [ring for ring, kind in kinds if kind == "same"]
        if same and self.judge_layers:
            why = self._layers(a, b, same) or self._layers(b, a, [ring.flipped() for ring in same])
            if why:
                return (why, at, count), False
        return None, bool(joined) and not same


def _around_line(points, start, end):
    """Whether points go all the way around a line, how long they are along it, and how far they are from it."""
    axis = end - start
    if axis.length < 1e-6 or len(points) < 3:
        return False, 0.0, 0.0
    axis = axis.normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    offsets = [p - start for p in points]
    angles = sorted(math.atan2(o.dot(v), o.dot(u)) for o in offsets)
    gaps = [b - a for a, b in zip(angles, angles[1:])] + [angles[0] + 2.0 * math.pi - angles[-1]]
    along = [o.dot(axis) for o in offsets]
    return max(gaps) < math.radians(130.0), max(along) - min(along), sum((o - axis * o.dot(axis)).length for o in offsets) / len(offsets)


def _long_axis(points):
    """The longest axis of a set of points: start and end of a line through them."""
    if len(points) < 2:
        return Vector(), Vector((0.0, 0.0, 1.0))
    center = sum(points, Vector()) / len(points)
    data = numpy.array([tuple(p - center) for p in points])
    _, _, axes = numpy.linalg.svd(data, full_matrices=False)
    axis = Vector(axes[0])
    return center, center + axis


def judge_rest(surfaces, between, judge, sight_for, seams=()):
    """The crossings between surfaces at rest that show as defects, and the pairs a joint holds. Pairs in `seams` were cut where
    they cross: what could tell a poke there is gone, and the whole parts' receipt is their proof."""
    pokes, joints = [], set()
    for (i, j), found in sorted(between.items()):
        a, b = surfaces[i], surfaces[j]
        if (i, j) in seams:
            continue
        result, joined = judge.pair(a, b, found, sight_for(a, b))
        if joined:
            joints.add((a.name, b.name))
        if result:
            pokes.append({"a": a, "b": b, "why": result[0], "at": result[1], "count": result[2]})
    return pokes, joints


def _boxes_apart(a, b, margin):
    for k in range(3):
        if max(v.co[k] for v in a.bm.verts) + margin < min(v.co[k] for v in b.bm.verts) or max(v.co[k] for v in b.bm.verts) + margin < min(v.co[k] for v in a.bm.verts):
            return True
    return False


def apart_from_body(surfaces, crossing, scale, enclosed=True):
    """The surfaces that hold on to nothing, or only to each other: a head above its neck, an arm beside the shoulder, a neck and
    head together. Surfaces hold each other when they cross, or come close: half a percent of the height for a joint, more
    for what is worn on the same bones, as a cape hangs off a back. And when one is around the other, as a loose hat is around
    a head. Whatever isn't in the largest group is apart."""
    if len(surfaces) < 2:
        return []
    index = {p.name: k for k, p in enumerate(surfaces)}
    group = list(range(len(surfaces)))

    def find(k):
        while group[k] != k:
            group[k] = group[group[k]]
            k = group[k]
        return k

    for x, y in crossing:
        if x in index and y in index:
            group[find(index[x])] = find(index[y])
    close, worn = 0.005 * scale, 0.03 * scale
    for i, a in enumerate(surfaces):
        for j in range(i + 1, len(surfaces)):
            if find(i) == find(j):
                continue
            b = surfaces[j]
            limit = worn if a.bones & b.bones else close
            if _boxes_apart(a, b, limit):
                if not enclosed or not any(inside(a, v.co) for v in b.bm.verts[:50]):
                    continue
            if distance_between(a, b, limit) <= limit or (enclosed and (any(inside(b, v.co) for v in a.bm.verts) or any(inside(a, v.co) for v in b.bm.verts))):
                group[find(i)] = find(j)
    areas = {}
    for k, part in enumerate(surfaces):
        areas[find(k)] = areas.get(find(k), 0.0) + part.area
    main = max(areas, key=areas.get)
    return [part for k, part in enumerate(surfaces) if find(k) != main]


def distance_between(a, b, enough):
    """How close two surfaces come, from a's vertices to b's surface and back, stopping once it's `enough`."""
    closest = float("inf")
    for first, second in ((a, b), (b, a)):
        for vertex in first.bm.verts:
            distance = second.tree.find_nearest(vertex.co)[3]
            if distance is not None and distance < closest:
                closest = distance
                if closest <= enough:
                    return closest
    return closest


def sunk_depth(a, b, details):
    """How far faces of a go behind the faces of b they cross: how deep two surfaces press into each other."""
    deepest = 0.0
    for x, y, _ in details:
        face = b.bm.faces[y]
        origin = face.calc_center_median()
        for vertex in a.bm.faces[x].verts:
            deepest = max(deepest, -face.normal.dot(vertex.co - origin))
    return deepest


def pose_pokes(surfaces, judge, sight_for, skip_pairs=frozenset(), rest_within=None):
    """What a pose shows wrong, by the same judgement as at rest. Returns the pokes (label, count, at, why), how many faces of each
    surface merely brush each other where a joint folds, and the crossings. `rest_within` holds a surface's own crossings at
    rest, by bone pair; `skip_pairs` are the pairs of names not to judge: cut where they cross, or reported at rest."""
    within, between = crossings(surfaces)
    judge.fresh()
    bones = judge.joints
    pokes, brushing = [], {}
    for i, pairs in within.items():
        s = surfaces[i]
        if s.owner in judge.see_through:
            continue
        known = (rest_within or {}).get(s.name, set())
        sight = sight_for(s, s)
        for ring in rings_of(s, s, pairs, judge.tolerance):
            if extent(ring.points) < judge.graze or not any(sight.visible(p) for p in ring.points):
                continue
            x, y, points = ring.details[0]
            ba, bb = s.bone_at(x, points), s.bone_at(y, points)
            # A thumb that touches a thigh on the way past isn't through it: what shows is how deep it goes.
            if bones.near(ba, bb) or _ordered(ba, bb) in known or sunk_depth(s, s, ring.details) < 0.015 * judge.scale:
                brushing[s.name] = brushing.get(s.name, 0) + len(ring.details)
            else:
                pokes.append({"label": f"{ba} into {bb}", "count": len(ring.details), "at": ring.points[0], "why": f"{ba} goes into {bb}"})
    for (i, j), found in sorted(between.items()):
        a, b = surfaces[i], surfaces[j]
        if (a.name, b.name) in skip_pairs or (judge.skip and judge.skip(a, b)):
            continue
        # Both carried by one bone alone: they move as one, and nothing a pose does can change how they sit.
        if len(a.bones | b.bones) == 1:
            continue
        sight = sight_for(a, b)
        if a.owner in judge.see_through or b.owner in judge.see_through:
            # Soft: they fail only on what no joint connects, as when hair cards go through a shoulder.
            for ring in judge.rings(a, b, found, sight):
                if judge.kind(a, b, ring) == "apart":
                    pokes.append({"label": _through(a, b), "count": len(ring.details), "at": ring.points[0], "why": "no joint connects them"})
                    break
            continue
        rings = rings_of(a, b, found, judge.tolerance)
        result, _ = judge.pair(a, b, found, sight)
        if result:
            # Thighs brush each other in a stride, a hand a hip on the way past: no joint connects them, and it's no poke until one sinks
            # into the other.
            if result[0].endswith("no joint connects them") and _only_brushing(a, b, judge):
                continue
            pokes.append({"label": _through(a, b), "count": result[2], "at": result[1], "why": result[0]})
    return pokes, brushing, between


def _only_brushing(a, b, judge):
    """Whether two parts press into each other only a little."""
    _, covered, fine, _ = judge.outer(a, b)
    return not covered or max(b.tree.find_nearest(fine.bm.verts[i].co)[3] for i in covered) < 0.015 * judge.scale


def folds_on_itself(surface, ring, judge):
    """Whether a surface's crossing of itself is a fold: on bones a joint connects, or pressed in only a little, as in a crease at the
    crotch or two thighs that touch. Deeper than that on one bone, where nothing bends, it is crumpled. With no bones nothing
    tells, and it counts."""
    bones = judge.joints
    if not bones.node:
        return False
    pressed = []
    for x, y, points in ring.details:
        ba, bb = surface.bone_at(x, points), surface.bone_at(y, points)
        if ba == bb or bones.mirrored(ba, bb):
            pressed.append((x, y, points))
        elif not bones.near(ba, bb):
            return False
    return not pressed or sunk_depth(surface, surface, pressed) < 0.015 * judge.scale


def _through(a, b):
    small, large = (a, b) if a.area <= b.area else (b, a)
    return f"{small.name} through {large.name}"


def _ordered(a, b):
    return (a, b) if (a or "") <= (b or "") else (b, a)
