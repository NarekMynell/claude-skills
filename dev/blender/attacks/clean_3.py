# Clean characters, third batch: open shells, unions, dense meshes, welds, scale, modifiers, proportions, whole outfits.
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
import defects_2 as fn2
import clean_1 as fp1
import clean_2 as fp2
import cuts_1 as cuts
from defects_1 import raise_z, move, plane, open_lathe, fits_hat
from clean_1 import union, hair_shell, hood_shell
from clean_2 import ring_on, blob_rig
from cuts_1 import culling_render, keys, run_clip
CASES.clear()
PROOFS = tempfile.mkdtemp(prefix="proofs", dir=HERE)


def smooth_head(rig, parts, r=0.105, segments=32):
    bpy.data.objects.remove(parts["Head"], do_unlink=True)
    return on(paint(capsule("Head", (0, 0, 1.62), (0, 0, 1.68), r, r, segments=segments, rings=10, sections=4), SKIN), rig, "head")


@case("hair_shell_high_rim_all_around", "pass", "one-sided hair, 4 mm over a smooth head, whose hairline stays above the head bone's base: low at the nape 1.66, high at the forehead 1.72")
def _():
    def extra(rig, parts):
        smooth_head(rig, parts)
        h = paint(hair_shell(r=0.109, front=1.72, side=1.69, back=1.66, segments=32), DARK)
        on(h, rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "back", "left", "front_left", "top"]}}
    return person(extra)


@case("hair_shell_nape_length_two_sided", "pass", "the same hair to the nape, 1.50, drawn two-sided: it holds the head bone's base, its head-bone faces are less than the head's, and it's taken for the skull")
def _():
    def extra(rig, parts):
        smooth_head(rig, parts)
        h = paint(hair_shell(r=0.109, front=1.72, side=1.62, back=1.50, segments=32), DARK)
        on(h, rig, "head")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Hair"], "_render": {"VIEWS": ["front", "back", "left", "front_left", "top"]}}
    return person(extra)


@case("hood_head_bone_only", "pass", "a two-sided hood with a face opening, weighted to the head alone, so its faces outweigh the head's")
def _():
    def extra(rig, parts):
        on(paint(hood_shell(), GREEN), rig, "head")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Hood"], "POSES": False, "_render": {"VIEWS": ["front", "back", "left", "front_left", "top"]}}
    return person(extra)


@case("helmet_open_face_closed_mesh", "pass", "a closed-mesh open-face helmet with thickness (no open edges): control for what an opening does")
def _():
    def extra(rig, parts):
        outer = lathe("HelmetOuter", [(0.0, 1.60), (0.13, 1.60), (0.13, 1.74), (0.10, 1.82), (0.0, 1.85)], segments=24)
        cutter = capsule("Cut", (0, -0.2, 1.64), (0, -0.05, 1.64), 0.085, 0.085, segments=16)
        m = outer.modifiers.new("D", "BOOLEAN")
        m.operation = "DIFFERENCE"; m.object = cutter; m.solver = "EXACT"
        bpy.context.view_layer.objects.active = outer
        bpy.ops.object.modifier_apply(modifier="D")
        bpy.data.objects.remove(cutter, do_unlink=True)
        outer.name = "Helmet"
        on(paint(outer, GRAY), rig, "head")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


# --- A boolean union, dense meshes, welds ----------------------------------------------------------------------------------

def union_person():
    rig = partsbody.person_rig()
    parts = list(partsbody.person(rig, sections=4))
    # A union of all parts with no weights: then the rig's automatic weights.
    for o in parts:
        o.vertex_groups.clear()
        o.modifiers.clear()
    body = union("Body", parts)
    body.parent = None
    paint(body, SKIN)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    mannequin.clean_weights(body, rig)
    return body, rig


