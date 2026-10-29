using System;
using System.Collections;
using System.IO;
using System.Text;
using System.Threading;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine.TestTools;

namespace Company.Product.Persistence.Tests
{
    // File work runs on the thread pool, so these tests await it instead of blocking.
    public sealed class FileSaveStorageTests
    {
        private string _directory;
        private FileSaveStorage _storage;

        private string SavePath => Path.Combine(_directory, "progress.sav");

        [SetUp]
        public void SetUp()
        {
            _directory = Path.Combine(Path.GetTempPath(), "save-tests-" + Guid.NewGuid().ToString("N"));
            _storage = new FileSaveStorage(_directory);
        }

        [TearDown]
        public void TearDown()
        {
            _storage.Dispose();
            if (Directory.Exists(_directory)) Directory.Delete(_directory, true);
        }

        [UnityTest]
        public IEnumerator WriteThenRead_RoundTrips_AndKeepsThePreviousSaveAsTheBackup() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Bytes("one"), CancellationToken.None);
            await _storage.WriteAsync("progress", Bytes("two"), CancellationToken.None);

            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("two"));
            Assert.That(Directory.GetFiles(_directory), Is.EquivalentTo(new[] { SavePath, SavePath + ".bak" }));
        });

        [UnityTest]
        public IEnumerator DamagedSave_ReadsTheBackup_AndRepairsTheSave() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Bytes("one"), CancellationToken.None);
            await _storage.WriteAsync("progress", Bytes("two"), CancellationToken.None);
            var damaged = File.ReadAllBytes(SavePath);
            damaged[damaged.Length - 1] ^= 0xFF;
            File.WriteAllBytes(SavePath, damaged);

            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("one"));
            Assert.That(File.ReadAllBytes(SavePath), Is.EqualTo(File.ReadAllBytes(SavePath + ".bak")));
        });

        [UnityTest]
        public IEnumerator EmptySaveAfterAPowerLoss_ReadsTheBackup() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Bytes("one"), CancellationToken.None);
            await _storage.WriteAsync("progress", Bytes("two"), CancellationToken.None);
            File.WriteAllBytes(SavePath, Array.Empty<byte>());

            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("one"));
        });

        [UnityTest]
        public IEnumerator CrashBetweenTheMoves_ReadsTheBackup() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Bytes("previous"), CancellationToken.None);
            File.Move(SavePath, SavePath + ".bak");
            File.WriteAllBytes(SavePath + ".tmp", Bytes("partial"));

            Assert.That(_storage.Exists("progress"), Is.True);
            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("previous"));
        });

        [UnityTest]
        public IEnumerator FileWithoutHeader_FromAnEarlierVersion_ReadsAsItIs() => UniTask.ToCoroutine(async () =>
        {
            Directory.CreateDirectory(_directory);
            File.WriteAllBytes(SavePath, Bytes("{\"version\":1}"));

            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("{\"version\":1}"));
        });

        [UnityTest]
        public IEnumerator MissingKey_ReadsAsNull_AndDeleteRemovesEverything() => UniTask.ToCoroutine(async () =>
        {
            Assert.That(await _storage.ReadAsync("nothing", CancellationToken.None), Is.Null);

            await _storage.WriteAsync("slot", new byte[] { 1 }, CancellationToken.None);
            await _storage.WriteAsync("slot", new byte[] { 2 }, CancellationToken.None);
            await _storage.DeleteAsync("slot", CancellationToken.None);

            Assert.That(_storage.Exists("slot"), Is.False);
            Assert.That(Directory.GetFiles(_directory), Is.Empty);
        });

        [UnityTest]
        public IEnumerator Delete_BeforeTheFirstSave_DoesNothing() => UniTask.ToCoroutine(async () =>
        {
            await _storage.DeleteAsync("progress", CancellationToken.None);

            Assert.That(Directory.Exists(_directory), Is.False);
        });

        [UnityTest]
        public IEnumerator OverlappingWrites_RunInOrder_AndTheLastOneWins() => UniTask.ToCoroutine(async () =>
        {
            var writes = new UniTask[20];
            for (var i = 0; i < writes.Length; i++)
                writes[i] = _storage.WriteAsync("progress", Bytes("save " + i), CancellationToken.None);

            await UniTask.WhenAll(writes);

            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("save 19"));
        });

        // Flush blocks the main thread, so the writes it waits for must finish without it, as they must when the app pauses.
        [UnityTest]
        public IEnumerator Flush_WaitsForPendingWrites_WithoutTheMainThread() => UniTask.ToCoroutine(async () =>
        {
            for (var i = 0; i < 20; i++) _storage.WriteAsync("progress", Bytes("save " + i), CancellationToken.None).Forget();

            Assert.That(_storage.Flush(TimeSpan.FromSeconds(10)), Is.True);
            Assert.That(Text(await _storage.ReadAsync("progress", CancellationToken.None)), Is.EqualTo("save 19"));
        });

        [UnityTest]
        public IEnumerator CancelledToken_StopsTheWriteBeforeItStarts() => UniTask.ToCoroutine(async () =>
        {
            var cancelled = new CancellationToken(true);

            var exception = await CatchAsync(_storage.WriteAsync("progress", Bytes("one"), cancelled));

            Assert.That(exception, Is.InstanceOf<OperationCanceledException>());
            Assert.That(_storage.Exists("progress"), Is.False);
        });

        [UnityTest]
        public IEnumerator Dispose_RejectsLaterOperations() => UniTask.ToCoroutine(async () =>
        {
            _storage.Dispose();
            _storage.Dispose();

            var exception = await CatchAsync(_storage.WriteAsync("progress", Bytes("one"), CancellationToken.None));

            Assert.That(exception, Is.InstanceOf<ObjectDisposedException>());
        });

        [TestCase("../escape")]
        [TestCase("with space")]
        [TestCase("")]
        public void UnsafeKey_IsRejected(string key)
        {
            Assert.Throws<ArgumentException>(() => _storage.Exists(key));
        }

        [Test]
        public void Crc32_MatchesTheStandardCheckValue()
        {
            var data = Bytes("123456789");

            Assert.That(Crc32.Compute(data, 0, data.Length), Is.EqualTo(0xCBF43926u));
        }

        private static byte[] Bytes(string text) => Encoding.UTF8.GetBytes(text);

        private static string Text(byte[] bytes) => Encoding.UTF8.GetString(bytes);

        private static async UniTask<Exception> CatchAsync(UniTask operation)
        {
            try
            {
                await operation;
                return null;
            }
            catch (Exception exception)
            {
                return exception;
            }
        }
    }
}
