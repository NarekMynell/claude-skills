using System;

namespace Company.Product.Core.Providers
{
    // Read access to one piece of shared state and its changes.
    public interface IProvider<T>
    {
        T Value { get; }

        // Dispose the returned subscription to stop receiving changes.
        IDisposable Subscribe(Action<T> onChanged, bool notifyCurrentValue = true);
    }
}
