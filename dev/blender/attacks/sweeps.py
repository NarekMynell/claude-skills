# Sweeps and clean accessories: low-poly against dense, how deep is deep, and what people wear.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
import cuts_1 as cuts
from defects_1 import raise_z, move, plane, open_lathe, fits_hat
from clean_1 import union, hair_shell
from clean_2 import ring_on
CASES.clear()


def head_part(rig, parts, segments):
    bpy.data.objects.remove(parts["Head"], do_unlink=True)
    rings = max(3, segments // 3)
    return on(paint(capsule("Head", (0, 0, 1.62), (0, 0, 1.68), 0.105, 0.105, segments=segments, rings=rings), SKIN), rig, "head")


for hs in (6, 8, 12, 24):
    for cs in (5, 6, 8, 12, 16, 32):
        for bite in (0.005, 0.015):
            def make(hs=hs, cs=cs, bite=bite):
                def build():
                    def extra(rig, parts):
                        head_part(rig, parts, hs)
                        # The band narrower than the head by `bite`, the crown clear above it.
                        r = 0.105 - bite
                        hat = lathe("Hat", [(0.0, 1.655), (r, 1.655), (0.128, 1.70), (0.122, 1.82), (0.0, 1.86)], segments=cs)
                        on(paint(hat, BROWN), rig, "head")
                        return {"WHOLE_PARTS": True}
                    return person(extra)
                return build
            case(f"biting_hat_head{hs}_hat{cs}_bite{int(bite * 1000)}mm", "pass", "a hat whose band bites into the forehead")(make())

for depth in (0.001, 0.003, 0.006, 0.012, 0.03):
    def make(depth=depth):
        def build():
            def extra(rig, parts):
                head_part(rig, parts, 24)
                top = 1.785 - depth
                hat = lathe("Hat", [(0.0, 1.70), (0.2, 1.70), (0.2, 1.705), (0.13, 1.71), (0.125, top - 0.03), (0.06, top - 0.004), (0.0, top)], segments=24)
                on(paint(hat, BROWN), rig, "head")
                return {"WHOLE_PARTS": True}
            return person(extra)
        return build
    case(f"crown_poke_{depth * 1000:.0f}mm", "fail" if depth >= 0.009 else "pass", "the head's top comes through the crown by this much (under half a percent of the height is a graze)")(make())


def wearing(fn):
    def build():
        return person(fn)
    return build


def _glasses(rig, parts):
    # Two rings, a bridge and two temples going into the head at the sides: one closed surface per piece, one object.
    objs = []
    for s, x in (("L", 1), ("R", -1)):
        objs.append(ring_on(f"Rim{s}", (0.04 * x, -0.112, 1.66), (0, 1, 0), 0.03, 0.024, 0.004, segments=12))
        objs.append(capsule(f"Temple{s}", (0.07 * x, -0.11, 1.665), (0.095 * x, 0.02, 1.665), 0.004, 0.004, segments=6, rings=1))
    objs.append(capsule("Bridge", (-0.012, -0.112, 1.665), (0.012, -0.112, 1.665), 0.004, 0.004, segments=6, rings=1))
    for o in objs:
        on(paint(o, DARK), rig, "head")
    partsbody.merge(objs, "Glasses")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "top"], "CLOSEUPS": [{"label": "face", "center": [0, -0.08, 1.65], "size": 0.35, "view": "front_left"}]}}


def _earrings(rig, parts):
    for s, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Ear.{s}", (0.09 * x, 0, 1.64), (0.135 * x, 0, 1.66), 0.025, 0.018, segments=8, rings=2), SKIN), rig, "head")
        on(paint(ring_on(f"Earring.{s}", (0.128 * x, -0.005, 1.625), (0, 1, 0), 0.022, 0.016, 0.003, segments=10), YELLOW), rig, "head")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front"], "CLOSEUPS": [{"label": "ear", "center": [0.12, 0, 1.64], "size": 0.2, "view": "front"}]}}


def _beard(rig, parts):
    on(paint(capsule("Beard", (0, -0.075, 1.55), (0, -0.10, 1.46), 0.06, 0.03, segments=10), DARK), rig, "head")
    on(paint(capsule("Moustache", (-0.04, -0.103, 1.60), (0.04, -0.103, 1.60), 0.012, 0.012, segments=6), DARK), rig, "head")
    for s, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Brow.{s}", (0.015 * x, -0.095, 1.69), (0.07 * x, -0.08, 1.695), 0.008, 0.006, segments=6), DARK), rig, "head")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


