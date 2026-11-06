# Clean characters that should pass. First batch: hair, hats, statues, off-center, bodies with no legs to see.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
import defects_1 as fn1
from defects_1 import raise_z, move, plane, open_lathe, fits_hat, penguin_rig, penguin
CASES.clear()


def union(name, objs):
    """A boolean union of closed objects into one: one surface, no inner faces."""
    base = objs[0]
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = base
    base.select_set(True)
    for other in objs[1:]:
        m = base.modifiers.new("U", "BOOLEAN")
        m.operation = "UNION"
        m.object = other
        m.solver = "EXACT"
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(other, do_unlink=True)
    base.name = name
    return base


def hair_shell(name="Hair", r=0.112, front=1.70, side=1.62, back=1.50, segments=24, thick=False):
    """A one-sided hair mesh 7 mm above a Head capsule: its hairline is high at the forehead, low at the nape, like any hair mesh."""
    rings = [(r, None), (r, 1.68), (r * 0.94, 1.72), (r * 0.78, 1.765), (r * 0.42, 1.79), (0.0, 1.797)]
    bm = bmesh.new()
    loops = []
    for radius, z in rings:
        if radius <= 0:
            loops.append(bm.verts.new((0, 0, z)))
            continue
        loop = []
        for s in range(segments):
            angle = 2 * math.pi * s / segments
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            if z is None:
                # front is -Y, back is +Y
                t = (math.sin(angle) + 1.0) / 2.0  # 0 front, 1 back
                zz = front + (back - front) * t if t > 0.5 else front + (side - front) * (t / 0.5)
                zz = (front + (side - front) * (t / 0.5)) if t <= 0.5 else (side + (back - side) * ((t - 0.5) / 0.5))
            else:
                zz = z
            loop.append(bm.verts.new((x, y, zz)))
        loops.append(loop)
    for a, b in zip(loops, loops[1:]):
        for s in range(segments):
            if isinstance(b, list):
                bm.faces.new((a[s], a[(s + 1) % segments], b[(s + 1) % segments], b[s]))
            else:
                bm.faces.new((a[s], a[(s + 1) % segments], b))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


@case("hair_shell_hairline_high_in_front", "pass", "a one-sided hair mesh, 7 mm above the scalp: low at the nape, high at the forehead. Its forehead edge reads as a hole in what covers the head")
def _():
    def extra(rig, parts):
        h = paint(hair_shell(), DARK)
        # Keep the outward normals outward.
        on(h, rig, "head", "neck")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "back", "left", "front_left", "top"]}}
    return person(extra)


def hood_shell(name="Hood", r=0.128, segments=32):
    """A hood draped to the shoulders, with a face opening."""
    bm = bmesh.new()
    rows = [(1.42, 0.17), (1.48, 0.15), (1.54, 0.135), (1.60, r), (1.66, r), (1.72, r * 0.95), (1.77, r * 0.8), (1.80, r * 0.5)]
    loops = []
    for z, radius in rows:
        loops.append([bm.verts.new((radius * math.cos(2 * math.pi * s / segments), radius * math.sin(2 * math.pi * s / segments), z)) for s in range(segments)])
    top = bm.verts.new((0, 0, 1.81))
    for a, b in zip(loops, loops[1:]):
        for s in range(segments):
            bm.faces.new((a[s], a[(s + 1) % segments], b[(s + 1) % segments], b[s]))
    for s in range(segments):
        bm.faces.new((loops[-1][s], loops[-1][(s + 1) % segments], top))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # The face opening: faces in front (y < 0, |x| small) between chin and brow.
    bm.faces.ensure_lookup_table()
    doomed = [f for f in bm.faces if f.calc_center_median().y < 0 and abs(f.calc_center_median().x) < 0.085 and 1.54 < f.calc_center_median().z < 1.72]
    bmesh.ops.delete(bm, geom=doomed, context="FACES_ONLY")
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


@case("hood_with_face_opening_two_sided", "pass", "a two-sided hood with a face opening, draped to the shoulders: the opening reads as a hole above the rim")
def _():
    def extra(rig, parts):
        on(paint(hood_shell(), GREEN), rig, "head", "neck", "chest")
        return {"WHOLE_PARTS": True, "TWO_SIDED": ["Hood"], "_render": {"VIEWS": ["front", "back", "left", "front_left", "top"]}}
    return person(extra)