@case("boolean_union_of_parts_auto_weights", "pass", "the body of parts as one boolean union, automatic weights: no inner faces, one surface")
def _():
    body, rig = union_person()
    print("  faces", len(body.data.polygons), "shortest edge", min((body.data.vertices[e.vertices[0]].co - body.data.vertices[e.vertices[1]].co).length for e in body.data.edges))
    def after(report):
        ex = report.get("examples", {}).get("stretched_in_poses")
        print("  stretched examples:", ex)
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "_after": after, "_render": {"VIEWS": ["front", "left"]}}


def subdivided_mannequin(level):
    body, rig = mannequin.build()
    m = body.modifiers.new("S", "SUBSURF")
    m.levels = level
    m.render_levels = level
    bpy.context.view_layer.objects.active = body
    arm = next(mo for mo in body.modifiers if mo.type == "ARMATURE")
    bpy.ops.object.modifier_move_to_index(modifier="S", index=0)
    bpy.ops.object.modifier_apply(modifier="S")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    return body, rig


@case("dense_mannequin_level2", "pass", "the clean mannequin subdivided twice, weights carried along: thousands of small edges")
def _():
    body, rig = subdivided_mannequin(2)
    print("  faces", len(body.data.polygons))
    def after(report):
        print("  stretched examples:", report.get("examples", {}).get("stretched_in_poses"))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "FINGERS": 5, "_after": after}


@case("dense_mannequin_level3", "pass", "the clean mannequin subdivided three times")
def _():
    body, rig = subdivided_mannequin(3)
    print("  faces", len(body.data.polygons))
    def after(report):
        print("  stretched examples:", report.get("examples", {}).get("stretched_in_poses"))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "FINGERS": 5, "_after": after}


