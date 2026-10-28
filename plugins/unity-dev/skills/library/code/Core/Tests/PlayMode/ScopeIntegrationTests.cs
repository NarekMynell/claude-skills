using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.Bootstrap;
using Company.Product.Core.DI;
using Company.Product.Core.Pooling;
using Company.Product.Core.Providers;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using VContainer;
using VContainer.Unity;
using Object = UnityEngine.Object;

namespace Company.Product.Core.PlayModeTests
{
    // Runs the DI building blocks inside real VContainer scopes, the way a project uses them.
    public sealed class ScopeIntegrationTests
    {
        private sealed class Greeting
        {
            public string Text => "hello";
        }

        private sealed class Greeter : MonoBehaviour, IPoolable
        {
            public Greeting Greeting { get; private set; }

            [Inject]
            public void Construct(Greeting greeting) => Greeting = greeting;

            public void OnSpawned() { }

            public void OnDespawned() { }
        }

        private sealed class CountingStep : IBootstrapStep
        {
            private readonly List<string> _log;

            public CountingStep(List<string> log) => _log = log;

            public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken)
            {
                _log.Add("step");
                return UniTask.CompletedTask;
            }
        }

        private sealed class TestInstaller : ScopeInstaller
        {
            public Action<IContainerBuilder> Registrations { get; set; }

            public override void Install(IContainerBuilder builder) => Registrations(builder);
        }

        private readonly List<Object> _created = new List<Object>();

        [TearDown]
        public void TearDown()
        {
            foreach (var created in _created)
                if (created != null) Object.Destroy(created);

            _created.Clear();
        }

        [UnityTest]
        public IEnumerator ExposedScope_SetsTheGlobalResolver_AndClearsItWhenDestroyed()
        {
            var scope = CreateScope(builder => builder.Register<Greeting>(Lifetime.Singleton), exposeAsGlobal: true);
            yield return null;

            Assert.That(GlobalResolver.IsAvailable, Is.True);
            Assert.That(GlobalResolver.Resolver.Resolve<Greeting>().Text, Is.EqualTo("hello"));

            Object.Destroy(scope.gameObject);
            yield return null;
            Assert.That(GlobalResolver.IsAvailable, Is.False);
        }

        [UnityTest]
        public IEnumerator DisposedScope_AlsoClearsTheGlobalResolver()
        {
            var scope = CreateScope(builder => builder.Register<Greeting>(Lifetime.Singleton), exposeAsGlobal: true);
            yield return null;
            Assert.That(GlobalResolver.IsAvailable, Is.True);

            scope.Dispose();
            yield return null;

            Assert.That(GlobalResolver.IsAvailable, Is.False);
            var next = CreateScope(builder => builder.Register<Greeting>(Lifetime.Singleton), exposeAsGlobal: true);
            yield return null;
            Assert.That(GlobalResolver.Resolver, Is.SameAs(next.Container));
            next.Dispose();
        }

        [UnityTest]
        public IEnumerator SpawnWithoutParent_JoinsTheActiveScene_EvenFromAPersistentContainer()
        {
            var prefab = new GameObject("GreeterPrefab").AddComponent<Greeter>();
            prefab.gameObject.SetActive(false);
            _created.Add(prefab.gameObject);
            var container = new GameObject("PersistentPools");
            Object.DontDestroyOnLoad(container);
            _created.Add(container);
            var scope = CreateScope(builder => builder.Register<Greeting>(Lifetime.Singleton));
            yield return null;

            var registry = new PrefabPoolRegistry(scope.Container, container.transform);
            var greeter = registry.Register(prefab, 1).Spawn();

            Assert.That(greeter.gameObject.scene, Is.EqualTo(UnityEngine.SceneManagement.SceneManager.GetActiveScene()));
            _created.Add(greeter.gameObject);
            registry.Dispose();
        }

        [UnityTest]
        public IEnumerator BootstrapFlow_RunsAsAnEntryPoint_AndCompletes()
        {
            var log = new List<string>();
            var scope = CreateScope(builder =>
            {
                builder.RegisterInstance(log);
                builder.Register<IBootstrapStep, CountingStep>(Lifetime.Singleton);
                builder.RegisterBootstrapFlow();
            });

            var progress = scope.Container.Resolve<IProvider<BootstrapProgress>>();
            for (var frame = 0; frame < 10 && progress.Value.Status != BootstrapStatus.Completed; frame++) yield return null;

            Assert.That(progress.Value.Status, Is.EqualTo(BootstrapStatus.Completed));
            Assert.That(log, Is.EqualTo(new[] { "step" }));
            Assert.That(scope.Container.Resolve<IProviderSetter<BootstrapProgress>>(), Is.SameAs(progress));
        }

        [UnityTest]
        public IEnumerator PrefabPool_InstancesReceiveInjection()
        {
            var prefab = new GameObject("GreeterPrefab").AddComponent<Greeter>();
            prefab.gameObject.SetActive(false);
            _created.Add(prefab.gameObject);
            var container = new GameObject("Pools");
            _created.Add(container);
            var scope = CreateScope(builder => builder.Register<Greeting>(Lifetime.Singleton));
            yield return null;

            var registry = new PrefabPoolRegistry(scope.Container, container.transform);
            var pool = registry.Register(prefab, 2);
            var greeter = pool.Spawn();

            Assert.That(greeter.Greeting, Is.Not.Null);
            Assert.That(pool.CountInactive, Is.EqualTo(1));
            Assert.That(registry.Get(prefab), Is.SameAs(pool));
            var stranger = new GameObject("Unregistered").AddComponent<Greeter>();
            _created.Add(stranger.gameObject);
            Assert.Throws<InvalidOperationException>(() => registry.Get(stranger));

            pool.Despawn(greeter);
            registry.Dispose();
        }

        private ModularLifetimeScope CreateScope(Action<IContainerBuilder> registrations, bool exposeAsGlobal = false)
        {
            var installerObject = new GameObject("Installer");
            _created.Add(installerObject);
            var installer = installerObject.AddComponent<TestInstaller>();
            installer.Registrations = registrations;

            // Inactive until configured, so Awake builds the container with the installer in place.
            var scopeObject = new GameObject("Scope");
            scopeObject.SetActive(false);
            _created.Add(scopeObject);
            var scope = scopeObject.AddComponent<ModularLifetimeScope>();
            scope.SetInstallersForTests(new ScopeInstaller[] { installer }, exposeAsGlobal);
            scopeObject.SetActive(true);
            return scope;
        }
    }
}
