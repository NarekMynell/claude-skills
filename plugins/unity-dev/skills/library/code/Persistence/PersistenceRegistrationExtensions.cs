using System;
using VContainer;

namespace Company.Product.Persistence
{
    // Registers the module's internal implementations under its public interfaces.
    public static class PersistenceRegistrationExtensions
    {
        // Files under persistentDataPath/Saves. Register one storage per directory, usually in the root scope.
        // The container disposes it, which gives pending writes a moment to finish on quit.
        public static RegistrationBuilder RegisterFileSaveStorage(this IContainerBuilder builder) =>
            builder.Register<ISaveStorage>(_ => new FileSaveStorage(), Lifetime.Singleton);

        // One versioned JSON save, kept in the scope's ISaveStorage.
        public static RegistrationBuilder RegisterJsonSave<TData>(this IContainerBuilder builder, SaveSchema<TData> schema)
            where TData : class
        {
            if (schema == null) throw new ArgumentNullException(nameof(schema));

            return builder.Register<ISaveService<TData>>(
                resolver => new JsonSaveService<TData>(resolver.Resolve<ISaveStorage>(), schema), Lifetime.Singleton);
        }
    }
}
