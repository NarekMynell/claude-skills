using System;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.ContentLoading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.ResourceManagement;
using UnityEngine.ResourceManagement.AsyncOperations;
using UnityEngine.TestTools;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.ContentLoading
{
    public sealed class AddressablesContentLoaderTests
    {
        private sealed class FakeOperations : IAssetOperations
        {
            private readonly ResourceManager _resourceManager = new ResourceManager();
            private readonly Dictionary<object, Object> _assets = new Dictionary<object, Object>();

            public int Loads { get; private set; }

            public int Releases { get; private set; }

            public void Add(object key, Object asset) => _assets[key] = asset;

            public AsyncOperationHandle<T> Load<T>(object key)
            {
                Loads++;
                return _assets.TryGetValue(key, out var asset)
                    ? _resourceManager.CreateCompletedOperation((T)(object)asset, null)
                    : _resourceManager.CreateCompletedOperation(default(T), $"No asset at '{key}'.");
            }

            public void Release(AsyncOperationHandle handle)
            {
                Releases++;
                _resourceManager.Release(handle);
            }
        }

        private FakeOperations _operations;
        private Material _material;

        [SetUp]
        public void SetUp()
        {
            _operations = new FakeOperations();
            _material = new Material(Shader.Find("Hidden/InternalErrorShader"));
            _operations.Add("material", _material);
        }

        [TearDown]
        public void TearDown() => Object.DestroyImmediate(_material);

        [Test]
        public void SameKeyLoadedTwice_SharesOneHandle_AndNeedsTwoReleases()
        {
            var loader = new AddressablesContentLoader(_operations);

            var first = loader.LoadAsync<Material>("material", CancellationToken.None).GetAwaiter().GetResult();
            var second = loader.LoadAsync<Material>("material", CancellationToken.None).GetAwaiter().GetResult();
            Assert.That(first, Is.SameAs(_material));
            Assert.That(second, Is.SameAs(_material));
            Assert.That(_operations.Loads, Is.EqualTo(1));

            loader.Release("material");
            Assert.That(_operations.Releases, Is.Zero);
            loader.Release("material");
            Assert.That(_operations.Releases, Is.EqualTo(1));
            Assert.Throws<InvalidOperationException>(() => loader.Release("material"));
        }

        [Test]
        public void FailedLoad_ReleasesItsHandle_AndThrows()
        {
            // The ResourceManager logs failed operations itself.
            LogAssert.ignoreFailingMessages = true;
            var loader = new AddressablesContentLoader(_operations);

            Assert.Throws<InvalidOperationException>(() => loader.LoadAsync<Material>("missing", CancellationToken.None).GetAwaiter().GetResult());
            Assert.That(_operations.Releases, Is.EqualTo(1));
        }

        [Test]
        public void LoadingAKeyAsAnotherType_Throws()
        {
            var loader = new AddressablesContentLoader(_operations);
            loader.LoadAsync<Material>("material", CancellationToken.None).GetAwaiter().GetResult();

            Assert.Throws<InvalidOperationException>(() => loader.LoadAsync<Texture2D>("material", CancellationToken.None).GetAwaiter().GetResult());
        }

        [Test]
        public void Dispose_ReleasesEverythingStillLoaded()
        {
            var loader = new AddressablesContentLoader(_operations);
            loader.LoadAsync<Material>("material", CancellationToken.None).GetAwaiter().GetResult();

            loader.Dispose();

            Assert.That(_operations.Releases, Is.EqualTo(1));
        }
    }
}
