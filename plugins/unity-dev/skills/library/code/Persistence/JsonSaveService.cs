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
    public sealed class JsonSaveService<TData> : ISaveService<TData> where TData : class
    {
        private const string VersionField = "version";
        private const string DataField = "data";

        private readonly ISaveStorage _storage;
        private readonly SaveSchema<TData> _schema;
        private readonly JsonSerializer _serializer;

        public JsonSaveService(ISaveStorage storage, SaveSchema<TData> schema)
        {
            _storage = storage ?? throw new ArgumentNullException(nameof(storage));
            _schema = schema ?? throw new ArgumentNullException(nameof(schema));
            _serializer = JsonSerializer.CreateDefault();
        }

        public bool HasSave => _storage.Exists(_schema.Key);

        public async UniTask<TData> LoadAsync(CancellationToken cancellationToken)
        {
            var bytes = await _storage.ReadAsync(_schema.Key, cancellationToken);
            if (bytes == null) return null;

            var root = Parse(Encoding.UTF8.GetString(bytes));
            var version = root.Value<int?>(VersionField) ?? throw new FormatException($"Save '{_schema.Key}' has no version.");
            var data = root[DataField] as JObject ?? throw new FormatException($"Save '{_schema.Key}' has no data.");
            Migrate(data, version);
            return data.ToObject<TData>(_serializer);
        }

        public UniTask SaveAsync(TData data, CancellationToken cancellationToken)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));

            var root = new JObject
            {
                [VersionField] = _schema.CurrentVersion,
                [DataField] = JObject.FromObject(data, _serializer),
            };
            var bytes = Encoding.UTF8.GetBytes(root.ToString(Formatting.None));
            return _storage.WriteAsync(_schema.Key, bytes, cancellationToken);
        }

        public UniTask DeleteAsync(CancellationToken cancellationToken) => _storage.DeleteAsync(_schema.Key, cancellationToken);

        // Date-looking strings stay strings: JObject.Parse would turn them into dates and lose their exact text.
        private static JObject Parse(string json)
        {
            using (var reader = new JsonTextReader(new StringReader(json)) { DateParseHandling = DateParseHandling.None })
                return JObject.Load(reader);
        }

        private void Migrate(JObject data, int version)
        {
            if (version > _schema.CurrentVersion)
                throw new InvalidOperationException($"Save '{_schema.Key}' has version {version}, newer than this build's {_schema.CurrentVersion}.");

            for (; version < _schema.CurrentVersion; version++) FindMigration(version).Migrate(data);
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
