using System;
using UnityEngine;
using VContainer;

namespace Company.Product.Core.DI
{
    // Last resort for code that DI can't reach. Every call site needs a comment explaining why.
    // Set by the ModularLifetimeScope that exposes itself, and cleared when that scope's container is disposed.
    public static class GlobalResolver
    {
        private static IObjectResolver _resolver;

        public static bool IsAvailable => _resolver != null;

        public static IObjectResolver Resolver =>
            _resolver ?? throw new InvalidOperationException("No global resolver. Enable 'Expose As Global Resolver' on the root ModularLifetimeScope.");

        internal static void Set(IObjectResolver resolver)
        {
            if (resolver == null) throw new ArgumentNullException(nameof(resolver));
            if (_resolver != null && !ReferenceEquals(_resolver, resolver))
                throw new InvalidOperationException("Another scope already exposes a global resolver.");

            _resolver = resolver;
        }

        internal static void Clear(IObjectResolver resolver)
        {
            if (ReferenceEquals(_resolver, resolver)) _resolver = null;
        }

        // Keeps Enter Play Mode without a domain reload from reusing the previous session's container.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetForPlayMode() => _resolver = null;
    }
}
