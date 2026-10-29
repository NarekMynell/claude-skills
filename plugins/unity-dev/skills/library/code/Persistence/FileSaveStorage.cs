using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Cysharp.Threading.Tasks;
using UnityEngine;

namespace Company.Product.Persistence
{
    // Files under persistentDataPath/Saves, written so that a crash or a power loss costs at most the write in
    // progress: the data goes to a temporary file that is flushed to disk, the current save becomes the backup,
    // and the temporary file takes its place. Each file starts with its length and a CRC-32 of its data, and a
    // read returns the newest intact copy: the save, else its backup, which then replaces the damaged save.
    // Operations run on the thread pool, one at a time, in the order they were started, and never wait for the
    // main thread, so a write started when the app pauses finishes while the app is in the background.
    // A cancellation token is checked when an operation starts; a started write always finishes.
    internal sealed class FileSaveStorage : ISaveStorage, IDisposable
    {
        private const string Extension = ".sav";
        private const string BackupSuffix = ".bak";
        private const string TemporarySuffix = ".tmp";
        private const int HeaderSize = 12;

        // On quit, pending writes get this long to finish before the scope's disposal moves on.
        private static readonly TimeSpan DisposeTimeout = TimeSpan.FromSeconds(2);

        private static readonly byte[] Magic = { (byte)'S', (byte)'A', (byte)'V', 1 };

        // Reserved by Windows even with an extension ("Naming Files, Paths, and Namespaces" in Microsoft's documentation).
        // Its superscript variants, such as COM¹, already fail the letters-and-digits rule.
        private static readonly string[] WindowsDeviceNames =
        {
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
        };

        private readonly string _directory;
        private readonly object _queueLock = new object();
        private Task _tail = Task.CompletedTask;
        private bool _isDisposed;

        public FileSaveStorage() : this(Path.Combine(Application.persistentDataPath, "Saves")) { }

        public FileSaveStorage(string directory)
        {
            if (string.IsNullOrEmpty(directory)) throw new ArgumentException("A directory is required.", nameof(directory));

            _directory = directory;
        }

        public bool Exists(string key)
        {
            var path = PathOf(key);
            return File.Exists(path) || File.Exists(path + BackupSuffix);
        }

        public UniTask<byte[]> ReadAsync(string key, CancellationToken cancellationToken)
        {
            var path = PathOf(key);
            return Enqueue(() => ReadIntact(path), cancellationToken);
        }