def nick(body, x_range, z_range, sign):
    """Pushes one arm-underside vertex into the torso by 2 mm: a nick nobody can see, as creases have."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    tree = helpers.BVHTree.FromBMesh(bm)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    best = None
    for v in bm.verts:
        if x_range[0] < abs(v.co.x) < x_range[1] and z_range[0] < v.co.z < z_range[1] and v.co.x * sign > 0:
            d = Vector((-sign, 0, -0.35)).normalized()
            hit = tree.ray_cast(v.co + d * 1e-4, d, 0.2)
            if hit[0] is not None and hit[3] > 1e-3 and hit[1].dot(d) < 0:
                faces = bm.faces[hit[2]]
                if v not in faces.verts and (best is None or hit[3] < best[1]):
                    best = (v.index, hit[3], d.copy())
    index, dist, d = best
    body.data.vertices[index].co += d * (dist + 0.002)
    bm.free()
    return index, dist


@case("one_nick_at_one_armpit", "pass", "a one-skin body with a 2 mm nick at one armpit: nothing to see, under the graze")
def _():
    body, rig = subdivided_mannequin(1)
    print("  nick:", nick(body, (0.1, 0.3), (1.2, 1.45), 1))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False}


@case("two_nicks_one_at_each_armpit", "pass", "the same with a 2 mm nick at each armpit: each is as small as before, and together their extent is half a metre")
def _():
    body, rig = subdivided_mannequin(1)
    print("  nicks:", nick(body, (0.1, 0.3), (1.2, 1.45), 1), nick(body, (0.1, 0.3), (1.2, 1.45), -1))
    return {"TARGETS": ["Body"], "ARMATURE": rig.name, "POSES": False}


@case("merged_with_one_weld", "pass", "a merged body of parts where a single vertex of the arm was welded to the torso (merge by distance, a stitched seam): one island, so the joint's crossing is the surface cutting into itself")
def _():
    settings = person(merged=True)
    obj = bpy.data.objects["Merged"]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    islands = helpers._islands(bm)
    bm.faces.ensure_lookup_table()
    arm = max((set(v.index for f in i for v in bm.faces[f].verts) for i in islands), key=lambda s: max(bm.verts[k].co.x for k in s))
    torso = next(set(v.index for f in i for v in bm.faces[f].verts) for i in islands if any(abs(bm.verts[k].co.z - 1.2) < 0.2 and abs(bm.verts[k].co.x) < 0.01 for k in set(v.index for f in i for v in bm.faces[f].verts)))
    pair = min(((a, t) for a in arm for t in torso), key=lambda p: (bm.verts[p[0]].co - bm.verts[p[1]].co).length)
    print("  welding", pair, (bm.verts[pair[0]].co - bm.verts[pair[1]].co).length)
    bmesh.ops.pointmerge(bm, verts=[bm.verts[pair[0]], bm.verts[pair[1]]], merge_co=bm.verts[pair[1]].co)
    bm.to_mesh(obj.data)
    bm.free()
    settings["WHOLE_PARTS"] = True
    return settings


# --- Scale and tessellation: what can't change a verdict ---------------------------------------------------------------------

def scale_all(factor):
    objs = [o for o in bpy.context.scene.objects]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    rig = next(o for o in objs if o.type == "ARMATURE")
    bpy.context.view_layer.objects.active = rig
    for o in objs:
        if o.type == "MESH":
            o.parent = None
    rig.scale = (factor, factor, factor)
    for o in objs:
        if o.type == "MESH":
            o.scale = (factor, factor, factor)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


for factor in (0.03, 0.1, 0.5, 3.0, 10.0, 100.0):
    def make(factor=factor):
        def build():
            settings = person()
            scale_all(factor)
            settings["WHOLE_PARTS"] = True
            return settings
        return build
    case(f"scale_clean_person_x{factor}", "pass", f"the clean person, scaled {factor} times and applied")(make())
    def make_dog(factor=factor):
        def build():
            settings = animal()
            scale_all(factor)
            settings["WHOLE_PARTS"] = True
            return settings
        return build
    case(f"scale_clean_animal_x{factor}", "pass", f"the clean animal, scaled {factor} times and applied")(make_dog())


def retess(kind):
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        if kind == "tri":
            m = o.modifiers.new("T", "TRIANGULATE")
        else:
            m = o.modifiers.new("T", "SUBSURF")
            m.levels = 1
            m.subdivision_type = "SIMPLE"
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_move_to_index(modifier="T", index=0)
        bpy.ops.object.modifier_apply(modifier="T")


@case("tess_clean_person_triangulated", "pass", "the clean person, triangulated")
def _():
    settings = person()
    retess("tri")
    settings["WHOLE_PARTS"] = True
    return settings


@case("tess_clean_person_subdivided_simple", "pass", "the clean person, subdivided without smoothing (the same shape)")
def _():
    settings = person()
    retess("simple")
    settings["WHOLE_PARTS"] = True
    return settings


@case("tess_clean_person_merged_triangulated", "pass", "the clean person, merged and triangulated")
def _():
    settings = person(merged=True)
    retess("tri")
    settings["WHOLE_PARTS"] = True
    return settings


# --- Modifiers, transforms, odd objects --------------------------------------------------------------------------------------

@case("mirror_by_negative_scale_child", "pass", "the right ear a mirrored copy of the left, by a negative scale on a child of the rig: how hand-built low-poly parts are often mirrored")
def _():
    def extra(rig, parts):
        left = on(paint(capsule("Ear.L", (0.09, 0, 1.64), (0.15, 0, 1.68), 0.025, 0.018, segments=6, rings=2), SKIN), rig, "head")
        right = bpy.data.objects.new("Ear.R", left.data)
        bpy.context.scene.collection.objects.link(right)
        right.parent = rig
        right.scale.x = -1
        right.vertex_groups.new(name="head").add(list(range(len(right.data.vertices))), 1.0, "REPLACE")
        right.modifiers.new("Armature", "ARMATURE").object = rig
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("mesh_with_loose_edges_only", "pass", "a helper mesh of loose edges (no faces) among the targets: must not stop the check")
def _():
    def extra(rig, parts):
        mesh = bpy.data.meshes.new("Guide")
        mesh.from_pydata([(0, 0.3, 1.0), (0, 0.3, 1.3)], [(0, 1)], [])
        obj = bpy.data.objects.new("Guide", mesh)
        bpy.context.scene.collection.objects.link(obj)
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("loose_vertex_far_away", "fail", "a stray vertex 3 m up in the head's mesh: height doubles and with it every threshold; the real poke under it passes")
def _():
    def extra(rig, parts):
        mesh = parts["Head"].data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        deform = bm.verts.layers.deform.active
        v = bm.verts.new((0, 0, 4.0))
        v[deform][0] = 1.0
        bm.to_mesh(mesh)
        bm.free()
        on(paint(lathe("Cap", [(0.0, 1.66), (0.125, 1.66), (0.12, 1.70), (0.095, 1.74), (0.0, 1.76)], segments=16), BROWN), rig, "head")
        return {"WHOLE_PARTS": True, "COVERS_FROM_ABOVE": []}
    return person(extra)


# --- Proportions: test poses that fit one body ---------------------------------------------------------------------------------

def humanoid_rig(h=1.0, head_r=0.25, chest_w=0.2, arm=0.35, leg=0.35, name="Rig"):
    """A plain rig with the Humanoid's bones, for a figure of any proportions. Heights in metres."""
    hip_z = leg
    chest_z = hip_z + 0.22
    neck_z = chest_z + 0.08
    head_z = neck_z + 0.02
    s = chest_w
    bones = [("hips", (0, 0, hip_z), (0, 0, hip_z + 0.11), None), ("spine", (0, 0, hip_z + 0.11), (0, 0, chest_z), "hips"), ("neck", (0, 0, chest_z), (0, 0, head_z), "spine"), ("head", (0, 0, head_z), (0, 0, head_z + 2 * head_r), "neck")]
    a = math.radians(35)
    dx, dz = math.cos(a), -math.sin(a)
    for side, x in (("L", 1), ("R", -1)):
        p0 = (x * s, 0, chest_z)
        p1 = (x * (s + dx * arm * 0.5), 0, chest_z + dz * arm * 0.5)
        p2 = (x * (s + dx * arm), 0, chest_z + dz * arm)
        p3 = (x * (s + dx * arm * 1.2), 0, chest_z + dz * arm * 1.2)
        bones += [(f"upper_arm.{side}", p0, p1, "spine"), (f"forearm.{side}", p1, p2, f"upper_arm.{side}"), (f"hand.{side}", p2, p3, f"forearm.{side}")]
        hx = 0.45 * s
        bones += [(f"thigh.{side}", (x * hx, 0, hip_z), (x * hx, 0, hip_z * 0.5), "hips"), (f"shin.{side}", (x * hx, 0, hip_z * 0.5), (x * hx, 0, 0.05), f"thigh.{side}"), (f"foot.{side}", (x * hx, 0, 0.05), (x * hx, -0.12, 0.03), f"shin.{side}")]
    return make_rig(name, bones), dict(hip_z=hip_z, chest_z=chest_z, neck_z=neck_z, head_z=head_z, s=s, dx=dx, dz=dz, arm=arm, hx=0.45 * s)


