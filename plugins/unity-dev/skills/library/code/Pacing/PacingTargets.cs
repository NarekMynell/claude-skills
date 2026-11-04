using System.Collections.Generic;

namespace ProjectName.Pacing
{
    // The promises the game makes to this kind of player, stated before the simulation runs. There are no defaults:
    // a number here is a design decision, with its reason in docs/balance.md. Every target is set, or marked as not
    // applying to this game with the reason why: a target left out is how a wall goes unnoticed.
    public sealed class PacingTargets
    {
        // How long the game must keep its promises: a simulation shorter than this proves nothing about the rest.
        public double MinSimulatedSeconds { get; set; }

        // Runs per kind of player. 1 only for a game with no randomness, as a reason in docs/balance.md says.
        public int MinRuns { get; set; }

        public double MaxSecondsToFirstReward { get; set; }

        // The longest the player waits between two decisions.
        public double MaxSecondsBetweenDecisions { get; set; }

        public double MaxSecondsBetweenUnlocks { get; set; }

        public double MaxSecondsBetweenNovelty { get; set; }

        // The same choice this many times in a row is repetition, not a decision.
        public int MaxSameChoiceInARow { get; set; }

        // One choice taking this share of all decisions is a dominant strategy. 0.4 means 40%.
        public double MaxShareOfOneChoice { get; set; }

        // The longest the player needs to save for the next goal at the current income.
        public double MaxSecondsToNextGoal { get; set; }

        // Money this many times the next goal's price, held for MinOverflowSeconds, means nothing is left to want.
        public double OverflowRatio { get; set; }

        public double MinOverflowSeconds { get; set; }

        // The largest value the design wants the player to see: money, income or a price.
        public double MaxShownValue { get; set; }

        // Income may grow at most this many times over per hour of play.
        public double MaxIncomeGrowthPerHour { get; set; }

        // Targets this game has no use for, such as money targets in a game with no money: name -> the reason, which the
        // design doc repeats.
        public Dictionary<string, string> NotApplicable { get; } = new Dictionary<string, string>();
    }
}
