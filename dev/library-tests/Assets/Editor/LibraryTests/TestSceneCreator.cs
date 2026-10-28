using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace LibraryTests.Editor
{
    // Creates the scenes the Play Mode tests need. Run once:
    // Unity -batchmode -projectPath <project> -executeMethod LibraryTests.Editor.TestSceneCreator.Create -quit
    public static class TestSceneCreator
    {
        // Loaded by the Scenes tests. Deliberately outside the build list, to exercise the Editor fallback.
        public const string TargetScenePath = "Assets/LibraryTests/Scenes/SceneLoaderTarget.unity";

        // Scene 0 of the build list, as a real project's Bootstrap scene is: Play From Bootstrap must not
        // hijack Play Mode test runs because of it.
        public const string BuildListScenePath = "Assets/LibraryTests/Scenes/BuildListScene.unity";

        public static void Create()
        {
            if (!System.IO.File.Exists(TargetScenePath))
            {
                var target = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                new GameObject("Marker");
                EditorSceneManager.SaveScene(target, TargetScenePath);
            }

            if (!System.IO.File.Exists(BuildListScenePath))
            {
                var buildListScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                EditorSceneManager.SaveScene(buildListScene, BuildListScenePath);
            }

            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(BuildListScenePath, true) };
            AssetDatabase.SaveAssets();
        }
    }
}
