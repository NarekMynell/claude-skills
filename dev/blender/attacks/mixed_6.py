# Sixth round: clean controls for what's going in the report, and what's left.
import os, shutil, sys, tempfile
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
from defects_1 import raise_z, move, plane, open_lathe, fits_hat, dense_leg, trouser
from defects_2 import constrained_rig, wide_hips
from clean_1 import union
from clean_2 import ring_on, spider_rig, spider, jointed_arm_person
from cuts_1 import culling_render, keys, run_clip, pipeline
CASES.clear()


@case("constraints_control", "fail", "hands through wide hips in a pose, LEGS_JOINED so nothing else speaks (control: must fail)")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True}
    return person(extra)


@case("constraints_copy_transforms", "fail", "the same, with deform bones driven by Copy Transforms from control bones, as Rigify and many control rigs do")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        constrained_rig(rig)
        def after(report):
            print("  poses_checked:", report["info"].get("poses_checked"))
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True, "_after": after}
    return person(extra)


@case("constraints_ik_on_the_forearm_only", "fail", "the same, with a two-bone IK constraint on each forearm toward a hand target: the arms stay in the rest pose whatever the test poses ask")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        for side in ("L", "R"):
            h = rig.data.edit_bones[f"hand.{side}"]
            t = rig.data.edit_bones.new(f"ik_target.{side}")
            t.head, t.tail = h.head.copy(), h.head + Vector((0, 0, 0.05))
            t.use_deform = False
        bpy.ops.object.mode_set(mode="OBJECT")
        for side in ("L", "R"):
            c = rig.pose.bones[f"forearm.{side}"].constraints.new("IK")
            c.target = rig
            c.subtarget = f"ik_target.{side}"
            c.chain_count = 2
        bpy.context.view_layer.update()
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True}
    return person(extra)


@case("twist_parts_control_plain_rig", "pass", "the body of parts with rings along its limbs, on the plain rig (control for the twist-bone case)")
def _():
    settings = person(sections=8)
    settings["WHOLE_PARTS"] = True
    return settings


@case("spider_where_the_joint_is", "pass", "a spider with coxa bones: where do the crossings that 'open' sit?")
def _():
    rig = spider_rig()
    spider(rig)
    objs = [bpy.data.objects[n] for n in meshes()]
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    character = helpers.Character(objs, rig)
    surfaces = character.gather()
    by = {s.name: s for s in surfaces}
    height = max(v.co.z for s in surfaces for v in s.bm.verts) - min(v.co.z for s in surfaces for v in s.bm.verts)
    sight = helpers.Sight(surfaces, height)
    a, b = by["Fem0.R"], by["Fem1.R"]
    pairs = a.tree.overlap(b.tree)
    points = [p for x, y in pairs for p in helpers.crossing_points(a, x, b, y)]
    print("  crossing points:", len(points), "visible:", sum(1 for p in points if sight.visible(p)), "at", [round(c, 3) for c in points[0]])
    helpers.free(surfaces)
    rig.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


@case("hair_under_hat_both_in_groups", "pass", "a hat that fits over the hair, each in a PART_GROUP as the docstring's example: the hair is mostly under the hat, as hair is")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=16), DARK), rig, "head")
        on(paint(lathe("HairLong", [(0.0, 1.66), (0.098, 1.66), (0.116, 1.70), (0.102, 1.78), (0.0, 1.812)], segments=16), DARK), rig, "head")
        on(paint(lathe("Cap", [(0.0, 1.70), (0.2, 1.70), (0.2, 1.705), (0.13, 1.71), (0.125, 1.82), (0.0, 1.86)], segments=16), RED), rig, "head")
        return {"WHOLE_PARTS": True, "PART_GROUPS": {"hair": ["Hair", "HairLong"], "hat": ["Cap"]}, "_render": {"VIEWS": ["front", "left"]}}
    return person(extra)


