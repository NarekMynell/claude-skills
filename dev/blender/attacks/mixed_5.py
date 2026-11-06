# Fifth round: loose ends.
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
from clean_1 import union
from clean_2 import ring_on, spider_rig, spider
from clean_3 import subdivided_mannequin
from defects_3 import add_head_top_end
from mixed_4 import hero_by_the_guide
from cuts_1 import culling_render, keys, run_clip, pipeline
CASES.clear()
PROOFS = tempfile.mkdtemp(prefix="proofs", dir=HERE)
cuts.PROOFS = PROOFS


def nick(body, sign, max_dist=0.02):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    tree = helpers.BVHTree.FromBMesh(bm)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    best = None
    for v in bm.verts:
        if 0.10 < abs(v.co.x) < 0.3 and 1.05 < v.co.z < 1.45 and v.co.x * sign > 0:
            for d in (Vector((-sign, 0, -0.35)).normalized(), Vector((-sign, 0, 0)), Vector((-sign, 0, 0.35)).normalized(), Vector((0, 0, -1))):
                hit = tree.ray_cast(v.co + d * 1e-4, d, max_dist)
                if hit[0] is None or hit[3] < 1e-3 or hit[1].dot(d) >= 0:
                    continue
                # Not a neighbor: the face it hits shares nothing with this vertex's ring.
                near = {n.index for f in v.link_faces for n in f.verts}
                if near & {n.index for n in bm.faces[hit[2]].verts}:
                    continue
                if best is None or hit[3] < best[1]:
                    best = (v.index, hit[3], d.copy())
    bm.free()
    if best is None:
        return None
    index, dist, d = best
    body.data.vertices[index].co += d * (dist + 0.002)
    return index, round(dist * 1000, 1), [round(c, 2) for c in d]


@case("nick_dense_none", "pass", "the dense mannequin (control)")
def _():
    body, rig = subdivided_mannequin(3)
    mannequin.clean_weights(body, rig)
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False}


@case("nick_dense_one", "pass", "the dense mannequin with one vertex at one armpit pushed 2 mm through the torso's side")
def _():
    body, rig = subdivided_mannequin(3)
    mannequin.clean_weights(body, rig)
    print("  nick", nick(body, 1))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False}


@case("nick_dense_two", "pass", "the same on both sides: each nick as small as before")
def _():
    body, rig = subdivided_mannequin(3)
    mannequin.clean_weights(body, rig)
    print("  nicks", nick(body, 1), nick(body, -1))
    def after(report):
        print("  examples:", report.get("examples", {}).get("intersections"))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False, "_after": after}


@case("hero_waist_bulge_on_pipeline", "pass", "the hero with WAIST_BULGE so whole parts pass: the guide's three steps with one cut")
def _():
    rig = partsbody.person_rig()
    hero_by_the_guide(rig)
    settings = {"TARGETS": meshes(), "ARMATURE": rig.name, "FINGERS": 5, "SYMMETRIC": ["Tunic"], "WAIST_BULGE": True}
    whole, done, final = pipeline(settings, "hero2")
    print("  whole:", whole["passed"], short(whole))
    print("  final after one cut:", final["passed"], short(final))
    culling_render("hero_after_one_cut", TARGETS=settings["TARGETS"], VIEWS=["front", "back", "left", "front_left", "top"])
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="hero2")


@case("hero_repeat_cut_until_stable", "pass", "the same hero, the cut repeated until stable")
def _():
    rig = partsbody.person_rig()
    hero_by_the_guide(rig)
    settings = {"TARGETS": meshes(), "ARMATURE": rig.name, "FINGERS": 5, "SYMMETRIC": ["Tunic"], "WAIST_BULGE": True}
    whole, done, final = pipeline(settings, "hero3")
    for k in range(6):
        again = cut(TARGETS=settings["TARGETS"], ARMATURE=rig.name)
        print("  cut again:", again["deleted"])
        if not again["deleted"]:
            break
    return dict(settings, PROOF_DIR=PROOFS, PROOF_NAME="hero3")


@case("mesh_child_feather_in_targets", "pass", "a hat parented to the head bone, and a feather parented to the hat: it follows in the game. In TARGETS it reads as not skinned")
def _():
    def extra(rig, parts):
        hat = paint(fits_hat(), BROWN)
        parent_to_bone(hat, rig, "head")
        feather = paint(capsule("Feather", (0.13, 0, 1.75), (0.2, 0.05, 1.92), 0.015, 0.006, segments=6), RED)
        feather.parent = hat
        feather.matrix_parent_inverse = hat.matrix_world.inverted()
        return {"WHOLE_PARTS": True, "TARGETS": meshes()}
    return person(extra)


