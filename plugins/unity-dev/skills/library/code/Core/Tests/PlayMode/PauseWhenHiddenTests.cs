using System.Collections;
using NUnit.Framework;
using ProjectName.Core.Culling;
using ProjectName.Core.Lifecycle;
using UnityEngine;
using UnityEngine.TestTools;
using VContainer;
using VContainer.Unity;
using Object = UnityEngine.Object;

namespace ProjectName.Core.PlayModeTests
{
    // The whole path from the guide: a pauser in a real scope, a real camera, an object injected with it.
    public sealed class PauseWhenHiddenTests
    {
        private sealed class Sway : MonoBehaviour, IPausable
        {
            public bool IsPaused { get; private set; }

            public void Pause() => IsPaused = true;

            public void Resume() => IsPaused = false;
        }

        private sealed class Scope : LifetimeScope
        {
            public static Camera Camera;

            protected override void Configure(IContainerBuilder builder) => builder.RegisterVisibilityPauser(Camera);
        }

        private Camera _camera;
        private GameObject _scopeObject;
        private GameObject _tree;

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            _camera = new GameObject("Camera", typeof(Camera)).GetComponent<Camera>();
            _camera.transform.position = new Vector3(0f, 0f, -10f);
            Scope.Camera = _camera;
            _scopeObject = new GameObject("Scope");
            _scopeObject.AddComponent<Scope>();
            yield return null;

            _tree = new GameObject("Tree");
            _tree.SetActive(false);
            _tree.AddComponent<Sway>();
            var hidden = _tree.AddComponent<PauseWhenHidden>();
            _scopeObject.GetComponent<Scope>().Container.Inject(hidden);
            _tree.SetActive(true);
            yield return null;
            yield return null;
        }

        [UnityTearDown]
        public IEnumerator TearDown()
        {
            Object.Destroy(_tree);
            Object.Destroy(_scopeObject);
            Object.Destroy(_camera.gameObject);
            Scope.Camera = null;
            yield return null;
        }

        private Sway Target => _tree.GetComponent<Sway>();

        // CullingGroup answers when a camera culls.
        private IEnumerator Culled()
        {
            _camera.Render();
            yield return null;
            _camera.Render();
            yield return null;
        }

        [UnityTest]
        public IEnumerator InView_ItRuns_OutOfView_ItPauses_BackInView_ItRuns()
        {
            yield return Culled();
            Assert.That(Target.IsPaused, Is.False, "in front of the camera");

            _camera.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
            yield return Culled();
            Assert.That(Target.IsPaused, Is.True, "behind the camera");

            _camera.transform.rotation = Quaternion.identity;
            yield return Culled();
            Assert.That(Target.IsPaused, Is.False, "back in view");
        }

        [UnityTest]
        public IEnumerator DisablingAHiddenObject_ResumesIt_SoNothingStaysPausedForGood()
        {
            _camera.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
            yield return Culled();
            Assert.That(Target.IsPaused, Is.True);

            _tree.SetActive(false);

            Assert.That(Target.IsPaused, Is.False);
        }

        [UnityTest]
        public IEnumerator DisposingTheScope_DisposesThePauser_AndDestroyingTheObjectAfterItIsSafe()
        {
            yield return Culled();
            Object.Destroy(_scopeObject);
            yield return null;

            LogAssert.NoUnexpectedReceived();
        }
    }
}
