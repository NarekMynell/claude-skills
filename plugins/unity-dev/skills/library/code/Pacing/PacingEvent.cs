namespace ProjectName.Pacing
{
    public readonly struct PacingEvent
    {
        public PacingEvent(double seconds, PacingEventKind kind, string label)
        {
            Seconds = seconds;
            Kind = kind;
            Label = label;
        }

        // Play time, not calendar time, when the simulation plays in sessions.
        public double Seconds { get; }

        public PacingEventKind Kind { get; }

        // What it was. The same label twice is the same choice again, however its level or price changed.
        public string Label { get; }
    }
}
