using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine.AddressableAssets;
using Object = UnityEngine.Object;

namespace Company.Product.Core.ContentLoading
{
    // Loads Addressables content and owns the handles. Every load needs a matching Release;
    // loading the same key twice shares one handle and needs two releases.
    public interface IContentLoader : IDisposable
    {
        UniTask<T> LoadAsync<T>(AssetReference reference, CancellationToken cancellationToken) where T : Object;
        UniTask<T> LoadAsync<T>(string address, CancellationToken cancellationToken) where T : Object;
        void Release(AssetReference reference);
        void Release(string address);
    }
}
