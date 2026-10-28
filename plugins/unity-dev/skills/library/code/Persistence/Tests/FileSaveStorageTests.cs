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

        [SetUp]
        public void SetUp()
        {
            _directory = Path.Combine(Path.GetTempPath(), "save-tests-" + Guid.NewGuid().ToString("N"));
            _storage = new FileSaveStorage(_directory);
        }

        [TearDown]
        public void TearDown()
        {
            if (Directory.Exists(_directory)) Directory.Delete(_directory, true);
        }

        [UnityTest]
        public IEnumerator WriteThenRead_RoundTrips_AndLeavesNoTemporaryFiles() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Encoding.UTF8.GetBytes("one"), CancellationToken.None);
            await _storage.WriteAsync("progress", Encoding.UTF8.GetBytes("two"), CancellationToken.None);

            var data = await _storage.ReadAsync("progress", CancellationToken.None);
            Assert.That(Encoding.UTF8.GetString(data), Is.EqualTo("two"));
            Assert.That(Directory.GetFiles(_directory), Is.EqualTo(new[] { Path.Combine(_directory, "progress.sav") }));
        });

        [UnityTest]
        public IEnumerator Read_AfterACrashBetweenTheMoves_RestoresTheBackup() => UniTask.ToCoroutine(async () =>
        {
            Directory.CreateDirectory(_directory);
            File.WriteAllBytes(Path.Combine(_directory, "progress.sav.bak"), Encoding.UTF8.GetBytes("previous"));
            File.WriteAllBytes(Path.Combine(_directory, "progress.sav.tmp"), Encoding.UTF8.GetBytes("partial"));

            Assert.That(_storage.Exists("progress"), Is.True);
            var data = await _storage.ReadAsync("progress", CancellationToken.None);
            Assert.That(Encoding.UTF8.GetString(data), Is.EqualTo("previous"));
        });

        [UnityTest]
        public IEnumerator MissingKey_ReadsAsNull_AndDeleteRemovesEverything() => UniTask.ToCoroutine(async () =>
        {
            Assert.That(await _storage.ReadAsync("nothing", CancellationToken.None), Is.Null);

            await _storage.WriteAsync("slot", new byte[] { 1 }, CancellationToken.None);
            await _storage.DeleteAsync("slot", CancellationToken.None);
            Assert.That(_storage.Exists("slot"), Is.False);
        });

        [UnityTest]
        public IEnumerator OverlappingWrites_RunInOrder_AndTheLastOneWins() => UniTask.ToCoroutine(async () =>
        {
            var writes = new UniTask[20];
            for (var i = 0; i < writes.Length; i++)
                writes[i] = _storage.WriteAsync("progress", Encoding.UTF8.GetBytes("save " + i), CancellationToken.None);

            await UniTask.WhenAll(writes);

            var data = await _storage.ReadAsync("progress", CancellationToken.None);
            Assert.That(Encoding.UTF8.GetString(data), Is.EqualTo("save 19"));
            Assert.That(Directory.GetFiles(_directory).Length, Is.EqualTo(1));
        });

        [TestCase("../escape")]
        [TestCase("with space")]
        [TestCase("")]
        public void UnsafeKey_IsRejected(string key)
        {
            Assert.Throws<ArgumentException>(() => _storage.Exists(key));
        }
    }
}
