using System;
using System.Collections.Generic;
using Company.Product.Core.Extensions;
using Company.Product.Core.Lifecycle;
using UnityEngine;

namespace Company.Product.Core.Culling
{
    // Pauses IPausable targets while their bounding sphere is outside the camera's view, using one CullingGroup
    // for all of them. Unity's built-in culling (Animator and particle culling modes) comes first; this is for custom behaviour.
    // A target is resumed when it's unregistered or the pauser is disposed, so nothing stays paused for good.
    public sealed class VisibilityPauser : IDisposable
    {
        private readonly CullingGroup _group;
        private readonly Dictionary<IPausable, int> _indices = new Dictionary<IPausable, int>();
        private BoundingSphere[] _spheres;
        private IPausable[] _targets;
        private bool[] _paused;

        public VisibilityPauser(Camera camera, int capacity = 64)
        {
            if (camera == null) throw new ArgumentNullException(nameof(camera));
            if (capacity < 1) throw new ArgumentOutOfRangeException(nameof(capacity));

            _spheres = new BoundingSphere[capacity];
            _targets = new IPausable[capacity];
            _paused = new bool[capacity];
            _group = new CullingGroup { targetCamera = camera, onStateChanged = OnStateChanged };
            _group.SetBoundingSpheres(_spheres);
            _group.SetBoundingSphereCount(0);
        }

        public int Count { get; private set; }

        public void Register(IPausable target, Vector3 position, float radius)
        {
            if (!target.IsAlive()) throw new ArgumentNullException(nameof(target));
            if (_indices.ContainsKey(target)) throw new ArgumentException("The target is already registered.", nameof(target));

            EnsureCapacity(Count + 1);
            var index = Count++;
            _spheres[index] = new BoundingSphere(position, radius);
            _targets[index] = target;
            _paused[index] = false;
            _indices.Add(target, index);
            _group.SetBoundingSphereCount(Count);
            Apply(index, _group.IsVisible(index));
        }

        public void UpdatePosition(IPausable target, Vector3 position) => _spheres[IndexOf(target)].position = position;

        public void Unregister(IPausable target)
        {
            if (target == null || !_indices.TryGetValue(target, out var index)) return;

            if (_paused[index] && target.IsAlive()) target.Resume();

            var last = Count - 1;
            if (index != last)
            {
                _spheres[index] = _spheres[last];
                _targets[index] = _targets[last];
                _paused[index] = _paused[last];
                _indices[_targets[index]] = index;
            }

            _targets[last] = null;
            _indices.Remove(target);
            Count = last;
            _group.SetBoundingSphereCount(Count);
            // The group's cached state at the reused slot belongs to the removed target.
            if (index < Count) Apply(index, _group.IsVisible(index));
        }

        public void Dispose()
        {
            _group.onStateChanged = null;
            for (var i = 0; i < Count; i++)
                if (_paused[i] && _targets[i].IsAlive()) _targets[i].Resume();

            _indices.Clear();
            Array.Clear(_targets, 0, _targets.Length);
            Count = 0;
            _group.Dispose();
        }

        internal void HandleVisibilityChanged(int index, bool isVisible)
        {
            if (index < Count) Apply(index, isVisible);
        }

        private void OnStateChanged(CullingGroupEvent sphere)
        {
            if (sphere.hasBecomeVisible) HandleVisibilityChanged(sphere.index, true);
            else if (sphere.hasBecomeInvisible) HandleVisibilityChanged(sphere.index, false);
        }

        private void Apply(int index, bool isVisible)
        {
            var shouldPause = !isVisible;
            if (_paused[index] == shouldPause) return;

            _paused[index] = shouldPause;
            var target = _targets[index];
            if (!target.IsAlive()) return;

            if (shouldPause)
                target.Pause();
            else
                target.Resume();
        }

        private int IndexOf(IPausable target) =>
            target != null && _indices.TryGetValue(target, out var index)
                ? index
                : throw new ArgumentException("The target isn't registered.", nameof(target));

        private void EnsureCapacity(int required)
        {
            if (_spheres.Length >= required) return;

            var capacity = Math.Max(required, _spheres.Length * 2);
            Array.Resize(ref _spheres, capacity);
            Array.Resize(ref _targets, capacity);
            Array.Resize(ref _paused, capacity);
            _group.SetBoundingSpheres(_spheres);
        }
    }
}
