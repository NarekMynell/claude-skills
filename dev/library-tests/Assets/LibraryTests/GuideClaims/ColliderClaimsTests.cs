using NUnit.Framework;
using UnityEngine;

namespace LibraryTests.GuideClaims
{
    // What ColliderAudit claims about Unity's colliders, checked against physics queries.
    public sealed class ColliderClaimsTests
    {
        private static bool HitAt(float x)
        {
            Physics.SyncTransforms();
            return Physics.Raycast(new Vector3(x, 5f, 0f), Vector3.down, 10f);
        }

        private static GameObject Mirrored<T>(System.Action<T> setUp) where T : Collider
        {
            var mirrored = new GameObject("Mirrored");
            mirrored.transform.localScale = new Vector3(-1f, 1f, 1f);
            setUp(mirrored.AddComponent<T>());
            return mirrored;
        }

        [Test]
        public void AMirroredBoxFollowsTheMirror()
        {
            var mirrored = Mirrored<BoxCollider>(box => box.center = new Vector3(2f, 0f, 0f));
            try
            {
                Assert.That(HitAt(-2f), Is.True, "where the mirror puts it");
                Assert.That(HitAt(2f), Is.False, "where it would be without the mirror");
            }
            finally
            {
                Object.DestroyImmediate(mirrored);
            }
        }

        [Test]
        public void AMirroredCapsuleFollowsTheMirror()
        {
            var mirrored = Mirrored<CapsuleCollider>(capsule => capsule.center = new Vector3(2f, 0f, 0f));
            try
            {
                Assert.That(HitAt(-2f), Is.True, "where the mirror puts it");
                Assert.That(HitAt(2f), Is.False, "where it would be without the mirror");
            }
            finally
            {
                Object.DestroyImmediate(mirrored);
            }
        }

        [Test]
        public void AMirroredSphereFollowsTheMirror()
        {
            var mirrored = Mirrored<SphereCollider>(sphere => sphere.center = new Vector3(2f, 0f, 0f));
            try
            {
                Assert.That(HitAt(-2f), Is.True, "where the mirror puts it");
                Assert.That(HitAt(2f), Is.False, "where it would be without the mirror");
            }
            finally
            {
                Object.DestroyImmediate(mirrored);
            }
        }

        [Test]
        public void ACapsulesRadiusScalesByTheLargerOfTheOtherTwoAxes()
        {
            var log = new GameObject("Log");
            log.transform.localScale = new Vector3(0.3f, 3f, 0.3f);
            var capsule = log.AddComponent<CapsuleCollider>();
            capsule.radius = 0.5f;
            capsule.height = 1f;
            try
            {
                Assert.That(HitAt(0.1f), Is.True);
                Assert.That(HitAt(0.2f), Is.False);
            }
            finally
            {
                Object.DestroyImmediate(log);
            }
        }
    }
}
