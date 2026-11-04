using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using ProjectName.Core.Proofs;
using ProjectName.Core.UI;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace ProjectName.Core.Editor.UiChecks
{
    // Finds what makes a UGUI screen look unmade: capsules, stretched sprites, squashed corners, a different radius on
    // every panel, too many fonts and text sizes, text leaving its box, tiny touch targets, placeholder art. It looks at
    // the laid-out screen, so run it on the real thing, in Play Mode for UI built at runtime. It can't judge beauty.
    public static class UiAudit
    {
        private const int CoverageSamples = 48;

        private static readonly string[] DefaultSprites = { "UISprite", "Background", "InputFieldBackground", "Knob", "Checkmark", "DropdownArrow", "UIMask" };
        private static readonly string[] DefaultFonts = { "LiberationSans", "Liberation Sans", "LegacyRuntime", "Arial" };
        private static readonly string[] PlaceholderTexts = { "New Text", "Button", "Text", "Lorem", "TODO", "Placeholder" };
        private static readonly Regex ScientificNumber = new Regex(@"\d[eE][+-]?\d");

        [MenuItem("Tools/Audit UI")]
        private static void AuditOpenCanvases() => Debug.Log(AuditAllCanvases());

        // For the Unity CLI: the report of every root canvas in the loaded scenes, against the project's UiAuditSettings.
        // receiptName: the screen and aspect ratio, such as "shop-20x9", written to docs/proofs/ui-<name>.txt.
        // noPanelOpen: this is the HUD alone, so its coverage limit applies.
        public static string AuditAllCanvases(string receiptName = null, bool noPanelOpen = false)
        {
            var options = UiAuditSettings.LoadOptions(noPanelOpen);
            var canvases = UnityEngine.Object.FindObjectsByType<Canvas>().Where(c => c.isRootCanvas).ToList();
            var clean = canvases.Count > 0;
            var text = new System.Text.StringBuilder();
            text.Append("Screen ").Append(Screen.width).Append(" x ").Append(Screen.height).Append(", ").Append(noPanelOpen ? "HUD alone" : "with panels").AppendLine();
            if (canvases.Count == 0) text.AppendLine("No canvas is loaded: nothing was audited.");
            foreach (var canvas in canvases)
            {
                var report = Run((RectTransform)canvas.transform, options);
                clean &= report.IsClean;
                text.Append("Canvas ").AppendLine(canvas.name).AppendLine(report.ToString());
            }

            if (receiptName != null) ProofReceipt.Write("ui-" + receiptName, clean, text.ToString());
            return text.ToString();
        }

        public static UiAuditReport Run(RectTransform root, UiAuditOptions options)
        {
            if (options == null) throw new ArgumentNullException(nameof(options));
            if (root == null) throw new ArgumentNullException(nameof(root));
            Canvas.ForceUpdateCanvases();
            var findings = new List<UiFinding>();
            var canvas = root.GetComponentInParent<Canvas>();
            var canvasRect = canvas != null ? (RectTransform)canvas.rootCanvas.transform : root;
            var bounds = WorldRect(canvasRect);
            var shortSide = Mathf.Min(canvasRect.rect.width, canvasRect.rect.height);
            CheckCanvas(canvas, findings);
            if (options.RequireTokens && options.AllowedCornerSizes.Length == 0)
                findings.Add(new UiFinding("no-ui-tokens", Path(root), "no radius scale to check against: create a UiAuditSettings asset from docs/ui-design.md"));

            var cornerSizes = CheckImages(root, shortSide, options, findings);
            CheckOwnShapes(root, options, cornerSizes, findings);
            var fonts = new SortedSet<string>();
            var fontSizes = new SortedSet<float>();
            CheckTexts(root, shortSide, options, fonts, fontSizes, findings);
            CheckScales(root, findings);
            CheckSelectables(root, shortSide, options, findings);
            CheckRaycasts(root, findings);
            CheckRawImages(root, options, findings);
            CheckPlacement(root, bounds, findings);
            CheckAlignment(root, options, findings);

            if (cornerSizes.Count > options.MaxCornerSizes)
                findings.Add(new UiFinding("corner-spread", Path(root), $"{cornerSizes.Count} different corner sizes ({string.Join(", ", cornerSizes.Select(s => s.ToString("0")))}), limit {options.MaxCornerSizes}: use one radius scale"));
            if (fonts.Count > options.MaxFonts)
                findings.Add(new UiFinding("font-spread", Path(root), $"{fonts.Count} fonts ({string.Join(", ", fonts)}), limit {options.MaxFonts}"));
            if (fontSizes.Count > options.MaxFontSizes)
                findings.Add(new UiFinding("font-size-spread", Path(root), $"{fontSizes.Count} text sizes ({string.Join(", ", fontSizes.Select(s => s.ToString("0.#")))}), limit {options.MaxFontSizes}: use one type scale"));

            var coverage = Coverage(root, bounds);
            if (coverage > options.MaxCoverage)
                findings.Add(new UiFinding("covers-too-much", Path(root), $"covers {coverage * 100f:0}% of the screen, limit {options.MaxCoverage * 100f:0}%"));
            var open = new List<UiFinding>();
            var accepted = new List<UiFinding>();
            foreach (var finding in findings)
            {
                var exception = options.Exceptions.FirstOrDefault(e => e.Key.Rule == finding.Rule && finding.Path.EndsWith(e.Key.Path, StringComparison.Ordinal));
                if (exception.Value == null) open.Add(finding);
                else accepted.Add(new UiFinding(finding.Rule, finding.Path, $"{finding.Detail} [accepted: {exception.Value}]"));
            }

            if (options.Exceptions.Count > options.MaxExceptions)
                open.Add(new UiFinding("too-many-exceptions", Path(root), $"{options.Exceptions.Count} exceptions, limit {options.MaxExceptions}: the system isn't being followed"));
            return new UiAuditReport(open, accepted, cornerSizes.ToList(), fonts.ToList(), fontSizes.ToList(), coverage);
        }

        // Graphics no sprite describes: they report their own corners through IUiShape, or nothing can check them.
        private static void CheckOwnShapes(RectTransform root, UiAuditOptions options, SortedSet<float> sizes, List<UiFinding> findings)
        {
            foreach (var graphic in Visible<Graphic>(root))
            {
                var isKnownKind = graphic is TMP_Text || graphic is TMP_SubMeshUI || graphic is Text || graphic is RawImage;
                var image = graphic as Image;
                var isPlainImage = image != null && image.material == image.defaultMaterial;
                if (isKnownKind || isPlainImage) continue;
                var shape = graphic.GetComponent<IUiShape>();
                if (shape == null)
                {
                    findings.Add(new UiFinding("unmeasured-shape", Path(graphic.transform), $"{graphic.GetType().Name} draws a shape this audit can't measure: implement IUiShape on it"));
                    continue;
                }

                var rect = graphic.rectTransform.rect;
                sizes.Add(Mathf.Round(shape.CornerRadius / 2f) * 2f);
                CheckScale(graphic.transform, shape.CornerRadius, options, findings);
                CheckCapsule(graphic.transform, rect, Mathf.Min(shape.CornerRadius, Mathf.Min(rect.width, rect.height) / 2f), options, findings);
            }
        }

        private static void CheckScale(Transform element, float size, UiAuditOptions options, List<UiFinding> findings)
        {
            if (options.AllowedCornerSizes.Length == 0) return;
            if (!options.AllowedCornerSizes.Any(allowed => Mathf.Abs(allowed - size) <= 1.5f))
                findings.Add(new UiFinding("off-scale-corner", Path(element), $"corner size {size:0} isn't on the radius scale ({string.Join(", ", options.AllowedCornerSizes)})"));
        }

        private static void CheckCanvas(Canvas canvas, List<UiFinding> findings)
        {
            if (canvas == null || canvas.renderMode == RenderMode.WorldSpace) return;
            var scaler = canvas.rootCanvas.GetComponent<CanvasScaler>();
            if (scaler == null || scaler.uiScaleMode != CanvasScaler.ScaleMode.ScaleWithScreenSize)
                findings.Add(new UiFinding("no-screen-scaling", Path(canvas.rootCanvas.transform), "the canvas needs a Canvas Scaler set to Scale With Screen Size"));
        }

        private static SortedSet<float> CheckImages(RectTransform root, float shortSide, UiAuditOptions options, List<UiFinding> findings)
        {
            var sizes = new SortedSet<float>();
            var corners = new SpriteCorners();
            foreach (var image in Visible<Image>(root))
            {
                var rect = image.rectTransform.rect;
                var sprite = image.sprite;
                if (sprite == null)
                {
                    if (image.material != image.defaultMaterial) continue; // CheckOwnShapes: an SDF drawn by its material.
                    var area = rect.width * rect.height;
                    var isOverlay = image.color.a < 0.95f && rect.width >= shortSide * 0.95f;
                    if (area > shortSide * shortSide * 0.02f && !isOverlay)
                        findings.Add(new UiFinding("plain-rectangle", Path(image.transform), "a flat rectangle with no sprite: the look of a placeholder panel"));
                    continue;
                }

                if (IsDefaultSprite(sprite))
                    findings.Add(new UiFinding("default-sprite", Path(image.transform), $"Unity's default sprite {sprite.name}"));

                // Canvas units per sprite pixel, the way Image.GenerateSlicedSprite works it out.
                var unitsPerPixel = 1f / (image.pixelsPerUnit * image.pixelsPerUnitMultiplier);
                if (image.material != image.defaultMaterial) continue; // CheckOwnShapes: a material can draw anything.
                var sliced = image.type == Image.Type.Sliced && sprite.border.sqrMagnitude > 0f;
                if (sliced) CheckSliced(image, sprite, rect, unitsPerPixel, corners, options, sizes, findings);
                else if (image.type != Image.Type.Tiled) CheckUnsliced(image, sprite, rect, corners, options, findings);
            }

            return sizes;
        }

        private static void CheckSliced(Image image, Sprite sprite, Rect rect, float unitsPerPixel, SpriteCorners corners, UiAuditOptions options, SortedSet<float> sizes, List<UiFinding> findings)
        {
            var border = sprite.border * unitsPerPixel;
            if (border.x + border.z > rect.width + 0.5f || border.y + border.w > rect.height + 0.5f)
                findings.Add(new UiFinding("squashed-corners", Path(image.transform), $"the sprite's corners need {border.x + border.z:0} x {border.y + border.w:0} units and the element is {rect.width:0} x {rect.height:0}: Unity squeezes them"));

            var radius = corners.RadiusPixels(sprite);
            var size = radius >= 0f ? radius * unitsPerPixel : Mathf.Max(border.x, border.y);
            // To the nearest 2 units: measuring pixels can't tell closer sizes apart, and neither can an eye.
            if (size >= 1f)
            {
                sizes.Add(Mathf.Round(size / 2f) * 2f);
                CheckScale(image.transform, size, options, findings);
            }

            CheckCapsule(image.transform, rect, Mathf.Min(size, Mathf.Min(rect.width, rect.height) / 2f), options, findings);
        }

        private static void CheckUnsliced(Image image, Sprite sprite, Rect rect, SpriteCorners corners, UiAuditOptions options, List<UiFinding> findings)
        {
            var size = sprite.rect.size;
            if (size.x <= 4f && size.y <= 4f || rect.width <= 0f || rect.height <= 0f) return;
            if (!image.preserveAspect)
            {
                var stretch = rect.width / rect.height / (size.x / size.y);
                if (Mathf.Abs(stretch - 1f) > options.StretchTolerance)
                    findings.Add(new UiFinding("stretched-sprite", Path(image.transform), $"sprite {sprite.name} is {size.x:0} x {size.y:0} and is drawn {rect.width:0} x {rect.height:0}: slice it, or keep its aspect"));
            }

            var radius = corners.RadiusPixels(sprite);
            if (radius <= 0f) return;
            var drawn = radius * Mathf.Min(rect.width / size.x, rect.height / size.y);
            CheckCapsule(image.transform, rect, drawn, options, findings);
            // A sprite with children is a container, whatever its image type: its corners are on the radius scale.
            if (!image.preserveAspect && image.transform.childCount > 0) CheckScale(image.transform, drawn, options, findings);
        }

        // A capsule is a container whose ends are half circles. The usual tell of generated UI, and ugly when stretched.
        private static void CheckCapsule(Transform element, Rect rect, float corner, UiAuditOptions options, List<UiFinding> findings)
        {
            var shortest = Mathf.Min(rect.width, rect.height);
            var longest = Mathf.Max(rect.width, rect.height);
            if (shortest <= 0f || longest < shortest * options.CapsuleLength) return;
            // A toggle or a slider is the one honest capsule: small, of one fixed height.
            var isControl = element.GetComponentInParent<Toggle>(true) != null || element.GetComponentInParent<Slider>(true) != null;
            if (isControl && longest <= options.MaxControlCapsule) return;
            if (corner >= shortest * options.CapsuleCornerShare)
                findings.Add(new UiFinding("capsule", Path(element), $"{rect.width:0} x {rect.height:0} with {corner:0}-unit corners: a capsule"));
        }

        private static void CheckRawImages(RectTransform root, UiAuditOptions options, List<UiFinding> findings)
        {
            foreach (var image in Visible<RawImage>(root))
            {
                var texture = image.texture;
                var rect = image.rectTransform.rect;
                if (texture == null || rect.height <= 0f || texture.height <= 0) continue;
                var uv = image.uvRect;
                var shown = texture.width * uv.width / (texture.height * uv.height);
                if (Mathf.Abs(rect.width / rect.height / shown - 1f) > options.StretchTolerance)
                    findings.Add(new UiFinding("stretched-sprite", Path(image.transform), $"texture {texture.name} is drawn {rect.width:0} x {rect.height:0}, not at its aspect ratio"));
            }
        }

        private static void CheckTexts(RectTransform root, float shortSide, UiAuditOptions options, SortedSet<string> fonts, SortedSet<float> fontSizes, List<UiFinding> findings)
        {
            foreach (var legacy in Visible<Text>(root))
                findings.Add(new UiFinding("legacy-text", Path(legacy.transform), "UnityEngine.UI.Text instead of TextMeshPro"));

            foreach (var text in Visible<TMP_Text>(root))
            {
                var path = Path(text.transform);
                text.ForceMeshUpdate(true);
                if (text.font != null)
                {
                    fonts.Add(text.font.name);
                    if (DefaultFonts.Any(d => text.font.name.IndexOf(d, StringComparison.OrdinalIgnoreCase) >= 0))
                        findings.Add(new UiFinding("default-font", path, $"the default font {text.font.name}"));
                    if (options.AllowedFonts.Length > 0 && !options.AllowedFonts.Contains(text.font.name))
                        findings.Add(new UiFinding("off-scale-font", path, $"the font {text.font.name} isn't one of the project's ({string.Join(", ", options.AllowedFonts)})"));
                }

                var fontSize = text.fontSize;
                fontSizes.Add(Mathf.Round(fontSize * 10f) / 10f);
                if (options.AllowedFontSizes.Length > 0 && !text.enableAutoSizing && !options.AllowedFontSizes.Any(allowed => Mathf.Abs(allowed - fontSize) < 0.5f))
                    findings.Add(new UiFinding("off-scale-font", path, $"text size {fontSize:0.#} isn't on the type scale ({string.Join(", ", options.AllowedFontSizes)})"));
                if (shortSide > 0f && fontSize < shortSide * options.MinFontFraction)
                    findings.Add(new UiFinding("text-too-small", path, $"size {fontSize:0.#}, below {shortSide * options.MinFontFraction:0.#} for this canvas"));

                var content = text.text ?? string.Empty;
                if (string.IsNullOrWhiteSpace(content)) continue;
                var box = text.rectTransform.rect;
                var used = text.textBounds.size;
                if (text.isTextOverflowing || used.x > box.width + 1f || used.y > box.height + 1f)
                    findings.Add(new UiFinding("text-overflow", path, $"\"{Short(content)}\" needs {used.x:0} x {used.y:0} in a {box.width:0} x {box.height:0} box"));
                if (ScientificNumber.IsMatch(content))
                    findings.Add(new UiFinding("scientific-number", path, $"\"{Short(content)}\": show players letters, such as 1.2T, not exponents"));
                if (content.Any(char.IsSurrogate) || content.Any(c => c >= '☀' && c <= '➿'))
                    findings.Add(new UiFinding("emoji", path, $"\"{Short(content)}\": emoji as icons"));
                if (PlaceholderTexts.Any(p => string.Equals(content.Trim(), p, StringComparison.OrdinalIgnoreCase)))
                    findings.Add(new UiFinding("placeholder-text", path, $"\"{content.Trim()}\""));
            }
        }

        private static void CheckScales(RectTransform root, List<UiFinding> findings)
        {
            foreach (var element in root.GetComponentsInChildren<RectTransform>(false))
            {
                var scale = element.localScale;
                if (Mathf.Abs(Mathf.Abs(scale.x) - Mathf.Abs(scale.y)) > 0.005f)
                    findings.Add(new UiFinding("uneven-scale", Path(element), $"scale {scale.x:0.##} x {scale.y:0.##}: it distorts everything inside"));
            }
        }

        private static void CheckSelectables(RectTransform root, float shortSide, UiAuditOptions options, List<UiFinding> findings)
        {
            foreach (var selectable in Visible<Selectable>(root))
            {
                var path = Path(selectable.transform);
                var graphic = selectable.targetGraphic;
                var rect = ((RectTransform)selectable.transform).rect;
                if (graphic != null)
                {
                    var padding = graphic.raycastPadding;
                    rect = new Rect(0f, 0f, rect.width - padding.x - padding.z, rect.height - padding.y - padding.w);
                }

                if (Mathf.Min(rect.width, rect.height) < shortSide * options.MinTouchFraction)
                    findings.Add(new UiFinding("small-touch-target", path, $"{rect.width:0} x {rect.height:0}, needs at least {shortSide * options.MinTouchFraction:0} on each side; a negative raycast padding extends it"));
                var animatedByCode = selectable.GetComponents<IPointerDownHandler>().Any(handler => !(handler is Selectable));
                if (selectable.transition == Selectable.Transition.None && !animatedByCode)
                    findings.Add(new UiFinding("no-press-state", path, "no transition and nothing that handles a press: it shows nothing"));
            }
        }

        private static void CheckRaycasts(RectTransform root, List<UiFinding> findings)
        {
            foreach (var graphic in Visible<Graphic>(root))
            {
                if (!graphic.raycastTarget) continue;
                if (graphic.GetComponentsInParent<IEventSystemHandler>(true).Length == 0)
                    findings.Add(new UiFinding("needless-raycast", Path(graphic.transform), "Raycast Target on something nothing listens to: it costs a check on every touch"));
            }
        }

        private static void CheckPlacement(RectTransform root, Rect bounds, List<UiFinding> findings)
        {
            var solid = new List<RectTransform>();
            foreach (var graphic in Visible<Graphic>(root))
                if (graphic is TMP_Text || graphic.GetComponent<Selectable>() != null) solid.Add(graphic.rectTransform);
            foreach (var selectable in Visible<Selectable>(root))
                if (selectable.targetGraphic == null) solid.Add((RectTransform)selectable.transform);

            var margin = bounds.width * 0.002f;
            var rects = new Dictionary<RectTransform, Rect>(solid.Count);
            foreach (var element in solid)
            {
                var rect = WorldRect(element);
                rects[element] = rect;
                if (IsClipped(element)) continue;
                if (rect.xMin < bounds.xMin - margin || rect.xMax > bounds.xMax + margin || rect.yMin < bounds.yMin - margin || rect.yMax > bounds.yMax + margin)
                    findings.Add(new UiFinding("off-screen", Path(element), "reaches outside the screen"));
            }

            for (var i = 0; i < solid.Count; i++)
            {
                for (var j = i + 1; j < solid.Count; j++)
                {
                    var a = solid[i];
                    var b = solid[j];
                    if (a == b || a.IsChildOf(b) || b.IsChildOf(a) || IsClipped(a) || IsClipped(b)) continue;
                    var overlap = Intersection(rects[a], rects[b]);
                    var smaller = Mathf.Min(rects[a].width * rects[a].height, rects[b].width * rects[b].height);
                    if (smaller > 0f && overlap > smaller * 0.05f)
                        findings.Add(new UiFinding("overlap", Path(a), $"covers {Path(b)}"));
                }
            }
        }

        private static void CheckAlignment(RectTransform root, UiAuditOptions options, List<UiFinding> findings)
        {
            foreach (var parent in root.GetComponentsInChildren<RectTransform>(false))
            {
                if (parent.GetComponent<LayoutGroup>() != null) continue;
                var children = new List<RectTransform>();
                foreach (Transform child in parent)
                    if (child.gameObject.activeInHierarchy && child is RectTransform element && element.GetComponent<Graphic>() != null) children.Add(element);
                for (var i = 0; i < children.Count; i++)
                {
                    for (var j = i + 1; j < children.Count; j++)
                    {
                        var miss = NearMiss(children[i], children[j], options.NearMissUnits);
                        if (miss != null) findings.Add(new UiFinding("near-miss-alignment", Path(children[i]), $"{miss} of {children[j].name} almost line up: align them or separate them on purpose"));
                    }
                }
            }
        }

        private static string NearMiss(RectTransform a, RectTransform b, float units)
        {
            Rect ra = LocalRect(a), rb = LocalRect(b);
            if (Misses(ra.xMin, rb.xMin, units)) return "left edges";
            if (Misses(ra.xMax, rb.xMax, units)) return "right edges";
            if (Misses(ra.yMin, rb.yMin, units)) return "bottom edges";
            if (Misses(ra.yMax, rb.yMax, units)) return "top edges";
            if (Misses(ra.center.x, rb.center.x, units)) return "horizontal centers";
            if (Misses(ra.center.y, rb.center.y, units)) return "vertical centers";
            return null;
        }

        private static bool Misses(float a, float b, float units)
        {
            var difference = Mathf.Abs(a - b);
            return difference > 0.5f && difference <= units;
        }

        private static Rect LocalRect(RectTransform element)
        {
            var rect = element.rect;
            rect.center += (Vector2)element.localPosition;
            return rect;
        }

        private static float Coverage(RectTransform root, Rect bounds)
        {
            var rects = Visible<Graphic>(root).Where(g => g.color.a > 0.05f).Select(g => WorldRect(g.rectTransform)).ToList();
            var hits = 0;
            for (var y = 0; y < CoverageSamples; y++)
            {
                for (var x = 0; x < CoverageSamples; x++)
                {
                    var point = new Vector2(bounds.xMin + (x + 0.5f) * bounds.width / CoverageSamples, bounds.yMin + (y + 0.5f) * bounds.height / CoverageSamples);
                    if (rects.Any(r => r.Contains(point))) hits++;
                }
            }

            return hits / (float)(CoverageSamples * CoverageSamples);
        }

        private static IEnumerable<T> Visible<T>(RectTransform root) where T : Component
        {
            foreach (var component in root.GetComponentsInChildren<T>(false))
            {
                if (component is Behaviour behaviour && !behaviour.enabled) continue;
                if (component is Graphic graphic && graphic.canvasRenderer != null && graphic.color.a <= 0f) continue;
                yield return component;
            }
        }

        private static bool IsDefaultSprite(Sprite sprite)
        {
            var path = AssetDatabase.GetAssetPath(sprite);
            return path.Contains("unity_builtin_extra") || path.Contains("unity default resources") || (string.IsNullOrEmpty(path) && DefaultSprites.Contains(sprite.name));
        }

        private static bool IsClipped(RectTransform element) =>
            element.GetComponentInParent<RectMask2D>(true) != null || element.GetComponentInParent<Mask>(true) != null;

        private static Rect WorldRect(RectTransform element)
        {
            var corners = new Vector3[4];
            element.GetWorldCorners(corners);
            return Rect.MinMaxRect(
                Mathf.Min(corners[0].x, corners[2].x), Mathf.Min(corners[0].y, corners[2].y),
                Mathf.Max(corners[0].x, corners[2].x), Mathf.Max(corners[0].y, corners[2].y));
        }

        private static float Intersection(Rect a, Rect b)
        {
            var width = Mathf.Min(a.xMax, b.xMax) - Mathf.Max(a.xMin, b.xMin);
            var height = Mathf.Min(a.yMax, b.yMax) - Mathf.Max(a.yMin, b.yMin);
            return width > 0f && height > 0f ? width * height : 0f;
        }

        private static string Short(string text) => text.Length > 40 ? text.Substring(0, 40) + "..." : text;

        private static string Path(Transform element)
        {
            var path = element.name;
            for (var parent = element.parent; parent != null; parent = parent.parent) path = parent.name + "/" + path;
            return path;
        }
    }
}
