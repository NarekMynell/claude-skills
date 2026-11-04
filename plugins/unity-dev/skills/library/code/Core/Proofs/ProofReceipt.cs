using System;
using System.Diagnostics;
using System.IO;
using UnityEngine;

namespace ProjectName.Core.Proofs
{
    // A check's own record of its last run, in docs/proofs/: the unity-dev Stop hook compares these with what changed, and
    // a review reads them. Written by the check, so it says what ran, not what someone remembers running.
    public static class ProofReceipt
    {
        // name: starts with the check's family, such as "architecture", "ui-shop-20x9", "locomotion-visitor", "balance-casual".
        [Conditional("UNITY_EDITOR")]
        public static void Write(string name, bool passed, string report)
        {
            if (string.IsNullOrWhiteSpace(name)) throw new ArgumentException("A receipt needs a name.", nameof(name));

            var folder = Path.Combine(Application.dataPath, "..", "docs", "proofs");
            Directory.CreateDirectory(folder);
            var text = $"passed: {(passed ? "true" : "false")}\nwhen: {DateTime.UtcNow:yyyy-MM-dd HH:mm} UTC\n\n{report}\n";
            File.WriteAllText(Path.Combine(folder, name + ".txt"), text);
        }
    }
}
