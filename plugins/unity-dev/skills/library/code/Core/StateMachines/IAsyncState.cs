using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.StateMachines
{
    public interface IAsyncState
    {
        UniTask EnterAsync(CancellationToken cancellationToken);
        UniTask ExitAsync(CancellationToken cancellationToken);
    }
}
