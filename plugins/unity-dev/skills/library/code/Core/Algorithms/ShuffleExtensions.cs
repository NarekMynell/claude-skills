using System;
using System.Collections.Generic;

namespace Company.Product.Core.Algorithms
{
    public static class ShuffleExtensions
    {
        // Fisher–Yates: every permutation is equally likely, and the same seed gives the same order.
        public static void Shuffle<T>(this IList<T> list, Random random)
        {
            if (random == null) throw new ArgumentNullException(nameof(random));

            for (var i = list.Count - 1; i > 0; i--)
            {
                var j = random.Next(i + 1);
                (list[i], list[j]) = (list[j], list[i]);
            }
        }
    }
}
