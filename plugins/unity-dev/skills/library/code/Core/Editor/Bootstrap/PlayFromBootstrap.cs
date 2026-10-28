using System;
using Company.Product.Core.Bootstrap;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

namespace Company.Product.Core.Editor.Bootstrap
{
    // Play in the Editor always starts from the Bootstrap scene (scene 0 of the active Build Profile),
    // so the Editor runs the same startup as a build; the startup then opens the scene that was open.
    // Tools > Company.Product > Play From Bootstrap turns it off, per user and project.
    // Play Mode test runs are left alone: the Test Framework must start in its own scene.
    [InitializeOnLoad]
    internal static class PlayFromBootstrap
    {
        private const string MenuPath = "Tools/Company.Product/Play From Bootstrap";
        private const string EnabledKey = "Company.Product.Core.PlayFromBootstrap";

        // Names the Unity Test Framework gives its run scene and controller object (internal to that package).
        private const string TestScenePathPrefix = "Assets/InitTestScene";
        private const string TestControllerName = "Code-based tests runner";

        static PlayFromBootstrap()
        {
            EditorApplication.playModeStateChanged += OnPlayModeStateChanged;
            EditorApplication.delayCall += Refresh;
        }

        private static bool IsEnabled
        {
            get => EditorUserSettings.GetConfigValue(EnabledKey) != "false";
            set => EditorUserSettings.SetConfigValue(EnabledKey, value ? "true" : "false");
        }

        [MenuItem(MenuPath)]
        private static void Toggle()
        {
            IsEnabled = !IsEnabled;
            Refresh();
        }

        [MenuItem(MenuPath, true)]
        private static bool ToggleValidate()
        {
            Menu.SetChecked(MenuPath, IsEnabled);
            return true;
        }

        private static void Refresh() => EditorSceneManager.playModeStartScene = IsEnabled ? FindBootstrapScene() : null;

        private static SceneAsset FindBootstrapScene()
        {
            var scenes = EditorBuildSettings.scenes;
            return scenes.Length > 0 ? AssetDatabase.LoadAssetAtPath<SceneAsset>(scenes[0].path) : null;
        }

        private static void OnPlayModeStateChanged(PlayModeStateChange change)
        {
            if (change != PlayModeStateChange.ExitingEditMode) return;

            var activeScene = SceneManager.GetActiveScene();
            if (IsTestRun(activeScene))
            {
                EditorSceneManager.playModeStartScene = null;
                return;
            }

            Refresh();
            var bootstrap = EditorSceneManager.playModeStartScene;
            if (bootstrap == null) return;

            // The startup opens the scene from disk, so unsaved changes would be missing in Play Mode.
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                EditorApplication.isPlaying = false;
                return;
            }

            var returnScene = activeScene.path == AssetDatabase.GetAssetPath(bootstrap) ? string.Empty : activeScene.path;
            SessionState.SetString(EditorPlaySession.ReturnSceneKey, returnScene);
        }

        private static bool IsTestRun(Scene scene)
        {
            if (scene.path.StartsWith(TestScenePathPrefix, StringComparison.Ordinal)) return true;

            foreach (var root in scene.GetRootGameObjects())
                if (root.name == TestControllerName) return true;

            return false;
        }
    }
}
