using Company.Product.Core.Serialization;
using UnityEngine;

namespace Company.Product.Core.Tests.Serialization
{
    internal sealed class ObjectKeyDictionaryAsset : ScriptableObject
    {
        [SerializeField] private SerializableDictionary<ScriptableObject, int> _byAsset = new SerializableDictionary<ScriptableObject, int>();

        public SerializableDictionary<ScriptableObject, int> ByAsset => _byAsset;
    }
}