        public UniTask WriteAsync(string key, byte[] data, CancellationToken cancellationToken)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));

            var path = PathOf(key);
            return Enqueue(() =>
            {
                Write(path, data);
                return true;
            }, cancellationToken);
        }

        // The backup goes first: a crash partway through then leaves the save as it was, never a restored old copy.
        public UniTask DeleteAsync(string key, CancellationToken cancellationToken)
        {
            var path = PathOf(key);
            return Enqueue(() =>
            {
                if (!Directory.Exists(_directory)) return true;

                File.Delete(path + TemporarySuffix);
                File.Delete(path + BackupSuffix);
                File.Delete(path);
                return true;
            }, cancellationToken);
        }

        public bool Flush(TimeSpan timeout)
        {
            Task tail;
            lock (_queueLock) tail = _tail;

            try
            {
                return tail.Wait(timeout);
            }
            catch (AggregateException)
            {
                return true; // It finished; the operation's own caller receives the failure.
            }
        }

        public void Dispose()
        {
            lock (_queueLock)
            {
                if (_isDisposed) return;

                _isDisposed = true;
            }

            Flush(DisposeTimeout);
        }

        private void Write(string path, byte[] data)
        {
            Directory.CreateDirectory(_directory);
            var temporary = path + TemporarySuffix;
            var backup = path + BackupSuffix;

            using (var stream = new FileStream(temporary, FileMode.Create, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough))
            {
                stream.Write(CreateHeader(data), 0, HeaderSize);
                stream.Write(data, 0, data.Length);
                stream.Flush(true);
            }

            if (File.Exists(path))
            {
                File.Delete(backup);
                File.Move(path, backup);
            }

            File.Move(temporary, path);
        }

        private static byte[] ReadIntact(string path)
        {
            var data = ReadPayload(path);
            if (data != null) return data;

            var backup = path + BackupSuffix;
            data = ReadPayload(backup);
            if (data != null)
            {
                File.Copy(backup, path, true);
                return data;
            }

            // A save exists but no copy is intact: that isn't "no save", which callers answer with a new game.
            if (File.Exists(path) || File.Exists(backup)) throw new InvalidDataException($"'{Path.GetFileName(path)}' and its backup are damaged.");

            return null;
        }

        // Null when the file is missing, empty or damaged. A file without the header was written before
        // the header existed and is returned as it is.
        private static byte[] ReadPayload(string path)
        {
            if (!File.Exists(path)) return null;

            var file = File.ReadAllBytes(path);
            if (!HasMagic(file)) return IsLegacyJson(file) ? file : null;
            if (file.Length < HeaderSize) return null;

            var length = ReadInt(file, 4);
            if (length != file.Length - HeaderSize) return null;
            if ((uint)ReadInt(file, 8) != Crc32.Compute(file, HeaderSize, length)) return null;

            var data = new byte[length];
            Buffer.BlockCopy(file, HeaderSize, data, 0, length);
            return data;
        }

        private static byte[] CreateHeader(byte[] data)
        {
            var header = new byte[HeaderSize];
            Buffer.BlockCopy(Magic, 0, header, 0, Magic.Length);
            WriteInt(header, 4, data.Length);
            WriteInt(header, 8, (int)Crc32.Compute(data, 0, data.Length));
            return header;
        }

        // Files from before the header are JSON documents; anything else without the header is damaged.
        private static bool IsLegacyJson(byte[] file)
        {
            var i = file.Length >= 3 && file[0] == 0xEF && file[1] == 0xBB && file[2] == 0xBF ? 3 : 0;
            while (i < file.Length && (file[i] == ' ' || file[i] == '\t' || file[i] == '\r' || file[i] == '\n')) i++;
            return i < file.Length && file[i] == '{';
        }

        private static bool HasMagic(byte[] file)
        {
            if (file.Length < Magic.Length) return false;

            for (var i = 0; i < Magic.Length; i++)
                if (file[i] != Magic[i]) return false;

            return true;
        }

        private static int ReadInt(byte[] buffer, int offset) =>
            buffer[offset] | buffer[offset + 1] << 8 | buffer[offset + 2] << 16 | buffer[offset + 3] << 24;

        private static void WriteInt(byte[] buffer, int offset, int value)
        {
            buffer[offset] = (byte)value;
            buffer[offset + 1] = (byte)(value >> 8);
            buffer[offset + 2] = (byte)(value >> 16);
            buffer[offset + 3] = (byte)(value >> 24);
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

            // Refused on every platform, so a key that works on one platform works on all of them.
            for (var i = 0; i < WindowsDeviceNames.Length; i++)
                if (string.Equals(key, WindowsDeviceNames[i], StringComparison.OrdinalIgnoreCase))
                    throw new ArgumentException($"Key '{key}' is a device name on Windows, where '{key}{Extension}' can't be a file.", nameof(key));

            return Path.Combine(_directory, key + Extension);
        }

        private UniTask<T> Enqueue<T>(Func<T> work, CancellationToken cancellationToken)
        {
            if (cancellationToken.IsCancellationRequested) return UniTask.FromCanceled<T>(cancellationToken);

#if UNITY_WEBGL && !UNITY_EDITOR
            // Web has no threads: the work runs inline, which also keeps the order.
            if (_isDisposed) return UniTask.FromException<T>(new ObjectDisposedException(nameof(FileSaveStorage)));

            try
            {
                return UniTask.FromResult(work());
            }
            catch (Exception exception)
            {
                return UniTask.FromException<T>(exception);
            }
#else
            Task<T> next;
            lock (_queueLock)
            {
                if (_isDisposed) return UniTask.FromException<T>(new ObjectDisposedException(nameof(FileSaveStorage)));

                next = _tail.ContinueWith(_ =>
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    return work();
                }, CancellationToken.None, TaskContinuationOptions.DenyChildAttach, TaskScheduler.Default);
                _tail = next;
            }

            return next.AsUniTask();
#endif
        }
    }
}
