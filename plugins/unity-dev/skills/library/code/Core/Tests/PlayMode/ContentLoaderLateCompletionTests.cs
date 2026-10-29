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

namespace Company.Product.Core.PlayModeTests
{
    public sealed class ContentLoaderLateCompletionTests
    {
        private sealed class PendingOperation<T> : AsyncOperationBase<T>
        {
            protected override void Execute() { }
        }

        // Each key gets its own pending operation, completed on demand.
        private sealed class KeyedOperations : IAssetOperations
        {
            private readonly ResourceManager _resourceManager = new ResourceManager();
            private readonly Dictionary<object, Action<bool>> _completions = new Dictionary<object, Action<bool>>();

            public AsyncOperationHandle<T> Load<T>(object key)
            {
                var operation = new PendingOperation<T>();
                var handle = _resourceManager.StartOperation(operation, default);
                _completions[key] = success => operation.Complete(default, success, success ? null : "load failed");
                return handle;
            }

            public void Release(AsyncOperationHandle handle) => _resourceManager.Release(handle);

            public void Complete(object key) => _completions[key](true);

            public void Fail(object key) => _completions[key](false);
        }

        // A cancelled load whose Addressables operation finishes later must not end some other, unrelated load.
        [UnityTest]
        public IEnumerator CancelledLoad_FinishingLate_DoesNotEndAnotherLoadEarly() => UniTask.ToCoroutine(async () =>
        {
            var operations = new KeyedOperations();
            var loader = new AddressablesContentLoader(operations);
            var cancellation = new CancellationTokenSource();

            var cancelled = loader.LoadAsync<Material>("cancelled", cancellation.Token);
            cancellation.Cancel();
            try
            {
                await cancelled;
            }
            catch (OperationCanceledException)
            {
            }

            var other = loader.LoadAsync<Material>("other", CancellationToken.None);
            operations.Complete("cancelled");

            var statusAfterUnrelatedCompletion = other.Status;
            Exception otherFailure = null;
            if (statusAfterUnrelatedCompletion != UniTaskStatus.Pending)
            {
                try
                {
                    await other;
                }
                catch (Exception exception)
                {
                    otherFailure = exception;
                }
            }

            Assert.That(statusAfterUnrelatedCompletion, Is.EqualTo(UniTaskStatus.Pending),
                $"'other' ended before its own operation finished: {otherFailure}");

            operations.Complete("other");
            await other;
            loader.Dispose();
        });

        // README: "Loads still running then end with ObjectDisposedException".
        [UnityTest]
        public IEnumerator LoadRunningAtDispose_ThatThenFails_EndsWithObjectDisposed() => UniTask.ToCoroutine(async () =>
        {
            LogAssert.ignoreFailingMessages = true;
            var operations = new KeyedOperations();
            var loader = new AddressablesContentLoader(operations);

            var load = loader.LoadAsync<Material>("failing", CancellationToken.None);
            loader.Dispose();
            operations.Fail("failing");

            Exception ended = null;
            try
            {
                await load;
            }
            catch (Exception exception)
            {
                ended = exception;
            }

            Assert.That(ended, Is.InstanceOf<ObjectDisposedException>());
        });
    }
}
