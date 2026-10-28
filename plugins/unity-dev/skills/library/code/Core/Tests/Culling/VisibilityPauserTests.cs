using Company.Product.Core.Culling;
using Company.Product.Core.Lifecycle;
using NUnit.Framework;
using UnityEngine;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Culling
{
    public sealed class VisibilityPauserTests
    {
        private sealed class Target : IPausable
        {
            public bool IsPaused { get; private set; }

            public void Pause() => IsPaused = true;

            public void Resume() => IsPaused = false;
        }

        private sealed class PausableBehaviour : MonoBehaviour, IPausable
        {
            public void Pause() { }

            public void Resume() { }
        }

        private Camera _camera;
        private VisibilityPauser _pauser;

        [SetUp]
        public void SetUp()
        {
            _camera = new GameObject("Camera").AddComponent<Camera>();
            _pauser = new VisibilityPauser(_camera, capacity: 1);
        }

        [TearDown]
        public void TearDown()
        {
            _pauser.Dispose();
            Object.DestroyImmediate(_camera.gameObject);
        }

        [Test]
        public void VisibilityChanges_PauseAndResumeTheTarget()
        {
            var target = new Target();
            _pauser.Register(target, Vector3.zero, 1f);

            _pauser.HandleVisibilityChanged(0, true);
            Assert.That(target.IsPaused, Is.False);

            _pauser.HandleVisibilityChanged(0, false);
            Assert.That(target.IsPaused, Is.True);
        }

        [Test]
        public void UnregisterAndDispose_ResumePausedTargets()
        {
            var first = new Target();
            var second = new Target();
            _pauser.Register(first, Vector3.zero, 1f);
            _pauser.Register(second, Vector3.zero, 1f);
            Assert.That(first.IsPaused && second.IsPaused, Is.True, "Targets start paused until a culling pass sees them.");

            _pauser.Unregister(first);
            Assert.That(first.IsPaused, Is.False);

            _pauser.Dispose();
            Assert.That(second.IsPaused, Is.False);
            _pauser = new VisibilityPauser(_camera);
        }

        [Test]
        public void DestroyedTarget_IsSkipped()
        {
            var target = new GameObject("Destroyed").AddComponent<PausableBehaviour>();
            _pauser.Register(target, Vector3.zero, 1f);
            Object.DestroyImmediate(target.gameObject);

            Assert.DoesNotThrow(() => _pauser.HandleVisibilityChanged(0, true));
            Assert.DoesNotThrow(() => _pauser.Unregister(target));
        }

        [Test]
        public void Unregister_KeepsTheRemainingTargetsMappedToTheirSpheres()
        {
            var first = new Target();
            var second = new Target();
            var third = new Target();
            _pauser.Register(first, Vector3.zero, 1f);
            _pauser.Register(second, Vector3.zero, 1f);
            _pauser.Register(third, Vector3.zero, 1f);

            _pauser.Unregister(first);
            _pauser.HandleVisibilityChanged(0, true);
            _pauser.HandleVisibilityChanged(1, true);
            _pauser.HandleVisibilityChanged(0, false);

            Assert.That(_pauser.Count, Is.EqualTo(2));
            Assert.That(third.IsPaused, Is.True, "The last target moved into the freed slot 0.");
            Assert.That(second.IsPaused, Is.False);
        }
    }
}
