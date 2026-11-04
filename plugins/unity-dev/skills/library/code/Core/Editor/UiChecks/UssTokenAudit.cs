using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using ProjectName.Core.Proofs;

namespace ProjectName.Core.Editor.UiChecks
{
    // The token check for UI Toolkit: radii, text sizes and colors come from USS variables in one file, so a literal value
    // anywhere else is off the scale. It looks only at the files: UiAudit's layout checks don't exist for UI Toolkit, so
    // screenshots carry more of the review there.
    public static class UssTokenAudit
    {
        private static readonly Regex Literal = new Regex(@"^\s*(border(-top|-bottom)?(-left|-right)?-radius|font-size|-unity-font(-definition)?)\s*:(?!\s*var\()[^;]+;", RegexOptions.IgnoreCase);

        // tokensFile: the one file that may hold the values. receiptName, such as "main", writes docs/proofs/ui-<name>.txt.
        public static IReadOnlyList<string> Run(string folder, string tokensFile, string receiptName = null)
        {
            var findings = new List<string>();
            var files = Directory.Exists(folder) ? Directory.EnumerateFiles(folder, "*.uss", SearchOption.AllDirectories).ToList() : new List<string>();
            if (files.Count == 0) findings.Add($"no USS files under {folder}: nothing was audited");
            foreach (var file in files.Where(f => Path.GetFileName(f) != Path.GetFileName(tokensFile)))
                findings.AddRange(ScanFile(file, File.ReadLines(file)));

            if (receiptName != null) ProofReceipt.Write("ui-" + receiptName, findings.Count == 0, string.Join("\n", findings));
            return findings;
        }

        internal static IEnumerable<string> ScanFile(string path, IEnumerable<string> lines)
        {
            var number = 0;
            foreach (var line in lines)
            {
                number++;
                if (Literal.IsMatch(line)) yield return $"{path}:{number}: a literal value instead of a token: {line.Trim()}";
            }
        }
    }
}
