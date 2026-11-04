namespace ProjectName.Core.Editor.Architecture
{
    // One place where the code departs from the architecture rules. Subject is a full type name, an assembly name,
    // or a source file's path; exceptions match on Rule and Subject.
    public readonly struct ArchitectureFinding
    {
        public ArchitectureFinding(string rule, string subject, string detail)
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
