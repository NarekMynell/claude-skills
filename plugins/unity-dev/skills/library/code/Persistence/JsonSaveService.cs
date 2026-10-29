using System;
using System.IO;
using System.Text;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Company.Product.Persistence
{
    // Saves TData as JSON in an envelope with its schema version: { "version": 2, "data": { ... } }.
    // Loading runs the migrations from the saved version up to the current one, and refuses saves from a newer version.
    internal sealed class JsonSaveService<TData> : ISaveService<TData> where TData : class
    {
        private const string VersionField = "version";
        private const string DataField = "data";

        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

        private readonly ISaveStorage _storage;
        private readonly SaveSchema<TData> _schema;
        private readonly JsonSerializer _serializer;

        public JsonSaveService(ISaveStorage storage, SaveSchema<TData> schema)
        {
            _storage = storage ?? throw new ArgumentNullException(nameof(storage));
            _schema = schema ?? throw new ArgumentNullException(nameof(schema));

            // Create, not CreateDefault: global JsonConvert.DefaultSettings, which any plugin can set,
            // must not change the save format or let a save name the types it loads.
            // MaxDepth null: the writer has no depth limit, so the reader may not have one either (Json.NET 13 reads 64 levels).
            _serializer = JsonSerializer.Create(new JsonSerializerSettings { MaxDepth = null });
        }

        public bool HasSave => _storage.Exists(_schema.Key);

        public async UniTask<TData> LoadAsync(CancellationToken cancellationToken)
        {
            var bytes = await _storage.ReadAsync(_schema.Key, cancellationToken);
            if (bytes == null) return null;

            var root = Parse(bytes);
            var version = root.Value<int?>(VersionField) ?? throw new FormatException($"Save '{_schema.Key}' has no version.");
            var data = root[DataField];
            if (data == null || data.Type == JTokenType.Null) throw new FormatException($"Save '{_schema.Key}' has no data.");

            Migrate(data, version);
            return data.ToObject<TData>(_serializer);
        }

        // Serializes on the calling thread, so the save holds the data as it is now; only the file work leaves it.
        public UniTask SaveAsync(TData data, CancellationToken cancellationToken)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));

            return _storage.WriteAsync(_schema.Key, Serialize(data), cancellationToken);
        }

        public UniTask DeleteAsync(CancellationToken cancellationToken) => _storage.DeleteAsync(_schema.Key, cancellationToken);

        private byte[] Serialize(TData data)
        {
            using (var stream = new MemoryStream())
            {
                using (var text = new StreamWriter(stream, Utf8, 4096, true))
                using (var writer = new JsonTextWriter(text))
                {
                    writer.WriteStartObject();
                    writer.WritePropertyName(VersionField);
                    writer.WriteValue(_schema.CurrentVersion);
                    writer.WritePropertyName(DataField);
                    _serializer.Serialize(writer, data);
                    writer.WriteEndObject();
                }

                return stream.ToArray();
            }
        }

        // Date-looking strings stay strings: JObject.Parse would turn them into dates and lose their exact text.
        private static JObject Parse(byte[] bytes)
        {
            using (var text = new StreamReader(new MemoryStream(bytes), Utf8))
            using (var reader = new JsonTextReader(text) { DateParseHandling = DateParseHandling.None, MaxDepth = null })
                return JObject.Load(reader);
        }

        // Any JSON value loads at the current version; migrations edit objects.
        private void Migrate(JToken data, int version)
        {
            if (version > _schema.CurrentVersion)
                throw new InvalidOperationException($"Save '{_schema.Key}' has version {version}, newer than this build's {_schema.CurrentVersion}.");
            if (version == _schema.CurrentVersion) return;

            var dataObject = data as JObject ?? throw new FormatException($"Save '{_schema.Key}' must be a JSON object to migrate.");
            for (; version < _schema.CurrentVersion; version++) FindMigration(version).Migrate(dataObject);
        }

        private ISaveMigration FindMigration(int fromVersion)
        {
            var migrations = _schema.Migrations;
            for (var i = 0; i < migrations.Count; i++)
                if (migrations[i].FromVersion == fromVersion) return migrations[i];

            throw new InvalidOperationException($"Save '{_schema.Key}' needs a migration from version {fromVersion}.");
        }
    }
}
