using System;
using System.Collections.Generic;

namespace Company.Product.Persistence
{
    // Describes one save file: its storage key, the current schema version and the migrations that reach it.
    public sealed class SaveSchema<TData> where TData : class
    {
        public SaveSchema(string key, int currentVersion, IReadOnlyList<ISaveMigration> migrations = null)
        {
            if (string.IsNullOrEmpty(key)) throw new ArgumentException("A key is required.", nameof(key));
            if (currentVersion < 1) throw new ArgumentOutOfRangeException(nameof(currentVersion), "Versions start at 1.");

            Key = key;
            CurrentVersion = currentVersion;
            Migrations = migrations ?? Array.Empty<ISaveMigration>();
        }

        public string Key { get; }

        public int CurrentVersion { get; }

        public IReadOnlyList<ISaveMigration> Migrations { get; }
    }
}
