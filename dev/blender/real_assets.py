# Runs the checks over the models and clips Unity ships in its built-in packages: professional work, with no defect planted. A check
# that fails most of it is crying wolf, whatever its own scenes say. Prints one line per model: path, check, what it reports.
# Run by dev/run-real-assets.sh. Nothing of Unity's is copied: the models are read where they are, by whoever has that Unity.
import glob
import os
import sys
import time

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
repo, packages = args[0], args[1]
scripts = os.path.join(repo, "plugins/unity-dev/skills/game-assets/scripts")


def compiled(name):
    path = os.path.join(scripts, name)
    with open(path) as source:
        return path, compile(source.read(), path, "exec")


MESH = compiled("validate_mesh.py")
CHARACTER = compiled("inspect_character.py")
ANIMATION = compiled("inspect_animation.py")


def run(script, **settings):
    namespace = {"__file__": script[0]}
    namespace.update(settings)
    exec(script[1], namespace)
    return namespace["result"]


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)


def say(relative, check, issues):
    print(f"REAL\t{relative}\t{check}\t{' '.join(sorted(issues))}", flush=True)


files = sorted(set(glob.glob(f"{packages}/**/*.fbx", recursive=True) + glob.glob(f"{packages}/**/*.FBX", recursive=True)))
started = time.time()
for path in files:
    relative = path[len(packages) + 1:]
    try:
        load(path)
    except RuntimeError:
        continue  # Blender reads binary FBX only.
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        continue
    if not any(o.type == "ARMATURE" for o in bpy.context.scene.objects):
        # What a pipeline does on import: the file's unit scale and axes go into the mesh.
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.make_single_user(object=True, obdata=True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    report = run(MESH, TARGETS=[o.name for o in meshes])
    say(relative, "mesh", {issue for entry in report["objects"] for issue in entry["issues"]})

for relative in ("com.unity.timeline/Samples~/GameplaySequenceDemo/Character/Models/DefaultMale.fbx",
                 "com.unity.timeline/Samples~/Customization/Demo/Animation/Staff_vs_Staff_OneFight_MaleA.fbx",
                 "com.unity.render-pipelines.core/Samples~/RendererShaderUserValue_Common/Models/Soldier.fbx",
                 "com.unity.visualeffectgraph/Samples~/Common/Meshes/Chomper.fbx"):
    load(f"{packages}/{relative}")
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    report = run(CHARACTER, ARMATURE=rig.name, TARGETS=[o.name for o in bpy.context.scene.objects if o.type == "MESH"])
    say(relative, "character", report["issues"])

male = f"{packages}/com.unity.timeline/Samples~/GameplaySequenceDemo/Character/Models/DefaultMale.fbx"
for clip in sorted(glob.glob(f"{packages}/com.unity.timeline/Samples~/GameplaySequenceDemo/Animation/*.fbx")):
    load(male)
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    known = set(bpy.data.actions)
    objects = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=clip)
    action = max((a for a in bpy.data.actions if a not in known), key=lambda a: sum(len(bag.fcurves) for layer in a.layers for strip in layer.strips for bag in strip.channelbags))
    for obj in set(bpy.context.scene.objects) - objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.scene.render.fps = 30
    report = run(ANIMATION, ARMATURE=rig.name, ACTIONS=[action.name], LOOP=False, STEP=2)
    say(clip[len(packages) + 1:], "clip", report["actions"][action.name]["issues"])
print(f"REAL seconds {time.time() - started:.0f}", flush=True)