def helmet_with_horns():
    dome = lathe("Dome", [(0.0, 1.66), (0.125, 1.66), (0.125, 1.75), (0.09, 1.82), (0.0, 1.84)], segments=20)
    hl = capsule("HornL", (0.08, 0, 1.74), (0.30, 0, 1.90), 0.035, 0.008, segments=8)
    hr = capsule("HornR", (-0.08, 0, 1.74), (-0.30, 0, 1.90), 0.035, 0.008, segments=8)
    return union("Helmet", [dome, hl, hr])


@case("viking_helmet_with_horns_one_surface", "pass", "a viking helmet with its horns in one closed surface: inside the outline but under no surface of the helmet, a look down meets the shoulders")
def _():
    def extra(rig, parts):
        on(paint(helmet_with_horns(), GRAY), rig, "head")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


def hair_with_tail():
    cap = lathe("Cap", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=20)
    tail = capsule("Tail", (0, 0.08, 1.74), (0, 0.17, 1.60), 0.04, 0.03, segments=10)
    tail2 = capsule("Tail2", (0, 0.17, 1.60), (0, 0.15, 1.32), 0.03, 0.012, segments=10)
    return union("Hair", [cap, tail, tail2])


@case("hair_with_ponytail_one_surface", "pass", "a hair cap with a ponytail in one closed surface, hanging down the back, clear of it")
def _():
    def extra(rig, parts):
        on(paint(hair_with_tail(), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["back", "left", "back_left", "top"], "COLUMNS": 2}}
    return person(extra)


def hair_with_pigtails():
    cap = lathe("Cap", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=20)
    objs = [cap]
    for s in (1, -1):
        objs.append(capsule(f"T{s}", (0.09 * s, 0, 1.72), (0.20 * s, 0, 1.62), 0.04, 0.03, segments=10))
        objs.append(capsule(f"U{s}", (0.20 * s, 0, 1.62), (0.27 * s, 0, 1.46), 0.03, 0.012, segments=10))
    return union("Hair", objs)


