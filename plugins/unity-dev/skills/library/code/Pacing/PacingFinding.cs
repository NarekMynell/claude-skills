namespace ProjectName.Pacing
{
    public readonly struct PacingFinding
    {
        public PacingFinding(string rule, double atSeconds, string detail)
        {
            Rule = rule;
            AtSeconds = atSeconds;
            Detail = detail;
        }

        public string Rule { get; }

        public double AtSeconds { get; }

        public string Detail { get; }

        public override string ToString() => $"{Rule} at {AtSeconds / 60d:0.#} min: {Detail}";
    }
}
