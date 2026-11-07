using NUnit.Framework;
using ProjectName.Core.Editor.Architecture;
using ProjectName.Core.Proofs;

namespace ProjectName.Core.Tests.Architecture
{
    // The project's own code against what a script can tell of the architecture rules. Green is the floor: the design itself is judged
    // by a review, which the report's signals point. A new exception needs a reason the user would accept, and it shows in the report.
    public sealed class ProjectArchitectureTests
    {
        [Test]
        public void CodeFollowsTheArchitectureRules()
        {
            var options = new ArchitectureAuditOptions("ProjectName")
                .Allow("mutable-static", "ProjectName.Core.DI.GlobalResolver", "The one documented last-resort access point.");

            var report = ArchitectureAudit.Run(options);
            ProofReceipt.Write("architecture", report.IsClean, report.ToString());

            Assert.That(report.IsClean, report.ToString());
        }
    }
}