@case("hair_with_pigtails_one_surface", "pass", "a hair cap with two pigtails in one closed surface, hanging over the shoulders in the air")
def _():
    def extra(rig, parts):
        on(paint(hair_with_pigtails(), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


@case("hair_bun_on_hair_cap", "pass", "a bun, a separate object, set into a hair cap")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=20), DARK), rig, "head")
        on(paint(capsule("HairBun", (0, 0.03, 1.80), (0, 0.03, 1.84), 0.04, 0.04, segments=12), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


@case("hair_fringe_on_hair_cap", "pass", "a fringe, a separate object, lying on the front of a hair cap")
def _():
    def extra(rig, parts):
        on(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=20), DARK), rig, "head")
        f = capsule("HairFringe", (-0.06, -0.09, 1.76), (0.06, -0.09, 1.76), 0.035, 0.035, segments=10)
        on(paint(f, DARK), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


def hair_chunks(rig):
    """Low-poly hair built of overlapping chunks, in one object: the way low-poly hair is usually made."""
    objs = []
    for k in range(7):
        a = 2 * math.pi * k / 7
        x, y = 0.06 * math.cos(a), 0.06 * math.sin(a)
        objs.append(capsule(f"Chunk{k}", (x * 0.5, y * 0.5, 1.76), (x * 1.5, y * 1.5, 1.68), 0.055, 0.03, segments=8))
    objs.append(capsule("Chunk7", (0, 0, 1.74), (0, 0, 1.76), 0.07, 0.07, segments=10))
    return objs


@case("hair_chunks_one_object", "pass", "low-poly hair of overlapping chunks, one object with many islands")
def _():
    def extra(rig, parts):
        objs = hair_chunks(rig)
        for o in objs:
            on(paint(o, DARK), rig, "head")
        keep = {o.name for o in parts.values()}
        h = partsbody.merge(objs, "Hair")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


@case("top_hat_of_two_parts_crown_through_brim", "pass", "a top hat of two closed parts: a brim disc, and a crown that goes through it, its base 1 cm under the brim, as cylinders are placed")
def _():
    def extra(rig, parts):
        on(paint(lathe("Brim", [(0.0, 1.705), (0.2, 1.705), (0.2, 1.715), (0.0, 1.72)], segments=24), DARK), rig, "head")
        on(paint(lathe("Crown", [(0.0, 1.695), (0.125, 1.695), (0.125, 1.88), (0.0, 1.88)], segments=20), DARK), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left", "front_left", "top"], "COLUMNS": 2}}
    return person(extra)


@case("top_hat_merged_one_object", "pass", "the same hat, its two parts in one object")
def _():
    def extra(rig, parts):
        a = on(paint(lathe("Brim", [(0.0, 1.705), (0.2, 1.705), (0.2, 1.715), (0.0, 1.72)], segments=24), DARK), rig, "head")
        b = on(paint(lathe("Crown", [(0.0, 1.695), (0.125, 1.695), (0.125, 1.88), (0.0, 1.88)], segments=20), DARK), rig, "head")
        partsbody.merge([a, b], "Hat")
        return {"WHOLE_PARTS": True}
    return person(extra)


@case("hat_band_on_hat", "pass", "a hat with a decorative band set into its crown, a separate object")
def _():
    def extra(rig, parts):
        on(paint(fits_hat(), DARK), rig, "head")
        on(paint(ring("Band", 0.133, 0.115, 1.72, 1.75, center=(0, 0, 0), segments=16), RED), rig, "head")
        return {"WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "front_left"]}}
    return person(extra)


def statue_parts(head=True):
    names = []
    for name, args, kwargs in (("Torso", ((0, 0, 0.92), (0, 0, 1.36), 0.16, 0.17), {"segments": 12, "squash_y": 0.68}),
                               ("Neck", ((0, 0, 1.42), (0, 0, 1.54), 0.05, 0.05), {"segments": 8, "rings": 2}),
                               ("Head", ((0, 0, 1.62), (0, 0, 1.68), 0.105, 0.105), {"segments": 12}),
                               ("Leg.L", ((0.09, 0, 0.90), (0.09, 0, 0.05), 0.07, 0.05), {"segments": 8}),
                               ("Leg.R", ((-0.09, 0, 0.90), (-0.09, 0, 0.05), 0.07, 0.05), {"segments": 8})):
        names.append(paint(capsule(name, *args, **kwargs), GRAY).name)
    return names


@case("statue_with_hair_cap", "pass", "a statue of parts with a hair cap: the check takes the torso for the head, the head for what covers it, and the hair for what shows through")
def _():
    names = statue_parts()
    names.append(paint(lathe("Hair", [(0.0, 1.66), (0.098, 1.66), (0.115, 1.70), (0.1, 1.78), (0.0, 1.81)], segments=20), DARK).name)
    return {"TARGETS": names, "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


@case("statue_with_hat", "pass", "a statue of parts with a hat")
def _():
    names = statue_parts()
    names.append(paint(fits_hat(), DARK).name)
    return {"TARGETS": names, "WHOLE_PARTS": True}


@case("statue_on_a_plinth", "pass", "a statue of parts on a plinth: the feet are one surface at the ground")
def _():
    names = statue_parts()
    for n in names:
        raise_z(bpy.data.objects[n], 0.1)
    names.append(paint(lathe("Plinth", [(0.0, 0.0), (0.3, 0.0), (0.3, 0.12), (0.0, 0.12)], segments=24), BROWN).name)
    return {"TARGETS": names, "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


@case("statue_chess_pawn_no_legs", "pass", "a statue with no legs, a chess pawn: no rig, one surface at the ground")
def _():
    o = lathe("Pawn", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.05), (0.08, 0.1), (0.05, 0.3), (0.09, 0.33), (0.05, 0.36), (0.09, 0.45), (0.0, 0.5)], segments=24)
    paint(o, GRAY)
    return {"TARGETS": ["Pawn"], "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


@case("statue_bust_no_rig", "pass", "a bust on a base: no rig")
def _():
    names = []
    names.append(paint(lathe("Base", [(0.0, 0.0), (0.12, 0.0), (0.12, 0.08), (0.0, 0.08)], segments=20), BROWN).name)
    names.append(paint(capsule("Chest", (0, 0, 0.18), (0, 0, 0.3), 0.14, 0.14, segments=12, squash_y=0.7), GRAY).name)
    names.append(paint(capsule("Neck", (0, 0, 0.40), (0, 0, 0.5), 0.05, 0.05, segments=8, rings=2), GRAY).name)
    names.append(paint(capsule("Head", (0, 0, 0.55), (0, 0, 0.62), 0.1, 0.1, segments=12), GRAY).name)
    return {"TARGETS": names, "WHOLE_PARTS": True}


@case("statue_fish_no_rig", "pass", "a fish statue: no rig, resting on the ground")
def _():
    body = capsule("Fish", (0, -0.2, 0.15), (0, 0.2, 0.15), 0.15, 0.04, segments=12)
    for v in body.data.vertices:
        v.co.x *= 0.4
    paint(body, BLUE)
    return {"TARGETS": ["Fish"], "WHOLE_PARTS": True, "_render": {"VIEWS": ["front", "left"]}}


@case("statue_cow_no_rig", "pass", "a cow statue of parts: no rig, four legs")
def _():
    names = []
    names.append(paint(capsule("Trunk", (0, 0.3, 0.6), (0, -0.3, 0.6), 0.2, 0.2, segments=12), BROWN).name)
    names.append(paint(capsule("HeadP", (0, -0.5, 0.8), (0, -0.65, 0.75), 0.1, 0.08, segments=10), BROWN).name)
    names.append(paint(capsule("NeckP", (0, -0.3, 0.65), (0, -0.5, 0.8), 0.1, 0.08, segments=10), BROWN).name)
    for s, x in (("L", 1), ("R", -1)):
        for e, y in (("F", -0.3), ("H", 0.3)):
            names.append(paint(capsule(f"Leg{e}{s}", (0.11 * x, y, 0.5), (0.11 * x, y, 0.05), 0.06, 0.05, segments=8), BROWN).name)
    return {"TARGETS": names, "WHOLE_PARTS": True}


@case("shield_on_left_arm", "pass", "a person holding a round shield beyond the left hand: the bounding box is off center")
def _():
    def extra(rig, parts):
        h = rig.data.bones["hand.L"].tail_local
        s = capsule("Shield", h + Vector((0.0, -0.06, 0.0)), h + Vector((0.0, -0.08, 0.0)), 0.28, 0.28, segments=16, rings=1)
        for v in s.data.vertices:
            v.co.x += 0.15
        on(paint(s, RED), rig, "hand.L")
        return {"WHOLE_PARTS": True, "POSES": False, "_render": {"VIEWS": ["front", "front_left"]}}
    return person(extra)


@case("sword_in_right_hand", "pass", "a person with a long sword held out in the right hand")
def _():
    def extra(rig, parts):
        h = rig.data.bones["hand.R"].tail_local
        on(paint(capsule("Sword", h + Vector((0.03, 0, 0)), h + Vector((-0.9, 0, -0.1)), 0.015, 0.005, segments=6), GRAY), rig, "hand.R")
        return {"WHOLE_PARTS": True, "POSES": False}
    return person(extra)


def snake_rig(count=10, length=2.0, wave=0.0, radius=0.04):
    bones = []
    for k in range(count):
        y0, y1 = -length / 2 + length * k / count, -length / 2 + length * (k + 1) / count
        x0, x1 = wave * math.sin(y0 * 4.0), wave * math.sin(y1 * 4.0)
        bones.append((f"spine{k:02d}", (x0, y0, radius), (x1, y1, radius), f"spine{k - 1:02d}" if k else None))
    return make_rig("SnakeRig", bones)


def snake_skin(rig, count=10, length=2.0, wave=0.0, radius=0.04, segments=10, rings_per=3):
    """One closed tube along the bones, weighted to the nearest bone."""
    bm = bmesh.new()
    loops = []
    n = count * rings_per
    for i in range(n + 1):
        t = i / n
        y = -length / 2 + length * t
        x = wave * math.sin(y * 4.0)
        r = radius * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.5) if t < 1.0 else radius * 0.3
        loops.append([bm.verts.new((x + r * math.cos(2 * math.pi * s / segments), y, radius + r * math.sin(2 * math.pi * s / segments))) for s in range(segments)])
    for a, b in zip(loops, loops[1:]):
        for s in range(segments):
            bm.faces.new((a[s], a[(s + 1) % segments], b[(s + 1) % segments], b[s]))
    bm.faces.new(loops[0])
    bm.faces.new(list(reversed(loops[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Snake")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Snake", mesh)
    bpy.context.scene.collection.objects.link(obj)
    # Lift to the ground: its lowest point at 0.
    low = min(v.co.z for v in mesh.vertices)
    for v in mesh.vertices:
        v.co.z -= low
    on(paint(obj, GREEN), rig, *[b.name for b in rig.data.bones])
    return obj


@case("snake_straight", "pass", "a straight snake, one skin")
def _():
    rig = snake_rig()
    snake_skin(rig)
    return {"TARGETS": ["Snake"], "ARMATURE": rig.name, "_render": {"VIEWS": ["left", "top"]}}


@case("snake_s_curve", "pass", "a snake modeled in an S curve: the sides of its center line read as left and right bones")
def _():
    rig = snake_rig(wave=0.15)
    snake_skin(rig, wave=0.15)
    return {"TARGETS": ["Snake"], "ARMATURE": rig.name, "_render": {"VIEWS": ["top", "left"]}}


@case("snake_s_curve_lopsided", "pass", "a snake in an S curve whose bounding box isn't centered")
def _():
    rig = snake_rig(wave=0.25, length=1.3)
    snake_skin(rig, wave=0.25, length=1.3)
    return {"TARGETS": ["Snake"], "ARMATURE": rig.name, "_render": {"VIEWS": ["top", "left"]}}


def fish_rig(z=0.0):
    return make_rig("FishRig", [
        ("root", (0, -0.1, z), (0, 0.05, z), None), ("mid", (0, 0.05, z), (0, 0.2, z), "root"), ("tail", (0, 0.2, z), (0, 0.33, z), "mid"), ("fin", (0, 0.33, z), (0, 0.45, z), "tail"),
        ("head", (0, -0.1, z), (0, -0.3, z), "root"),
        ("pectoral.L", (0.07, -0.12, z - 0.02), (0.17, -0.06, z - 0.06), "root"), ("pectoral.R", (-0.07, -0.12, z - 0.02), (-0.17, -0.06, z - 0.06), "root"),
        ("dorsal", (0, 0.0, z + 0.1), (0, 0.1, z + 0.2), "root"),
    ])


def fish(rig, z=0.0, lowest_on_ground=False):
    body = capsule("FBody", (0, -0.25, z), (0, 0.2, z), 0.13, 0.04, segments=12, sections=4)
    for v in body.data.vertices:
        v.co.x *= 0.45
    on(paint(body, BLUE), rig, "head", "root", "mid", "tail")
    tailfin = capsule("TailFin", (0, 0.22, z), (0, 0.42, z), 0.03, 0.09, segments=8)
    for v in tailfin.data.vertices:
        v.co.x *= 0.15
    on(paint(tailfin, YELLOW), rig, "tail", "fin")
    dorsal = capsule("Dorsal", (0, 0.0, z + 0.09), (0, 0.1, z + 0.2), 0.05, 0.02, segments=8)
    for v in dorsal.data.vertices:
        v.co.x *= 0.15
    on(paint(dorsal, YELLOW), rig, "dorsal")
    for s, x in (("L", 1), ("R", -1)):
        p = capsule(f"Pectoral.{s}", (0.05 * x, -0.12, z - 0.02), (0.17 * x, -0.06, z - 0.07), 0.035, 0.02, segments=8)
        for v in p.data.vertices:
            v.co.y = -0.09 + (v.co.y + 0.09) * 1.0
        on(paint(p, YELLOW), rig, f"pectoral.{s}")


@case("fish_centered_on_its_origin", "pass", "a swimming fish with its pivot at its center, as swimming things are placed: there is no ground, and no setting says so")
def _():
    rig = fish_rig()
    fish(rig)
    return {"TARGETS": meshes(), "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front", "top"]}}


@case("fish_on_the_ground_control", "pass", "the same fish lifted so its lowest point is at z = 0")
def _():
    rig = fish_rig(0.2)
    fish(rig, 0.2)
    low = min(v.co.z for o in bpy.context.scene.objects if o.type == "MESH" for v in o.data.vertices)
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            for v in o.data.vertices:
                v.co.z -= low
    rig.location.z -= low
    for o in bpy.context.scene.objects:
        if o.type == "MESH":
            o.location.z += low
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    return {"TARGETS": [o.name for o in bpy.context.scene.objects if o.type == "MESH"], "ARMATURE": rig.name, "WHOLE_PARTS": True, "_render": {"VIEWS": ["left", "front", "top"]}}


if __name__ == "__main__":
    main()
