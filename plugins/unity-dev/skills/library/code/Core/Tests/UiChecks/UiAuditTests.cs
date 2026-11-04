using System.Linq;
using NUnit.Framework;
using ProjectName.Core.Editor.UiChecks;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ProjectName.Core.Tests.UiChecks
{
    public sealed class UiAuditTests
    {
        private const float CanvasWidth = 1080f;
        private const float CanvasHeight = 1920f;

        private GameObject _canvas;
        private RectTransform _root;
        private TMP_FontAsset _font;
        private readonly System.Collections.Generic.List<Object> _created = new System.Collections.Generic.List<Object>();

        [SetUp]
        public void SetUp()
        {
            if (Resources.Load<TMP_Settings>("TMP Settings") == null) Assert.Ignore("These tests need TMP Essentials: Window > TextMeshPro > Import TMP Essential Resources.");

            _canvas = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler));
            var canvas = _canvas.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            _root = (RectTransform)_canvas.transform;
            _root.sizeDelta = new Vector2(CanvasWidth, CanvasHeight);
            _font = SystemFont();
            if (_font == null) Assert.Ignore("No system font that TextMesh Pro can load on this machine.");
            _font.name = "GameFont";
            _created.Add(_font);
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(_canvas);
            foreach (var item in _created) Object.DestroyImmediate(item);
            _created.Clear();
        }

        // Unity's built-in font has no font data for TextMesh Pro to read, and tests carry no font file of their own.
        private static TMP_FontAsset SystemFont()
        {
            foreach (var family in Font.GetOSInstalledFontNames())
            {
                var font = TMP_FontAsset.CreateFontAsset(family, "Regular");
                if (font != null) return font;
            }

            return null;
        }

        private string[] Rules(UiAuditOptions options = null) => UiAudit.Run(_root, options ?? new UiAuditOptions()).Findings.Select(f => f.Rule).Distinct().ToArray();

        // A rounded rectangle sprite with a real alpha shape.
        private Sprite Rounded(int width, int height, int radius, int border)
        {
            var texture = new Texture2D(width, height, TextureFormat.RGBA32, false);
            for (var y = 0; y < height; y++)
            {
                for (var x = 0; x < width; x++)
                {
                    var dx = Mathf.Max(radius - x - 0.5f, x + 0.5f - (width - radius));
                    var dy = Mathf.Max(radius - y - 0.5f, y + 0.5f - (height - radius));
                    var inside = dx <= 0f || dy <= 0f || dx * dx + dy * dy <= radius * radius;
                    texture.SetPixel(x, y, inside ? Color.white : Color.clear);
                }
            }

            texture.Apply();
            _created.Add(texture);
            var sprite = Sprite.Create(texture, new Rect(0, 0, width, height), Vector2.one * 0.5f, 100f, 0, SpriteMeshType.FullRect, Vector4.one * border);
            sprite.name = "Panel";
            _created.Add(sprite);
            return sprite;
        }

        private Image AddImage(string name, Sprite sprite, Image.Type type, Vector2 size, Vector2 position, bool raycast = false)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
            var rect = (RectTransform)go.transform;
            rect.SetParent(_root, false);
            rect.sizeDelta = size;
            rect.anchoredPosition = position;
            var image = go.GetComponent<Image>();
            image.sprite = sprite;
            image.type = type;
            image.raycastTarget = raycast;
            return image;
        }

        private TextMeshProUGUI AddText(string name, string content, float size, Vector2 box, Vector2 position)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
            var rect = (RectTransform)go.transform;
            rect.SetParent(_root, false);
            rect.sizeDelta = box;
            rect.anchoredPosition = position;
            var text = go.GetComponent<TextMeshProUGUI>();
            text.font = _font;
            text.fontSize = size;
            text.text = content;
            text.raycastTarget = false;
            text.textWrappingMode = TextWrappingModes.NoWrap;
            return text;
        }

        [Test]
        public void ACleanPanel_Passes()
        {
            AddImage("Panel", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(600f, 300f), new Vector2(0f, 200f));
            AddText("Title", "Shop", 48f, new Vector2(400f, 80f), new Vector2(0f, -200f));

            var report = UiAudit.Run(_root, new UiAuditOptions());

            Assert.That(report.IsClean, report.ToString());
            Assert.That(report.CornerSizes, Is.EqualTo(new[] { 12f }));
        }

        [Test]
        public void ALongElementWithHalfCircleEnds_IsACapsule()
        {
            AddImage("Pill", Rounded(64, 64, 32, 32), Image.Type.Sliced, new Vector2(400f, 64f), Vector2.zero);

            Assert.That(Rules(), Does.Contain("capsule"));
        }

        [Test]
        public void ASquareElementWithRoundCorners_IsNotACapsule()
        {
            AddImage("Badge", Rounded(64, 64, 32, 32), Image.Type.Sliced, new Vector2(64f, 64f), Vector2.zero);

            Assert.That(Rules(), Does.Not.Contain("capsule"));
        }

        [Test]
        public void ASimpleImageDrawnAtAnotherAspect_IsStretched_AndAStretchedPillIsACapsule()
        {
            AddImage("Stretched", Rounded(64, 64, 32, 0), Image.Type.Simple, new Vector2(400f, 64f), Vector2.zero);

            var rules = Rules();

            Assert.That(rules, Does.Contain("stretched-sprite"));
            Assert.That(rules, Does.Contain("capsule"));
        }

        [Test]
        public void PreservedAspect_IsNotStretched()
        {
            var image = AddImage("Icon", Rounded(64, 64, 6, 0), Image.Type.Simple, new Vector2(400f, 64f), Vector2.zero);
            image.preserveAspect = true;

            Assert.That(Rules(), Does.Not.Contain("stretched-sprite"));
        }

        [Test]
        public void AnElementSmallerThanItsCorners_IsSquashed()
        {
            AddImage("Tiny", Rounded(64, 64, 12, 30), Image.Type.Sliced, new Vector2(300f, 40f), Vector2.zero);

            Assert.That(Rules(), Does.Contain("squashed-corners"));
        }

        [Test]
        public void TheCornerSize_FollowsTheMultiplier_AsUnityDrawsIt()
        {
            var image = AddImage("Panel", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(600f, 300f), Vector2.zero);
            image.pixelsPerUnitMultiplier = 2f;

            Assert.That(UiAudit.Run(_root, new UiAuditOptions()).CornerSizes, Is.EqualTo(new[] { 6f }));
        }

        [Test]
        public void ManyCornerSizes_AreReported()
        {
            var y = -800f;
            foreach (var radius in new[] { 4, 8, 12, 16 })
            {
                AddImage($"Panel{radius}", Rounded(64, 64, radius, 20), Image.Type.Sliced, new Vector2(300f, 200f), new Vector2(0f, y));
                y += 400f;
            }

            Assert.That(Rules(), Does.Contain("corner-spread"));
        }

        [Test]
        public void TextThatDoesNotFit_IsReported()
        {
            AddText("Long", "A label much longer than its box", 48f, new Vector2(100f, 60f), Vector2.zero);

            Assert.That(Rules(), Does.Contain("text-overflow"));
        }

        [Test]
        public void TemplateTells_AreReported()
        {
            AddText("Money", "$1.12e60", 48f, new Vector2(400f, 80f), new Vector2(0f, 0f));
            AddText("Icon", "★ Stars", 48f, new Vector2(400f, 80f), new Vector2(0f, 200f));
            AddText("Label", "New Text", 48f, new Vector2(400f, 80f), new Vector2(0f, 400f));

            var rules = Rules();

            Assert.That(rules, Does.Contain("scientific-number"));
            Assert.That(rules, Does.Contain("emoji"));
            Assert.That(rules, Does.Contain("placeholder-text"));
        }

        [Test]
        public void TinyText_IsReported()
        {
            AddText("Small", "fine print", 16f, new Vector2(400f, 80f), Vector2.zero);

            Assert.That(Rules(), Does.Contain("text-too-small"));
        }

        [Test]
        public void ManyFontSizes_AreReported()
        {
            var y = -800f;
            foreach (var size in new[] { 32f, 36f, 40f, 44f, 48f, 52f, 56f })
            {
                AddText($"T{size}", "Label", size, new Vector2(600f, 100f), new Vector2(0f, y));
                y += 200f;
            }

            Assert.That(Rules(), Does.Contain("font-size-spread"));
        }

        [Test]
        public void UnevenScale_IsReported()
        {
            var image = AddImage("Panel", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(300f, 200f), Vector2.zero);
            image.transform.localScale = new Vector3(1.5f, 1f, 1f);

            Assert.That(Rules(), Does.Contain("uneven-scale"));
        }

        [Test]
        public void ASmallButton_IsReported_AndRaycastPaddingFixesIt()
        {
            var image = AddImage("Close", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(60f, 60f), Vector2.zero, raycast: true);
            image.gameObject.AddComponent<Button>().targetGraphic = image;

            Assert.That(Rules(), Does.Contain("small-touch-target"));

            image.raycastPadding = Vector4.one * -40f;

            Assert.That(Rules(), Does.Not.Contain("small-touch-target"));
        }

        [Test]
        public void ARaycastTargetNothingListensTo_IsReported()
        {
            AddImage("Decor", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(300f, 200f), Vector2.zero, raycast: true);

            Assert.That(Rules(), Does.Contain("needless-raycast"));
        }

        [Test]
        public void OverlappingTexts_AreReported_ButALabelInsideItsButtonIsNot()
        {
            AddText("A", "One", 48f, new Vector2(300f, 80f), Vector2.zero);
            AddText("B", "Two", 48f, new Vector2(300f, 80f), new Vector2(50f, 0f));

            Assert.That(Rules(), Does.Contain("overlap"));

            Object.DestroyImmediate(_root.Find("B").gameObject);
            var button = AddImage("Button", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(400f, 150f), new Vector2(0f, 400f), raycast: true);
            button.gameObject.AddComponent<Button>().targetGraphic = button;
            var label = AddText("Label", "Buy", 48f, new Vector2(300f, 80f), Vector2.zero);
            label.transform.SetParent(button.transform, false);

            Assert.That(Rules(), Does.Not.Contain("overlap"));
        }

        [Test]
        public void AnElementOutsideTheScreen_IsReported()
        {
            AddText("Far", "Coins", 48f, new Vector2(300f, 80f), new Vector2(CanvasWidth, 0f));

            Assert.That(Rules(), Does.Contain("off-screen"));
        }

        [Test]
        public void NeighborsThatAlmostAlign_AreReported()
        {
            AddImage("A", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(300f, 100f), new Vector2(0f, 200f));
            AddImage("B", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(300f, 100f), new Vector2(2f, -200f));

            Assert.That(Rules(), Does.Contain("near-miss-alignment"));
        }

        [Test]
        public void AHudOverItsCoverageLimit_IsReported()
        {
            AddImage("Huge", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(CanvasWidth, CanvasHeight * 0.5f), Vector2.zero);

            Assert.That(Rules(new UiAuditOptions { MaxCoverage = 0.2f }), Does.Contain("covers-too-much"));
            Assert.That(UiAudit.Run(_root, new UiAuditOptions()).Coverage, Is.EqualTo(0.5f).Within(0.05f));
        }

        [Test]
        public void AFlatRectangleWithoutASprite_IsReported()
        {
            AddImage("Panel", null, Image.Type.Simple, new Vector2(600f, 400f), Vector2.zero);

            Assert.That(Rules(), Does.Contain("plain-rectangle"));
        }

        [Test]
        public void TokensApplyToEveryScreen()
        {
            AddImage("Panel", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(600f, 300f), new Vector2(0f, 200f));
            AddText("Title", "Shop", 48f, new Vector2(400f, 80f), new Vector2(0f, -200f));

            Assert.That(Rules(new UiAuditOptions { AllowedCornerSizes = new[] { 12f }, AllowedFontSizes = new[] { 48f }, AllowedFonts = new[] { "GameFont" } }), Is.Empty);
            Assert.That(Rules(new UiAuditOptions { AllowedCornerSizes = new[] { 8f, 16f } }), Does.Contain("off-scale-corner"));
            Assert.That(Rules(new UiAuditOptions { AllowedFontSizes = new[] { 40f } }), Does.Contain("off-scale-font"));
            Assert.That(Rules(new UiAuditOptions { AllowedFonts = new[] { "Other" } }), Does.Contain("off-scale-font"));
        }

        [Test]
        public void AnAuditThatNeedsTokensAndHasNone_IsReported()
        {
            Assert.That(Rules(new UiAuditOptions { RequireTokens = true }), Does.Contain("no-ui-tokens"));
        }

        private sealed class CustomGraphic : Graphic { }

        private sealed class MeasuredGraphic : Graphic, ProjectName.Core.UI.IUiShape
        {
            public float CornerRadius { get; set; }
        }

        private T AddGraphic<T>(string name, Vector2 size) where T : Graphic
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer));
            go.transform.SetParent(_root, false);
            ((RectTransform)go.transform).sizeDelta = size;
            var graphic = go.AddComponent<T>();
            graphic.raycastTarget = false;
            return graphic;
        }

        [Test]
        public void AShapeNoSpriteDescribes_MustMeasureItself()
        {
            AddGraphic<CustomGraphic>("Sdf", new Vector2(400f, 64f));

            Assert.That(Rules(), Does.Contain("unmeasured-shape"));
        }

        [Test]
        public void AShapeThatMeasuresItself_CountsLikeAnyOther_AndCanBeACapsule()
        {
            AddGraphic<MeasuredGraphic>("Sdf", new Vector2(400f, 64f)).CornerRadius = 32f;

            var report = UiAudit.Run(_root, new UiAuditOptions());

            Assert.That(report.Findings.Select(f => f.Rule), Does.Contain("capsule"));
            Assert.That(report.CornerSizes, Does.Contain(32f));
        }

        [Test]
        public void AnImageWithItsOwnMaterial_MustMeasureItself()
        {
            var material = new Material(Shader.Find("UI/Default"));
            _created.Add(material);
            AddImage("Sdf", null, Image.Type.Simple, new Vector2(400f, 64f), Vector2.zero).material = material;

            Assert.That(Rules(), Does.Contain("unmeasured-shape"));
        }

        [Test]
        public void APillInsideAToggle_IsAllowed()
        {
            var image = AddImage("Track", Rounded(64, 64, 32, 32), Image.Type.Sliced, new Vector2(160f, 64f), Vector2.zero);
            image.gameObject.AddComponent<Toggle>().targetGraphic = image;

            Assert.That(Rules(), Does.Not.Contain("capsule"));
        }

        [Test]
        public void ALongCapsuleInsideASlider_IsStillACapsule()
        {
            var image = AddImage("Track", Rounded(64, 64, 32, 32), Image.Type.Sliced, new Vector2(900f, 64f), Vector2.zero);
            image.gameObject.AddComponent<Slider>();

            Assert.That(Rules(), Does.Contain("capsule"));
        }

        [Test]
        public void ASpriteWithChildren_IsAContainer_AndItsCornersAreOnTheScale()
        {
            var image = AddImage("Panel", Rounded(64, 64, 12, 0), Image.Type.Simple, new Vector2(128f, 128f), Vector2.zero);
            new GameObject("Child", typeof(RectTransform)).transform.SetParent(image.transform, false);

            Assert.That(Rules(new UiAuditOptions { AllowedCornerSizes = new[] { 8f } }), Does.Contain("off-scale-corner"));
        }

        [Test]
        public void ARawImageDrawnAtAnotherAspect_IsStretched()
        {
            var go = new GameObject("Picture", typeof(RectTransform), typeof(CanvasRenderer));
            go.transform.SetParent(_root, false);
            ((RectTransform)go.transform).sizeDelta = new Vector2(400f, 100f);
            var raw = go.AddComponent<RawImage>();
            var texture = new Texture2D(64, 64);
            _created.Add(texture);
            raw.texture = texture;
            raw.raycastTarget = false;

            Assert.That(Rules(), Does.Contain("stretched-sprite"));
        }

        [Test]
        public void LiteralValuesInUss_AreReported_VariablesAreNot()
        {
            string[] lines = { ".a {", "  border-radius: 12px;", "  font-size: var(--text-m);", "  border-top-left-radius: var(--radius-s);", "  font-size: 18px;", "}" };

            var findings = UssTokenAudit.ScanFile("hud.uss", lines).ToList();

            Assert.That(findings.Count, Is.EqualTo(2));
            Assert.That(findings[0], Does.Contain("hud.uss:2"));
        }

        [Test]
        public void AUssAuditOfNothing_CannotPass()
        {
            Assert.That(UssTokenAudit.Run("No/Such/Folder", "tokens.uss"), Is.Not.Empty);
        }

        private sealed class PressAnimation : MonoBehaviour, UnityEngine.EventSystems.IPointerDownHandler
        {
            public void OnPointerDown(UnityEngine.EventSystems.PointerEventData eventData) { }
        }

        [Test]
        public void AButtonWithNoTransition_IsReported_UnlessCodeHandlesThePress()
        {
            var image = AddImage("Buy", Rounded(64, 64, 12, 20), Image.Type.Sliced, new Vector2(300f, 200f), Vector2.zero, raycast: true);
            var button = image.gameObject.AddComponent<Button>();
            button.transition = Selectable.Transition.None;

            Assert.That(Rules(), Does.Contain("no-press-state"));

            image.gameObject.AddComponent<PressAnimation>();

            Assert.That(Rules(), Does.Not.Contain("no-press-state"));
        }

        [Test]
        public void AnException_MovesTheFindingToTheAcceptedList_WithItsReason()
        {
            AddImage("Pill", Rounded(64, 64, 32, 32), Image.Type.Sliced, new Vector2(400f, 64f), Vector2.zero);

            var report = UiAudit.Run(_root, new UiAuditOptions().Allow("capsule", "Canvas/Pill", "Test reason."));

            Assert.That(report.IsClean, report.ToString());
            Assert.That(report.ToString(), Does.Contain("Test reason."));
            Assert.Throws<System.ArgumentException>(() => new UiAuditOptions().Allow("capsule", "Canvas/Pill", ""));
        }

        [Test]
        public void ManyExceptions_AreAFindingOfTheirOwn()
        {
            var options = new UiAuditOptions { MaxExceptions = 1 }.Allow("capsule", "A", "One.").Allow("capsule", "B", "Two.");

            Assert.That(UiAudit.Run(_root, options).Findings.Select(f => f.Rule), Does.Contain("too-many-exceptions"));
        }

        [Test]
        public void HiddenElements_AreIgnored()
        {
            var image = AddImage("Pill", Rounded(64, 64, 32, 32), Image.Type.Sliced, new Vector2(400f, 64f), Vector2.zero);
            image.gameObject.SetActive(false);

            Assert.That(Rules(), Does.Not.Contain("capsule"));
        }
    }
}
