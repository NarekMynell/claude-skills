using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;

namespace Company.Product.Persistence.Tests
{
    public sealed class JsonSaveServiceTests
    {
        private sealed class MemoryStorage : ISaveStorage
        {
            public readonly Dictionary<string, byte[]> Files = new Dictionary<string, byte[]>();

            public bool Exists(string key) => Files.ContainsKey(key);

            public UniTask<byte[]> ReadAsync(string key, CancellationToken cancellationToken) =>
                UniTask.FromResult(Files.TryGetValue(key, out var data) ? data : null);

            public UniTask WriteAsync(string key, byte[] data, CancellationToken cancellationToken)
            {
                Files[key] = data;
                return UniTask.CompletedTask;
            }

            public UniTask DeleteAsync(string key, CancellationToken cancellationToken)
            {
                Files.Remove(key);
                return UniTask.CompletedTask;
            }
        }

        private sealed class Progress
        {
            public int Level { get; set; }

            public int Coins { get; set; }

            public string LastLogin { get; set; }
        }

        private sealed class RenameGoldToCoins : ISaveMigration
        {
            public int FromVersion => 1;

            public void Migrate(JObject data)
            {
                data["Coins"] = data["Gold"];
                data.Remove("Gold");
            }
        }

        private sealed class DoubleCoins : ISaveMigration
        {
            public int FromVersion => 2;

            public void Migrate(JObject data) => data["Coins"] = data.Value<int>("Coins") * 2;
        }

        private MemoryStorage _storage;

        [SetUp]
        public void SetUp() => _storage = new MemoryStorage();

        [Test]
        public void SaveThenLoad_RoundTrips()
        {
            var service = new JsonSaveService<Progress>(_storage, new SaveSchema<Progress>("progress", 1));
            service.SaveAsync(new Progress { Level = 4, Coins = 30 }, CancellationToken.None).GetAwaiter().GetResult();

            var loaded = service.LoadAsync(CancellationToken.None).GetAwaiter().GetResult();

            Assert.That(service.HasSave, Is.True);
            Assert.That(loaded.Level, Is.EqualTo(4));
            Assert.That(loaded.Coins, Is.EqualTo(30));
        }

        [Test]
        public void OldSave_RunsEveryMigrationUpToTheCurrentVersion()
        {
            _storage.Files["progress"] = Encoding.UTF8.GetBytes("{\"version\":1,\"data\":{\"Level\":2,\"Gold\":10}}");
            var schema = new SaveSchema<Progress>("progress", 3, new ISaveMigration[] { new DoubleCoins(), new RenameGoldToCoins() });

            var loaded = new JsonSaveService<Progress>(_storage, schema).LoadAsync(CancellationToken.None).GetAwaiter().GetResult();

            Assert.That(loaded.Level, Is.EqualTo(2));
            Assert.That(loaded.Coins, Is.EqualTo(20));
        }

        [Test]
        public void SaveFromANewerBuild_IsRefused()
        {
            _storage.Files["progress"] = Encoding.UTF8.GetBytes("{\"version\":5,\"data\":{}}");
            var service = new JsonSaveService<Progress>(_storage, new SaveSchema<Progress>("progress", 2));

            Assert.Throws<InvalidOperationException>(() => service.LoadAsync(CancellationToken.None).GetAwaiter().GetResult());
        }

        [Test]
        public void MissingMigration_IsReported()
        {
            _storage.Files["progress"] = Encoding.UTF8.GetBytes("{\"version\":1,\"data\":{}}");
            var service = new JsonSaveService<Progress>(_storage, new SaveSchema<Progress>("progress", 2));

            var exception = Assert.Throws<InvalidOperationException>(() => service.LoadAsync(CancellationToken.None).GetAwaiter().GetResult());
            Assert.That(exception.Message, Does.Contain("from version 1"));
        }

        [Test]
        public void DateLookingString_LoadsExactlyAsSaved()
        {
            var service = new JsonSaveService<Progress>(_storage, new SaveSchema<Progress>("progress", 1));
            service.SaveAsync(new Progress { LastLogin = "2026-10-29T10:00:00.0000000Z" }, CancellationToken.None).GetAwaiter().GetResult();

            var loaded = service.LoadAsync(CancellationToken.None).GetAwaiter().GetResult();

            Assert.That(loaded.LastLogin, Is.EqualTo("2026-10-29T10:00:00.0000000Z"));
        }

        [Test]
        public void NoSave_LoadsAsNull()
        {
            var service = new JsonSaveService<Progress>(_storage, new SaveSchema<Progress>("progress", 1));

            Assert.That(service.HasSave, Is.False);
            Assert.That(service.LoadAsync(CancellationToken.None).GetAwaiter().GetResult(), Is.Null);
        }
    }
}
