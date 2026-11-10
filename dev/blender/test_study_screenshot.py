# Runs game-design's art-direction/scripts/study_screenshot.py on generated pictures with known structure.
# Run by dev/run-blender-tests.sh: blender -b --factory-startup --python-exit-code 1 --python <this> -- <study_screenshot.py> <output dir>
import json
import os
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
script_path, output_dir = args[0], args[1]
script = open(script_path).read()
problems = []


def run(**settings):
    namespace = {"__file__": script_path, "OUTPUT_DIR": output_dir}
    namespace.update(settings)
    exec(compile(script, script_path, "exec"), namespace)
    return namespace["result"]


def write(name, pixels):
    height, width = pixels.shape[:2]
    rgba = np.concatenate([pixels, np.ones((height, width, 1), dtype=np.float32)], axis=-1)
    image = bpy.data.images.new(name, width, height, alpha=False)
    image.colorspace_settings.name = "sRGB"
    image.pixels.foreach_set(np.flipud(rgba).astype(np.float32).ravel())
    path = os.path.join(output_dir, name + ".png")
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return path


def expect(condition, message):
    if not condition:
        problems.append(message)


size = (256, 256)
y, x = np.mgrid[0:size[0], 0:size[1]] / 255.0

# A flat, dated picture: one green, one sand, hard edge.
flat = np.zeros((*size, 3), dtype=np.float32)
flat[:] = (0.45, 0.75, 0.25)
flat[:, 128:] = (0.85, 0.75, 0.55)

# A rich one: gradients everywhere, dark cool shadows, warm lights, more than one hue.
rich = np.zeros((*size, 3), dtype=np.float32)
light = 0.15 + 0.8 * y
rich[..., 0] = light * (0.55 + 0.45 * y)
rich[..., 1] = light * (0.6 + 0.15 * np.sin(x * 9))
rich[..., 2] = light * (0.95 - 0.6 * y)

flat_path = write("flat", flat)
rich_path = write("rich", rich)

alone = run(IMAGE=flat_path, NAME="alone")
expect(list(alone["issues"]) == ["no_references"] and not alone["passed"], f"a picture with no references must stay unproven: {alone['issues']}")
expect(alone["image"]["flat_share"] > 0.9, f"flat picture measured {alone['image']['flat_share']}")
colors = [c for c, _ in alone["image"]["palette"]]
expect(len(colors) >= 2, f"palette {alone['image']['palette']}")
top = alone["image"]["palette"][0][0]
expect(top in ("#73bf40", "#d9bf8c"), f"the palette's main color is {top}: colors must come through as stored")
expect(os.path.exists(alone["sheet"]), "no sheet")

# The references: the same rich look, varied a little, as different screenshots of one style are.
rich_a = write("rich_a", np.clip(rich * 0.95, 0, 1))
rich_b = write("rich_b", np.clip(rich * 1.05, 0, 1))
references = [rich_path, rich_a, rich_b]

compared = run(IMAGE=flat_path, REFERENCES=references, NAME="compared", TILE=64)
for issue in ("narrow_values", "too_flat", "flat_shadows"):
    expect(issue in compared["issues"], f"{issue} not found: {compared['issues']}, {compared['image']}, {compared['references']}")
expect("few_references" in run(IMAGE=flat_path, REFERENCES=[rich_path], NAME="one_ref", TILE=32)["issues"], "one reference was accepted")
expect(compared["references"][0]["flat_share"] < 0.2, f"rich picture measured flat {compared['references'][0]['flat_share']}")
expect(compared["references"][0]["shadow_tint"] > 0.1, f"rich picture's shadows {compared['references'][0]['shadow_tint']}")

for note in ("no_dark_anchor", "washed_out", "one_note"):
    expect(note in compared["notes"], f"{note} not noted: {compared['notes']}")
rich_alone = run(IMAGE=rich_path, NAME="rich_alone", TILE=64)
for note in ("no_dark_anchor", "washed_out", "shadows_not_cooler"):
    expect(note not in rich_alone["notes"], f"rich picture noted: {rich_alone['notes']}")

# The same picture with its colors swapped: warm darks, cool lights.
upside_down = rich.copy()
upside_down[..., 0], upside_down[..., 2] = rich[..., 2].copy(), rich[..., 0].copy()
reversed_alone = run(IMAGE=write("reversed", upside_down), NAME="reversed_alone", TILE=64)
expect("shadows_not_cooler" in reversed_alone["notes"], f"warm shadows not noted: {reversed_alone['notes']}")

same = run(IMAGE=write("rich_c", np.clip(rich * 0.98, 0, 1)), REFERENCES=references, NAME="same", TILE=64)
expect(same["issues"] == {} and same["passed"], f"a picture that matches its references has gaps: {same['issues']}")
itself = run(IMAGE=rich_path, REFERENCES=references, NAME="itself", TILE=32)
expect("reference_is_the_image" in itself["issues"] and not itself["passed"], f"a picture passed as its own reference: {itself['issues']}")
receipt = run(IMAGE=rich_a, REFERENCES=[rich_path, rich_b, write("rich_d", np.clip(rich * 0.9, 0, 1))], NAME="receipt", TILE=32, PROOF_DIR=output_dir)
expect(os.path.exists(os.path.join(output_dir, "study-receipt.json")), "no receipt")

image = bpy.data.images.load(compared["sheet"], check_existing=False)
expect(image.size[1] == 4 * 64 + 3 * 4, f"sheet height {image.size[1]}")
bpy.data.images.remove(image)
left = [i.name for i in bpy.data.images if i.name not in ("Render Result", "Viewer Node")]
expect(not left, f"images left behind: {left}")

print("STUDY", json.dumps({"problems": problems}))
if problems:
    raise AssertionError("; ".join(problems))
