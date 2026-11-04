"""Studies a game screenshot the way an art director squints at it: the picture, its values in gray, a blurred version
that shows only the big shapes, and its real palette, with numbers. Next to references it says where the game falls
short of them. It reads structure and color, not taste: the written critique stays yours.

Runs in any Blender, through the connector or headless. Settings:
    IMAGE = "/abs/game.png"          required
    REFERENCES = ["/abs/ref.png"]    screenshots of the look to reach, at least 3, none of them the game itself
    OUTPUT_DIR = "/abs/path"         required; the study is written here
    NAME = "study"                   file name, without .png
    TILE = 384                       height of each picture
    PROOF_DIR = "/abs/docs/proofs"   writes the numbers to study-<NAME>.json there

Sets `result`: `passed`, `sheet` (path), `image` and `references` (each: `value_low`, `value_mid`, `value_high`,
`value_range`, `value_bands`, `saturation_mean`, `flat_share`, `shadow_tint`, `hue_families`, `palette`), `notes`, and
`issues`, gaps measured against the references:
    no_references      nothing to compare with: the picture is unproven, however it looks
    few_references     fewer than 3: one picture is a copy target, not a look
    reference_is_the_image  a reference is this very picture
    narrow_values      the value range is much narrower: the picture reads flat in gray
    too_flat           much more of it is perfectly even color: no gradient or surface
    dull, too_saturated  the average saturation is far from the references'
    flat_shadows       its shadows are less cool than the references' lights: shadows that are only darker
`notes` are questions that hold without references, not verdicts, since a style can answer them on purpose:
    no_dark_anchor     almost nothing is dark: it reads washed out, and the eye has nothing to rest on
    washed_out         nearly all of it sits in the top of the value range
    shadows_not_cooler its shadows are no cooler than its lights: shading by darkening alone looks flat
    one_note           one or two hue families carry the picture
Bright UI and screen edges count too, so crop to the same framing when comparing.
"""

import json
import os

import bpy
import numpy as np

MIN_REFERENCES = 3
STUDY_SIDE = 256
BLOCK = 8
PALETTE = 8
SEED = 7


def _setting(name, default=None):
    return globals().get(name, default)


