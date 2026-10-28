using UnityEngine.ResourceManagement.AsyncOperations;

namespace Company.Product.Core.ContentLoading
{
    // Test seam over the Addressables calls the loader makes.
    internal interface IAssetOperations
    {
        AsyncOperationHandle<T> Load<T>(object key);
        void Release(AsyncOperationHandle handle);
    }
}
