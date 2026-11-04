using System;
using System.Collections.Generic;

namespace ProjectName.Core.Editor.UiChecks
{
    // Limits for one audit. Sizes given as fractions are of the canvas's short side, so they hold at any resolution.
    public sealed class UiAuditOptions
    {
        private readonly Dictionary<(string Rule, string Path), string> _exceptions = new Dictionary<(string Rule, string Path), string>();

        // The radius scale from docs/ui-design.md, in canvas units. A corner off the scale is a finding, on every screen.
        public float[] AllowedCornerSizes { get; set; } = Array.Empty<float>();

        // The type scale, the same way.
        public float[] AllowedFontSizes { get; set; } = Array.Empty<float>();

        public string[] AllowedFonts { get; set; } = Array.Empty<string>();

        // True: an audit without the tokens above is a finding. What the menu and the CLI use, through UiAuditSettings.
        public bool RequireTokens { get; set; }

        // Different corner sizes on panels and buttons on one screen.
        public int MaxCornerSizes { get; set; } = 3;

        public int MaxFonts { get; set; } = 2;

        // Different text sizes on one screen.
        public int MaxFontSizes { get; set; } = 6;

        // 44 pt on a 390 pt wide phone.
        public float MinTouchFraction { get; set; } = 0.11f;

        // 11 pt on a 390 pt wide phone.
        public float MinFontFraction { get; set; } = 0.028f;

        // A corner this share of the short side or more, on an element this much longer than tall, is a capsule.
        public float CapsuleCornerShare { get; set; } = 0.45f;

        public float CapsuleLength { get; set; } = 1.6f;

        // A toggle or a slider may be a capsule up to this long, in canvas units.
        public float MaxControlCapsule { get; set; } = 240f;

        // How far a sprite may leave its own aspect ratio before it counts as stretched.
        public float StretchTolerance { get; set; } = 0.03f;

        // Neighbors whose edges or centers differ by more than 0 and up to this many canvas units almost align.
        public float NearMissUnits { get; set; } = 3f;

        // Share of the screen the audited elements may cover; 1 turns the check off. Set it when auditing a HUD.
        public float MaxCoverage { get; set; } = 1f;

        // Exceptions are for what the rules didn't foresee. Many of them mean the rules aren't being followed.
        public int MaxExceptions { get; set; } = 10;

        internal IReadOnlyDictionary<(string Rule, string Path), string> Exceptions => _exceptions;

        // path: the end of the element's path in the hierarchy. The report lists accepted exceptions with their reasons.
        public UiAuditOptions Allow(string rule, string path, string reason)
        {
            if (string.IsNullOrWhiteSpace(rule)) throw new ArgumentException("A rule is required.", nameof(rule));
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("A path is required.", nameof(path));
            if (string.IsNullOrWhiteSpace(reason)) throw new ArgumentException("An exception needs a reason.", nameof(reason));
            _exceptions[(rule, path)] = reason;
            return this;
        }
    }
}
