using System;

namespace Company.Product.Audio
{
    // Identifies one playing sound. Stays safe to use after the sound ends: it simply refers to nothing.
    public readonly struct AudioHandle : IEquatable<AudioHandle>
    {
        internal readonly int Id;

        internal AudioHandle(int id) => Id = id;

        public bool IsValid => Id != 0;

        public bool Equals(AudioHandle other) => Id == other.Id;

        public override bool Equals(object obj) => obj is AudioHandle other && Equals(other);

        public override int GetHashCode() => Id;
    }
}
