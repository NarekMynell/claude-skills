using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;

namespace Company.Product.Core.ContentLoading
{
    internal sealed class AddressablesOperations : IAssetOperations
    {
        public AsyncOperationHandle<T> Load<T>(object key) => Addressables.LoadAssetAsync<T>(key);

        public void Release(AsyncOperationHandle handle) => Addressables.Release(handle);
    }
}
