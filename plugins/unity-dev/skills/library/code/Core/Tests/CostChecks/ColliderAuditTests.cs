using System.Linq;
using NUnit.Framework;
using ProjectName.Core.Editor.CostChecks;
using UnityEditor;
using UnityEngine;

namespace ProjectName.Core.Tests.CostChecks
{
    public sealed class ColliderAuditTests
    {
        private GameObject _root;

        [SetUp]
        public void SetUp() => _root = new GameObject("Root");

        [TearDown]
        public void TearDown() => Object.DestroyImmediate(_root);

        private string[] Rules(params string[] solid) =>
            ColliderAudit.Run(new[] { _root }, new CostAuditOptions(), solid.Length == 0 ? null : solid).Findings.Select(f => f.Rule).Distinct().ToArray();

        private GameObject Cube(string name, Vector3 position, Vector3 scale)
        {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.name = name;
            cube.transform.SetParent(_root.transform);
            cube.transform.position = position;
            cube.transform.localScale = scale;
            return cube;
        }

        [Test]
        public void APrimitiveOnItsModel_IsFine()
        {
            Cube("Crate", Vector3.zero, Vector3.one);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void ACompoundOfBoxesOnChildren_IsFine()
        {
            var table = Cube("Table", Vector3.up, new Vector3(2f, 0.2f, 1f));
            Object.DestroyImmediate(table.GetComponent<BoxCollider>());
            var legs = new GameObject("LegsCollider");
            legs.transform.SetParent(_root.transform);
            var box = legs.AddComponent<BoxCollider>();
            box.center = Vector3.up;
            box.size = new Vector3(2f, 0.2f, 1f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AnInvisibleRamp_IsFine()
        {
            var ramp = new GameObject("Ramp");
            ramp.transform.SetParent(_root.transform);
            ramp.AddComponent<BoxCollider>().size = new Vector3(4f, 0.1f, 4f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AColliderFarLargerThanTheModel_IsAnInvisibleWall()
        {
            Cube("Fence", Vector3.zero, Vector3.one).GetComponent<BoxCollider>().size = new Vector3(4f, 1f, 1f);

            Assert.That(Rules(), Does.Contain("collider-beyond-model"));
        }

        [Test]
        public void AThickColliderUnderAFloor_IsFine()
        {
            var floor = Cube("Floor", Vector3.zero, new Vector3(10f, 0.1f, 10f)).GetComponent<BoxCollider>();
            floor.center = new Vector3(0f, -10f, 0f);
            floor.size = new Vector3(1f, 20.2f, 1f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AColliderAwayFromItsModel_IsReported()
        {
            Cube("Rock", Vector3.zero, Vector3.one).GetComponent<BoxCollider>().center = new Vector3(5f, 0f, 0f);

            Assert.That(Rules(), Does.Contain("collider-off-model"));
        }

        [Test]
        public void ATriggerAroundAModel_IsFine()
        {
            var zone = Cube("Shop", Vector3.zero, Vector3.one).GetComponent<BoxCollider>();
            zone.isTrigger = true;
            zone.size = new Vector3(8f, 1f, 8f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AMeshColliderWithNoMesh_IsReported()
        {
            var cube = Cube("Wall", Vector3.zero, Vector3.one);
            Object.DestroyImmediate(cube.GetComponent<BoxCollider>());
            cube.AddComponent<MeshCollider>().sharedMesh = null;

            Assert.That(Rules(), Does.Contain("no-collision-mesh"));
        }

        [Test]
        public void AConcaveMeshOnAMovingBody_IsReported()
        {
            var cube = Cube("Barrel", Vector3.zero, Vector3.one);
            var mesh = cube.GetComponent<MeshFilter>().sharedMesh;
            Object.DestroyImmediate(cube.GetComponent<BoxCollider>());
            var collider = cube.AddComponent<MeshCollider>();
            collider.sharedMesh = mesh;
            collider.convex = false;
            var body = cube.AddComponent<Rigidbody>();
            body.isKinematic = true;
            Assert.That(Rules(), Does.Not.Contain("moving-concave"));

            body.isKinematic = false;
            Assert.That(Rules(), Does.Contain("moving-concave"));
        }

        [Test]
        public void AMirroredBoxWhereTheMirrorPutsIt_IsFine()
        {
            var fence = Cube("Mirrored", Vector3.zero, new Vector3(-1f, 1f, 1f));
            Part("Beside", fence.transform, new Vector3(-3f, 0f, 0f), Vector3.one);
            var box = fence.GetComponent<BoxCollider>();
            box.center = new Vector3(1.5f, 0f, 0f);
            box.size = new Vector3(4f, 1f, 1f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AWheelCollider_IsARayAndNotAShape()
        {
            var car = Cube("Car", Vector3.zero, new Vector3(2f, 1f, 4f));
            var wheel = Child("Wheel", car.transform);
            wheel.transform.position = new Vector3(3f, 3f, 3f);
            wheel.AddComponent<WheelCollider>();

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AStaticObjectThatPhysicsMoves_IsReported()
        {
            var cube = Cube("Crate", Vector3.zero, Vector3.one);
            cube.isStatic = true;
            cube.AddComponent<Rigidbody>();

            Assert.That(Rules(), Does.Contain("static-rigidbody"));
        }

        private GameObject Character(float capsuleBottom, float capsuleHeight)
        {
            var actor = new GameObject("Actor");
            actor.transform.SetParent(_root.transform);
            var controller = actor.AddComponent<CharacterController>();
            controller.height = capsuleHeight;
            controller.radius = 0.3f;
            controller.skinWidth = 0.01f;
            controller.center = new Vector3(0f, capsuleBottom + capsuleHeight / 2f, 0f);
            var body = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Object.DestroyImmediate(body.GetComponent<BoxCollider>());
            body.transform.SetParent(actor.transform);
            body.transform.localScale = new Vector3(0.5f, 1.8f, 0.3f);
            body.transform.localPosition = new Vector3(0f, 0.9f, 0f);
            return actor;
        }

        [Test]
        public void ACapsuleThatFitsTheBody_IsFine()
        {
            Character(0f, 1.8f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void ACapsuleWhoseFootIsAboveTheFeet_SinksTheCharacter()
        {
            Character(0.3f, 1.5f);

            Assert.That(Rules(), Does.Contain("feet-off-ground"));
        }

        [Test]
        public void ACapsuleWhoseFootIsBelowTheFeet_FloatsIt()
        {
            Character(-0.3f, 2.1f);

            Assert.That(Rules(), Does.Contain("feet-off-ground"));
        }

        [Test]
        public void ACapsuleMuchShorterThanTheBody_IsReported()
        {
            Character(0f, 0.8f);

            Assert.That(Rules(), Does.Contain("capsule-size"));
        }

        [Test]
        public void AWallWithoutACollider_IsReportedWhereTheProjectSaysWallsAreSolid()
        {
            var wall = Cube("Wall", Vector3.zero, Vector3.one);
            Object.DestroyImmediate(wall.GetComponent<BoxCollider>());

            Assert.That(Rules(), Is.Empty);
            Assert.That(Rules("Root"), Does.Contain("solid-without-collider"));
        }

        private GameObject Child(string name, Transform parent)
        {
            var child = new GameObject(name);
            child.transform.SetParent(parent);
            return child;
        }

        private GameObject Part(string name, Transform parent, Vector3 position, Vector3 scale)
        {
            var part = GameObject.CreatePrimitive(PrimitiveType.Cube);
            part.name = name;
            Object.DestroyImmediate(part.GetComponent<BoxCollider>());
            part.transform.SetParent(parent);
            part.transform.position = position;
            part.transform.localScale = scale;
            return part;
        }

        [Test]
        public void ATerrainBesideProps_IsTheGround()
        {
            var type = System.Type.GetType("UnityEngine.TerrainCollider, UnityEngine.TerrainPhysicsModule");
            Assume.That(type, Is.Not.Null);
            Child("Ground", _root.transform).AddComponent(type);
            Cube("Crate", new Vector3(30f, 0f, 30f), Vector3.one);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AnInvisibleRampBesideACrate_IsARamp()
        {
            var props = Child("Props", _root.transform);
            Cube("Crate", Vector3.zero, Vector3.one).transform.SetParent(props.transform);
            Child("Ramp", props.transform).AddComponent<BoxCollider>().center = new Vector3(20f, 0f, 0f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void ALogLyingDownWithACapsule_IsNotACharacterStanding()
        {
            var log = Cube("Log", Vector3.zero, new Vector3(0.3f, 3f, 0.3f));
            Object.DestroyImmediate(log.GetComponent<BoxCollider>());
            var capsule = log.AddComponent<CapsuleCollider>();
            capsule.radius = 0.5f;
            capsule.height = 1f;
            log.AddComponent<Rigidbody>();
            log.transform.rotation = Quaternion.Euler(0f, 0f, 90f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void ArmsOnAFirstPersonCamera_SayNothingOfTheFeet()
        {
            var player = Child("Player", _root.transform);
            var controller = player.AddComponent<CharacterController>();
            controller.height = 1.8f;
            controller.center = new Vector3(0f, 0.9f, 0f);
            Part("Arms", player.transform, new Vector3(0f, 1.5f, 0.2f), new Vector3(0.4f, 0.2f, 0.5f));

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void ARagdollCarryingASword_IsJudgedByItsBody()
        {
            var actor = Child("Actor", _root.transform);
            actor.AddComponent<Animator>();
            var hips = Child("Hips", actor.transform);
            hips.transform.position = Vector3.up;
            hips.AddComponent<Rigidbody>();
            hips.AddComponent<CapsuleCollider>().height = 1.8f;
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var skin = Child("Skin", actor.transform).AddComponent<SkinnedMeshRenderer>();
            skin.sharedMesh = cube.GetComponent<MeshFilter>().sharedMesh;
            Object.DestroyImmediate(cube);
            skin.rootBone = hips.transform;
            skin.bones = new[] { hips.transform };
            skin.localBounds = new Bounds(Vector3.zero, new Vector3(0.6f, 1.8f, 0.4f));
            Part("Sword", hips.transform, new Vector3(3f, 2f, 3f), Vector3.one * 0.1f);

            Assert.That(Rules(), Does.Not.Contain("collider-off-model"));
        }

        [Test]
        public void ABoxBesideItsMesh_MakesTheWallSolid()
        {
            var wall = Child("Wall", _root.transform);
            Part("Mesh", wall.transform, Vector3.zero, new Vector3(4f, 3f, 0.2f));
            Child("Box", wall.transform).AddComponent<BoxCollider>().size = new Vector3(4f, 3f, 0.2f);

            Assert.That(Rules("Root/Wall"), Is.Empty);
        }

        [Test]
        public void ALowerLevelOfDetailBesideTheCollider_IsSolidToo()
        {
            var wall = Child("Wall", _root.transform);
            Cube("LOD0", Vector3.zero, new Vector3(4f, 3f, 0.2f)).transform.SetParent(wall.transform);
            Part("LOD1", wall.transform, Vector3.zero, new Vector3(4f, 3f, 0.2f));

            Assert.That(Rules("Root/Wall"), Does.Not.Contain("solid-without-collider"));
        }

        [Test]
        public void AColliderOnTheLevelsRoot_DoesntMakeEachWallSolid()
        {
            var floor = _root.AddComponent<BoxCollider>();
            floor.size = new Vector3(40f, 0.2f, 40f);
            Part("Wall", _root.transform, new Vector3(0f, 1.5f, 5f), new Vector3(10f, 3f, 0.2f));

            Assert.That(Rules("Root/Wall"), Does.Contain("solid-without-collider"));
        }

        [Test]
        public void ABoxMovedInsideARoom_StopsAtNothing()
        {
            var house = Child("House", _root.transform);
            Part("WallA", house.transform, new Vector3(0f, 1.5f, -5f), new Vector3(10f, 3f, 0.2f));
            Part("WallB", house.transform, new Vector3(0f, 1.5f, 5f), new Vector3(10f, 3f, 0.2f));
            var boxA = Child("BoxA", house.transform).AddComponent<BoxCollider>();
            boxA.center = new Vector3(0f, 1.5f, -2f);
            boxA.size = new Vector3(10f, 3f, 0.2f);
            var boxB = Child("BoxB", house.transform).AddComponent<BoxCollider>();
            boxB.center = new Vector3(0f, 1.5f, 5f);
            boxB.size = new Vector3(10f, 3f, 0.2f);

            Assert.That(Rules(), Does.Contain("collider-off-model"));
        }

        [Test]
        public void AnInvisibleBoundaryInAPrefabWhoseModelsHaveTheirColliders_IsABoundary()
        {
            var arena = Child("Arena", _root.transform);
            foreach (var z in new[] { -5f, 5f })
            {
                Part("Wall", arena.transform, new Vector3(0f, 1.5f, z), new Vector3(10f, 3f, 0.2f));
                var wall = Child("WallBox", arena.transform).AddComponent<BoxCollider>();
                wall.center = new Vector3(0f, 1.5f, z);
                wall.size = new Vector3(10f, 3f, 0.2f);
            }

            var edge = Child("Kerb", arena.transform).AddComponent<BoxCollider>();
            edge.center = new Vector3(0f, 0.5f, 0f);
            edge.size = new Vector3(10f, 1f, 0.2f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void ABoxOffATurnedWallsFace_IsFoundThoughTheSquareAroundThemHidesIt()
        {
            var wall = Cube("Wall", Vector3.zero, new Vector3(10f, 3f, 0.2f));
            wall.transform.rotation = Quaternion.Euler(0f, 45f, 0f);
            wall.GetComponent<BoxCollider>().center = new Vector3(0f, 0f, 10f);

            Assert.That(Rules(), Does.Contain("collider-off-model"));
        }

        [Test]
        public void AnAgentWhoseFeetAreOffItsGround_IsReported()
        {
            var type = System.Type.GetType("UnityEngine.AI.NavMeshAgent, UnityEngine.AIModule");
            Assume.That(type, Is.Not.Null);
            var actor = Child("Actor", _root.transform);
            var agent = actor.AddComponent(type);
            using (var write = new SerializedObject(agent))
            {
                write.FindProperty("m_BaseOffset").floatValue = 0f;
                write.ApplyModifiedPropertiesWithoutUndo();
            }

            Part("Body", actor.transform, new Vector3(0f, 0.9f, 0f), new Vector3(0.5f, 1.8f, 0.3f));
            Assert.That(Rules(), Is.Empty);

            Object.DestroyImmediate(actor.transform.GetChild(0).gameObject);
            Part("Body", actor.transform, new Vector3(0f, 1.3f, 0f), new Vector3(0.5f, 1.8f, 0.3f));
            Assert.That(Rules(), Does.Contain("feet-off-ground"));
        }

        [Test]
        public void AnAnimalOnACapsuleAlongItsBack_IsJudgedByItsFeet()
        {
            var animal = Child("Animal", _root.transform);
            animal.AddComponent<Rigidbody>();
            animal.AddComponent<Animator>();
            var capsule = animal.AddComponent<CapsuleCollider>();
            capsule.direction = 2;
            capsule.radius = 0.4f;
            capsule.height = 1.5f;
            capsule.center = new Vector3(0f, 0.4f, 0f);
            Part("Body", animal.transform, new Vector3(0f, 0.4f, 0f), new Vector3(0.5f, 0.8f, 1.5f));
            Assert.That(Rules(), Is.Empty);

            capsule.center = new Vector3(0f, 0f, 0f);
            Assert.That(Rules(), Does.Contain("feet-off-ground"));
        }

        [Test]
        public void ABlobShadowOnTheGround_DoesntHideFloatingFeet()
        {
            var actor = Character(0f, 1.8f);
            actor.transform.GetChild(0).localPosition = new Vector3(0f, 1.3f, 0f);
            Part("Shadow", actor.transform, new Vector3(0f, 0f, 0f), new Vector3(1f, 0.001f, 1f));

            Assert.That(Rules(), Does.Contain("feet-off-ground"));
        }

        private void Arch(params (Vector3 center, Vector3 size)[] boxes)
        {
            var arch = Child("Arch", _root.transform);
            Part("Left", arch.transform, new Vector3(-1.25f, 1.25f, 0f), new Vector3(0.5f, 2.5f, 0.5f));
            Part("Right", arch.transform, new Vector3(1.25f, 1.25f, 0f), new Vector3(0.5f, 2.5f, 0.5f));
            Part("Top", arch.transform, new Vector3(0f, 2.75f, 0f), new Vector3(3f, 0.5f, 0.5f));
            foreach (var (center, size) in boxes)
            {
                var box = Child("Box", arch.transform).AddComponent<BoxCollider>();
                box.center = center;
                box.size = size;
            }
        }

        [Test]
        public void AnArchClosedByOneBox_StopsThePlayerAtAir()
        {
            Arch((new Vector3(0f, 1.5f, 0f), new Vector3(3f, 3f, 0.5f)));

            Assert.That(Rules(), Does.Contain("collider-closes-opening"));
        }

        [Test]
        public void AnArchWithABoxPerPart_LetsHimThrough()
        {
            Arch((new Vector3(-1.25f, 1.25f, 0f), new Vector3(0.5f, 2.5f, 0.5f)), (new Vector3(1.25f, 1.25f, 0f), new Vector3(0.5f, 2.5f, 0.5f)), (new Vector3(0f, 2.75f, 0f), new Vector3(3f, 0.5f, 0.5f)));

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void AWallThatOnlyHasAFront_ClosesNoWayThroughBehindIt()
        {
            var front = Child("Front", _root.transform);
            Part("Face", front.transform, new Vector3(0f, 1.5f, 1f), new Vector3(8f, 3f, 0.02f));
            var box = Child("Box", front.transform).AddComponent<BoxCollider>();
            box.center = new Vector3(0f, 1.5f, 0f);
            box.size = new Vector3(8f, 3f, 2f);

            Assert.That(Rules(), Does.Not.Contain("collider-closes-opening"));
        }

        [Test]
        public void ATableAsOneBlock_ClosesNothingAPersonFits()
        {
            var table = Child("Table", _root.transform);
            Part("Top", table.transform, new Vector3(0f, 0.72f, 0f), new Vector3(2f, 0.06f, 1f));
            Part("Leg", table.transform, new Vector3(-0.9f, 0.35f, -0.4f), new Vector3(0.1f, 0.7f, 0.1f));
            var box = Child("Box", table.transform).AddComponent<BoxCollider>();
            box.center = new Vector3(0f, 0.375f, 0f);
            box.size = new Vector3(2f, 0.75f, 1f);

            Assert.That(Rules(), Is.Empty);
        }

        [Test]
        public void APrefabIsReadWithoutPlacingItInAScene()
        {
            const string folder = "Assets/ColliderAuditTest";
            UnityEditor.AssetDatabase.CreateFolder("Assets", "ColliderAuditTest");
            try
            {
                var fence = Cube("Fence", Vector3.zero, Vector3.one);
                fence.GetComponent<BoxCollider>().size = new Vector3(4f, 1f, 1f);
                UnityEditor.PrefabUtility.SaveAsPrefabAsset(fence, folder + "/Fence.prefab");

                Assert.That(ColliderAudit.AuditPrefabs(folder), Does.Contain("collider-beyond-model"));
            }
            finally
            {
                UnityEditor.AssetDatabase.DeleteAsset(folder);
            }
        }

        [Test]
        public void AnExceptionWithItsReason_IsAccepted()
        {
            Cube("Fence", Vector3.zero, Vector3.one).GetComponent<BoxCollider>().size = new Vector3(4f, 1f, 1f);
            var options = new CostAuditOptions().Allow("collider-beyond-model", "Fence", "Stops the player at the map's edge.");

            var report = ColliderAudit.Run(new[] { _root }, options);

            Assert.That(report.IsClean, report.ToString());
            Assert.That(report.Accepted, Has.Count.EqualTo(1));
        }
    }
}
