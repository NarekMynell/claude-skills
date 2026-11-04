namespace ProjectName.Core.Editor.UiChecks
{
    // One defect on a screen. Path is the element's place in the hierarchy.
    public readonly struct UiFinding
    {
        public UiFinding(string rule, string path, string detail)
        {
            Rule = rule;
            Path = path;
            Detail = detail;
        }

        public string Rule { get; }

        public string Path { get; }

        public string Detail { get; }

        public override string ToString() => $"{Rule}: {Path}: {Detail}";
    }
}