@case("hair_cards_through_hat_crown", "fail", "hair cards, in SEE_THROUGH, coming out through the crown of a hat")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), BROWN), rig, "head")
        mesh = bpy.data.meshes.new("Cards")
        verts, faces = [], []
        for k in range(6):
            angle = k * math.pi / 6
            dx, dy = 0.12 * math.cos(angle), 0.12 * math.sin(angle)
            base = len(verts)
            verts += [(-dx, -dy, 1.74), (dx, dy, 1.74), (dx, dy, 1.96), (-dx, -dy, 1.96)]
            faces.append((base, base + 1, base + 2, base + 3))
        mesh.from_pydata(verts, [], faces)
        cards = bpy.data.objects.new("Cards", mesh)
        bpy.context.scene.collection.objects.link(cards)
        on(paint(cards, DARK), rig, "head")
        return {"WHOLE_PARTS": True, "SEE_THROUGH": ["Cards"], "_render": {"VIEWS": ["front", "left", "top"]}}
    return person(extra)


@case("hair_cards_through_hat_side_named_fringe_low", "fail", "hair cards, in SEE_THROUGH, named Strands, poking out of the crown's side, under where a look from above meets the crown")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hat", [(0.0, 1.70), (0.2, 1.70), (0.2, 1.705), (0.13, 1.71), (0.125, 1.82), (0.09, 1.86), (0.0, 1.87)], segments=16), BROWN), rig, "head")
        mesh = bpy.data.meshes.new("Strands")
        verts = [(-0.02, -0.07, 1.74), (0.02, -0.07, 1.74), (0.02, -0.16, 1.80), (-0.02, -0.16, 1.80)]
        mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
        cards = bpy.data.objects.new("Strands", mesh)
        bpy.context.scene.collection.objects.link(cards)
        on(paint(cards, DARK), rig, "head")
        return {"WHOLE_PARTS": True, "SEE_THROUGH": ["Strands"], "_render": {"VIEWS": ["front", "left", "top"]}}
    return person(extra)


@case("dog_with_collar_saddle_and_hat", "pass", "the repo's one-skin dog with a collar, a saddle with a girth, and a little hat")
def _():
    body, rig = quadruped.build()
    paint(body, BROWN)
    neck = rig.data.bones["neck"]
    a = neck.head_local.lerp(neck.tail_local, 0.5)
    on(paint(ring_on("Collar", a, neck.tail_local - neck.head_local, 0.075, 0.04, 0.012, segments=14), RED), rig, "neck")
    on(paint(lathe("Saddle", [(0.0, 0.575), (0.14, 0.575), (0.14, 0.59), (0.10, 0.62), (0.0, 0.625)], center=(0.0, 0.05), segments=16), DARK), rig, "spine", "hips")
    on(paint(ring_on("Girth", (0, 0.05, 0.47), (0, 1, 0), 0.138, 0.11, 0.02, segments=16), DARK), rig, "spine", "hips")
    skull = rig.data.bones["head"].head_local
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front", "front_left", "top"], "COLUMNS": 2}}


@case("wand_with_allow_crossing", "pass", "the wand in a fist, declared with ALLOW_CROSSING")
def _():
    def extra(rig, parts):
        jointed_arm_person(rig, parts)
        bones = rig.data.bones
        w, h = bones["forearm.L"].tail_local, bones["hand.L"].tail_local
        c = w.lerp(h, 0.5)
        on(paint(capsule("Fist", c, c + Vector((0.0, 0.0, 0.001)), 0.05, 0.05, segments=12), SKIN), rig, "hand.L")
        on(paint(capsule("Wand", c + Vector((0, -0.28, 0)), c + Vector((0, 0.05, 0)), 0.006, 0.01, segments=6, rings=1), BROWN), rig, "hand.L")
        return {"WHOLE_PARTS": True, "POSES": False, "SYMMETRIC": ["Torso"], "ALLOW_CROSSING": ["Fist+Wand"]}
    return person(extra)


@case("hat_band_explicit_covers", "pass", "the hat with a band, COVERS_FROM_ABOVE naming the hat alone")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), DARK), rig, "head")
        on(paint(ring("Band", 0.133, 0.115, 1.72, 1.75, center=(0, 0, 0), segments=16), RED), rig, "head")
        return {"WHOLE_PARTS": True, "COVERS_FROM_ABOVE": ["Hat"]}
    return person(extra)


if __name__ == "__main__":
    main()
