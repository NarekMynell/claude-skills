using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Persistence
{
    // Where save data lives. Keys are file-name-safe identifiers such as "progress".
    public interface ISaveStorage
    {
        bool Exists(string key);

        // Null when there is no data for the key.
        UniTask<byte[]> ReadAsync(string key, CancellationToken cancellationToken);

        UniTask WriteAsync(string key, byte[] data, CancellationToken cancellationToken);

        UniTask DeleteAsync(string key, CancellationToken cancellationToken);
    }
}
