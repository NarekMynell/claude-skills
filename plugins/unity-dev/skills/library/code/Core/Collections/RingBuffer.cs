using System;
using System.Collections;
using System.Collections.Generic;

namespace Company.Product.Core.Collections
{
    // Fixed-capacity buffer: once full, each Add overwrites the oldest item. Index 0 is the oldest.
    public sealed class RingBuffer<T> : IReadOnlyList<T>
    {
        private readonly T[] _items;
        private int _start;

        public RingBuffer(int capacity)
        {
            if (capacity < 1) throw new ArgumentOutOfRangeException(nameof(capacity));

            _items = new T[capacity];
        }

        public int Count { get; private set; }

        public int Capacity => _items.Length;

        public bool IsFull => Count == _items.Length;

        public T this[int index]
        {
            get
            {
                if ((uint)index >= (uint)Count) throw new ArgumentOutOfRangeException(nameof(index));

                return _items[(_start + index) % _items.Length];
            }
        }

        public void Add(T item)
        {
            if (Count < _items.Length)
            {
                _items[(_start + Count) % _items.Length] = item;
                Count++;
                return;
            }

            _items[_start] = item;
            _start = (_start + 1) % _items.Length;
        }

        public void Clear()
        {
            Array.Clear(_items, 0, _items.Length);
            _start = 0;
            Count = 0;
        }

        public Enumerator GetEnumerator() => new Enumerator(this);

        IEnumerator<T> IEnumerable<T>.GetEnumerator() => GetEnumerator();

        IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();

        public struct Enumerator : IEnumerator<T>
        {
            private readonly RingBuffer<T> _buffer;
            private int _index;

            internal Enumerator(RingBuffer<T> buffer)
            {
                _buffer = buffer;
                _index = -1;
            }

            public T Current => _buffer[_index];

            object IEnumerator.Current => Current;

            public bool MoveNext() => ++_index < _buffer.Count;

            public void Reset() => _index = -1;

            public void Dispose() { }
        }
    }
}
