using System;
using System.Diagnostics;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Logging
{
    public static class Log
    {
        [Conditional("UNITY_EDITOR"), Conditional("DEVELOPMENT_BUILD")]
        public static void Debug(string message, Object context = null) => UnityEngine.Debug.Log(message, context);

        public static void Warning(string message, Object context = null) => UnityEngine.Debug.LogWarning(message, context);

        public static void Error(string message, Object context = null) => UnityEngine.Debug.LogError(message, context);

        public static void Exception(Exception exception, Object context = null) => UnityEngine.Debug.LogException(exception, context);
    }
}
