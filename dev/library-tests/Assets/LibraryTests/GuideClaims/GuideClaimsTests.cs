using System;
using System.Collections;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Threading;
using Cysharp.Threading.Tasks;
using MessagePipe;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using VContainer;
using VContainer.Unity;
using Object = UnityEngine.Object;

namespace LibraryTests.GuideClaims
{
    // What the code standards claim about VContainer, MessagePipe, UniTask and Unity, checked at runtime.
    // A failure after a package or Unity upgrade means a guide is out of date: fix the guide, not the test.
    public sealed class GuideClaimsTests
    {
        private static readonly List<string> Log = new List<string>();

        private sealed class First : IDisposable { public void Dispose() => Log.Add("first"); }

        private sealed class Second : IDisposable { public void Dispose() => Log.Add("second"); }

        private sealed class MadeByDelegate : IDisposable { public void Dispose() => Log.Add("delegate"); }

        private sealed class Instance : IDisposable { public void Dispose() => Log.Add("instance"); }

        private sealed class Transient : IDisposable { public void Dispose() => Log.Add("transient"); }

        private sealed class Thrower : IDisposable { public void Dispose() => throw new InvalidOperationException("Dispose failed."); }

        private sealed class Ticker : ITickable, IDisposable
        {
            public void Tick() { }

            public void Dispose() => Log.Add("entry point");
        }

        private sealed class Dependency { }

        private sealed class Probe : MonoBehaviour
        {
            [Inject]
            public void Construct(Dependency dependency) => Log.Add("construct");

            private void Awake() => Log.Add("awake");

            private void OnDestroy() => Log.Add("destroy");
        }

        private sealed class Plain : MonoBehaviour { }

        private sealed class WaitsForCancellation : IAsyncStartable
        {
            public async UniTask StartAsync(CancellationToken cancellation) =>
                await UniTask.Delay(TimeSpan.FromSeconds(30), cancellationToken: cancellation);
        }

        private sealed class Fails : IAsyncStartable
        {
            public async UniTask StartAsync(CancellationToken cancellation)
            {
                await UniTask.Yield();
                throw new InvalidOperationException("Startup failed.");
            }
        }

        [SetUp]
        public void SetUp() => Log.Clear();

        // resource-lifetimes.md, Ownership.
        [Test]
        public void Container_DisposesWhatItCreated_NewestFirst_NeverInstancesOrTransients()
        {
            var builder = new ContainerBuilder();
            builder.Register<First>(Lifetime.Singleton);
            builder.Register<Second>(Lifetime.Singleton);
            builder.Register(_ => new MadeByDelegate(), Lifetime.Singleton);
            builder.RegisterInstance(new Instance());
            builder.Register<Transient>(Lifetime.Transient);
            var container = builder.Build();
            container.Resolve<First>();
            container.Resolve<Second>();
            container.Resolve<Instance>();
            container.Resolve<Transient>();
            container.Resolve<MadeByDelegate>();

            container.Dispose();

            Assert.That(Log, Is.EqualTo(new[] { "delegate", "second", "first" }));
        }

        // resource-lifetimes.md, Ownership: entry points included.
        [UnityTest]
        public IEnumerator EntryPoint_IsDisposedWithItsScope()
        {
            var scope = LifetimeScope.Create(builder => builder.RegisterEntryPoint<Ticker>());
            yield return null;

            scope.Dispose();

            Assert.That(Log, Is.EqualTo(new[] { "entry point" }));
        }

        // resource-lifetimes.md, Implementing IDisposable.
        [Test]
        public void ThrowingDispose_SkipsTheRestOfTheScope()
        {
            var builder = new ContainerBuilder();
            builder.Register<First>(Lifetime.Singleton);
            builder.Register<Thrower>(Lifetime.Singleton);
            builder.Register<Second>(Lifetime.Singleton);
            var container = builder.Build();
            container.Resolve<First>();
            container.Resolve<Thrower>();
            container.Resolve<Second>();

            Assert.Throws<InvalidOperationException>(() => container.Dispose());
            Assert.That(Log, Is.EqualTo(new[] { "second" }));
        }

        // resource-lifetimes.md, Where to release: Construct runs before Awake, also on objects that never become
        // active, and OnDestroy runs only on objects that were active.
        [UnityTest]
        public IEnumerator Instantiate_InjectsBeforeAwake_AndIntoObjectsThatNeverBecomeActive()
        {
            var builder = new ContainerBuilder();
            builder.Register<Dependency>(Lifetime.Singleton);
            var container = builder.Build();
            var prefab = new GameObject("ProbePrefab");
            prefab.SetActive(false);
            var probe = prefab.AddComponent<Probe>();
            var inactiveParent = new GameObject("InactiveParent");
            inactiveParent.SetActive(false);

            var inactive = container.Instantiate(probe, inactiveParent.transform);
            Assert.That(Log, Is.EqualTo(new[] { "construct" }));
            Object.Destroy(inactive.gameObject);
            yield return null;
            Assert.That(Log, Is.EqualTo(new[] { "construct" }), "OnDestroy ran on an object that was never active.");

            prefab.SetActive(true);
            Log.Clear();
            var active = container.Instantiate(probe);
            Assert.That(Log, Is.EqualTo(new[] { "construct", "awake" }));
            Object.Destroy(active.gameObject);
            yield return null;
            Assert.That(Log, Is.EqualTo(new[] { "construct", "awake", "destroy" }));

            Object.Destroy(prefab);
            Object.Destroy(inactiveParent);
            container.Dispose();
        }

