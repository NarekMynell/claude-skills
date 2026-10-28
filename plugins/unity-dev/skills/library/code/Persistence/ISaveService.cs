using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Persistence
{
    public interface ISaveService<TData> where TData : class
    {
        bool HasSave { get; }

        // Null when there is no save yet.
        UniTask<TData> LoadAsync(CancellationToken cancellationToken);

        UniTask SaveAsync(TData data, CancellationToken cancellationToken);

        UniTask DeleteAsync(CancellationToken cancellationToken);
    }
}
