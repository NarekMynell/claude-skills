using System;
using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.Bootstrap
{
    // One unit of startup work. Steps run in registration order; report progress from 0 to 1.
    public interface IBootstrapStep
    {
        UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken);
    }
}
