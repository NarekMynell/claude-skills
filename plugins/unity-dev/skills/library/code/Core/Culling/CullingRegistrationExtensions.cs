using System;
using UnityEngine;
using VContainer;

namespace ProjectName.Core.Culling
{
    public static class CullingRegistrationExtensions
    {
        // One pauser, and one CullingGroup, for the scope. The container disposes it with the scope.
        public static RegistrationBuilder RegisterVisibilityPauser(this IContainerBuilder builder, Camera camera, int capacity = 64)
        {
            if (camera == null) throw new ArgumentNullException(nameof(camera));

            return builder.Register<IVisibilityPauser>(_ => new VisibilityPauser(camera, capacity), Lifetime.Singleton);
        }
    }
}