        // dependency-injection.md, MessagePipe registration: open generics, no registration per message type.
        [Test]
        public void MessagePipe_ResolvesAnyMessageType_WithoutRegistration()
        {
            var builder = new ContainerBuilder();
            builder.RegisterMessagePipe();
            var container = builder.Build();
            var received = new List<int>();

            using (container.Resolve<ISubscriber<int>>().Subscribe(received.Add))
                container.Resolve<IPublisher<int>>().Publish(5);

            Assert.That(received, Is.EqualTo(new[] { 5 }));
            container.Dispose();
        }

        // resource-lifetimes.md, Subscriptions.
        [Test]
        public void MessagePipe_ThrowingHandler_StopsTheHandlersAfterIt_AndReachesThePublisher()
        {
            var builder = new ContainerBuilder();
            builder.RegisterMessagePipe();
            var container = builder.Build();
            var received = new List<int>();
            var subscriber = container.Resolve<ISubscriber<int>>();
            var bag = DisposableBag.CreateBuilder();
            subscriber.Subscribe(_ => throw new InvalidOperationException("Handler failed.")).AddTo(bag);
            subscriber.Subscribe(received.Add).AddTo(bag);
            var subscriptions = bag.Build();

            Assert.Throws<InvalidOperationException>(() => container.Resolve<IPublisher<int>>().Publish(1));
            Assert.That(received, Is.Empty);

            subscriptions.Dispose();
            container.Dispose();
        }

        // dependency-injection.md, MessagePipe registration: one broker per message type, in the root.
        [Test]
        public void MessagePipe_SecondRegistrationInAChildScope_SplitsTheChannel()
        {
            var builder = new ContainerBuilder();
            builder.RegisterMessagePipe();
            var root = builder.Build();
            var received = new List<int>();
            var subscription = root.Resolve<ISubscriber<int>>().Subscribe(received.Add);

            using (var child = root.CreateScope(_ => { }))
                child.Resolve<IPublisher<int>>().Publish(1);
            using (var childWithItsOwn = root.CreateScope(child => child.RegisterMessagePipe()))
                childWithItsOwn.Resolve<IPublisher<int>>().Publish(2);

            Assert.That(received, Is.EqualTo(new[] { 1 }));
            subscription.Dispose();
            root.Dispose();
        }

        // dependency-injection.md and resource-lifetimes.md, Finding leaks.
        [Test]
        public void MessagePipe_GlobalProviderFromABuildCallback_AndSubscribeCount()
        {
            var builder = new ContainerBuilder();
            builder.RegisterMessagePipe();
            builder.RegisterBuildCallback(c => GlobalMessagePipe.SetProvider(c.AsServiceProvider()));
            var container = builder.Build();
            var diagnostics = container.Resolve<MessagePipeDiagnosticsInfo>();
            var received = new List<int>();
            var before = diagnostics.SubscribeCount;

            var bag = DisposableBag.CreateBuilder();
            container.Resolve<ISubscriber<int>>().Subscribe(received.Add).AddTo(bag);
            var subscriptions = bag.Build();
            Assert.That(diagnostics.SubscribeCount, Is.EqualTo(before + 1));
            GlobalMessagePipe.GetPublisher<int>().Publish(7);
            subscriptions.Dispose();

            Assert.That(received, Is.EqualTo(new[] { 7 }));
            Assert.That(diagnostics.SubscribeCount, Is.EqualTo(before));
            container.Dispose();
        }

        // resource-lifetimes.md, Async and cancellation: a LifetimeScope always has an entry point exception
        // handler, Debug.LogException unless one is registered, and it receives cancellations too.
        [UnityTest]
        public IEnumerator AsyncStartable_CancelledByItsScope_IsLoggedByTheDefaultHandler()
        {
            LogAssert.Expect(LogType.Exception, new Regex("OperationCanceledException"));
            var scope = LifetimeScope.Create(builder => builder.RegisterEntryPoint<WaitsForCancellation>());
            for (var i = 0; i < 3; i++) yield return null;

            scope.Dispose();
            for (var i = 0; i < 3; i++) yield return null;
        }

        [UnityTest]
        public IEnumerator AsyncStartable_CancelledByItsScope_ReachesARegisteredHandler()
        {
            var received = new List<Exception>();
            var scope = LifetimeScope.Create(builder =>
            {
                builder.RegisterEntryPoint<WaitsForCancellation>();
                builder.RegisterEntryPointExceptionHandler(received.Add);
            });
            for (var i = 0; i < 3; i++) yield return null;

            scope.Dispose();
            for (var i = 0; i < 3; i++) yield return null;

            Assert.That(received, Has.Exactly(1).InstanceOf<OperationCanceledException>());
        }

        [UnityTest]
        public IEnumerator AsyncStartable_Failure_IsLoggedByTheDefaultHandler()
        {
            LogAssert.Expect(LogType.Exception, new Regex("Startup failed"));
            var scope = LifetimeScope.Create(builder => builder.RegisterEntryPoint<Fails>());
            for (var i = 0; i < 5; i++) yield return null;

            scope.Dispose();
        }

        // resource-lifetimes.md, Where to release: destroyCancellationToken is read while the object is alive.
        [UnityTest]
        public IEnumerator DestroyCancellationToken_CannotBeReadAfterDestroy()
        {
            var component = new GameObject("Plain").AddComponent<Plain>();
            var token = component.destroyCancellationToken;

            Object.Destroy(component.gameObject);
            yield return null;

            Assert.That(token.IsCancellationRequested, Is.True);
            Assert.Throws<MissingReferenceException>(() => _ = component.destroyCancellationToken);
        }
    }
}
