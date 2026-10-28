using System;
using System.Collections.Generic;
using System.Linq;
using Company.Product.Core.Serialization;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Editor.Serialization
{
    [CustomPropertyDrawer(typeof(SubclassSelectorAttribute))]
    internal sealed class SubclassSelectorDrawer : PropertyDrawer
    {
        private static HashSet<string> _playerAssemblies;

        public override float GetPropertyHeight(SerializedProperty property, GUIContent label) =>
            property.propertyType == SerializedPropertyType.ManagedReference
                ? EditorGUI.GetPropertyHeight(property, label, true)
                : EditorGUIUtility.singleLineHeight * 2f;

        public override void OnGUI(Rect position, SerializedProperty property, GUIContent label)
        {
            if (property.propertyType != SerializedPropertyType.ManagedReference)
            {
                EditorGUI.HelpBox(position, $"{label.text}: [SubclassSelector] needs a [SerializeReference] field.", MessageType.Error);
                return;
            }

            var current = property.managedReferenceValue?.GetType();
            var button = new Rect(
                position.x + EditorGUIUtility.labelWidth + 2f,
                position.y,
                position.width - EditorGUIUtility.labelWidth - 2f,
                EditorGUIUtility.singleLineHeight);
            var buttonLabel = new GUIContent(current != null ? ObjectNames.NicifyVariableName(current.Name) : "None");
            if (EditorGUI.DropdownButton(button, buttonLabel, FocusType.Keyboard)) ShowMenu(button, property, current);

            EditorGUI.PropertyField(position, property, label, true);
        }

        // Editor and test assemblies are left out: their types don't exist in builds.
        internal static IEnumerable<Type> AssignableTypes(Type baseType)
        {
            _playerAssemblies ??= new HashSet<string>(CompilationPipeline.GetAssemblies(AssembliesType.Player).Select(assembly => assembly.name));
            return AssignableTypes(baseType, _playerAssemblies);
        }

        internal static IEnumerable<Type> AssignableTypes(Type baseType, ICollection<string> allowedAssemblies) =>
            TypeCache.GetTypesDerivedFrom(baseType)
                .Append(baseType)
                .Where(type => allowedAssemblies.Contains(type.Assembly.GetName().Name)
                               && !type.IsAbstract && !type.IsInterface && !type.ContainsGenericParameters
                               && !typeof(Object).IsAssignableFrom(type)
                               && type.IsDefined(typeof(SerializableAttribute), false)
                               && (type.IsValueType || type.GetConstructor(Type.EmptyTypes) != null))
                .Distinct()
                .OrderBy(type => type.Name);

        private void ShowMenu(Rect button, SerializedProperty property, Type current)
        {
            var target = property.Copy();
            var baseType = FieldTypes.ElementType(fieldInfo.FieldType);
            var menu = new GenericMenu();
            menu.AddItem(new GUIContent("None"), current == null, () => Assign(target, null));
            foreach (var type in AssignableTypes(baseType))
                menu.AddItem(new GUIContent(ObjectNames.NicifyVariableName(type.Name)), type == current, () => Assign(target, type));
            menu.DropDown(button);
        }

        private static void Assign(SerializedProperty property, Type type)
        {
            property.serializedObject.Update();
            property.managedReferenceValue = type != null ? Activator.CreateInstance(type) : null;
            property.serializedObject.ApplyModifiedProperties();
        }
    }
}
