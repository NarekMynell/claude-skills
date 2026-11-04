namespace ProjectName.Core.Editor.CostChecks
{
    public readonly struct CostFinding
    {
        public CostFinding(string rule, string subject, string detail)
        {
            Rule = rule;
            Subject = subject;
            Detail = detail;
        }

        public string Rule { get; }

        public string Subject { get; }

        public string Detail { get; }

        public override string ToString() => $"{Rule}: {Subject}: {Detail}";
    }
}
