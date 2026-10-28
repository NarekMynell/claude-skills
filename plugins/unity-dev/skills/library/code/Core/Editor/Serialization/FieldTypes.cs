using System;
using System.Collections.Generic;

namespace Company.Product.Core.Editor.Serialization
{
    internal static class FieldTypes
    {
        // A drawer for an array or list element receives the collection's field type.
        public static Type ElementType(Type fieldType)
        {
            if (fieldType.IsArray) return fieldType.GetElementType();
            if (fieldType.IsGenericType && fieldType.GetGenericTypeDefinition() == typeof(List<>)) return fieldType.GetGenericArguments()[0];
            return fieldType;
        }
    }
}
