using System.Linq;
using NUnit.Framework;
using ProjectName.Core.Editor.CostChecks;
using UnityEngine;

namespace ProjectName.Core.Tests.CostChecks
{
    public sealed class SceneCostAuditTests
    {
        private GameObject _root;

        private sealed class Mover : MonoBehaviour { }

        [SetUp]
        public void SetUp() => _root = new GameObject("Root");

        [TearDown]
        public void TearDown() => Object.DestroyImmediate(_root);

        private string[] Rules() => SceneCostAudit.Run(new[] { _root }, new CostAuditOptions()).Findings.Select(f => f.Rule).Distinct().ToArray();

        private GameObject Child(string name, params System.Type[] components)
        {
            var child = new GameObject(name, components);
            child.transform.SetParent(_root.transform);
            return child;
        }

        [Test]
        public void ARealtimeLightWithShadows_IsReported()
        {
            var light = Child("Sun", typeof(Light)).GetComponent<Light>();
            light.lightmapBakeType = LightmapBakeType.Realtime;
            light.shadows = LightShadows.Soft;

            var rules = Rules();

            Assert.That(rules, Does.Contain("runtime-light"));
            Assert.That(rules, Does.Contain("runtime-shadow"));
        }

        [Test]
        public void ABakedLight_IsFine()
        {
            var light = Child("Lamp", typeof(Light)).GetComponent<Light>();
            light.lightmapBakeType = LightmapBakeType.Baked;

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AnAnimatorThatAlwaysAnimates_IsReported()
        {
            Child("Hero", typeof(Animator)).GetComponent<Animator>().cullingMode = AnimatorCullingMode.AlwaysAnimate;

            Assert.That(Rules(), Does.Contain("animates-off-screen"));
        }

        [Test]
        public void ACulledAnimator_IsFine()
        {
            Child("Hero", typeof(Animator)).GetComponent<Animator>().cullingMode = AnimatorCullingMode.CullCompletely;

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void SkinningOffScreen_IsReported()
        {
            Child("Body", typeof(SkinnedMeshRenderer)).GetComponent<SkinnedMeshRenderer>().updateWhenOffscreen = true;

            Assert.That(Rules(), Does.Contain("skins-off-screen"));
        }

        [Test]
        public void ParticlesAlwaysSimulating_AreReported()
        {
            var main = Child("Smoke", typeof(ParticleSystem)).GetComponent<ParticleSystem>().main;
            main.cullingMode = ParticleSystemCullingMode.AlwaysSimulate;

            Assert.That(Rules(), Does.Contain("particles-off-screen"));
        }

        [Test]
        public void ARendererNothingMoves_CouldBeStatic()
        {
            Child("Rock", typeof(MeshFilter), typeof(MeshRenderer));

            Assert.That(Rules(), Does.Contain("could-be-static"));
        }

        [Test]
        public void AStaticRenderer_OneWithAScript_AndOneUnderAnAnimator_AreFine()
        {
            Child("Rock", typeof(MeshFilter), typeof(MeshRenderer)).isStatic = true;
            Child("Cart", typeof(Mover), typeof(MeshFilter), typeof(MeshRenderer));
            var animated = Child("Crane", typeof(Animator));
            animated.GetComponent<Animator>().cullingMode = AnimatorCullingMode.CullCompletely;
            var arm = new GameObject("Arm", typeof(MeshFilter), typeof(MeshRenderer));
            arm.transform.SetParent(animated.transform);

            Assert.That(Rules(), Does.Not.Contain("could-be-static"));
        }

        [Test]
        public void AScriptOnTheLevelRoot_DoesNotHideThePropsUnderIt()
        {
            _root.AddComponent<Mover>();
            Child("Rock", typeof(MeshFilter), typeof(MeshRenderer));

            Assert.That(Rules(), Does.Contain("could-be-static"));
        }

        [Test]
        public void AnException_MovesTheFindingToTheAcceptedList_WithItsReason()
        {
            Child("Rock", typeof(MeshFilter), typeof(MeshRenderer));

            var report = SceneCostAudit.Run(new[] { _root }, new CostAuditOptions().Allow("could-be-static", "Root/Rock", "Test reason."));

            Assert.That(report.IsClean, report.ToString());
            Assert.That(report.ToString(), Does.Contain("Test reason."));
        }

        [Test]
        public void TheMovementProbe_NamesWhatMoved()
        {
            var still = Child("Rock", typeof(MeshFilter), typeof(MeshRenderer));
            var moving = Child("Tree", typeof(MeshFilter), typeof(MeshRenderer));

            var probe = new ProjectName.Core.Culling.MovementProbe(new[] { _root });
            moving.transform.Rotate(0f, 0f, 3f);

            Assert.That(probe.Moved().Select(r => r.name), Is.EqualTo(new[] { "Tree" }));
            Assert.That(probe.Stayed().Select(r => r.name), Is.EqualTo(new[] { "Rock" }));
            Assert.That(still.activeSelf);
        }

        [Test]
        public void ManyExceptions_AreAFindingOfTheirOwn()
        {
            var options = new CostAuditOptions { MaxExceptions = 1 }.Allow("a", "b", "One.").Allow("c", "d", "Two.");

            Assert.That(SceneCostAudit.Run(new[] { _root }, options).IsClean, Is.False);
        }

        [Test]
        public void TheProbe_NamesWhatStayedStill_NotWhatMoved()
        {
            var still = Child("Rock", typeof(MeshFilter), typeof(MeshRenderer));
            still.AddComponent<Mover>();
            var moving = Child("Cart", typeof(Mover), typeof(MeshFilter), typeof(MeshRenderer));
            var marked = Child("Wall", typeof(MeshFilter), typeof(MeshRenderer));
            marked.isStatic = true;

            var probe = new NeverMovedProbe(new[] { _root });
            moving.transform.position += Vector3.up;

            Assert.That(probe.Report().Select(f => f.Subject), Is.EqualTo(new[] { "Rock" }));
        }
    }
}
