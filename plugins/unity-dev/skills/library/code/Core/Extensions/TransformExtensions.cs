using UnityEngine;

namespace Company.Product.Core.Extensions
{
    public static class TransformExtensions
    {
        public static void ResetLocal(this Transform transform)
        {
            transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            transform.localScale = Vector3.one;
        }

        public static void DestroyChildren(this Transform transform)
        {
            for (var i = transform.childCount - 1; i >= 0; i--)
                transform.GetChild(i).gameObject.SafeDestroy();
        }
    }
}
