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
    public sealed class SaveRecoveryTests
    {
        public sealed class Node
        {
            public Node Child { get; set; }
        }

        public sealed class Progress
        {
            public int Level { get; set; }
        }

        private string _directory;
        private FileSaveStorage _storage;

        private string SavePath => Path.Combine(_directory, "progress.sav");

        [SetUp]
        public void SetUp()
        {
            _directory = Path.Combine(Path.GetTempPath(), "save-recovery-tests-" + Guid.NewGuid().ToString("N"));
            _storage = new FileSaveStorage(_directory);
        }

        [TearDown]
        public void TearDown()
        {
            _storage.Dispose();
            if (Directory.Exists(_directory)) Directory.Delete(_directory, true);
        }

        // Windows can't create these files, with or without an extension: refused everywhere, so a key that works on
        // one platform works on all of them.
        [TestCase("con")]
        [TestCase("NUL")]
        [TestCase("Com1")]
        [TestCase("lpt9")]
        public void Key_ThatIsAWindowsDeviceName_IsRefused(string key)
        {
            Assert.Throws<ArgumentException>(() => _storage.Exists(key));
        }

        [TestCase("console")]
        [TestCase("com10")]
        [TestCase("nul_backup")]
        public void Key_ThatOnlyStartsLikeADeviceName_IsAccepted(string key)
        {
            Assert.That(_storage.Exists(key), Is.False);
        }

        // Whatever SaveAsync accepts, LoadAsync must read back.
        [UnityTest]
        public IEnumerator DeeplyNestedData_ThatSaves_AlsoLoads() => UniTask.ToCoroutine(async () =>
        {
            var service = new JsonSaveService<Node>(_storage, new SaveSchema<Node>("progress", 1));
            var root = new Node();
            var node = root;
            for (var i = 0; i < 70; i++)
            {
                node.Child = new Node();
                node = node.Child;
            }

            await service.SaveAsync(root, CancellationToken.None);

            Exception loadFailure = null;
            try
            {
                await service.LoadAsync(CancellationToken.None);
            }
            catch (Exception exception)
            {
                loadFailure = exception;
            }

            Assert.That(loadFailure, Is.Null, "The save was written but can't be loaded.");
        });

        // ISaveService.LoadAsync: "Null when there is no save yet." Here there is a save; it's damaged.
        [UnityTest]
        public IEnumerator BothCopiesDamaged_IsNotReportedAsNoSave() => UniTask.ToCoroutine(async () =>
        {
            var service = new JsonSaveService<Progress>(_storage, new SaveSchema<Progress>("progress", 1));
            await service.SaveAsync(new Progress { Level = 1 }, CancellationToken.None);
            await service.SaveAsync(new Progress { Level = 2 }, CancellationToken.None);
            Damage(SavePath);
            Damage(SavePath + ".bak");

            Progress loaded = null;
            Exception loadFailure = null;
            try
            {
                loaded = await service.LoadAsync(CancellationToken.None);
            }
            catch (Exception exception)
            {
                loadFailure = exception;
            }

            Assert.That(service.HasSave, Is.True);
            Assert.That(loaded != null || loadFailure != null, Is.True,
                "A damaged save loads as null, exactly like 'no save yet', so the game starts over and the next save overwrites it.");
        });

        // README: "A read returns the newest intact copy, the save or else its backup".
        [UnityTest]
        public IEnumerator SaveWhoseHeaderIsDamaged_ReadsTheBackup() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Encoding.UTF8.GetBytes("one"), CancellationToken.None);
            await _storage.WriteAsync("progress", Encoding.UTF8.GetBytes("two"), CancellationToken.None);
            var damaged = File.ReadAllBytes(SavePath);
            Array.Clear(damaged, 0, damaged.Length);   // a zero-filled file, the typical result of a lost write
            File.WriteAllBytes(SavePath, damaged);

            var read = await _storage.ReadAsync("progress", CancellationToken.None);

            Assert.That(read == null ? null : Encoding.UTF8.GetString(read), Is.EqualTo("one"));
        });

        // ISaveService<TData> accepts any class; a collection saves fine and then can't be loaded.
        [UnityTest]
        public IEnumerator CollectionData_ThatSaves_AlsoLoads() => UniTask.ToCoroutine(async () =>
        {
            var service = new JsonSaveService<System.Collections.Generic.List<int>>(_storage,
                new SaveSchema<System.Collections.Generic.List<int>>("progress", 1));

            await service.SaveAsync(new System.Collections.Generic.List<int> { 1, 2, 3 }, CancellationToken.None);

            Exception loadFailure = null;
            System.Collections.Generic.List<int> loaded = null;
            try
            {
                loaded = await service.LoadAsync(CancellationToken.None);
            }
            catch (Exception exception)
            {
                loadFailure = exception;
            }

            Assert.That(loadFailure, Is.Null, "The save was written but can't be loaded.");
            Assert.That(loaded, Is.EqualTo(new[] { 1, 2, 3 }));
        });

        // README: "A cancellation token is checked when an operation starts". The read below starts only after the
        // large write ahead of it finishes, long after its token was cancelled.
        [UnityTest]
        public IEnumerator ReadQueuedBehindAWrite_WhoseTokenIsCancelledBeforeItStarts_IsCancelled() => UniTask.ToCoroutine(async () =>
        {
            await _storage.WriteAsync("progress", Encoding.UTF8.GetBytes("small"), CancellationToken.None);
            var large = new byte[64 * 1024 * 1024];
            var write = _storage.WriteAsync("other", large, CancellationToken.None);
            var cancellation = new CancellationTokenSource();
            var read = _storage.ReadAsync("progress", cancellation.Token);
            cancellation.Cancel();
            var writeStillRunning = write.Status == UniTaskStatus.Pending;

            Exception ended = null;
            try
            {
                await read;
            }
            catch (Exception exception)
            {
                ended = exception;
            }

            await write;
            cancellation.Dispose();
            Assert.That(writeStillRunning, Is.True, "Precondition: the read was still queued when its token was cancelled.");
            Assert.That(ended, Is.InstanceOf<OperationCanceledException>(), "The read ran although its token was cancelled before it started.");
        });

        private static void Damage(string path)
        {
            var bytes = File.ReadAllBytes(path);
            bytes[bytes.Length - 1] ^= 0xFF;
            File.WriteAllBytes(path, bytes);
        }
    }
}
