# Is it the name? The same bun and fringe, under names the hair word list doesn't hold.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import clean_1 as fp1
CASES.clear()


def cap(rig):
    on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=20), DARK), rig, "head")


@case("bun_named_knot", "pass", "the same bun as hair_bun_on_hair_cap, named Knot")
def _():
    def extra(rig, parts):
        cap(rig)
        on(paint(capsule("Knot", (0, 0.03, 1.80), (0, 0.03, 1.84), 0.04, 0.04, segments=12), DARK), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("fringe_named_forelock", "pass", "the same fringe as hair_fringe_on_hair_cap, named Forelock")
def _():
    def extra(rig, parts):
        cap(rig)
        on(paint(capsule("Forelock", (-0.06, -0.09, 1.76), (0.06, -0.09, 1.76), 0.035, 0.035, segments=10), DARK), rig, "head")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("hair_cards_with_covers_off", "pass", "hair cards in SEE_THROUGH with COVERS_FROM_ABOVE off, as the repo's own test runs them")
def _():
    def extra(rig, parts):
        mesh = bpy.data.meshes.new("Cards")
        verts, faces = [], []
        for k in range(6):
            angle = k * math.pi / 6
            dx, dy = 0.12 * math.cos(angle), 0.12 * math.sin(angle)
            base = len(verts)
            verts += [(-dx, -dy, 1.74), (dx, dy, 1.74), (dx, dy, 1.84), (-dx, -dy, 1.84)]
            faces.append((base, base + 1, base + 2, base + 3))
        mesh.from_pydata(verts, [], faces)
        cards = bpy.data.objects.new("Cards", mesh)
        bpy.context.scene.collection.objects.link(cards)
        on(paint(cards, DARK), rig, "head")
        return {"WHOLE_PARTS": True, "SEE_THROUGH": ["Cards"], "COVERS_FROM_ABOVE": []}
    return person(extra)


@case("statue_plinth_legs_joined", "pass", "the statue on a plinth, no neck part, LEGS_JOINED on: what the setting buys")
def _():
    names = []
    for name, args, kwargs in (("Torso", ((0, 0, 1.02), (0, 0, 1.46), 0.16, 0.17), {"segments": 12, "squash_y": 0.68}),
                               ("Head", ((0, 0, 1.65), (0, 0, 1.78), 0.1, 0.1), {"segments": 12}),
                               ("Leg.L", ((0.09, 0, 1.0), (0.09, 0, 0.15), 0.07, 0.05), {"segments": 8}),
                               ("Leg.R", ((-0.09, 0, 1.0), (-0.09, 0, 0.15), 0.07, 0.05), {"segments": 8})):
        names.append(paint(capsule(name, *args, **kwargs), GRAY).name)
    names.append(paint(lathe("Plinth", [(0.0, 0.0), (0.3, 0.0), (0.3, 0.12), (0.0, 0.12)], segments=24), BROWN).name)
    return {"TARGETS": names, "WHOLE_PARTS": True, "LEGS_JOINED": True}


if __name__ == "__main__":
    main()
