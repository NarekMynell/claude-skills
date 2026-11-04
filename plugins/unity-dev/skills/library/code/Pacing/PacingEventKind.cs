namespace ProjectName.Pacing
{
    public enum PacingEventKind
    {
        // The player chose something: a purchase, an upgrade, a route, a build.
        Decision,

        // Something good arrived that the player didn't choose at that moment: a payout, a gift, a level up.
        Reward,

        // A new thing the player can now do or buy.
        Unlock,

        // Something the player hasn't seen before: a new zone, a new mechanic, a new kind of enemy.
        Novelty,
    }
}
