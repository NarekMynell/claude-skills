namespace ProjectName.Core.Bootstrap
{
    // Hands the scene that was open in the Editor to the startup flow, which plays from the Bootstrap scene.
    internal static class EditorPlaySession
    {
        internal const string ReturnSceneKey = "ProjectName.Core.Bootstrap.ReturnScene";

        public static bool TryTakeReturnScene(out string scenePath)
        {
#if UNITY_EDITOR
            scenePath = UnityEditor.SessionState.GetString(ReturnSceneKey, string.Empty);
            UnityEditor.SessionState.EraseString(ReturnSceneKey);
            return !string.IsNullOrEmpty(scenePath);
#else
            scenePath = null;
            return false;
#endif
        }
    }
}
