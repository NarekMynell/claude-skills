using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.Scenes
{
    public sealed class NoSceneTransition : ISceneTransition
    {
        public UniTask ShowAsync(CancellationToken cancellationToken) => UniTask.CompletedTask;

        public UniTask HideAsync(CancellationToken cancellationToken) => UniTask.CompletedTask;
    }
}
