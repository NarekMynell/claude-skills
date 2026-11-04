using System.IO;
using System.Linq;
using NUnit.Framework;
using ProjectName.Core.Motion;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace LibraryTests.AnimationClaims
{
    // What the characters and animation guides claim about Unity's Humanoid import, checked on a mannequin that
    // dev/blender/make_fixtures.py exports from Blender with the guides' settings: it faces -Y in Blender, its bones
    // are named hand.L, thigh.R and so on, and its walk moves it at 1 m/s. A failure after a Unity or Blender upgrade
    // means a guide is out of date: fix the guide, not the test.
    public sealed class HumanoidImportTests
    {
        private const string Folder = "Assets/AnimationClaimsTemp";
        private const string ModelPath = Folder + "/Mannequin.fbx";
        private const float BlenderWalkSpeed = 1f;

        private GameObject _instance;

        [OneTimeSetUp]
        public void ImportAsHumanoid()
        {
            Directory.CreateDirectory(Folder);
            string fixture = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Fixtures", "Mannequin.fbx"));
            File.Copy(fixture, ModelPath, true);
            AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport);
            var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            importer.animationType = ModelImporterAnimationType.Human;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            importer.SaveAndReimport();
        }

        [TearDown]
        public void DestroyInstance()
        {
            if (_instance != null)
            {
                Object.DestroyImmediate(_instance);
            }
        }

        [OneTimeTearDown]
        public void RemoveAssets() => AssetDatabase.DeleteAsset(Folder);

        [Test]
        public void BlenderSideMarkersMapToTheSameSidesInUnity()
        {
            Avatar avatar = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Avatar>().Single();
            Assert.That(avatar.isHuman && avatar.isValid, "the mannequin isn't a valid Humanoid avatar");

            var importer = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            var bones = importer.humanDescription.human.ToDictionary(bone => bone.humanName, bone => bone.boneName);
            Assert.That(bones["LeftHand"], Is.EqualTo("hand.L"));
            Assert.That(bones["RightHand"], Is.EqualTo("hand.R"));
            Assert.That(bones["LeftUpperLeg"], Is.EqualTo("thigh.L"));
            Assert.That(bones["RightFoot"], Is.EqualTo("foot.R"));
        }

        [Test]
        public void ACharacterFacingMinusYInBlenderFacesPlusZWithItsLeftAtMinusX()
        {
            _instance = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath));
            var animator = _instance.GetComponent<Animator>();

            Assert.That(animator.GetBoneTransform(HumanBodyBones.LeftHand).position.x, Is.LessThan(0f));
            Assert.That(animator.GetBoneTransform(HumanBodyBones.RightHand).position.x, Is.GreaterThan(0f));
            Assert.That(animator.GetBoneTransform(HumanBodyBones.LeftToes).position.z,
                Is.GreaterThan(animator.GetBoneTransform(HumanBodyBones.LeftFoot).position.z));
        }

        [Test]
        public void RootMotionMovesTheCharacterForwardAtTheSpeedItHadInBlender()
        {
            AnimationClip walk = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<AnimationClip>()
                .Single(clip => !clip.name.StartsWith("__preview__"));
            var controller = AnimatorController.CreateAnimatorControllerAtPathWithClip(Folder + "/Walk.controller", walk);
            _instance = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath));
            var animator = _instance.GetComponent<Animator>();
            animator.runtimeAnimatorController = controller;
            animator.applyRootMotion = true;
            animator.Rebind();

            const float step = 1f / 30f;
            animator.Update(step);
            Vector3 start = _instance.transform.position;
            for (int frame = 0; frame < 15; frame++)
            {
                animator.Update(step);
            }

            Vector3 moved = _instance.transform.position - start;
            float speed = moved.magnitude / (15 * step);
            Assert.That(speed, Is.EqualTo(BlenderWalkSpeed).Within(0.05f), $"moved {moved}");
            Assert.That(moved.z / moved.magnitude, Is.GreaterThan(0.99f), $"moved {moved}: not toward +Z");
            Assert.That(animator.velocity.magnitude, Is.EqualTo(BlenderWalkSpeed).Within(0.1f), $"velocity {animator.velocity}");
        }

        // The animation guide's central claim, on the imported clip: feet stay planted when code moves the character at the
        // clip's speed, and slide when it doesn't, faster or slower.
        [Test]
        public void PlantedFeetStayPut_AtTheClipsSpeed()
        {
            FootSlideMeter meter = MeasureSlide(BlenderWalkSpeed, playbackRate: 1f);

            Assert.That(meter.WorstSlide, Is.LessThanOrEqualTo(meter.AllowedSlide));
        }

        [TestCase(1.5f)]
        [TestCase(0.5f)]
        [TestCase(1.2f)]
        public void PlantedFeetSlide_AtAnyOtherSpeed(float speedFactor)
        {
            FootSlideMeter meter = MeasureSlide(BlenderWalkSpeed * speedFactor, playbackRate: 1f);

            Assert.That(meter.WorstSlide, Is.GreaterThan(meter.AllowedSlide));
        }

        // The guide's cure for a speed that differs from the clip's: play it at the rate that matches.
        [Test]
        public void PlayingTheClipAtTheMatchingRateKeepsFeetPlanted()
        {
            const float speed = 1.2f;

            FootSlideMeter meter = MeasureSlide(speed, playbackRate: speed / BlenderWalkSpeed);

            Assert.That(meter.WorstSlide, Is.LessThanOrEqualTo(meter.AllowedSlide));
        }

        // In Edit Mode an Animator doesn't write its bones, so this samples the clip and moves the body by code, as
        // in-place locomotion does: the foot's place relative to the hips, carried along at the code's speed.
        private FootSlideMeter MeasureSlide(float speed, float playbackRate)
        {
            AnimationClip walk = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<AnimationClip>()
                .Single(clip => !clip.name.StartsWith("__preview__"));
            _instance = Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath));
            var animator = _instance.GetComponent<Animator>();

            const float step = 1f / 60f;
            Transform foot = animator.GetBoneTransform(HumanBodyBones.LeftFoot);
            Transform hips = animator.GetBoneTransform(HumanBodyBones.Hips);
            var meter = new FootSlideMeter(legLength: 0.8f);
            Vector3 body = Vector3.zero;
            for (int frame = 0; frame < 300; frame++)
            {
                walk.SampleAnimation(_instance, frame * step * playbackRate % walk.length);
                body += Vector3.forward * (speed * step);
                Vector3 relative = foot.position - hips.position;
                meter.Sample(new Vector3(body.x + relative.x, foot.position.y, body.z + relative.z));
            }

            Assert.That(meter.Steps, Is.GreaterThanOrEqualTo(2));
            return meter;
        }
    }
}
