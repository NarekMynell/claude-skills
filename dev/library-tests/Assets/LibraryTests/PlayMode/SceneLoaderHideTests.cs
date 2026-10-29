using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.Scenes;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine.TestTools;

namespace LibraryTests.PlayMode
{
    public sealed class SceneLoaderHideTests
    {
        private const string ScenePath = "Assets/LibraryTests/Scenes/SceneLoaderTarget.unity";

        // Hides only when the test opens the gate, like a fade that takes a while.
        private sealed class SlowHideTransition : ISceneTransition
        {
            public readonly List<string> Log = new List<string>();
            public readonly UniTaskCompletionSource HideGate = new UniTaskCompletionSource();

            public UniTask ShowAsync(CancellationToken cancellationToken)
            {
                Log.Add("show");
                return UniTask.CompletedTask;
            }

            public async UniTask HideAsync(CancellationToken cancellationToken)
            {
                Log.Add("hide started");
                await HideGate.Task;
                Log.Add("hide finished");
            }
        }

        // README: "A second load while one runs throws InvalidOperationException." The first LoadAsync hasn't
        // returned yet: it is still hiding the transition.
        [UnityTest]
        public IEnumerator SecondLoad_WhileTheFirstIsStillHidingTheTransition_IsRefused() => UniTask.ToCoroutine(async () =>
        {
            var transition = new SlowHideTransition();
            var loader = new SceneLoader(transition);
            var first = loader.LoadAsync(ScenePath, null, CancellationToken.None);
            await UniTask.WaitUntil(() => transition.Log.Contains("hide started"));

            var second = loader.LoadAsync(ScenePath, null, CancellationToken.None);
            var secondStatus = second.Status;
            var log = string.Join(", ", transition.Log);

            transition.HideGate.TrySetResult();
            await first;
            try
            {
                await second;
            }
            catch (InvalidOperationException)
            {
            }

            Assert.That(secondStatus, Is.EqualTo(UniTaskStatus.Faulted), $"The second load was accepted. Transition calls: {log}");
        });
    }
}
