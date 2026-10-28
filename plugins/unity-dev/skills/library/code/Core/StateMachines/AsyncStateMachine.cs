using System;
using System.Threading;
using Cysharp.Threading.Tasks;

namespace Company.Product.Core.StateMachines
{
    // One transition at a time: starting a second one while the first runs throws, so callers await each change.
    // If Exit or Enter fails or is cancelled, Current becomes null, so a retry enters again and no state is exited twice.
    public sealed class AsyncStateMachine<TState> where TState : class, IAsyncState
    {
        public TState Current { get; private set; }

        public bool IsTransitioning { get; private set; }

        // Previous state (null on the first change), then the new state.
        public event Action<TState, TState> Changed;

        public async UniTask ChangeStateAsync(TState next, CancellationToken cancellationToken)
        {
            if (next == null) throw new ArgumentNullException(nameof(next));
            if (IsTransitioning) throw new InvalidOperationException("A transition is already running. Await it before starting another.");
            if (ReferenceEquals(next, Current)) return;

            IsTransitioning = true;
            var previous = Current;
            try
            {
                if (previous != null) await previous.ExitAsync(cancellationToken);

                Current = next;
                await next.EnterAsync(cancellationToken);
            }
            catch
            {
                Current = null;
                throw;
            }
            finally
            {
                IsTransitioning = false;
            }

            Changed?.Invoke(previous, next);
        }
    }
}
