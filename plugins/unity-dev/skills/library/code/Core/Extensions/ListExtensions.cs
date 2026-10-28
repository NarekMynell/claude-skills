using System;
using System.Collections.Generic;

namespace Company.Product.Core.Extensions
{
    public static class ListExtensions
    {
        // O(1) removal that doesn't keep the order: the last element takes the removed slot.
        public static void SwapRemoveAt<T>(this List<T> list, int index)
        {
            if (index < 0 || index >= list.Count) throw new ArgumentOutOfRangeException(nameof(index));

            var last = list.Count - 1;
            list[index] = list[last];
            list.RemoveAt(last);
        }
    }
}
