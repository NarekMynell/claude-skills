using System;
using System.Reflection;
using Company.Product.Core.Culling;
using Company.Product.Core.Lifecycle;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Culling
{
    public sealed class VisibilityPauserCallbackTests
    {
        private sealed class Target : IPausable
        {
            public bool IsPaused { get; private set; }

            public void Pause() => IsPaused = true;

            public void Resume() => IsPaused = false;
        }

        private sealed class ThrowingOnResume : IPausable
        {
            public void Pause() { }

            public void Resume() => throw new InvalidOperationException("Resume failed.");
        }

        private Camera _camera;

        [SetUp]
        public void SetUp()
        {
            _camera = new GameObject("Camera").AddComponent<Camera>();
            _camera.transform.position = new Vector3(0f, 0f, -10f);
        }

        [TearDown]
        public void TearDown() => Object.DestroyImmediate(_camera.gameObject);

        // Resource-lifetime rules: Dispose never throws and releases everything. README: "Dispose resume[s] a paused
        // target, so nothing stays paused for good."
        [Test]
        public void Dispose_WithATargetWhoseResumeThrows_StillReleasesTheGroup_AndResumesTheOthers()
        {
            LogAssert.ignoreFailingMessages = true;
            var pauser = new VisibilityPauser(_camera);
            var other = new Target();
            pauser.Register(new ThrowingOnResume(), Vector3.zero, 1f);
            pauser.Register(other, Vector3.zero, 1f);
            Assert.That(other.IsPaused, Is.True, "Targets start paused until the first culling pass.");

            Exception thrown = null;
            try
            {
                pauser.Dispose();
            }
            catch (Exception exception)
            {
                thrown = exception;
            }

            var group = (CullingGroup)typeof(VisibilityPauser).GetField("_group", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(pauser);
            var groupPointer = (IntPtr)typeof(CullingGroup).GetField("m_Ptr", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(group);
            var groupDisposed = groupPointer == IntPtr.Zero;
            if (!groupDisposed) group.Dispose();

            var failures = new System.Collections.Generic.List<string>();
            if (thrown != null) failures.Add("Dispose threw " + thrown.GetType().Name + ".");
            if (!groupDisposed) failures.Add("The CullingGroup was not disposed.");
            if (other.IsPaused) failures.Add("The other target stays paused for good.");
            Assert.That(failures, Is.Empty);
        }

        // Control: a culling pass reports both targets visible and resumes them.
        [Test]
        public void CullingPass_ResumesVisibleTargets()
        {
            var pauser = new VisibilityPauser(_camera);
            var first = new Target();
            var second = new Target();
            pauser.Register(first, Vector3.zero, 1f);
            pauser.Register(second, Vector3.zero, 1f);

            _camera.Render();

            Assert.That(first.IsPaused || second.IsPaused, Is.False);
            pauser.Dispose();
        }

        // CullingGroup.SendEvents loops over the pass's events without a try/catch, so a throwing target drops the
        // events of every target after it in that pass, and those targets only get another event when their
        // visibility changes again.
        [Test]
        public void CullingPass_WithATargetWhoseResumeThrows_StillResumesTheOtherVisibleTargets()
        {
            LogAssert.ignoreFailingMessages = true;
            var pauser = new VisibilityPauser(_camera);
            var other = new Target();
            pauser.Register(new ThrowingOnResume(), Vector3.zero, 1f);
            pauser.Register(other, Vector3.zero, 1f);

            _camera.Render();
            _camera.Render();

            var otherPaused = other.IsPaused;
            try
            {
                pauser.Dispose();
            }
            catch (InvalidOperationException)
            {
            }

            DisposeGroup(pauser);
            Assert.That(otherPaused, Is.False, "A visible target stays paused because another target's Resume threw.");
        }

        private static void DisposeGroup(VisibilityPauser pauser)
        {
            var group = (CullingGroup)typeof(VisibilityPauser).GetField("_group", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(pauser);
            var pointer = (IntPtr)typeof(CullingGroup).GetField("m_Ptr", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(group);
            if (pointer != IntPtr.Zero) group.Dispose();
        }
    }
}
