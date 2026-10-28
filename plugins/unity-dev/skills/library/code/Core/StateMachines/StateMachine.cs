using System;

namespace Company.Product.Core.StateMachines
{
    // A change requested from Enter or Exit runs right after the current transition finishes.
    // If Exit or Enter throws, Current becomes null, so a retry enters again and no state is exited twice.
    public sealed class StateMachine<TState> where TState : class, IState
    {
        private TState _pending;
        private bool _isChanging;

        public TState Current { get; private set; }

        // Previous state (null on the first change), then the new state.
        public event Action<TState, TState> Changed;

        public void ChangeState(TState next)
        {
            if (next == null) throw new ArgumentNullException(nameof(next));

            if (_isChanging)
            {
                _pending = next;
                return;
            }

            _isChanging = true;
            try
            {
                while (next != null)
                {
                    if (!ReferenceEquals(next, Current)) Transition(next);
                    next = _pending;
                    _pending = null;
                }
            }
            finally
            {
                _isChanging = false;
                _pending = null;
            }
        }

        private void Transition(TState next)
        {
            var previous = Current;
            try
            {
                previous?.Exit();
                Current = next;
                next.Enter();
            }
            catch
            {
                Current = null;
                throw;
            }

            Changed?.Invoke(previous, next);
        }
    }
}
