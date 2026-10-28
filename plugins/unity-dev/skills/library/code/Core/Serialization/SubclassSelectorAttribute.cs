using System;
using UnityEngine;

namespace Company.Product.Core.Serialization
{
    // Adds a type picker to a [SerializeReference] field: the dropdown lists every concrete
    // [Serializable] class that can be assigned to the field.
    [AttributeUsage(AttributeTargets.Field)]
    public sealed class SubclassSelectorAttribute : PropertyAttribute { }
}
