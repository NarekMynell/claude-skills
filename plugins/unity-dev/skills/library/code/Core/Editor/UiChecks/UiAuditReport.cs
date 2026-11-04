using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ProjectName.Core.Editor.UiChecks
{
    public sealed class UiAuditReport
    {
        internal UiAuditReport(IReadOnlyList<UiFinding> findings, IReadOnlyList<UiFinding> accepted, IReadOnlyList<float> cornerSizes, IReadOnlyList<string> fonts, IReadOnlyList<float> fontSizes, float coverage)
        {
            Findings = findings;
            Accepted = accepted;
            CornerSizes = cornerSizes;
            Fonts = fonts;
            FontSizes = fontSizes;
            Coverage = coverage;
        }

        public IReadOnlyList<UiFinding> Findings { get; }

        // Findings the project accepted, with their reasons.
        public IReadOnlyList<UiFinding> Accepted { get; }

        // Canvas units, sorted: the screen's real radius scale.
        public IReadOnlyList<float> CornerSizes { get; }

        public IReadOnlyList<string> Fonts { get; }

        public IReadOnlyList<float> FontSizes { get; }

        // Share of the canvas covered by visible elements, 0 to 1.
        public float Coverage { get; }

        public bool IsClean => Findings.Count == 0;

        public override string ToString()
        {
            var text = new StringBuilder();
            text.Append("Findings: ").Append(Findings.Count).AppendLine();
            foreach (var finding in Findings) text.Append("  ").AppendLine(finding.ToString());
            if (Accepted.Count > 0) text.Append("Accepted: ").Append(Accepted.Count).AppendLine();
            foreach (var finding in Accepted) text.Append("  ").AppendLine(finding.ToString());
            text.Append("Corner sizes: ").AppendLine(string.Join(", ", CornerSizes.Select(s => s.ToString("0"))));
            text.Append("Fonts: ").AppendLine(string.Join(", ", Fonts));
            text.Append("Font sizes: ").AppendLine(string.Join(", ", FontSizes.Select(s => s.ToString("0.#"))));
            text.Append("Coverage: ").Append((Coverage * 100f).ToString("0")).AppendLine("%");
            return text.ToString();
        }
    }
}
