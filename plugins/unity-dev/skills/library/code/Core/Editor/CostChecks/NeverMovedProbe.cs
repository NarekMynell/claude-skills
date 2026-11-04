using System.Collections.Generic;
using System.Linq;
using ProjectName.Core.Culling;
using UnityEngine;

namespace ProjectName.Core.Editor.CostChecks
{
    // Settles what SceneCostAudit can't: which renderers really stayed still while the game ran, whatever scripts sit near
    // them. Begin in Play Mode, play a real session, then ask. What it names should be marked static, unless the game
    // moves it later than this session reached.
    public sealed class NeverMovedProbe
    {
        private readonly MovementProbe _probe;

        public NeverMovedProbe(IEnumerable<GameObject> roots) => _probe = new MovementProbe(roots);

        public IReadOnlyList<CostFinding> Report() =>
            _probe.Stayed()
                .Where(renderer => !renderer.gameObject.isStatic && !(renderer is SkinnedMeshRenderer))
                .Select(renderer => new CostFinding("never-moved", renderer.name, "it didn't move in this session, and it isn't marked static"))
                .ToList();
    }
}
