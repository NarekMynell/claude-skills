using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ProjectName.Pacing
{
    public sealed class PacingReport
    {
        internal PacingReport(string player, IReadOnlyList<PacingFinding> findings, IReadOnlyDictionary<string, double> measures, string targets)
        {
            Player = player;
            Targets = targets;
            Findings = findings;
            Measures = measures;
        }

        public string Player { get; }

        // What this report held the game to, and what it was excused from, so a passing report can be judged.
        public string Targets { get; }

        public IReadOnlyList<PacingFinding> Findings { get; }

        // Name -> value, for docs/balance.md: gaps in seconds, shares from 0 to 1, per-hour rates.
        public IReadOnlyDictionary<string, double> Measures { get; }

        public bool IsClean => Findings.Count == 0;

        public override string ToString()
        {
            var text = new StringBuilder();
            text.Append(Player).Append(": ").Append(Findings.Count).AppendLine(" findings");
            text.Append("  Targets: ").AppendLine(Targets);
            foreach (var finding in Findings) text.Append("  ").AppendLine(finding.ToString());
            foreach (var pair in Measures.OrderBy(p => p.Key)) text.Append("  ").Append(pair.Key).Append(" = ").AppendLine(pair.Value.ToString("0.##"));
            return text.ToString();
        }
    }
}
