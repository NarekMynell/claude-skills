# StateMachines

- **Destination:** `Core/StateMachines/`
- **Depends on:** UniTask (async machine).

| Type | Use |
|---|---|
| `StateMachine<TState>` with `IState` | Synchronous modes: character behaviour, simple screens. A change requested from `Enter` or `Exit` runs right after the current transition. |
| `AsyncStateMachine<TState>` with `IAsyncState` | App flow with loading in `EnterAsync`/`ExitAsync`. One transition at a time: starting another while one runs throws, so await each change. |

Both raise `Changed(previous, next)` after a transition and ignore a change to the current state. If `Exit` or `Enter` fails, `Current` becomes `null`: a retry enters again, and no state is exited twice.
