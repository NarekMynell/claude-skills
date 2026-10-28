using System;
using VContainer;

namespace Company.Product.Core.DI
{
    // Created by the exposing scope's container, so the container disposes it, and clears the
    // global resolver, however the scope ends: destroyed, disposed, or unloaded with its scene.
    internal sealed class GlobalResolverRegistration : IDisposable
    {
        private readonly IObjectResolver _resolver;

        public GlobalResolverRegistration(IObjectResolver resolver)
        {
            _resolver = resolver;
            GlobalResolver.Set(resolver);
        }

        public void Dispose() => GlobalResolver.Clear(_resolver);
    }
}
