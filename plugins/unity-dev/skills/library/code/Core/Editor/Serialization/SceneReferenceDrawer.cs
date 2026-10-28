using Company.Product.Core.Serialization;
using UnityEditor;
using UnityEngine;

namespace Company.Product.Core.Editor.Serialization
{
    [CustomPropertyDrawer(typeof(SceneReference))]
    internal sealed class SceneReferenceDrawer : PropertyDrawer
    {
        public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
        {
            var assetProperty = property.FindPropertyRelative("_sceneAsset");
            var pathProperty = property.FindPropertyRelative("_scenePath");
            label = EditorGUI.BeginProperty(position, label, property);

            EditorGUI.BeginChangeCheck();
            var scene = EditorGUI.ObjectField(position, label, assetProperty.objectReferenceValue, typeof(SceneAsset), false);
            if (EditorGUI.EndChangeCheck())
            {
                assetProperty.objectReferenceValue = scene;
                pathProperty.stringValue = scene != null ? AssetDatabase.GetAssetPath(scene) : string.Empty;
            }

            EditorGUI.EndProperty();
        }
    }
}
