using System.Linq;
using Company.Product.Core.Editor.Serialization;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Serialization
{
    public sealed class SerializationTests
    {
        private SerializationTestAsset _asset;

        [SetUp]
        public void SetUp() => _asset = ScriptableObject.CreateInstance<SerializationTestAsset>();

        [TearDown]
        public void TearDown()
        {
            if (_asset != null) Object.DestroyImmediate(_asset);
        }

        [Test]
        public void SerializableDictionary_IsBuiltFromInspectorEntries_AndSkipsDuplicates()
        {
            var serializedObject = new SerializedObject(_asset);
            var entries = serializedObject.FindProperty("_prices._entries");
            AddEntry(entries, "sword", 100);
            AddEntry(entries, "shield", 60);
            AddEntry(entries, "sword", 999);
            serializedObject.ApplyModifiedPropertiesWithoutUndo();

            Assert.That(_asset.Prices.Count, Is.EqualTo(2));
            Assert.That(_asset.Prices["sword"], Is.EqualTo(100));
            Assert.That(_asset.Prices.InvalidEntryCount, Is.EqualTo(1));
        }

        [Test]
        public void SerializedInterface_ReturnsTheObject_AndNullOnceItIsDestroyed()
        {
            var target = ScriptableObject.CreateInstance<SerializationTestAsset>();
            var serializedObject = new SerializedObject(_asset);
            serializedObject.FindProperty("_service._object").objectReferenceValue = target;
            serializedObject.ApplyModifiedPropertiesWithoutUndo();

            Assert.That(_asset.Service.Value, Is.SameAs(target));

            Object.DestroyImmediate(target);
            Assert.That(_asset.Service.Value, Is.Null);
        }

        [Test]
        public void SerializedInterfaceDrawer_AcceptsMatchingObjects_AndKeepsThePreviousOtherwise()
        {
            var previous = ScriptableObject.CreateInstance<SerializationTestAsset>();
            var wrong = new Material(Shader.Find("Hidden/InternalErrorShader"));

            Assert.That(SerializedInterfaceDrawer.Resolve(_asset, typeof(ITestService), null), Is.SameAs(_asset));
            LogAssert.Expect(LogType.Warning, $"{wrong.name} doesn't implement ITestService.");
            Assert.That(SerializedInterfaceDrawer.Resolve(wrong, typeof(ITestService), previous), Is.SameAs(previous));

            Object.DestroyImmediate(previous);
            Object.DestroyImmediate(wrong);
        }

        [Test]
        public void SubclassSelector_OffersOnlyConcreteSerializableTypes()
        {
            var testAssembly = new[] { typeof(TestStrategy).Assembly.GetName().Name };
            var types = SubclassSelectorDrawer.AssignableTypes(typeof(TestStrategy), testAssembly).ToList();

            Assert.That(types, Is.EqualTo(new[] { typeof(AggressiveStrategy) }));
        }

        [Test]
        public void SubclassSelector_LeavesOutTypesThatDontExistInBuilds()
        {
            Assert.That(SubclassSelectorDrawer.AssignableTypes(typeof(TestStrategy)), Is.Empty);
            Assert.That(SubclassSelectorDrawer.PlayerAssemblyNames, Does.Contain("Company.Product.Core"));
            Assert.That(SubclassSelectorDrawer.PlayerAssemblyNames, Does.Not.Contain("Company.Product.Core.PlayModeTests"));
        }

        [Test]
        public void SerializeReference_KeepsTheAssignedSubclass()
        {
            var serializedObject = new SerializedObject(_asset);
            serializedObject.FindProperty("_strategy").managedReferenceValue = new AggressiveStrategy();
            serializedObject.ApplyModifiedPropertiesWithoutUndo();

            Assert.That(_asset.Strategy, Is.TypeOf<AggressiveStrategy>());
        }

        private static void AddEntry(SerializedProperty entries, string key, int value)
        {
            entries.arraySize++;
            var entry = entries.GetArrayElementAtIndex(entries.arraySize - 1);
            entry.FindPropertyRelative("_key").stringValue = key;
            entry.FindPropertyRelative("_value").intValue = value;
        }
    }
}
