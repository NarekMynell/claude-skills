using System;
using UnityEngine;
using VContainer;
using VContainer.Unity;

namespace Company.Product.Core.DI
{
    // The scope lists its installers and runs them in that order. Nothing depends on script execution order,
    // and the composition root shows all of its parts in one place.
    public class ModularLifetimeScope : LifetimeScope
    {
        [SerializeField] private ScopeInstaller[] _installers = Array.Empty<ScopeInstaller>();

        [Tooltip("Last resort for code DI can't reach. Only one scope may expose itself, usually the root.")]
        [SerializeField] private bool _exposeAsGlobalResolver;

        protected override void Configure(IContainerBuilder builder)
        {
            for (var i = 0; i < _installers.Length; i++)
            {
                var installer = _installers[i];
                if (installer == null) throw new InvalidOperationException($"{name}: installer slot {i} is empty.");

                installer.Install(builder);
            }

            if (!_exposeAsGlobalResolver) return;

            builder.Register<GlobalResolverRegistration>(Lifetime.Singleton);
            builder.RegisterBuildCallback(resolver => resolver.Resolve<GlobalResolverRegistration>());
        }

        // Play Mode tests can't use SerializedObject to fill the Inspector fields.
        internal void SetInstallersForTests(ScopeInstaller[] installers, bool exposeAsGlobalResolver)
        {
            _installers = installers;
            _exposeAsGlobalResolver = exposeAsGlobalResolver;
        }
    }
}
