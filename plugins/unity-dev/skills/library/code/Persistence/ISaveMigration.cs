using Newtonsoft.Json.Linq;

namespace Company.Product.Persistence
{
    // Moves save data from FromVersion to FromVersion + 1 by editing its JSON.
    public interface ISaveMigration
    {
        int FromVersion { get; }

        void Migrate(JObject data);
    }
}
