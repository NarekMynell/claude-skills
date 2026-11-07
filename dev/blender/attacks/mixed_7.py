# Seventh round: one skin versions, hair cards, modifiers, NLA, undersides, cost.
import os, shutil, sys, tempfile, time
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
from defects_1 import raise_z, move, plane, open_lathe, fits_hat, penguin_rig, penguin
from defects_2 import wide_hips
from clean_1 import union
from clean_2 import ring_on, jointed_arm_person
from clean_3 import subdivided_mannequin
CASES.clear()


def hair_cards_mesh(name="Cards", z0=1.74, z1=1.84):
    mesh = bpy.data.meshes.new(name)
    verts, faces = [], []
    for k in range(6):
        angle = k * math.pi / 6
        dx, dy = 0.12 * math.cos(angle), 0.12 * math.sin(angle)
        base = len(verts)
        verts += [(-dx, -dy, z0), (dx, dy, z0), (dx, dy, z1), (-dx, -dy, z1)]
        faces.append((base, base + 1, base + 2, base + 3))
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


@case("hair_cards_the_guides_way", "pass", "hair cards listed in SEE_THROUGH and nothing else, as the guide says, in the repo's own geometry: the repo's case also turns COVERS_FROM_ABOVE off")
def _():
    def extra(rig, parts):
        on(paint(hair_cards_mesh(), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "SEE_THROUGH": ["Cards"], "_render": {"VIEWS": ["front", "top"]}}
    return person(extra)


def one_skin_with_trousers():
    body, rig = subdivided_mannequin(3)
    mannequin.clean_weights(body, rig)
    paint(body, SKIN)
    tr = body.copy()
    tr.data = body.data.copy()
    tr.name = "Trousers"
    bpy.context.scene.collection.objects.link(tr)
    bm = bmesh.new()
    bm.from_mesh(tr.data)
    keep = lambda c: 0.16 < c.z < 0.92 and c.x > 0.0 and abs(c.x) < 0.3
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f.calc_center_median())], context="FACES")
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.012
    bm.to_mesh(tr.data)
    bm.free()
    paint(tr, BLUE)
    return body, tr, rig


