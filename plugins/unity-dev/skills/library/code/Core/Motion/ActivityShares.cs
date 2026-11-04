using System;
using System.Collections.Generic;

namespace ProjectName.Core.Motion
{
    // How an actor spends its time, from a test or a simulation: state names against time in each. Compared with a species'
    // activity budget, it shows an animal that never rests.
    public sealed class ActivityShares
    {
        private readonly Dictionary<string, double> _seconds = new Dictionary<string, double>();
        private double _total;

        public void Add(string state, float seconds)
        {
            if (string.IsNullOrEmpty(state)) throw new ArgumentException("A state needs a name.", nameof(state));
            if (seconds < 0f) throw new ArgumentOutOfRangeException(nameof(seconds));
            _seconds.TryGetValue(state, out var known);
            _seconds[state] = known + seconds;
            _total += seconds;
        }

        // From 0 to 1.
        public float ShareOf(string state) => _total > 0d && _seconds.TryGetValue(state, out var seconds) ? (float)(seconds / _total) : 0f;
    }
}