@case("mesh_child_hat_through_head_no_targets", "fail", "the same mesh child, a spike going right through the head, parented to the head mesh: with ARMATURE and no TARGETS it isn't gathered and nothing says so")
def _():
    def extra(rig, parts):
        spike = paint(capsule("Spike", (-0.18, 0, 1.65), (0.18, 0, 1.65), 0.015, 0.015, segments=6, rings=2), RED)
        spike.parent = parts["Head"]
        return {"WHOLE_PARTS": True}
    settings = person(extra)
    settings.pop("TARGETS", None)
    return settings


@case("flipped_arm_part", "fail", "an arm part inside out: the player sees through it. Only what covers the head is checked for this")
def _():
    def extra(rig, parts):
        parts["Arm.L"].data.flip_normals()
        parts["Arm.L"].data.update()
        def after(report):
            ns = {"__file__": SCRIPTS + "/validate_mesh.py", "TARGETS": ["Arm.L"]}
            exec(compile(open(ns["__file__"]).read(), ns["__file__"], "exec"), ns)
            r = ns["result"]
            print("  validate_mesh passed:", r.get("passed"), {k: v for k, v in r.items() if k not in ("passed",)} if len(str(r)) < 400 else str(r)[:400])
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("facing_back_no_toes_no_fingers", "fail", "a person of the mitten kind, with no toe or finger bones, facing +Y")
def _():
    def extra(rig, parts):
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="EDIT")
        edit = rig.data.edit_bones
        for b in list(edit):
            if b.name.startswith(("toe", "thumb", "index", "middle", "ring", "little")):
                edit.remove(b)
        for b in edit:
            b.head.y, b.tail.y = -b.head.y, -b.tail.y
        bpy.ops.object.mode_set(mode="OBJECT")
        for o in parts.values():
            for v in o.data.vertices:
                v.co.y = -v.co.y
            o.data.flip_normals()
            o.data.update()
        return {"WHOLE_PARTS": True, "FINGERS": 0, "_render": {"VIEWS": ["left", "front_left"]}}
    return person(extra)


