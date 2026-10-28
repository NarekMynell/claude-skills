using System;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Serialization
{
    // An Inspector field for a MonoBehaviour or ScriptableObject that implements T.
    [Serializable]
    public struct SerializedInterface<T> where T : class
    {
        [SerializeField] private Object _object;

        public SerializedInterface(T value)
        {
            if (value != null && !(value is Object))
                throw new ArgumentException($"{value.GetType().Name} isn't a UnityEngine.Object, so it can't be serialized as a reference.", nameof(value));

            _object = value as Object;
        }

        // Null when nothing is assigned or the assigned object was destroyed.
        public T Value => _object != null ? _object as T : null;
    }
}
