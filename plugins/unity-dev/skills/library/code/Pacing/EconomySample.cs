namespace ProjectName.Pacing
{
    // The economy at one moment of the simulation. Sample it at a regular interval.
    public readonly struct EconomySample
    {
        public EconomySample(double seconds, double money, double incomePerSecond, double nextGoalCost)
        {
            Seconds = seconds;
            Money = money;
            IncomePerSecond = incomePerSecond;
            NextGoalCost = nextGoalCost;
        }

        public double Seconds { get; }

        public double Money { get; }

        public double IncomePerSecond { get; }

        // The price of the cheapest thing worth buying now; 0 when nothing is left to buy.
        public double NextGoalCost { get; }
    }
}
