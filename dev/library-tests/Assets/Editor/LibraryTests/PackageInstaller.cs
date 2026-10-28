using System.Linq;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEditor.PackageManager.Requests;
using UnityEngine;

namespace LibraryTests.Editor
{
    // Installs the packages the code library needs. Run headless without -quit:
    // Unity -batchmode -projectPath <project> -executeMethod LibraryTests.Editor.PackageInstaller.Install
    public static class PackageInstaller
    {
        private static readonly string[] PackagesToAdd =
        {
            "com.unity.test-framework",
            "com.unity.addressables",
            "com.unity.nuget.newtonsoft-json",
            "jp.hadashikick.vcontainer@1.19.0",
            "com.cysharp.unitask@2.5.11",
        };

        private const double TimeoutSeconds = 900;

        private static AddAndRemoveRequest _request;
        private static double _deadline;

        public static void Install()
        {
            _request = Client.AddAndRemove(packagesToAdd: PackagesToAdd);
            _deadline = EditorApplication.timeSinceStartup + TimeoutSeconds;
            EditorApplication.update += Poll;
        }

        private static void Poll()
        {
            if (!_request.IsCompleted)
            {
                if (EditorApplication.timeSinceStartup <= _deadline) return;
                EditorApplication.update -= Poll;
                Debug.LogError("[PackageInstaller] Timed out.");
                EditorApplication.Exit(2);
                return;
            }

            EditorApplication.update -= Poll;
            if (_request.Status == StatusCode.Success)
            {
                Debug.Log("[PackageInstaller] Resolved: " + string.Join(", ", _request.Result.Select(p => p.name + "@" + p.version)));
                EditorApplication.Exit(0);
            }
            else
            {
                Debug.LogError("[PackageInstaller] Failed: " + _request.Error?.message);
                EditorApplication.Exit(1);
            }
        }
    }
}
