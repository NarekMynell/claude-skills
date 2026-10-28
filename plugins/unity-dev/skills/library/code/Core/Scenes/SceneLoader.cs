using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Company.Product.Core.Scenes
{
    // Starts loading in the background, shows the transition, waits for the load, activates the scene, then hides
    // the transition. The transition is hidden however the load ends. Once activation starts the load can't be
    // stopped, so it finishes even if the caller's scope is destroyed by the new scene.
    public sealed class SceneLoader : ISceneLoader
    {
        private const float LoadedProgress = 0.9f;

        private readonly ISceneTransition _transition;

        public SceneLoader(ISceneTransition transition) => _transition = transition ?? throw new ArgumentNullException(nameof(transition));

        public async UniTask LoadAsync(string scenePath, IProgress<float> progress, CancellationToken cancellationToken)
        {
            if (string.IsNullOrEmpty(scenePath)) throw new ArgumentException("A scene path is required.", nameof(scenePath));

            var operation = StartLoading(scenePath);
            operation.allowSceneActivation = false;
            try
            {
                await _transition.ShowAsync(cancellationToken);

                // AsyncOperation reports progress only by polling.
                while (operation.progress < LoadedProgress)
                {
                    progress?.Report(operation.progress / LoadedProgress);
                    await UniTask.Yield(PlayerLoopTiming.Update, cancellationToken);
                }

                progress?.Report(1f);
                operation.allowSceneActivation = true;
                await operation.ToUniTask();
            }
            finally
            {
                // A load held before activation would block every later load, so it always completes.
                operation.allowSceneActivation = true;
                await _transition.HideAsync(CancellationToken.None);
            }
        }

        private static AsyncOperation StartLoading(string scenePath)
        {
            AsyncOperation operation;
#if UNITY_EDITOR
            // In the Editor, a scene outside the build list still loads, so any open scene can be played.
            if (SceneUtility.GetBuildIndexByScenePath(scenePath) < 0)
            {
                operation = UnityEditor.SceneManagement.EditorSceneManager.LoadSceneAsyncInPlayMode(scenePath, new LoadSceneParameters(LoadSceneMode.Single));
                return operation ?? throw new ArgumentException($"No scene at '{scenePath}'.", nameof(scenePath));
            }
#endif
            operation = SceneManager.LoadSceneAsync(scenePath, LoadSceneMode.Single);
            return operation ?? throw new ArgumentException($"Scene '{scenePath}' isn't in the active Build Profile's scene list.", nameof(scenePath));
        }
    }
}
