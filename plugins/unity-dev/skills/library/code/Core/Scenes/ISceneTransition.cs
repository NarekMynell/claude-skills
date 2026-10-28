using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.Scenes
{
    // Covers the screen while a scene loads. It must survive the load: put it in the root scope's prefab.
    public interface ISceneTransition
    {
        UniTask ShowAsync(CancellationToken cancellationToken);
        UniTask HideAsync(CancellationToken cancellationToken);
    }
}
