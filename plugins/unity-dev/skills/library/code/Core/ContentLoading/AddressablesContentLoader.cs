using System;
using System.Collections.Generic;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;
using VContainer;
using Object = UnityEngine.Object;

namespace Company.Product.Core.ContentLoading
{
    // Each LoadAsync holds one reference to its key's handle until the matching Release; the handle is released
    // with the last reference. A load that fails or is cancelled drops its own reference. Dispose releases
    // everything; loads still running then end with ObjectDisposedException and release their handle themselves.
    public sealed class AddressablesContentLoader : IContentLoader
    {
        private readonly IAssetOperations _operations;
        private readonly Dictionary<object, Entry> _entries = new Dictionary<object, Entry>();
        private bool _isDisposed;

        [Inject]
        public AddressablesContentLoader() : this(new AddressablesOperations()) { }

        internal AddressablesContentLoader(IAssetOperations operations) => _operations = operations;

        public UniTask<T> LoadAsync<T>(AssetReference reference, CancellationToken cancellationToken) where T : Object
        {
            if (reference == null || !reference.RuntimeKeyIsValid()) throw new ArgumentException("The asset reference isn't assigned.", nameof(reference));

            return LoadKeyAsync<T>(reference.RuntimeKey, cancellationToken);
        }

        public UniTask<T> LoadAsync<T>(string address, CancellationToken cancellationToken) where T : Object
        {
            if (string.IsNullOrEmpty(address)) throw new ArgumentException("An address is required.", nameof(address));

            return LoadKeyAsync<T>(address, cancellationToken);
        }

        public void Release(AssetReference reference)
        {
            if (reference == null) throw new ArgumentNullException(nameof(reference));

            ReleaseKey(reference.RuntimeKey);
        }

        public void Release(string address) => ReleaseKey(address);

        public void Dispose()
        {
            if (_isDisposed) return;

            _isDisposed = true;
            foreach (var entry in _entries.Values)
                if (entry.Handle.IsDone) ReleaseHandle(entry);

            _entries.Clear();
        }

        private async UniTask<T> LoadKeyAsync<T>(object key, CancellationToken cancellationToken) where T : Object
        {
            if (_isDisposed) throw new ObjectDisposedException(nameof(AddressablesContentLoader));

            if (_entries.TryGetValue(key, out var entry))
            {
                if (entry.AssetType != typeof(T))
                    throw new InvalidOperationException($"'{key}' is already loaded as {entry.AssetType.Name}, not {typeof(T).Name}.");
            }
            else
            {
                entry = new Entry(_operations.Load<T>(key), typeof(T));
                _entries.Add(key, entry);
            }

            entry.References++;
            try
            {
                // Polled, not awaited through the handle: UniTask 2.5.11's ToUniTask returns a source cancelled from
                // the player loop to its pool while the source's Completed callback is still on the handle, and the
                // handle's late completion then ends whichever load reuses that source. Polling also keeps every
                // release on the main thread, whichever thread cancels the token.
                while (!entry.Handle.IsDone) await UniTask.Yield(PlayerLoopTiming.Update, cancellationToken);
            }
            catch (OperationCanceledException)
            {
                Drop(key, entry);
                throw;
            }

            if (_isDisposed)
            {
                Drop(key, entry);
                throw new ObjectDisposedException(nameof(AddressablesContentLoader));
            }

            if (entry.Handle.Status != AsyncOperationStatus.Succeeded)
            {
                var exception = entry.Handle.OperationException;
                Drop(key, entry);
                throw new InvalidOperationException($"Loading '{key}' failed.", exception);
            }

            return (T)entry.Handle.Result;
        }

        private void ReleaseKey(object key)
        {
            // After Dispose every handle is already released.
            if (_isDisposed) return;

            if (!_entries.TryGetValue(key, out var entry)) throw new InvalidOperationException($"'{key}' isn't loaded.");
            if (!entry.Handle.IsDone) throw new InvalidOperationException($"'{key}' is still loading. Release it after its load completes.");

            Drop(key, entry);
        }

        private void Drop(object key, Entry entry)
        {
            if (--entry.References > 0) return;

            if (_entries.TryGetValue(key, out var current) && current == entry) _entries.Remove(key);
            ReleaseHandle(entry);
        }

        private void ReleaseHandle(Entry entry)
        {
            if (entry.IsReleased) return;

            entry.IsReleased = true;
            _operations.Release(entry.Handle);
        }

        private sealed class Entry
        {
            public Entry(AsyncOperationHandle handle, Type assetType)
            {
                Handle = handle;
                AssetType = assetType;
            }

            public AsyncOperationHandle Handle { get; }

            public Type AssetType { get; }

            public int References { get; set; }

            public bool IsReleased { get; set; }
        }
    }
}
