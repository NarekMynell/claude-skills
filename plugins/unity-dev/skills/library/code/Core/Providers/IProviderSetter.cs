namespace Company.Product.Core.Providers
{
    // Write access, for the owner of the state only.
    public interface IProviderSetter<T> : IProvider<T>
    {
        // Notifies only when the value changed.
        void Set(T value);

        void SetWithoutNotify(T value);

        void ForceNotify();
    }
}
