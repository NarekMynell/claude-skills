using System;
using System.Collections.Generic;

namespace Company.Product.Core.Algorithms
{
    // Picks items with probability proportional to their weight. Zero-weight items are never picked.
    public sealed class WeightedPicker<T>
    {
        private readonly T[] _items;
        private readonly double[] _cumulativeWeights;

        public WeightedPicker(IReadOnlyList<T> items, IReadOnlyList<float> weights)
        {
            if (items == null) throw new ArgumentNullException(nameof(items));
            if (weights == null) throw new ArgumentNullException(nameof(weights));
            if (items.Count != weights.Count) throw new ArgumentException("Items and weights must have the same count.");
            if (items.Count == 0) throw new ArgumentException("At least one item is required.", nameof(items));

            _items = new T[items.Count];
            _cumulativeWeights = new double[items.Count];
            double total = 0;
            for (var i = 0; i < items.Count; i++)
            {
                var weight = weights[i];
                if (weight < 0f || float.IsNaN(weight) || float.IsInfinity(weight))
                    throw new ArgumentException($"Weight {i} must be a finite non-negative number.", nameof(weights));

                total += weight;
                _items[i] = items[i];
                _cumulativeWeights[i] = total;
            }

            if (total <= 0) throw new ArgumentException("At least one weight must be positive.", nameof(weights));

            TotalWeight = total;
        }

        public int Count => _items.Length;

        public double TotalWeight { get; }

        public T Pick(Random random) => _items[PickIndex(random)];

        public int PickIndex(Random random)
        {
            if (random == null) throw new ArgumentNullException(nameof(random));

            var target = random.NextDouble() * TotalWeight;
            var low = 0;
            var high = _cumulativeWeights.Length - 1;
            while (low < high)
            {
                var middle = (low + high) >> 1;
                if (_cumulativeWeights[middle] > target)
                    high = middle;
                else
                    low = middle + 1;
            }

            return low;
        }
    }
}
