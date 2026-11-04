using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using UnityEngine.UI;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace LibraryTests.GuideClaims
{
    // What the capabilities reference and the UI guide claim, checked at runtime. A failure after a Unity upgrade means a
    // guide is out of date: fix the guide, not the test.
    public sealed class InterfaceAndSpriteClaimsTests
    {
        private interface IActor
        {
            void Advance(float deltaTime);
        }

        private struct Walker : IActor
        {
            public float Phase;

            public void Advance(float deltaTime) => Phase += deltaTime;
        }

        private static void AdvanceAll<T>(T[] actors, float deltaTime) where T : struct, IActor
        {
            for (var i = 0; i < actors.Length; i++) actors[i].Advance(deltaTime);
        }

        [Test]
        public void AGenericStructConstraintUsesAnInterfaceWithoutAllocating()
        {
            var actors = new Walker[256];
            AdvanceAll(actors, 0.01f);

            Assert.That(() => AdvanceAll(actors, 0.01f), Is.Not.AllocatingGCMemory());
            Assert.That(actors[0].Phase, NUnit.Framework.Is.EqualTo(0.02f).Within(0.0001f));
        }

        // The performance guide's budget test reads these counters.
        [TestCase("Draw Calls Count")]
        [TestCase("SetPass Calls Count")]
        [TestCase("Triangles Count")]
        public void TheRenderCountersOfTheBudgetTestExist(string counter)
        {
            using var recorder = Unity.Profiling.ProfilerRecorder.StartNew(Unity.Profiling.ProfilerCategory.Render, counter);

            Assert.That(recorder.Valid, NUnit.Framework.Is.True);
        }

        private sealed class ProbeImage : Image
        {
            public List<UIVertex> Vertices()
            {
                var helper = new VertexHelper();
                OnPopulateMesh(helper);
                var stream = new List<UIVertex>();
                helper.GetUIVertexStream(stream);
                helper.Dispose();
                return stream;
            }
        }

        private GameObject _canvas;
        private Texture2D _texture;
        private Sprite _sprite;

        [SetUp]
        public void SetUp()
        {
            _canvas = new GameObject("Canvas", typeof(Canvas));
            _canvas.GetComponent<Canvas>().referencePixelsPerUnit = 100f;
            _texture = new Texture2D(64, 64);
            _sprite = Sprite.Create(_texture, new Rect(0, 0, 64, 64), Vector2.one * 0.5f, 200f, 0, SpriteMeshType.FullRect, Vector4.one * 20f);
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(_canvas);
            Object.DestroyImmediate(_sprite);
            Object.DestroyImmediate(_texture);
        }

        private float FirstCornerWidth(Vector2 size, float multiplier)
        {
            var go = new GameObject("Image", typeof(RectTransform), typeof(CanvasRenderer));
            go.transform.SetParent(_canvas.transform, false);
            ((RectTransform)go.transform).sizeDelta = size;
            var image = go.AddComponent<ProbeImage>();
            image.sprite = _sprite;
            image.type = Image.Type.Sliced;
            image.pixelsPerUnitMultiplier = multiplier;
            var xs = image.Vertices().Select(v => v.position.x).Distinct().OrderBy(x => x).ToList();
            return xs[1] - xs[0];
        }

        // UI guide: border pixels / (sprite PPU / canvas Reference PPU x multiplier).
        [TestCase(1f, 10f)]
        [TestCase(2f, 5f)]
        public void ASlicedCornerHasItsSize_WhateverTheElementsSize(float multiplier, float expected)
        {
            Assert.That(FirstCornerWidth(new Vector2(400f, 100f), multiplier), NUnit.Framework.Is.EqualTo(expected).Within(0.01f));
            Assert.That(FirstCornerWidth(new Vector2(800f, 100f), multiplier), NUnit.Framework.Is.EqualTo(expected).Within(0.01f));
        }

        // UI guide: an element smaller than its two borders squeezes them to fit.
        [Test]
        public void AnElementSmallerThanItsBorders_SqueezesThem()
        {
            Assert.That(FirstCornerWidth(new Vector2(10f, 100f), 1f), NUnit.Framework.Is.EqualTo(5f).Within(0.01f));
        }
    }
}
