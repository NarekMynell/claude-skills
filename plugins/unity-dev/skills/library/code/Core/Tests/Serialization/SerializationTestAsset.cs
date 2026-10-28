using System;
using Company.Product.Core.Serialization;
using UnityEngine;

namespace Company.Product.Core.Tests.Serialization
{
    internal interface ITestService
    {
    }

    internal sealed class SerializationTestAsset : ScriptableObject, ITestService
    {
        [SerializeField] private SerializableDictionary<string, int> _prices = new SerializableDictionary<string, int>();
        [SerializeField] private SerializedInterface<ITestService> _service;
        [SerializeReference, SubclassSelector] private TestStrategy _strategy;

        public SerializableDictionary<string, int> Prices => _prices;

        public SerializedInterface<ITestService> Service => _service;

        public TestStrategy Strategy => _strategy;
    }

    [Serializable]
    internal abstract class TestStrategy
    {
    }

    [Serializable]
    internal sealed class AggressiveStrategy : TestStrategy
    {
        [SerializeField] private float _speed = 1f;

        public float Speed => _speed;
    }

    internal sealed class NotSerializableStrategy : TestStrategy
    {
    }
}
