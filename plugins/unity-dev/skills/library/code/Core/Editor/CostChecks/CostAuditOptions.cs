using System;
using System.Collections.Generic;

namespace ProjectName.Core.Editor.CostChecks
{
    public sealed class CostAuditOptions
    {
        private readonly Dictionary<(string Rule, string Subject), string> _exceptions = new Dictionary<(string Rule, string Subject), string>();

        // Exceptions are for what the look truly needs. Many of them mean nobody decided.
        public int MaxExceptions { get; set; } = 10;

        internal IReadOnlyDictionary<(string Rule, string Subject), string> Exceptions => _exceptions;

        // subject: the end of the finding's path. The report lists accepted exceptions with their reasons.
        public CostAuditOptions Allow(string rule, string subject, string reason)
        {
            if (string.IsNullOrWhiteSpace(rule)) throw new ArgumentException("A rule is required.", nameof(rule));
            if (string.IsNullOrWhiteSpace(subject)) throw new ArgumentException("A subject is required.", nameof(subject));
            if (string.IsNullOrWhiteSpace(reason)) throw new ArgumentException("An exception needs a reason.", nameof(reason));
            _exceptions[(rule, subject)] = reason;
            return this;
        }
    }
}