def figure(rig, g, head_r, torso_r, arm_r=0.04, leg_r=0.05, color=SKIN):
    on(paint(capsule("Torso", (0, 0, g["hip_z"] + 0.05), (0, 0, g["chest_z"] + 0.02), torso_r, torso_r * 0.9, segments=12, squash_y=0.75), color), rig, "hips", "spine")
    on(paint(capsule("Head", (0, 0, g["head_z"] + head_r - 0.01), (0, 0, g["head_z"] + head_r), head_r, head_r, segments=16), color), rig, "head")
    for side, x in (("L", 1), ("R", -1)):
        p0 = Vector((x * g["s"], 0, g["chest_z"]))
        p3 = Vector((x * (g["s"] + g["dx"] * g["arm"] * 1.2), 0, g["chest_z"] + g["dz"] * g["arm"] * 1.2))
        on(paint(capsule(f"Arm.{side}", p0, p3, arm_r, arm_r * 0.8, segments=8, sections=6), color), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        on(paint(capsule(f"Leg.{side}", (x * g["hx"], 0, g["hip_z"] + 0.02), (x * g["hx"], 0, 0.05), leg_r, leg_r * 0.8, segments=8, sections=6), color), rig, f"thigh.{side}", f"shin.{side}")
        on(paint(capsule(f"Foot.{side}", (x * g["hx"], 0, 0.035), (x * g["hx"], -0.12, 0.035), 0.035, 0.035, segments=8), color), rig, f"foot.{side}")


@case("chibi_big_head", "pass", "a chibi, 2.5 heads tall: a head as wide as the shoulders, short arms. arms_up raises them into the head, as it would any chibi")
def _():
    head_r = 0.21
    rig, g = humanoid_rig(head_r=head_r, chest_w=0.16, arm=0.30, leg=0.28)
    figure(rig, g, head_r, 0.15, arm_r=0.035)
    def after(report):
        apply_named_pose(rig, "arms_up")
        render("chibi_arms_up", VIEWS=["front", "left"], COLUMNS=2)
        rest_rig(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "FINGERS": 0, "_after": after, "_render": {"VIEWS": ["front", "left", "front_left"]}}


@case("ogre_wide_belly", "pass", "an ogre: a wide belly, thick arms, held out in an A-pose. arms_down puts any arms this short through a belly this wide")
def _():
    head_r = 0.13
    rig, g = humanoid_rig(head_r=head_r, chest_w=0.34, arm=0.55, leg=0.5)
    on(paint(capsule("Torso", (0, 0, g["hip_z"] + 0.14), (0, 0, g["chest_z"] + 0.03), 0.34, 0.28, segments=16, squash_y=0.85, sections=2), GREEN), rig, "hips", "spine")
    on(paint(capsule("Head", (0, 0, g["head_z"] + head_r - 0.02), (0, 0, g["head_z"] + head_r), head_r, head_r, segments=16), GREEN), rig, "head")
    for side, x in (("L", 1), ("R", -1)):
        p0 = Vector((x * g["s"] * 0.8, 0, g["chest_z"]))
        p3 = Vector((x * (g["s"] + g["dx"] * g["arm"] * 1.2), 0, g["chest_z"] + g["dz"] * g["arm"] * 1.2))
        on(paint(capsule(f"Arm.{side}", p0, p3, 0.09, 0.07, segments=10, sections=6), GREEN), rig, f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}")
        on(paint(capsule(f"Leg.{side}", (x * g["hx"], 0, g["hip_z"] + 0.05), (x * g["hx"], 0, 0.05), 0.09, 0.07, segments=10, sections=6), GREEN), rig, f"thigh.{side}", f"shin.{side}")
        on(paint(capsule(f"Foot.{side}", (x * g["hx"], 0, 0.05), (x * g["hx"], -0.14, 0.05), 0.05, 0.05, segments=8), GREEN), rig, f"foot.{side}")
    def after(report):
        apply_named_pose(rig, "arms_down")
        render("ogre_arms_down", VIEWS=["front", "left"], COLUMNS=2)
        rest_rig(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "FINGERS": 0, "WAIST_BULGE": True, "_after": after, "_render": {"VIEWS": ["front", "left", "front_left"]}}


# --- A dressed-up character --------------------------------------------------------------------------------------------------

def hero(rig, parts):
    b = rig.data.bones
    # Trousers and boots.
    for side, x in (("L", 1), ("R", -1)):
        hip, ankle = b[f"thigh.{side}"].head_local, b[f"shin.{side}"].tail_local
        end = hip.lerp(ankle, 0.8)
        on(paint(capsule(f"Trouser.{side}", hip + Vector((0, 0, 0.03)), end, 0.095, 0.07, segments=10, sections=6), BLUE), rig, f"thigh.{side}", f"shin.{side}")
        boot = capsule(f"Boot.{side}", (ankle.x, ankle.y, 0.27), (ankle.x, ankle.y, 0.09), 0.075, 0.065, segments=10, sections=2)
        on(paint(boot, BROWN), rig, f"shin.{side}")
    # Tunic and belt.
    tunic = capsule("Tunic", (0, 0, 0.95), (0, 0, 1.37), 0.178, 0.185, segments=12, squash_y=0.72, sections=3)
    on(paint(tunic, GREEN), rig, "hips", "spine", "chest")
    on(paint(ring("Belt", 0.19, 0.12, 1.03, 1.07, squash_y=0.72, segments=16), BROWN), rig, "hips", "spine")
    # A pouch on the belt.
    on(paint(capsule("Pouch", (0.16, -0.06, 1.0), (0.16, -0.06, 1.03), 0.04, 0.04, segments=8), BROWN), rig, "hips")
    # Sleeves, cuffs, shoulder pads.
    for side, x in (("L", 1), ("R", -1)):
        s, e, w = b[f"upper_arm.{side}"].head_local, b[f"forearm.{side}"].head_local, b[f"forearm.{side}"].tail_local
        on(paint(capsule(f"Sleeve.{side}", s, s.lerp(w, 0.7), 0.072, 0.055, segments=10, sections=5), GREEN), rig, f"upper_arm.{side}", f"forearm.{side}")
        pad = capsule(f"Pad.{side}", s + Vector((0.01 * x, 0, 0.02)), s + Vector((0.05 * x, 0, 0.01)), 0.075, 0.07, segments=10)
        on(paint(pad, GRAY), rig, f"upper_arm.{side}")
        axis = (w - e).normalized()
        on(paint(ring_on(f"Cuff.{side}", s.lerp(w, 0.85), axis, 0.052, 0.028, 0.03, segments=10), BROWN), rig, f"forearm.{side}")
    # Hair and a cap.
    on(paint(lathe("Hair", [(0.0, 1.62), (0.09, 1.62), (0.113, 1.67), (0.112, 1.72), (0.09, 1.78), (0.0, 1.805)], segments=16), DARK), rig, "head")
    on(paint(capsule("Nose", (0, -0.09, 1.63), (0, -0.125, 1.62), 0.022, 0.018, segments=6, rings=2), SKIN), rig, "head")
    for side, x in (("L", 1), ("R", -1)):
        on(paint(capsule(f"Eye.{side}", (0.04 * x, -0.092, 1.66), (0.04 * x, -0.0925, 1.66), 0.014, 0.014, segments=8), DARK), rig, "head")
    # A sheathed sword at the left hip, a quiver on the back.
    on(paint(capsule("Scabbard", (0.20, 0.04, 1.02), (0.25, 0.14, 0.45), 0.018, 0.012, segments=6, sections=3), DARK), rig, "hips")
    on(paint(capsule("Quiver", (-0.08, 0.145, 1.42), (0.08, 0.145, 1.02), 0.045, 0.04, segments=8), BROWN), rig, "chest")


@case("rpg_hero_whole_parts", "pass", "a low-poly RPG hero of parts: trousers, boots, tunic, belt and pouch, sleeves, cuffs, shoulder pads, hair, sword and quiver. Each set into what it sits on")
def _():
    def extra(rig, parts):
        hero(rig, parts)
        return {"WHOLE_PARTS": True, "SYMMETRIC": ["Torso"], "_render": {"VIEWS": ["front", "back", "left", "front_left"], "COLUMNS": 2, "COLOR": "MATERIAL"}}
    return person(extra, sections=4)


if __name__ == "__main__":
    main()
    shutil.rmtree(PROOFS, ignore_errors=True)
else:
    shutil.rmtree(PROOFS, ignore_errors=True)