@case("one_skin_trousers_clean_control", "pass", "one skin, one trouser leg 12 mm above it, weighted like the body")
def _():
    body, tr, rig = one_skin_with_trousers()
    return {"TARGETS": ["Body", "Trousers"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "POSES": False, "ALLOW_HIDDEN": ["Body<Trousers"], "TWO_SIDED": ["Trousers"], "SYMMETRIC": ["Body"]}


@case("one_skin_local_knee_poke_control", "fail", "the knee comes through the trouser front, in one place (control: must fail)")
def _():
    body, tr, rig = one_skin_with_trousers()
    knee = Vector((0.10, -0.05, 0.50))
    bump(body, knee, 0.06, (0.0, -0.05, 0.0))
    return {"TARGETS": ["Body", "Trousers"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "POSES": False, "ALLOW_HIDDEN": ["Body<Trousers"], "TWO_SIDED": ["Trousers"], "SYMMETRIC": ["Torso"], "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("one_skin_knee_ring_through_trousers", "fail", "the knee is wider than the trousers all the way around: a band of skin between two lengths of trouser, on one skin")
def _():
    body, tr, rig = one_skin_with_trousers()
    knee = Vector((0.10, 0.0, 0.50))
    for v in body.data.vertices:
        if abs(v.co.z - 0.50) < 0.04 and v.co.x > 0.02:
            d = Vector((v.co.x - knee.x, v.co.y - knee.y, 0))
            if d.length > 1e-4:
                v.co.x, v.co.y = knee.x + d.x * 2.0, knee.y + d.y * 2.0
    return {"TARGETS": ["Body", "Trousers"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "POSES": False, "ALLOW_HIDDEN": ["Body<Trousers"], "TWO_SIDED": ["Trousers"], "SYMMETRIC": ["Torso"], "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("one_skin_hem_poke", "fail", "the shin comes out through the trouser front from the hem up, joined to the bare ankle, on one skin")
def _():
    body, tr, rig = one_skin_with_trousers()
    for v in body.data.vertices:
        if 0.12 < v.co.z < 0.40 and v.co.x > 0.02 and v.co.y < -0.005:
            v.co.y -= 0.05 * min(1.0, (0.40 - v.co.z) / 0.04, (v.co.z - 0.12) / 0.04)
    return {"TARGETS": ["Body", "Trousers"], "ARMATURE": rig.name, "SINGLE_LAYER": False, "POSES": False, "ALLOW_HIDDEN": ["Body<Trousers"], "TWO_SIDED": ["Trousers"], "SYMMETRIC": ["Torso"], "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("nla_control", "fail", "hands through wide hips in a pose (control: must fail)")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True}
    return person(extra)


@case("nla_track_on_the_rig", "fail", "the same, on a rig whose clips are in NLA tracks, as game rigs are kept: does a pose survive?")
def _():
    def extra(rig, parts):
        wide_hips(rig, parts)
        rig.animation_data_create()
        action = bpy.data.actions.new("Idle")
        rig.animation_data.action = action
        for frame in (0, 20):
            for pb in rig.pose.bones:
                pb.rotation_mode = "QUATERNION"
                pb.keyframe_insert("rotation_quaternion", frame=frame)
        track = rig.animation_data.nla_tracks.new()
        track.strips.new("Idle", 0, action)
        rig.animation_data.action = None
        bpy.context.view_layer.update()
        return {"WHOLE_PARTS": True, "LEGS_JOINED": True}
    return person(extra)


@case("underside_hole_bird_default_view", "pass", "a penguin with a hole in its underside, seen by the default LOWEST_VIEW: not from under the horizon (documented setting)")
def _():
    rig = penguin_rig()
    penguin(rig)
    body = bpy.data.objects["Body"]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    doomed = [f for f in bm.faces if f.calc_center_median().z < 0.13 and abs(f.calc_center_median().x) > 0.05]
    bmesh.ops.delete(bm, geom=doomed[:2], context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True}


@case("underside_hole_bird_from_below", "fail", "the same with LOWEST_VIEW = -90")
def _():
    rig = penguin_rig()
    penguin(rig)
    body = bpy.data.objects["Body"]
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    doomed = [f for f in bm.faces if f.calc_center_median().z < 0.13 and abs(f.calc_center_median().x) > 0.05]
    bmesh.ops.delete(bm, geom=doomed[:2], context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "LOWEST_VIEW": -90}


@case("modifier_mirror_limbs", "pass", "the clean person whose right limbs come from Mirror modifiers on the left ones")
def _():
    def extra(rig, parts):
        for side_name in ("Arm", "Leg", "Foot"):
            bpy.data.objects.remove(parts[f"{side_name}.R"], do_unlink=True)
            o = parts[f"{side_name}.L"]
            arm_mod = o.modifiers[0]
            m = o.modifiers.new("Mirror", "MIRROR")
            m.use_axis[0] = True
            m.use_mirror_vertex_groups = True
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_move_to_index(modifier="Mirror", index=0)
            names = [g.name for g in o.vertex_groups]
            for n in names:
                o.vertex_groups.new(name=n.replace(".L", ".R"))
            o.data.update()  # the modifier reads the new groups on its next evaluation
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("modifier_subsurf_on_parts", "pass", "the clean person with a Subsurf modifier on its parts, before the Armature")
def _():
    settings = person()
    for name in settings["TARGETS"]:
        o = bpy.data.objects[name]
        m = o.modifiers.new("S", "SUBSURF")
        m.levels = 1
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_move_to_index(modifier="S", index=0)
    settings["WHOLE_PARTS"] = True
    return settings


@case("cost_two_dense_shells_crossing", "fail", "cost: a dense body and a dense layer crossing each other everywhere: how long does the check take?")
def _():
    body, rig = subdivided_mannequin(4)
    mannequin.clean_weights(body, rig)
    print("  faces", len(body.data.polygons))
    tr = body.copy()
    tr.data = body.data.copy()
    tr.name = "Layer"
    bpy.context.scene.collection.objects.link(tr)
    for v in tr.data.vertices:
        v.co += v.normal * (0.004 * math.sin(v.co.z * 40.0) * math.sin(v.co.x * 40.0))
    t0 = time.time()
    def after(report):
        print(f"  check ran in {time.time() - t0:.0f} s")
    return {"TARGETS": ["Body", "Layer"], "ARMATURE": rig.name, "WHOLE_PARTS": True, "_after": after}


if __name__ == "__main__":
    main()
