using System.Linq;
using UnityEditor;
using UnityEngine;

namespace ProjectName.Core.Editor.UiChecks
{
    // The project's UI tokens from docs/ui-design.md, so every screen is held to the same scales. One asset per project.
    [CreateAssetMenu(menuName = "Tools/UI Audit Settings", fileName = "UiAuditSettings")]
    public sealed class UiAuditSettings : ScriptableObject
    {
        [SerializeField] private float[] _cornerSizes = new float[0];
        [SerializeField] private float[] _fontSizes = new float[0];
        [SerializeField] private string[] _fonts = new string[0];
        [SerializeField, Range(0f, 1f), Tooltip("The share of the screen the HUD may cover, with no panel open.")] private float _hudCoverage = 0.2f;
        [SerializeField, Tooltip("Findings accepted for this project, each with its reason.")] private Exception[] _exceptions = new Exception[0];

        [System.Serializable]
        private struct Exception
        {
            public string Rule;
            public string Path;
            public string Reason;
        }

        public static UiAuditOptions LoadOptions(bool noPanelOpen)
        {
            var settings = AssetDatabase.FindAssets("t:" + nameof(UiAuditSettings))
                .Select(guid => AssetDatabase.LoadAssetAtPath<UiAuditSettings>(AssetDatabase.GUIDToAssetPath(guid)))
                .FirstOrDefault();
            var options = new UiAuditOptions { RequireTokens = true };
            if (settings == null) return options;

            options.AllowedCornerSizes = settings._cornerSizes;
            options.AllowedFontSizes = settings._fontSizes;
            options.AllowedFonts = settings._fonts;
            if (noPanelOpen) options.MaxCoverage = settings._hudCoverage;
            foreach (var exception in settings._exceptions) options.Allow(exception.Rule, exception.Path, exception.Reason);
            return options;
        }
    }
}
