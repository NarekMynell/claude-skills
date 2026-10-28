using VContainer;

namespace Company.Product.Core.Providers
{
    public static class ProviderRegistrationExtensions
    {
        // One Provider per state type and scope, resolvable as IProvider<T> for readers and IProviderSetter<T> for the owner.
        public static RegistrationBuilder RegisterProvider<T>(this IContainerBuilder builder, T initialValue = default) =>
            builder.RegisterInstance(new Provider<T>(initialValue)).As<IProvider<T>, IProviderSetter<T>>();
    }
}
