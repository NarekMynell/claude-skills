using System;
using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.Scenes
{
    public interface ISceneLoader
    {
        // Replaces the open scenes with the scene at scenePath (as in Build Profiles, e.g. "Assets/_Project/Scenes/Level1.unity").
        UniTask LoadAsync(string scenePath, IProgress<float> progress, CancellationToken cancellationToken);
    }
}
