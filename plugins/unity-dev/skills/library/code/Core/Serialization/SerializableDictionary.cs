using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Company.Product.Core.Serialization
{
    // A dictionary edited in the Inspector as a list of entries and read-only at runtime, like any config data.
    // Entries with a null or repeated key are skipped; validate them with InvalidEntryCount in OnValidate.
    [Serializable]
    public sealed class SerializableDictionary<TKey, TValue> : IReadOnlyDictionary<TKey, TValue>, ISerializationCallbackReceiver
    {
        [SerializeField] private List<Entry> _entries = new List<Entry>();

        private readonly Dictionary<TKey, TValue> _dictionary = new Dictionary<TKey, TValue>();

        public int Count => _dictionary.Count;

        public int InvalidEntryCount { get; private set; }

        public IEnumerable<TKey> Keys => _dictionary.Keys;

        public IEnumerable<TValue> Values => _dictionary.Values;

        public TValue this[TKey key] => _dictionary[key];

        public bool ContainsKey(TKey key) => _dictionary.ContainsKey(key);

        public bool TryGetValue(TKey key, out TValue value) => _dictionary.TryGetValue(key, out value);

        public Dictionary<TKey, TValue>.Enumerator GetEnumerator() => _dictionary.GetEnumerator();

        IEnumerator<KeyValuePair<TKey, TValue>> IEnumerable<KeyValuePair<TKey, TValue>>.GetEnumerator() => GetEnumerator();

        IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

        void ISerializationCallbackReceiver.OnBeforeSerialize() { }

        void ISerializationCallbackReceiver.OnAfterDeserialize()
        {
            _dictionary.Clear();
            InvalidEntryCount = 0;
            for (var i = 0; i < _entries.Count; i++)
            {
                var entry = _entries[i];
                if (entry.Key == null || !_dictionary.TryAdd(entry.Key, entry.Value)) InvalidEntryCount++;
            }
        }

        [Serializable]
        private struct Entry
        {
            [SerializeField] private TKey _key;
            [SerializeField] private TValue _value;

            public TKey Key => _key;

            public TValue Value => _value;
        }
    }
}
