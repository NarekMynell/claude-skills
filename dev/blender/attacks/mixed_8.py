# One skin under a closed trouser leg and a closed sleeve: the same pokes as on parts.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
import clean_3 as fp3
import defects_3 as fn3
import cuts_1 as cuts
import mixed_4 as round4
import mixed_7 as round7
from defects_1 import raise_z, move, plane, open_lathe, fits_hat, trouser
from clean_3 import subdivided_mannequin
from mixed_7 import one_skin_with_trousers
CASES.clear()


def skin(level=3):
    body, rig = subdivided_mannequin(level)
    mannequin.clean_weights(body, rig)
    paint(body, SKIN)
    return body, rig


SETTINGS = dict(WHOLE_PARTS=True, POSES=False, SINGLE_LAYER=False)


@case("skin_closed_trouser_clean_control", "pass", "one skin, a closed trouser leg around its left leg")
def _():
    body, rig = skin()
    trouser(rig)
    return dict(SETTINGS, TARGETS=["Body", "Trouser.L"], ARMATURE=rig.name)


@case("skin_closed_trouser_local_poke_control", "fail", "the knee through it in one place (control: must fail)")
def _():
    body, rig = skin()
    trouser(rig)
    bump(body, (0.10, -0.05, 0.50), 0.06, (0.0, -0.09, 0.0))
    return dict(SETTINGS, TARGETS=["Body", "Trouser.L"], ARMATURE=rig.name, _render={"VIEWS": ["front", "left"]})


@case("skin_closed_trouser_knee_ring", "fail", "the knee wider than the trouser leg all the way around, on one skin")
def _():
    body, rig = skin()
    trouser(rig)
    knee = Vector((0.10, 0.0, 0.50))
    for v in body.data.vertices:
        if abs(v.co.z - 0.50) < 0.04 and v.co.x > 0.02:
            d = Vector((v.co.x - knee.x, v.co.y - knee.y, 0))
            if d.length > 1e-4:
                v.co.x, v.co.y = knee.x + d.x / d.length * 0.115, knee.y + d.y / d.length * 0.115
    return dict(SETTINGS, TARGETS=["Body", "Trouser.L"], ARMATURE=rig.name, _render={"VIEWS": ["front", "left", "front_left"], "TARGETS": ["Body", "Trouser.L"]})


@case("skin_closed_trouser_hem_poke", "fail", "the shin through the front of the leg from the hem up, joined to the bare ankle, on one skin")
def _():
    body, rig = skin()
    trouser(rig)
    for v in body.data.vertices:
        if 0.12 < v.co.z < 0.42 and v.co.x > 0.02 and v.co.y < -0.005:
            v.co.y -= 0.08 * min(1.0, (0.42 - v.co.z) / 0.04, (v.co.z - 0.12) / 0.04)
    return dict(SETTINGS, TARGETS=["Body", "Trouser.L"], ARMATURE=rig.name, _render={"VIEWS": ["front", "left", "front_left"], "TARGETS": ["Body", "Trouser.L"]})


@case("skin_open_trouser_knee_ring", "fail", "an open trouser leg, offset from the skin: the knee wider than it all the way around")
def _():
    body, tr, rig = one_skin_with_trousers()
    knee = Vector((0.10, 0.0, 0.50))
    for v in body.data.vertices:
        if abs(v.co.z - 0.50) < 0.04 and v.co.x > 0.02:
            d = Vector((v.co.x - knee.x, v.co.y - knee.y, 0))
            if d.length > 1e-4:
                v.co.x, v.co.y = knee.x + d.x * 1.6, knee.y + d.y * 1.6
    def after(report):
        print("  why:", report.get("examples", {}).get("intersections"))
    return dict(SETTINGS, TARGETS=["Body", "Trousers"], ARMATURE=rig.name, TWO_SIDED=["Trousers"], _after=after, _render={"VIEWS": ["front", "left", "front_left"]})


if __name__ == "__main__":
    main()
