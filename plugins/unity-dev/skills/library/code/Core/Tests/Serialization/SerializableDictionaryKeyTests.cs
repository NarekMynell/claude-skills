using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Serialization
{
    public sealed class SerializableDictionaryKeyTests
    {
        // README example: `if (_prices.InvalidEntryCount > 0) Debug.LogWarning("repeated or empty price keys")`.
        [Test]
        public void SerializableDictionary_EmptyStringKey_IsCountedAsInvalid()
        {
            var asset = ScriptableObject.CreateInstance<SerializationTestAsset>();
            var serializedObject = new SerializedObject(asset);
            var entries = serializedObject.FindProperty("_prices._entries");
            entries.arraySize = 2;
            entries.GetArrayElementAtIndex(0).FindPropertyRelative("_key").stringValue = "sword";
            entries.GetArrayElementAtIndex(0).FindPropertyRelative("_value").intValue = 100;
            entries.GetArrayElementAtIndex(1).FindPropertyRelative("_key").stringValue = string.Empty;
            entries.GetArrayElementAtIndex(1).FindPropertyRelative("_value").intValue = 5;
            serializedObject.ApplyModifiedPropertiesWithoutUndo();

            var invalid = asset.Prices.InvalidEntryCount;
            var count = asset.Prices.Count;
            Object.DestroyImmediate(asset);

            Assert.That(invalid, Is.EqualTo(1), $"Empty key accepted as valid; Count = {count}.");
        }

        // README: "Repeated or null keys are skipped and counted in InvalidEntryCount".
        [Test]
        public void SerializableDictionary_UnassignedObjectKey_IsCountedAsInvalid()
        {
            var asset = ScriptableObject.CreateInstance<ObjectKeyDictionaryAsset>();
            var serializedObject = new SerializedObject(asset);
            var entries = serializedObject.FindProperty("_byAsset._entries");
            entries.arraySize = 1;
            entries.GetArrayElementAtIndex(0).FindPropertyRelative("_key").objectReferenceValue = null;
            entries.GetArrayElementAtIndex(0).FindPropertyRelative("_value").intValue = 5;
            serializedObject.ApplyModifiedPropertiesWithoutUndo();

            var invalid = asset.ByAsset.InvalidEntryCount;
            var count = asset.ByAsset.Count;
            Object.DestroyImmediate(asset);

            Assert.That(invalid, Is.EqualTo(1), $"Unassigned key accepted as valid; Count = {count}.");
        }
    }
}
