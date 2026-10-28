using UnityEngine;

namespace Company.Product.Core.Extensions
{
    public static class GameObjectExtensions
    {
        public static void SetLayerRecursively(this GameObject gameObject, int layer)
        {
            gameObject.layer = layer;
            var transform = gameObject.transform;
            for (var i = 0; i < transform.childCount; i++)
                transform.GetChild(i).gameObject.SetLayerRecursively(layer);
        }
    }
}
