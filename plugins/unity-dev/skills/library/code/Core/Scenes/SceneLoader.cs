using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Company.Product.Core.Scenes
{
    // Shows the transition, loads the scene, then hides the transition, which is hidden however the load ends.
    // The load starts only once the transition covers the screen, and the scene activates as soon as it has loaded:
    // holding activation back would stall every other AsyncOperation, including asset loads a transition waits for.
    // Cancellation stops the load only before it starts.
    public sealed class SceneLoader : ISceneLoader
    {
        private const float LoadedProgress = 0.9f;

        private readonly ISceneTransition _transition;
        private bool _isLoading;

        public SceneLoader(ISceneTransition transition) => _transition = transition ?? throw new ArgumentNullException(nameof(transition));

        public async UniTask LoadAsync(string scenePath, IProgress<float> progress, CancellationToken cancellationToken)
        {
            Validate(scenePath);
            if (_isLoading) throw new InvalidOperationException($"Can't load '{scenePath}': another scene is still loading.");

            _isLoading = true;
            try
            {
                await _transition.ShowAsync(cancellationToken);
                cancellationToken.ThrowIfCancellationRequested();

                // From here the load can't be stopped. It finishes, and LoadAsync returns normally, also when the
                // new scene destroys the caller's scope and cancels its token.
                var operation = StartLoading(scenePath);
                while (!operation.isDone)
                {
                    progress?.Report(Mathf.Clamp01(operation.progress / LoadedProgress));
                    await UniTask.Yield(PlayerLoopTiming.Update);
                }

                progress?.Report(1f);
            }
            finally
            {
                _isLoading = false;
                await _transition.HideAsync(CancellationToken.None);
            }
        }

        private static void Validate(string scenePath)
        {
            if (string.IsNullOrEmpty(scenePath)) throw new ArgumentException("A scene path is required.", nameof(scenePath));
            if (SceneUtility.GetBuildIndexByScenePath(scenePath) >= 0) return;

#if UNITY_EDITOR
            // In the Editor, a scene outside the build list still loads, so any open scene can be played.
            if (UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEditor.SceneAsset>(scenePath) != null) return;

            throw new ArgumentException($"No scene at '{scenePath}'.", nameof(scenePath));
#else
            throw new ArgumentException($"Scene '{scenePath}' isn't in the active Build Profile's scene list.", nameof(scenePath));
#endif
        }

        private static AsyncOperation StartLoading(string scenePath)
        {
#if UNITY_EDITOR
            if (SceneUtility.GetBuildIndexByScenePath(scenePath) < 0)
                return UnityEditor.SceneManagement.EditorSceneManager.LoadSceneAsyncInPlayMode(scenePath, new LoadSceneParameters(LoadSceneMode.Single));
#endif
            return SceneManager.LoadSceneAsync(scenePath, LoadSceneMode.Single);
        }
    }
}
