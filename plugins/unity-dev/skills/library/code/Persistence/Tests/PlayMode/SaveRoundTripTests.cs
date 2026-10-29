using System.Collections;
using System.Collections.Generic;
using System.Threading;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine.TestTools;
using VContainer;

namespace Company.Product.Persistence.PlayModeTests
{
    // The public API end to end, on the real file storage of the platform the tests run on, which on Web is the
    // inline path without threads. Run it in a player of each target platform, not only in the Editor.
    public sealed class SaveRoundTripTests
    {
        private const string Key = "library_test_roundtrip";

        public sealed class Data
        {
            public int Level;
            public string Name;
            public List<int> Items = new List<int>();
            public Dictionary<string, int> Counts = new Dictionary<string, int>();
        }

        [UnityTest]
        public IEnumerator SaveLoadAndDelete_RoundTrip() => UniTask.ToCoroutine(async () =>
        {
            var builder = new ContainerBuilder();
            builder.RegisterFileSaveStorage();
            builder.RegisterJsonSave(new SaveSchema<Data>(Key, 1));
            var container = builder.Build();
            var saves = container.Resolve<ISaveService<Data>>();
            try
            {
                await saves.DeleteAsync(CancellationToken.None);
                Assert.That(saves.HasSave, Is.False);

                var saved = new Data { Level = 3, Name = "ünïcode ✓", Items = { 1, 2 }, Counts = { { "a", 1 } } };
                await saves.SaveAsync(saved, CancellationToken.None);
                await saves.SaveAsync(saved, CancellationToken.None);
                Assert.That(saves.HasSave, Is.True);

                var loaded = await saves.LoadAsync(CancellationToken.None);
                Assert.That(loaded.Level, Is.EqualTo(3));
                Assert.That(loaded.Name, Is.EqualTo("ünïcode ✓"));
                Assert.That(loaded.Items, Is.EqualTo(new[] { 1, 2 }));
                Assert.That(loaded.Counts["a"], Is.EqualTo(1));

                await saves.DeleteAsync(CancellationToken.None);
                Assert.That(saves.HasSave, Is.False);
                Assert.That(await saves.LoadAsync(CancellationToken.None), Is.Null);
            }
            finally
            {
                // The test file sits next to the project's real saves: it never stays behind.
                await saves.DeleteAsync(CancellationToken.None);
                container.Dispose();
            }
        });
    }
}
