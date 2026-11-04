using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ProjectName.Core.Culling
{
    // Which renderers move, whatever moves them: a tween, a tick, an Animator. Point the camera at empty sky, take one, wait,
    // and what moved is work the player couldn't see. For tests and audits.
    public sealed class MovementProbe
    {
        private readonly Dictionary<Renderer, Matrix4x4> _start = new Dictionary<Renderer, Matrix4x4>();

        public MovementProbe(IEnumerable<GameObject> roots)
        {
            foreach (var renderer in roots.SelectMany(root => root.GetComponentsInChildren<Renderer>(false)))
                if (!(renderer is ParticleSystemRenderer)) _start[renderer] = renderer.transform.localToWorldMatrix;
        }

        public IReadOnlyList<Renderer> Moved() =>
            _start.Where(pair => pair.Key != null && pair.Key.transform.localToWorldMatrix != pair.Value).Select(pair => pair.Key).ToList();

        public IReadOnlyList<Renderer> Stayed() =>
            _start.Where(pair => pair.Key != null && pair.Key.transform.localToWorldMatrix == pair.Value).Select(pair => pair.Key).ToList();
    }
}
