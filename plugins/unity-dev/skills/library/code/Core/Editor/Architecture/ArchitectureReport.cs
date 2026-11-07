using System.Collections.Generic;
using System.Text;

namespace ProjectName.Core.Editor.Architecture
{
    public sealed class ArchitectureReport
    {
        internal ArchitectureReport(
            IReadOnlyList<ArchitectureFinding> findings,
            IReadOnlyList<ArchitectureFinding> excepted,
            IReadOnlyList<ArchitectureFinding> unusedExceptions,
            IReadOnlyList<ArchitectureFinding> signals,
            IReadOnlyList<string> assemblyStats)
        {
            Findings = findings;
            Excepted = excepted;
            UnusedExceptions = unusedExceptions;
            Signals = signals;
            AssemblyStats = assemblyStats;
        }

        public IReadOnlyList<ArchitectureFinding> Findings { get; }

        public IReadOnlyList<ArchitectureFinding> Excepted { get; }

        // Exceptions that no longer match anything: remove them, so they can't hide a later violation.
        public IReadOnlyList<ArchitectureFinding> UnusedExceptions { get; }

        // Where a review should look: a number can point at a class, and can't say it's wrong. They don't fail.
        public IReadOnlyList<ArchitectureFinding> Signals { get; }

        public IReadOnlyList<string> AssemblyStats { get; }

        public bool IsClean => Findings.Count == 0 && UnusedExceptions.Count == 0;

        public override string ToString()
        {
            var text = new StringBuilder();
            Append(text, "Findings", Findings);
            Append(text, "Unused exceptions", UnusedExceptions);
            Append(text, "Accepted exceptions", Excepted);
            Append(text, "For the review, not failures", Signals);
            text.AppendLine("Assemblies:");
            foreach (var line in AssemblyStats) text.Append("  ").AppendLine(line);
            return text.ToString();
        }

        private static void Append(StringBuilder text, string title, IReadOnlyList<ArchitectureFinding> items)
        {
            if (items.Count == 0) return;
            text.Append(title).Append(" (").Append(items.Count).AppendLine("):");
            foreach (var item in items) text.Append("  ").AppendLine(item.ToString());
        }
    }
}
