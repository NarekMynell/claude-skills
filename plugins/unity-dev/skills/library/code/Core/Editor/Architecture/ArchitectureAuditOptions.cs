using System;
using System.Collections.Generic;

namespace ProjectName.Core.Editor.Architecture
{
    // What to audit, the limits, and the exceptions the project has decided on. Every exception needs a reason.
    public sealed class ArchitectureAuditOptions
    {
        private readonly Dictionary<(string Rule, string Subject), string> _exceptions =
            new Dictionary<(string Rule, string Subject), string>();

        public ArchitectureAuditOptions(string rootNamespace)
        {
            if (string.IsNullOrWhiteSpace(rootNamespace)) throw new ArgumentException("A root namespace is required.", nameof(rootNamespace));
            RootNamespace = rootNamespace;
        }

        public string RootNamespace { get; }

        // Scanned for calls the standards forbid. Editor and Tests folders are skipped. Null skips the scan.
        public string SourceFolder { get; set; } = "Assets/_Project/Scripts";

        // The document whose table lists capabilities, with a column named Interface. Null skips the comparison.
        public string CapabilityMapFile { get; set; } = "docs/architecture.md";

        public int MaxConstructorDependencies { get; set; } = 6;

        public int MaxInterfaceMembers { get; set; } = 8;

        public int MaxMethods { get; set; } = 30;

        public int MaxFields { get; set; } = 25;

        public int MaxFileLines { get; set; } = 400;

        // An assembly with this many classes that do work needs interfaces of its own.
        public int MinClassesForInterfaces { get; set; } = 3;

        // The share of interfaces per class with behavior, in an assembly outside Core.
        public double MinInterfaceShare { get; set; } = 0.2d;

        // Exceptions are for what the rules didn't foresee. Many of them mean the rules aren't being followed.
        public int MaxExceptions { get; set; } = 10;

        internal IReadOnlyDictionary<(string Rule, string Subject), string> Exceptions => _exceptions;

        public ArchitectureAuditOptions Allow(string rule, string subject, string reason)
        {
            if (string.IsNullOrWhiteSpace(rule)) throw new ArgumentException("A rule is required.", nameof(rule));
            if (string.IsNullOrWhiteSpace(subject)) throw new ArgumentException("A subject is required.", nameof(subject));
            if (string.IsNullOrWhiteSpace(reason)) throw new ArgumentException("An exception needs a reason.", nameof(reason));
            _exceptions[(rule, subject)] = reason;
            return this;
        }
    }
}
