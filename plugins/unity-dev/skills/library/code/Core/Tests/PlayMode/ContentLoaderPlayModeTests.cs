using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.ContentLoading;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.ResourceManagement;
using UnityEngine.ResourceManagement.AsyncOperations;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace Company.Product.Core.PlayModeTests
{
    // Loads that are still running when they're cancelled or the loader is disposed.
    public sealed class ContentLoaderPlayModeTests
    {
        private sealed class PendingOperation<T> : AsyncOperationBase<T>
        {
            protected override void Execute() { }
        }

        private sealed class PendingOperations : IAssetOperations
        {
            private readonly ResourceManager _resourceManager = new ResourceManager();
            private readonly List<Action> _completions = new List<Action>();

            public int Releases { get; private set; }

            public AsyncOperationHandle<T> Load<T>(object key)
            {
                var operation = new PendingOperation<T>();
                var handle = _resourceManager.StartOperation(operation, default);
                _completions.Add(() => operation.Complete(default, true, null));
                return handle;
            }

            public void Release(AsyncOperationHandle handle)
            {
                Releases++;
                _resourceManager.Release(handle);
            }

            public void CompleteAll()
            {
                foreach (var complete in _completions) complete();
                _completions.Clear();
            }
        }

        [UnityTest]
        public IEnumerator CancelledLoad_ReleasesItsHandle() => UniTask.ToCoroutine(async () =>
        {
            var operations = new PendingOperations();
            var loader = new AddressablesContentLoader(operations);
            var cancellation = new CancellationTokenSource();

            var load = loader.LoadAsync<Material>("material", cancellation.Token);
            cancellation.Cancel();

            var exception = await CatchAsync(load);
            Assert.That(exception, Is.InstanceOf<OperationCanceledException>());
            Assert.That(operations.Releases, Is.EqualTo(1));
            operations.CompleteAll();
        });

        [UnityTest]
        public IEnumerator DisposeDuringALoad_EndsItWithObjectDisposed_AndReleasesOnce() => UniTask.ToCoroutine(async () =>
        {
            var operations = new PendingOperations();
            var loader = new AddressablesContentLoader(operations);

            var load = loader.LoadAsync<Material>("material", CancellationToken.None);
            loader.Dispose();
            Assert.That(operations.Releases, Is.Zero, "A running handle is released by its own load, once it ends.");
            operations.CompleteAll();

            var exception = await CatchAsync(load);
            Assert.That(exception, Is.InstanceOf<ObjectDisposedException>());
            Assert.That(operations.Releases, Is.EqualTo(1));
            Assert.DoesNotThrow(() => loader.Release("material"), "Release after Dispose is a no-op.");
        });

        private static async UniTask<Exception> CatchAsync(UniTask<Material> load)
        {
            try
            {
                await load;
                return null;
            }
            catch (Exception exception)
            {
                return exception;
            }
        }
    }
}
