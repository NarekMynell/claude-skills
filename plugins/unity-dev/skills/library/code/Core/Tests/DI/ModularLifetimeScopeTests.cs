using System;
using System.Collections.Generic;
using Company.Product.Core.DI;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using VContainer;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.DI
{
    public sealed class ModularLifetimeScopeTests
    {
        // Nested so that it has no MonoScript: Unity refuses to add components whose script lives in an Editor assembly.
        private sealed class RecordingInstaller : ScopeInstaller
        {
            public List<string> Order { get; set; }

            public override void Install(IContainerBuilder builder)
            {
                Order.Add(name);
                if (Order.Count == 1) builder.RegisterInstance(Order);
            }
        }

        private readonly List<GameObject> _created = new List<GameObject>();
        private readonly List<ModularLifetimeScope> _scopes = new List<ModularLifetimeScope>();

        [TearDown]
        public void TearDown()
        {
            // LifetimeScope.Dispose also destroys its GameObject, which only Play Mode allows.
            foreach (var scope in _scopes) scope.Container?.Dispose();
            foreach (var gameObject in _created) Object.DestroyImmediate(gameObject);
            _scopes.Clear();
            _created.Clear();
        }

        [Test]
        public void Build_RunsTheListedInstallersInOrder()
        {
            var order = new List<string>();
            var scope = CreateScope(CreateInstaller("first", order), CreateInstaller("second", order));

            scope.Build();

            Assert.That(order, Is.EqualTo(new[] { "first", "second" }));
            Assert.That(scope.Container.Resolve<List<string>>(), Is.SameAs(order));
        }

        [Test]
        public void Build_WithAnEmptySlot_ThrowsAndNamesTheScope()
        {
            var scope = CreateScope(new ScopeInstaller[] { null });

            var exception = Assert.Throws<InvalidOperationException>(() => scope.Build());
            Assert.That(exception.Message, Does.Contain(scope.name));
        }

        [Test]
        public void GlobalResolver_IsClearedOnlyByItsOwnContainer()
        {
            var first = new ContainerBuilder().Build();
            var second = new ContainerBuilder().Build();
            try
            {
                GlobalResolver.Set(first);
                Assert.Throws<InvalidOperationException>(() => GlobalResolver.Set(second));

                GlobalResolver.Clear(second);
                Assert.That(GlobalResolver.Resolver, Is.SameAs(first));

                GlobalResolver.Clear(first);
                Assert.That(GlobalResolver.IsAvailable, Is.False);
            }
            finally
            {
                GlobalResolver.Clear(first);
                first.Dispose();
                second.Dispose();
            }
        }

        private ModularLifetimeScope CreateScope(params ScopeInstaller[] installers)
        {
            var gameObject = new GameObject("TestScope");
            gameObject.SetActive(false);
            _created.Add(gameObject);
            var scope = gameObject.AddComponent<ModularLifetimeScope>();
            var serialized = new SerializedObject(scope);
            var list = serialized.FindProperty("_installers");
            list.arraySize = installers.Length;
            for (var i = 0; i < installers.Length; i++) list.GetArrayElementAtIndex(i).objectReferenceValue = installers[i];
            serialized.ApplyModifiedPropertiesWithoutUndo();
            _scopes.Add(scope);
            return scope;
        }

        private RecordingInstaller CreateInstaller(string name, List<string> order)
        {
            var gameObject = new GameObject(name);
            _created.Add(gameObject);
            var installer = gameObject.AddComponent<RecordingInstaller>();
            installer.Order = order;
            return installer;
        }
    }
}
