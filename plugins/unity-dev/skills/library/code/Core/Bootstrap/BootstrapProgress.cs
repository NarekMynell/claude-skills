using System;

namespace Company.Product.Core.Bootstrap
{
    public readonly struct BootstrapProgress : IEquatable<BootstrapProgress>
    {
        public readonly BootstrapStatus Status;

        // Overall progress of the whole startup, from 0 to 1.
        public readonly float Value;

        public BootstrapProgress(BootstrapStatus status, float value)
        {
            Status = status;
            Value = value;
        }

        public bool Equals(BootstrapProgress other) => Status == other.Status && Value.Equals(other.Value);

        public override bool Equals(object obj) => obj is BootstrapProgress other && Equals(other);

        public override int GetHashCode() => ((int)Status * 397) ^ Value.GetHashCode();
    }
}
