using System;
using Company.Product.Core.Serialization;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Editor.Serialization
{
    [CustomPropertyDrawer(typeof(SerializedInterface<>))]
    internal sealed class SerializedInterfaceDrawer : PropertyDrawer
    {
        public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
        {
            var objectProperty = property.FindPropertyRelative("_object");
            var interfaceType = FieldTypes.ElementType(fieldInfo.FieldType).GetGenericArguments()[0];
            label = EditorGUI.BeginProperty(position, label, property);
            var content = new GUIContent($"{label.text} ({interfaceType.Name})", label.tooltip);

            EditorGUI.BeginChangeCheck();
            var assigned = EditorGUI.ObjectField(position, content, objectProperty.objectReferenceValue, typeof(Object), true);
            if (EditorGUI.EndChangeCheck()) objectProperty.objectReferenceValue = Resolve(assigned, interfaceType, objectProperty.objectReferenceValue);

            EditorGUI.EndProperty();
        }

        internal static Object Resolve(Object assigned, Type interfaceType, Object previous)
        {
            if (assigned == null) return null;
            if (interfaceType.IsInstanceOfType(assigned)) return assigned;

            if (assigned is GameObject gameObject)
            {
                var component = gameObject.GetComponent(interfaceType);
                if (component != null) return component;
            }

            Debug.LogWarning($"{assigned.name} doesn't implement {interfaceType.Name}.", assigned);
            return previous;
        }
    }
}
