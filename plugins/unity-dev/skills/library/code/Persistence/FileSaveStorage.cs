using System;
using System.IO;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;
using VContainer;

namespace Company.Product.Persistence
{
    // Files under persistentDataPath/Saves. A write never leaves a half-written save behind:
    // the new data goes to a temporary file, the old save becomes a backup, the temporary file takes its place,
    // and only then is the backup deleted. A read restores the backup if a crash interrupted that sequence.
    // Operations run one at a time, in the order they were started, so two saves in the same frame can't
    // interleave and the later one wins. Register one instance per directory.
    public sealed class FileSaveStorage : ISaveStorage
    {
        private const string Extension = ".sav";

        private readonly string _directory;
        private readonly SemaphoreSlim _gate = new SemaphoreSlim(1, 1);

        [Inject]
        public FileSaveStorage() : this(Path.Combine(Application.persistentDataPath, "Saves")) { }

        public FileSaveStorage(string directory)
        {
            if (string.IsNullOrEmpty(directory)) throw new ArgumentException("A directory is required.", nameof(directory));

            _directory = directory;
        }

        public bool Exists(string key)
        {
            var path = PathOf(key);
            return File.Exists(path) || File.Exists(path + ".bak");
        }

        public UniTask<byte[]> ReadAsync(string key, CancellationToken cancellationToken)
        {
            var path = PathOf(key);
            return RunExclusiveAsync(() =>
            {
                RecoverInterruptedWrite(path);
                return File.Exists(path) ? File.ReadAllBytes(path) : null;
            }, cancellationToken);
        }

        public UniTask WriteAsync(string key, byte[] data, CancellationToken cancellationToken)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));

            var path = PathOf(key);
            return RunExclusiveAsync(() =>
            {
                Directory.CreateDirectory(_directory);
                var temporary = path + ".tmp";
                var backup = path + ".bak";
                File.WriteAllBytes(temporary, data);
                if (File.Exists(path))
                {
                    if (File.Exists(backup)) File.Delete(backup);
                    File.Move(path, backup);
                }

                File.Move(temporary, path);
                if (File.Exists(backup)) File.Delete(backup);
                return true;
            }, cancellationToken);
        }

        public UniTask DeleteAsync(string key, CancellationToken cancellationToken)
        {
            var path = PathOf(key);
            return RunExclusiveAsync(() =>
            {
                File.Delete(path);
                File.Delete(path + ".bak");
                File.Delete(path + ".tmp");
                return true;
            }, cancellationToken);
        }

        private static void RecoverInterruptedWrite(string path)
        {
            var backup = path + ".bak";
            if (!File.Exists(path) && File.Exists(backup)) File.Move(backup, path);
        }

        private string PathOf(string key)
        {
            if (string.IsNullOrEmpty(key)) throw new ArgumentException("A key is required.", nameof(key));

            for (var i = 0; i < key.Length; i++)
            {
                var c = key[i];
                if (!char.IsLetterOrDigit(c) && c != '-' && c != '_')
                    throw new ArgumentException($"Key '{key}' may contain only letters, digits, '-' and '_'.", nameof(key));
            }

            return Path.Combine(_directory, key + Extension);
        }

        // Web has no threads, so the file work runs inline there.
        private async UniTask<T> RunExclusiveAsync<T>(Func<T> work, CancellationToken cancellationToken)
        {
            await _gate.WaitAsync(cancellationToken);
            try
            {
#if UNITY_WEBGL && !UNITY_EDITOR
                return work();
#else
                return await UniTask.RunOnThreadPool(work, cancellationToken: cancellationToken);
#endif
            }
            finally
            {
                _gate.Release();
            }
        }
    }
}
