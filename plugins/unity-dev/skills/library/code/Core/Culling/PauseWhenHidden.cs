using ProjectName.Core.Lifecycle;
using UnityEngine;
using VContainer;

namespace ProjectName.Core.Culling
{
    // Add it to any object with IPausable components: they pause while the object is off screen, through the one
    // injected pauser. The components only implement Pause and Resume; they know nothing about cameras or culling.
    [DisallowMultipleComponent]
    public sealed class PauseWhenHidden : MonoBehaviour, IPausable
    {
        [SerializeField, Min(0.01f)] private float _radius = 1f;

        private IVisibilityPauser _pauser;
        private IPausable[] _targets;
        private bool _isRegistered;
        private bool _hasStarted;

        [Inject]
        public void Construct(IVisibilityPauser pauser) => _pauser = pauser;

        // For an object that moves: called by the system that moves it, after moving it.
        public void MovedTo(Vector3 position)
        {
            if (_isRegistered) _pauser.UpdatePosition(this, position);
        }

        public void Pause()
        {
            foreach (var target in _targets) target.Pause();
        }

        public void Resume()
        {
            foreach (var target in _targets) target.Resume();
        }

        private void Awake()
        {
            var all = GetComponentsInChildren<IPausable>(true);
            _targets = new IPausable[all.Length - 1];
            var next = 0;
            foreach (var target in all)
                if (!ReferenceEquals(target, this)) _targets[next++] = target;
        }

        // Injection into scene objects can come after OnEnable, so the first registration waits for Start.
        private void Start()
        {
            _hasStarted = true;
            Register();
        }

        private void OnEnable()
        {
            if (_hasStarted) Register();
        }

        private void OnDisable()
        {
            if (!_isRegistered) return;
            _isRegistered = false;
            _pauser.Unregister(this);
        }

        private void Register()
        {
            _pauser.Register(this, transform.position, _radius);
            _isRegistered = true;
        }
    }
}
