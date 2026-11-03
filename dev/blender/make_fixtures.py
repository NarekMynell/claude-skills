# Writes dev/library-tests/Fixtures/Mannequin.fbx for the Unity tests in LibraryTests/AnimationClaims: the test
# mannequin (facing -Y, .L/.R bone names) with a root-motion walk at gait.SPEED (1 m/s along -Y), exported by
# game-assets/scripts/export_fbx.py with the guides' settings.
# Run: blender -b --factory-startup --python-exit-code 1 --python dev/blender/make_fixtures.py
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gait  # noqa: E402
import mannequin  # noqa: E402

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
scripts = os.path.join(root, "plugins", "unity-dev", "skills", "game-assets", "scripts")
output = os.path.join(root, "dev", "library-tests", "Fixtures", "Mannequin.fbx")


def load(name, **settings):
    path = os.path.join(scripts, name)
    namespace = {"__file__": path}
    namespace.update(settings)
    with open(path) as source:
        exec(compile(source.read(), path, "exec"), namespace)
    return namespace


mannequin.clear()
body, rig = mannequin.build()
mannequin.add_uvs(body)
helpers = types.SimpleNamespace(**load("rig.py"))
gait.key_walk(rig, rig_helpers=helpers)
result = load("export_fbx.py", TARGETS=["Body"], FILEPATH=output, ANIMATION=True)["result"]
if result["exported"] != output:
    raise SystemExit(f"not exported: {result['issues']}")
print("FIXTURE", output, os.path.getsize(output))
