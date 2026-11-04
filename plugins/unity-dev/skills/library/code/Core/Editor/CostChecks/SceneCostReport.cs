using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ProjectName.Core.Editor.CostChecks
{
    public sealed class SceneCostReport
    {
        internal SceneCostReport(IEnumerable<CostFinding> findings, CostAuditOptions options)
        {
            var open = new List<CostFinding>();
            var accepted = new List<CostFinding>();
            foreach (var finding in findings)
            {
                var exception = options.Exceptions.FirstOrDefault(e => e.Key.Rule == finding.Rule && finding.Subject.EndsWith(e.Key.Subject, StringComparison.Ordinal));
                if (exception.Value == null) open.Add(finding);
                else accepted.Add(new CostFinding(finding.Rule, finding.Subject, $"{finding.Detail} [accepted: {exception.Value}]"));
            }

            if (options.Exceptions.Count > options.MaxExceptions)
                open.Add(new CostFinding("too-many-exceptions", "scene", $"{options.Exceptions.Count} exceptions, limit {options.MaxExceptions}"));
            Findings = open;
            Accepted = accepted;
        }

        public IReadOnlyList<CostFinding> Findings { get; }

        public IReadOnlyList<CostFinding> Accepted { get; }

        public bool IsClean => Findings.Count == 0;

        public override string ToString()
        {
            var text = new StringBuilder();
            text.Append(Findings.Count).AppendLine(" findings");
            foreach (var finding in Findings) text.Append("  ").AppendLine(finding.ToString());
            if (Accepted.Count > 0) text.Append(Accepted.Count).AppendLine(" accepted");
            foreach (var finding in Accepted) text.Append("  ").AppendLine(finding.ToString());
            return text.ToString();
        }
    }
}
