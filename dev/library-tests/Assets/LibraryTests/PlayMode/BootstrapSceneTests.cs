using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.Bootstrap;
using Company.Product.Core.Providers;
using Company.Product.Core.Scenes;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace LibraryTests.PlayMode
{
    // The startup's last step replaces the scenes, including the one that runs the startup.
    public sealed class BootstrapSceneTests
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

        [UnityTest]
        public IEnumerator CancellationAfterTheLoadStarted_StillActivatesTheScene_AndHidesTheTransition() => UniTask.ToCoroutine(async () =>
        {
            var transition = new RecordingTransition();
            var cancellation = new CancellationTokenSource();
            var load = new SceneLoader(transition).LoadAsync(ScenePath, null, cancellation.Token);
            cancellation.Cancel();

            await load;

            Assert.That(transition.Log, Is.EqualTo(new[] { "show", "hide" }));
            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo("SceneLoaderTarget"));
            cancellation.Dispose();
        });

        [UnityTest]
        public IEnumerator CancellationBeforeTheLoad_LoadsNothing_AndHidesTheTransition() => UniTask.ToCoroutine(async () =>
        {
            var transition = new RecordingTransition();
            var sceneBefore = SceneManager.GetActiveScene().name;

            var cancelled = false;
            try
            {
                await new SceneLoader(transition).LoadAsync(ScenePath, null, new CancellationToken(true));
            }
            catch (OperationCanceledException)
            {
                cancelled = true;
            }

            Assert.That(cancelled, Is.True);
            Assert.That(transition.Log, Is.EqualTo(new[] { "show", "hide" }));
            Assert.That(SceneManager.GetActiveScene().name, Is.EqualTo(sceneBefore));
        });

        [UnityTest]
        public IEnumerator StartupWhoseSceneIsReplaced_StillCompletes_AndHidesTheTransition() => UniTask.ToCoroutine(async () =>
        {
            var transition = new RecordingTransition();
            var firstScene = ScriptableObject.CreateInstance<FirstSceneConfig>();
            JsonUtility.FromJsonOverwrite($"{{\"_firstScene\":{{\"_scenePath\":\"{ScenePath}\"}}}}", firstScene);
            var progress = new Provider<BootstrapProgress>();
            var steps = new IBootstrapStep[] { new LoadFirstSceneStep(new SceneLoader(transition), firstScene) };

            // Owned by an object in the scene that the load replaces, as a Bootstrap scene's scope would be.
            var owner = new GameObject("BootstrapScope");
            var cancellation = CancellationTokenSource.CreateLinkedTokenSource(owner.GetCancellationTokenOnDestroy());
            await new BootstrapFlow(steps, progress).StartAsync(cancellation.Token);

            Assert.That(owner == null, Is.True, "The scene load destroyed the startup's owner.");
            Assert.That(progress.Value.Status, Is.EqualTo(BootstrapStatus.Completed));
            Assert.That(transition.Log, Is.EqualTo(new[] { "show", "hide" }));
            Object.Destroy(firstScene);
        });
    }
}