def _load(path):
    image = bpy.data.images.load(path, check_existing=False)
    try:
        width, height = image.size
        if width == 0 or height == 0:
            raise ValueError(f"can't read {path}")
        pixels = np.empty(width * height * image.channels, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        # Byte images come through as stored, in display color: the values an eye reads.
        return np.flipud(pixels.reshape(height, width, image.channels))[..., :3]
    finally:
        bpy.data.images.remove(image)


def _resized(pixels, height):
    """Area averaging when shrinking, so fine detail averages out as it does in an eye."""
    source_height, source_width = pixels.shape[:2]
    width = max(1, round(source_width * height / source_height))
    rows = (np.arange(height + 1) * source_height // height).astype(int)
    columns = (np.arange(width + 1) * source_width // width).astype(int)
    integral = np.zeros((source_height + 1, source_width + 1, 3), dtype=np.float64)
    integral[1:, 1:] = pixels.cumsum(0).cumsum(1)
    r0, r1 = rows[:-1], np.maximum(rows[1:], rows[:-1] + 1)
    c0, c1 = columns[:-1], np.maximum(columns[1:], columns[:-1] + 1)
    total = (integral[r1][:, c1] - integral[r0][:, c1] - integral[r1][:, c0] + integral[r0][:, c0])
    area = ((r1 - r0)[:, None] * (c1 - c0)[None, :])[..., None]
    return (total / area).astype(np.float32)


def _luma(pixels):
    return pixels[..., 0] * 0.2126 + pixels[..., 1] * 0.7152 + pixels[..., 2] * 0.0722


def _blurred(pixels, radius):
    """Three box passes, close to a Gaussian."""
    result = pixels.astype(np.float64)
    for _ in range(3):
        for axis in (0, 1):
            padded = np.concatenate([np.repeat(np.take(result, [0], axis), radius + 1, axis), result,
                                     np.repeat(np.take(result, [-1], axis), radius, axis)], axis)
            summed = padded.cumsum(axis)
            size = result.shape[axis]
            upper = np.take(summed, np.arange(2 * radius + 1, size + 2 * radius + 1), axis)
            lower = np.take(summed, np.arange(0, size), axis)
            result = (upper - lower) / (2 * radius + 1)
    return result.astype(np.float32)


def _hsv(pixels):
    high = pixels.max(-1)
    low = pixels.min(-1)
    delta = high - low
    saturation = np.where(high > 1e-6, delta / np.maximum(high, 1e-6), 0.0)
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    hue = np.zeros_like(high)
    mask = delta > 1e-6
    hue = np.where(mask & (high == r), ((g - b) / np.maximum(delta, 1e-6)) % 6, hue)
    hue = np.where(mask & (high == g), (b - r) / np.maximum(delta, 1e-6) + 2, hue)
    hue = np.where(mask & (high == b), (r - g) / np.maximum(delta, 1e-6) + 4, hue)
    return hue / 6.0, saturation, high


def _palette(pixels):
    """The main colors and their shares, by k-means from a fixed seed, largest first."""
    samples = pixels.reshape(-1, 3)
    random = np.random.RandomState(SEED)
    if len(samples) > 6000:
        samples = samples[random.choice(len(samples), 6000, replace=False)]
    centers = samples[random.choice(len(samples), PALETTE, replace=False)].copy()
    for _ in range(12):
        distances = ((samples[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        nearest = distances.argmin(1)
        for k in range(PALETTE):
            members = samples[nearest == k]
            if len(members):
                centers[k] = members.mean(0)
    shares = np.bincount(nearest, minlength=PALETTE) / len(samples)
    order = np.argsort(-shares)
    return [("#%02x%02x%02x" % tuple(int(round(float(c) * 255)) for c in np.clip(centers[k], 0, 1)), round(float(shares[k]), 3))
            for k in order if shares[k] > 0.005]


def _measure(pixels):
    small = _resized(pixels, STUDY_SIDE)
    luma = _luma(small)
    low, mid, high = (float(np.percentile(luma, p)) for p in (5, 50, 95))
    bands = np.histogram(luma, bins=5, range=(0.0, 1.0))[0] / luma.size
    hue, saturation, _ = _hsv(small)

    rows, columns = small.shape[0] // BLOCK, small.shape[1] // BLOCK
    flat = 0
    for r in range(rows):
        for c in range(columns):
            block = small[r * BLOCK:(r + 1) * BLOCK, c * BLOCK:(c + 1) * BLOCK]
            flat += float(block.std(axis=(0, 1)).max()) < 0.006
    flat_share = flat / max(1, rows * columns)

    # Blue minus red in the darkest and the brightest parts: positive when the shadows are cooler than the lights.
    dark = small[luma <= np.percentile(luma, 15)]
    light = small[luma >= np.percentile(luma, 85)]
    shadow_tint = float((dark[:, 2] - dark[:, 0]).mean() - (light[:, 2] - light[:, 0]).mean()) if len(dark) and len(light) else 0.0

    colored = hue[saturation > 0.2]
    families = np.histogram(colored, bins=12, range=(0.0, 1.0))[0] / max(1, luma.size) if colored.size else np.zeros(12)
    return {
        "value_low": round(low, 3), "value_mid": round(mid, 3), "value_high": round(high, 3), "value_range": round(high - low, 3),
        "value_bands": [round(float(b), 3) for b in bands],
        "saturation_mean": round(float(saturation.mean()), 3),
        "flat_share": round(flat_share, 3),
        "shadow_tint": round(shadow_tint, 3),
        "hue_families": int((families > 0.05).sum()),
        "palette": _palette(small),
    }


def _row(pixels, palette, tile):
    picture = _resized(pixels, tile)
    gray = np.repeat(_luma(picture)[..., None], 3, -1)
    squint = _blurred(gray, max(1, tile // 40))
    swatch = np.zeros((tile, tile // 3, 3), dtype=np.float32)
    start = 0
    for index, (color, share) in enumerate(palette):
        end = tile if index == len(palette) - 1 else min(tile, start + int(round(share * tile)))
        swatch[start:end] = [int(color[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
        start = end
    gap = np.full((tile, 4, 3), 0.9, dtype=np.float32)
    return np.concatenate([picture, gap, gray, gap, squint, gap, swatch], axis=1)


def _compare(image, references):
    issues = {}
    if not references:
        issues["no_references"] = "nothing to compare with: collect references, or the user's word that this look is the one"
        return issues
    if len(references) < MIN_REFERENCES:
        issues["few_references"] = f"{len(references)} references, at least {MIN_REFERENCES}: one picture is a copy target, not a look"

    def mean(key):
        return sum(r[key] for r in references) / len(references)

    if image["value_range"] < 0.75 * mean("value_range"):
        issues["narrow_values"] = f"value range {image['value_range']}, references {mean('value_range'):.3f}: it reads flat in gray"
    if image["flat_share"] > mean("flat_share") + 0.2:
        issues["too_flat"] = f"{image['flat_share'] * 100:.0f}% of it is perfectly even color, references {mean('flat_share') * 100:.0f}%"
    if image["saturation_mean"] < mean("saturation_mean") - 0.15:
        issues["dull"] = f"saturation {image['saturation_mean']}, references {mean('saturation_mean'):.3f}"
    if image["saturation_mean"] > mean("saturation_mean") + 0.15:
        issues["too_saturated"] = f"saturation {image['saturation_mean']}, references {mean('saturation_mean'):.3f}"
    if image["shadow_tint"] < mean("shadow_tint") - 0.05:
        issues["flat_shadows"] = f"shadow tint {image['shadow_tint']}, references {mean('shadow_tint'):.3f}: its shadows are only darker, not cooler"
    return issues


def _notes(image):
    notes = {}
    if image["value_low"] > 0.45:
        notes["no_dark_anchor"] = f"the darkest 5% of the picture is still at value {image['value_low']}: where are its darks?"
    if sum(image["value_bands"][3:]) > 0.85:
        notes["washed_out"] = f"{sum(image['value_bands'][3:]) * 100:.0f}% of the picture is in the top two of five value bands"
    if image["shadow_tint"] <= 0.0:
        notes["shadows_not_cooler"] = f"shadow tint {image['shadow_tint']}: are the shadows only darker versions of the lights?"
    if image["hue_families"] <= 2:
        notes["one_note"] = f"{image['hue_families']} hue families cover more than 5% of it each"
    return notes


def study():
    path = _setting("IMAGE")
    output_dir = _setting("OUTPUT_DIR")
    if not path or not output_dir:
        raise ValueError("IMAGE and OUTPUT_DIR are required")
    os.makedirs(output_dir, exist_ok=True)
    tile = int(_setting("TILE", 384))
    pictures = [_load(path)] + [_load(p) for p in _setting("REFERENCES", [])]
    measures = [_measure(p) for p in pictures]
    rows = [_row(p, m["palette"], tile) for p, m in zip(pictures, measures)]
    width = max(r.shape[1] for r in rows)
    height = len(rows) * tile + (len(rows) - 1) * 4
    sheet = np.full((height, width, 3), 0.9, dtype=np.float32)
    for index, row in enumerate(rows):
        y = index * (tile + 4)
        sheet[y:y + tile, :row.shape[1]] = row
    rgba = np.concatenate([sheet, np.ones((height, width, 1), dtype=np.float32)], axis=-1)
    image = bpy.data.images.new("ScreenshotStudy", width, height, alpha=False)
    output = os.path.join(output_dir, _setting("NAME", "study") + ".png")
    try:
        image.colorspace_settings.name = "sRGB"
        image.pixels.foreach_set(np.flipud(rgba).ravel())
        image.filepath_raw = output
        image.file_format = "PNG"
        image.save()
    finally:
        bpy.data.images.remove(image)
    issues = _compare(measures[0], measures[1:])
    if any(p.shape == pictures[0].shape and np.array_equal(p, pictures[0]) for p in pictures[1:]):
        issues["reference_is_the_image"] = "a reference is this very picture: it compares with itself"
    report = {"passed": not issues, "sheet": output, "image": measures[0], "references": measures[1:], "issues": issues, "notes": _notes(measures[0])}
    folder = _setting("PROOF_DIR")
    if folder:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"study-{_setting('NAME', 'study')}.json"), "w") as out:
            json.dump(report, out, indent=1)
    return report


result = study()
