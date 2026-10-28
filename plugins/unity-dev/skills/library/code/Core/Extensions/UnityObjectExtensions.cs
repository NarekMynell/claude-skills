using UnityEngine;

namespace Company.Product.Core.Extensions
{
    public static class UnityObjectExtensions
    {
        // An interface reference doesn't see Unity's destroyed state, so `?.` and `== null` can't be trusted on it.
        public static bool IsAlive<T>(this T value) where T : class =>
            value is Object unityObject ? unityObject != null : value != null;

        public static T OrNull<T>(this T value) where T : class => value.IsAlive() ? value : null;

        public static void SafeDestroy(this Object value)
        {
            if (value == null) return;

            if (Application.isPlaying)
                Object.Destroy(value);
            else
                Object.DestroyImmediate(value);
        }
    }
}
