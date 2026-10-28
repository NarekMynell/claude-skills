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
    }
}