def _antlers(rig, parts):
    for s, x in (("L", 1), ("R", -1)):
        a = capsule(f"AntlerBase{s}", (0.05 * x, 0, 1.76), (0.16 * x, 0, 1.92), 0.015, 0.01, segments=6)
        b = capsule(f"AntlerTine{s}", (0.10 * x, 0, 1.84), (0.10 * x, -0.09, 1.93), 0.01, 0.006, segments=6)
        on(paint(union(f"Antler.{s}", [a, b]), BROWN), rig, "head")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


def _headband(rig, parts):
    on(paint(ring("Headband", 0.112, 0.085, 1.70, 1.74, segments=20), RED), rig, "head")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "top"]}}


def _crown(rig, parts):
    c = ring("Crown", 0.115, 0.09, 1.74, 1.80, segments=20)
    on(paint(c, YELLOW), rig, "head")
    return {"WHOLE_PARTS": True, "COVERS_FROM_ABOVE": [], "_render": {"VIEWS": ["front", "top"]}}


def _goggles(rig, parts):
    on(paint(ring("Strap", 0.112, 0.09, 1.70, 1.725, segments=20), DARK), rig, "head")
    for s, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Lens.{s}", (0.04 * x, -0.095, 1.74), (0.04 * x, -0.115, 1.74), 0.028, 0.028, segments=10), GRAY), rig, "head")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


def _backpack(rig, parts):
    on(paint(capsule("Pack", (0, 0.20, 1.05), (0, 0.20, 1.32), 0.11, 0.10, segments=10, squash_y=1.0), BROWN), rig, "chest")
    for s, x in (("L", 1), ("R", -1)):
        strap = ring_on(f"Strap.{s}", (0.105 * x, 0.01, 1.33), (1, 0, 0), 0.155, 0.135, 0.016, segments=14)
        for v in strap.data.vertices:
            pass
        on(paint(strap, DARK), rig, "chest")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "back", "left", "front_left"], "COLUMNS": 2}}


def _scarf(rig, parts):
    on(paint(ring("Scarf", 0.09, 0.03, 1.46, 1.53, segments=12), RED), rig, "neck")
    on(paint(capsule("ScarfTail", (0.03, -0.08, 1.46), (0.05, -0.135, 1.20), 0.03, 0.025, segments=8), RED), rig, "chest")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}


def _shoulder_pads(rig, parts):
    for s, x in (("L", 1), ("R", -1)):
        p = rig.data.bones[f"upper_arm.{s}"].head_local
        on(paint(capsule(f"Pad.{s}", p + Vector((-0.01 * x, 0, 0.01)), p + Vector((0.05 * x, 0, -0.01)), 0.08, 0.075, segments=12), GRAY), rig, f"upper_arm.{s}")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left"]}}


def _holster(rig, parts):
    on(paint(capsule("Holster", (0.155, 0.0, 0.92), (0.18, 0.0, 0.72), 0.04, 0.03, segments=8), BROWN), rig, "thigh.L")
    on(paint(capsule("HolsterStrap", (0.17, 0, 0.95), (0.17, 0, 0.99), 0.05, 0.05, segments=8, rings=1), BROWN), rig, "hips")
    return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


for name, fn, note in (("glasses", _glasses, "glasses whose temples go into the head"), ("earrings", _earrings, "earrings through the ear lobes"), ("beard_moustache_brows", _beard, "beard, moustache and brows set into the face"),
                       ("antlers_one_surface", _antlers, "antlers in one surface each, set in the head"), ("headband", _headband, "a headband, whose top edge is a little over 4 cm under the head's top"), ("crown_covers_off", _crown, "a ring crown, with COVERS_FROM_ABOVE off as the docstring asks"),
                       ("goggles_on_forehead", _goggles, "goggles on the forehead, strap around the head"), ("backpack_and_straps", _backpack, "a backpack with strap loops over the shoulders"), ("scarf", _scarf, "a scarf around the neck, resting on the shoulders, with a tail"),
                       ("shoulder_pads", _shoulder_pads, "shoulder pads set over the shoulders"), ("holster_on_the_thigh", _holster, "a holster on the thigh and a strap around it")):
    case(f"wear_{name}", "pass", note)(wearing(fn))


if __name__ == "__main__":
    main()
