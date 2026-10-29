using System;
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

        // Keeps data until the write has finished: don't change or reuse the array before the task completes.
        UniTask WriteAsync(string key, byte[] data, CancellationToken cancellationToken);

        UniTask DeleteAsync(string key, CancellationToken cancellationToken);

        // Blocks until every operation started so far has finished, or the timeout passes; false on a timeout.
        // For the moment the app pauses or quits, when no later frame would let a pending write finish.
        bool Flush(TimeSpan timeout);
    }
}
