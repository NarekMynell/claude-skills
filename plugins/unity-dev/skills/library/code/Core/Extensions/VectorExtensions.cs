using UnityEngine;

namespace Company.Product.Core.Extensions
{
    public static class VectorExtensions
    {
        public static Vector3 WithX(this Vector3 vector, float x) => new Vector3(x, vector.y, vector.z);

        public static Vector3 WithY(this Vector3 vector, float y) => new Vector3(vector.x, y, vector.z);

        public static Vector3 WithZ(this Vector3 vector, float z) => new Vector3(vector.x, vector.y, z);

        public static Vector2 WithX(this Vector2 vector, float x) => new Vector2(x, vector.y);

        public static Vector2 WithY(this Vector2 vector, float y) => new Vector2(vector.x, y);

        public static Vector2 ToXZ(this Vector3 vector) => new Vector2(vector.x, vector.z);

        public static Vector3 FromXZ(this Vector2 vector, float y = 0f) => new Vector3(vector.x, y, vector.y);
    }
}
