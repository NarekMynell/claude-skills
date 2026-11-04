using ProjectName.Core.Lifecycle;
using UnityEngine;

namespace ProjectName.Core.Culling
{
    // Pauses a target while its bounding sphere is outside the camera's view.
    public interface IVisibilityPauser
    {
        void Register(IPausable target, Vector3 position, float radius);

        void UpdatePosition(IPausable target, Vector3 position);

        void Unregister(IPausable target);
    }
}
