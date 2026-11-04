using System;
using System.Collections.Generic;
using UnityEngine;

namespace ProjectName.Core.Motion
{
    // Measures how often actors stand inside each other, in the running game at real density. For tests: it checks every
    // pair, on the ground plane.
    public sealed class CrowdOverlapMeter
    {
        private readonly float _minimumDistanceSquared;
        private double _pairs;
        private double _seconds;

        public CrowdOverlapMeter(float minimumDistance)
        {
            if (minimumDistance <= 0f) throw new ArgumentOutOfRangeException(nameof(minimumDistance));
            _minimumDistanceSquared = minimumDistance * minimumDistance;
        }

        public float PairsPerSecond => _seconds > 0d ? (float)(_pairs / _seconds) : 0f;

        public void Sample(IReadOnlyList<Vector3> positions, float deltaTime)
        {
            _seconds += deltaTime;
            for (var i = 0; i < positions.Count; i++)
            {
                for (var j = i + 1; j < positions.Count; j++)
                {
                    var dx = positions[i].x - positions[j].x;
                    var dz = positions[i].z - positions[j].z;
                    if (dx * dx + dz * dz < _minimumDistanceSquared) _pairs += deltaTime;
                }
            }
        }
    }
}