def lowpoly_arm(rig, parts, end_r):
    bones = rig.data.bones
    for side in ("L", "R"):
        bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
        a, h = bones[f"upper_arm.{side}"].head_local, bones[f"hand.{side}"].tail_local
        on(paint(capsule(f"Arm.{side}", a, h, 0.052, 0.042, segments=6, sections=2), SKIN), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        w = bones[f"forearm.{side}"].tail_local
        on(paint(capsule(f"Sleeve.{side}", a, a.lerp(w, 0.8), 0.066, end_r, segments=6, sections=2), RED), rig, f"upper_arm.{side}", f"forearm.{side}")


@case("lowpoly_sleeve_no_bite", "fail", "a low-poly sleeve clear of the arm at rest: at a bent elbow the arm pokes through (control: must fail)")
def _():
    def extra(rig, parts):
        lowpoly_arm(rig, parts, 0.06)
        def after(report):
            apply_named_pose(rig, "arms_forward")
            render("lowpoly_no_bite_pose", VIEWS=["left", "top", "front_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("lowpoly_sleeve_with_bite", "fail", "the same sleeve whose cuff bites the arm a little at rest: its big faces are 'known' to cross, so the same poke at the elbow is forgiven")
def _():
    def extra(rig, parts):
        lowpoly_arm(rig, parts, 0.037)
        def after(report):
            apply_named_pose(rig, "arms_forward")
            render("lowpoly_bite_pose", VIEWS=["left", "top", "front_left"], COLUMNS=3)
            rest_rig(rig)
        return {"WHOLE_PARTS": True, "_after": after}
    return person(extra)


@case("body_hole_past_the_hem", "fail", "one skin, faces deleted under a shirt and 2 cm past its hem: a visible slot at the hem")
def _():
    body, rig = subdivided_mannequin(2)
    mannequin.clean_weights(body, rig)
    paint(body, SKIN)
    shirt = body.copy()
    shirt.data = body.data.copy()
    shirt.name = "Shirt"
    bpy.context.scene.collection.objects.link(shirt)
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    torso = lambda c: 1.05 < c.z < 1.38 and abs(c.x) < 0.16
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not torso(f.calc_center_median())], context="FACES")
    bm.normal_update()
    for vertex in bm.verts:
        vertex.co += vertex.normal * 0.012
    bm.to_mesh(shirt.data)
    bm.free()
    paint(shirt, RED)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    doomed = [f for f in bm.faces if 1.03 < f.calc_center_median().z < 1.36 and abs(f.calc_center_median().x) < 0.14]
    print("  deleted", len(doomed), "of", len(bm.faces))
    bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()
    return {"TARGETS": ["Body", "Shirt"], "ARMATURE": rig.name, "ALLOW_HIDDEN": ["Body<Shirt"], "TWO_SIDED": [], "_render": {"VIEWS": ["front", "front_left"]}}


@case("hole_in_dense_shirt", "fail", "a dense shirt with a real hole on the belly, skin behind it: an opening shows skin, not the shirt's own back")
def _():
    body, rig = subdivided_mannequin(2)
    mannequin.clean_weights(body, rig)
    paint(body, SKIN)
    shirt = body.copy()
    shirt.data = body.data.copy()
    shirt.name = "Shirt"
    bpy.context.scene.collection.objects.link(shirt)
    bm = bmesh.new()
    bm.from_mesh(shirt.data)
    torso = lambda c: 1.05 < c.z < 1.38 and abs(c.x) < 0.16
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not torso(f.calc_center_median())], context="FACES")
    bm.normal_update()
    for vertex in bm.verts:
        vertex.co += vertex.normal * 0.012
    area = [f for f in bm.faces if f.calc_center_median().y < -0.03 and abs(f.calc_center_median().z - 1.2) < 0.05 and abs(f.calc_center_median().x) < 0.05]
    print("  deleting", len(area), "of", len(bm.faces))
    bmesh.ops.delete(bm, geom=area, context="FACES_ONLY")
    bm.to_mesh(shirt.data)
    bm.free()
    paint(shirt, RED)
    return {"TARGETS": ["Body", "Shirt"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "POSES": False, "_render": {"VIEWS": ["front", "front_left"]}}


@case("arm_root_head_control_plain_rig", "fail", "arm's inner end into the head when the arms come down (plain rig, control)")
def _():
    def extra(rig, parts):
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            s, h = rig.data.bones[f"upper_arm.{side}"].head_local, rig.data.bones[f"hand.{side}"].tail_local
            on(paint(capsule(f"Arm.{side}", (s.x - 0.17 * sign, s.y, s.z), h, 0.05, 0.035, segments=8, sections=8), YELLOW), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("arm_root_head_mixamo_top_end", "fail", "the same on a rig with HeadTop_End: the head becomes trunk")
def _():
    def extra(rig, parts):
        for side, sign in (("L", 1), ("R", -1)):
            bpy.data.objects.remove(parts[f"Arm.{side}"], do_unlink=True)
            s, h = rig.data.bones[f"upper_arm.{side}"].head_local, rig.data.bones[f"hand.{side}"].tail_local
            on(paint(capsule(f"Arm.{side}", (s.x - 0.17 * sign, s.y, s.z), h, 0.05, 0.035, segments=8, sections=8), YELLOW), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        add_head_top_end(rig)
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("spider_single_bone_what_the_poses_do", "pass", "a spider on one body bone: its chains and what its poses move")
def _():
    rig = spider_rig(coxa=False)
    spider(rig, coxa=False)
    roles = helpers.map_roles(rig)
    chains = helpers.leg_chains(rig, roles)
    poses = helpers.creature_poses(rig, roles)
    print("  chains:", [[b.name for b in c] for c in chains])
    print("  legs_forward:", [s[0] for s in poses["legs_forward"]], " legs_folded:", [s[0] for s in poses["legs_folded"]])
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "ALLOW_CROSSING": ["Fem0.R+Fem1.R"]}


@case("clip_spike_down_the_back", "fail", "a rear neck guard on the helmet: the head tilts back in a clip, and it goes through the back and out of the chest. Head and trunk are near: no report")
def _():
    def extra(rig, parts):
        bpy.data.objects.remove(parts["Torso"], do_unlink=True)
        on(paint(capsule("Torso", (0, 0, 0.92), (0, 0, 1.33), 0.16, 0.17, segments=12, squash_y=0.68), SKIN), rig, "hips", "spine", "chest")
        helmet = lathe("Helmet", [(0.0, 1.62), (0.125, 1.62), (0.125, 1.75), (0.09, 1.82), (0.0, 1.84)], segments=20)
        spike = capsule("Spike", (0, 0.10, 1.66), (0, 0.17, 1.30), 0.025, 0.012, segments=8, sections=3)
        on(paint(union("Helmet", [helmet, spike]), GRAY), rig, "head")
        return {"WHOLE_PARTS": True, "COVERS_FROM_ABOVE": []}
    settings = person(extra)
    rig = bpy.data.objects[settings["ARMATURE"]]
    tilt = ("turn", (1, 0, 0), -62.0)
    action = keys(rig, {0: [], 10: [("head", tilt)], 20: [("head", tilt)]})
    entry = run_clip(rig, action, "head back")
    culling_render("clip_spike_down_the_back", TARGETS=settings["TARGETS"], VIEWS=["left", "front", "back"], COLUMNS=3, FRAMES=[15])
    bpy.context.scene.frame_set(0)
    rig.animation_data.action = None
    rest_rig(rig)
    def after(r):
        print("  rest and test poses:", "PASS" if r["passed"] else r["issues"], "| clip:", entry["issues"] or "PASS")
        # The case's verdict: the clip's.
        r["issues"] = dict(entry["issues"])
        r["passed"] = not r["issues"]
    return dict(settings, _after=after)


if __name__ == "__main__":
    main()
    shutil.rmtree(PROOFS, ignore_errors=True)
else:
    shutil.rmtree(PROOFS, ignore_errors=True)
