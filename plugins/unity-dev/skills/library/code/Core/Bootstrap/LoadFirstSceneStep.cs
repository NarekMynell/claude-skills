using System;
using System.Threading;
using Company.Product.Core.Scenes;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.Bootstrap
{
    // The last startup step: opens the first scene, or in the Editor the scene that was open when Play was pressed.
    public sealed class LoadFirstSceneStep : IBootstrapStep
    {
        private readonly ISceneLoader _sceneLoader;
        private readonly FirstSceneConfig _config;

        public LoadFirstSceneStep(ISceneLoader sceneLoader, FirstSceneConfig config)
        {
            _sceneLoader = sceneLoader ?? throw new ArgumentNullException(nameof(sceneLoader));
            _config = config != null ? config : throw new ArgumentNullException(nameof(config));
        }

        public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken)
        {
            var scenePath = EditorPlaySession.TryTakeReturnScene(out var returnScene)
                ? returnScene
                : _config.FirstScene.ScenePath;

            if (string.IsNullOrEmpty(scenePath)) throw new InvalidOperationException($"{_config.name}: the first scene isn't assigned.");

            return _sceneLoader.LoadAsync(scenePath, progress, cancellationToken);
        }
    }
}
