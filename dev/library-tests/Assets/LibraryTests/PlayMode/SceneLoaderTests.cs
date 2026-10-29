using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.Scenes;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace LibraryTests.PlayMode
{
    // Lives in the test project because it needs a scene asset; the scene is outside the build list,
    // which also exercises the loader's Editor fallback (see TestSceneCreator).
    public sealed class SceneLoaderTests
    {
        private const string ScenePath = "Assets/LibraryTests/Scenes/SceneLoaderTarget.unity";

        private sealed class RecordingTransition : ISceneTransition
        {
            public readonly List<string> Log = new List<string>();

            public UniTask ShowAsync(CancellationToken cancellationToken)
            {
                Log.Add("show");
                return UniTask.CompletedTask;
            }

            public UniTask HideAsync(CancellationToken cancellationToken)
            {
                Log.Add("hide");
                return UniTask.CompletedTask;
            }
        }

        private sealed class RecordingProgress : IProgress<float>
        {
            public readonly List<float> Values = new List<float>();

            public void Report(float value) => Values.Add(value);
        }

        [UnityTest]
        public IEnumerator LoadAsync_OpensTheScene_InsideTheTransition() => UniTask.ToCoroutine(async () =>
        {
            var transition = new RecordingTransition();
            var progress = new RecordingProgress();

            await new SceneLoader(transition).LoadAsync(ScenePath, progress, CancellationToken.None);

            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo("SceneLoaderTarget"));
            Assert.That(GameObject.Find("Marker"), Is.Not.Null);
            Assert.That(transition.Log, Is.EqualTo(new[] { "show", "hide" }));
            Assert.That(progress.Values[progress.Values.Count - 1], Is.EqualTo(1f));
        });

        // A scene load held before activation stalls every AsyncOperation queued after it, so a transition that
        // waits for one would never finish.
        [UnityTest]
        public IEnumerator TransitionThatAwaitsAnAsyncOperation_DoesNotStallTheLoad() => UniTask.ToCoroutine(async () =>
        {
            var load = new SceneLoader(new UnloadingTransition()).LoadAsync(ScenePath, null, CancellationToken.None);

            var finished = await UniTask.WhenAny(load, UniTask.Delay(TimeSpan.FromSeconds(20), DelayType.Realtime));

            Assert.That(finished, Is.EqualTo(0), "The load didn't finish within 20 seconds.");
            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo("SceneLoaderTarget"));
        });

        [UnityTest]
        public IEnumerator SecondLoad_WhileOneIsRunning_IsRefused() => UniTask.ToCoroutine(async () =>
        {
            var loader = new SceneLoader(new RecordingTransition());
            var first = loader.LoadAsync(ScenePath, null, CancellationToken.None);

            Exception refused = null;
            try
            {
                await loader.LoadAsync(ScenePath, null, CancellationToken.None);
            }
            catch (InvalidOperationException exception)
            {
                refused = exception;
            }

            await first;
            Assert.That(refused, Is.Not.Null);
        });

        private sealed class UnloadingTransition : ISceneTransition
        {
            public async UniTask ShowAsync(CancellationToken cancellationToken) => await Resources.UnloadUnusedAssets().ToUniTask(cancellationToken: cancellationToken);

            public async UniTask HideAsync(CancellationToken cancellationToken) => await Resources.UnloadUnusedAssets().ToUniTask(cancellationToken: cancellationToken);
        }
    }
}
