namespace Company.Product.Core.Pooling
{
    // Implemented by components of pooled objects: reset all state in OnDespawned.
    public interface IPoolable
    {
        void OnSpawned();
        void OnDespawned();
    }
}
