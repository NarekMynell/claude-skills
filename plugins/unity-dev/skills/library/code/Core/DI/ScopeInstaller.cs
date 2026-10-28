using UnityEngine;
using VContainer;
using VContainer.Unity;

namespace Company.Product.Core.DI
{
    // One per domain: registers that domain's services and holds its scene and config references.
    public abstract class ScopeInstaller : MonoBehaviour, IInstaller
    {
        public abstract void Install(IContainerBuilder builder);
    }
}
