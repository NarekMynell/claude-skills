using System;
using System.Collections.Generic;
using UnityEngine;

namespace ProjectName.Core.Motion
{
    // Measures foot sliding in the running game, where it shows: real movement code, real speeds, real blends. Feed it a
    // foot's world position every frame on flat ground. It finds each step, where the foot is at its lowest, and measures
    // how far the foot wandered during it, the same way inspect_animation.py does on a clip. For tests: it keeps every sample.
    public sealed class FootSlideMeter
    {
        private const float PlantedShareOfLeg = 0.02f;
        private const float MinimumPlantedHeight = 0.004f;
        private const float AllowedShareOfLeg = 0.035f;
        private const float MinimumAllowed = 0.01f;
        private const int FewestSamplesInAStep = 4;

        private readonly float _plantedHeight;
        private readonly List<Vector3> _samples = new List<Vector3>();

        public FootSlideMeter(float legLength)
        {
            if (legLength <= 0f) throw new ArgumentOutOfRangeException(nameof(legLength));
            _plantedHeight = Mathf.Max(MinimumPlantedHeight, PlantedShareOfLeg * legLength);
            AllowedSlide = Mathf.Max(MinimumAllowed, AllowedShareOfLeg * legLength);
        }

        // In metres per step, from the leg's length: about 3 cm for a person.
        public float AllowedSlide { get; }

        // Steps measured. A run with fewer than two proves nothing: the character didn't walk.
        public int Steps { get; private set; }

        // The longest a foot wandered during one step, in metres. Infinite until two steps are measured, so a character
        // that never moved can't pass.
        public float WorstSlide { get; private set; } = float.PositiveInfinity;

        public void Sample(Vector3 footPosition)
        {
            _samples.Add(footPosition);
            Measure();
        }

        private void Measure()
        {
            var lowest = float.PositiveInfinity;
            foreach (var sample in _samples) lowest = Mathf.Min(lowest, sample.y);

            var steps = 0;
            var worst = 0f;
            var start = -1;
            for (var i = 0; i <= _samples.Count; i++)
            {
                var planted = i < _samples.Count && _samples[i].y < lowest + _plantedHeight;
                if (planted)
                {
                    if (start < 0) start = i;
                    continue;
                }

                if (start >= 0 && i - start >= FewestSamplesInAStep)
                {
                    steps++;
                    // The ends of a step are the foot landing and leaving, however many frames that takes.
                    var ends = Mathf.Max(1, (i - start) / 10);
                    worst = Mathf.Max(worst, Wander(start + ends, i - 1 - ends));
                }

                start = -1;
            }

            Steps = steps;
            WorstSlide = steps >= 2 ? worst : float.PositiveInfinity;
        }

        // The farthest from where the step began: it counts a foot that slides and comes back, and not jitter summed up.
        private float Wander(int first, int last)
        {
            var origin = new Vector2(_samples[first].x, _samples[first].z);
            var farthest = 0f;
            for (var i = first + 1; i <= last; i++)
                farthest = Mathf.Max(farthest, (new Vector2(_samples[i].x, _samples[i].z) - origin).magnitude);
            return farthest;
        }
    }
}
