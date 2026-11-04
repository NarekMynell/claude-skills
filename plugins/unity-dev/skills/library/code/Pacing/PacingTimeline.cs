using System;
using System.Collections.Generic;

namespace ProjectName.Pacing
{
    // What one simulated player experienced: fed by the balance simulation, read by PacingAnalyzer.
    public sealed class PacingTimeline
    {
        public PacingTimeline(string player, double totalSeconds)
        {
            if (string.IsNullOrWhiteSpace(player)) throw new ArgumentException("Name the simulated player.", nameof(player));
            if (totalSeconds <= 0d) throw new ArgumentOutOfRangeException(nameof(totalSeconds));
            Player = player;
            TotalSeconds = totalSeconds;
        }

        public string Player { get; }

        public double TotalSeconds { get; }

        public List<PacingEvent> Events { get; } = new List<PacingEvent>();

        public List<EconomySample> Samples { get; } = new List<EconomySample>();
    }
}
