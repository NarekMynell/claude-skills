# Collections

Data structures that .NET Standard 2.1 lacks. Both reuse their storage, so steady-state use doesn't allocate.

- **Destination:** `Core/Collections/`
- **Depends on:** nothing.

| Type | Use |
|---|---|
| `MinHeap<TElement, TPriority>` | Priority queue (pathfinding, schedulers). Pass a comparer for a max-heap. Named to avoid clashing with .NET's `PriorityQueue` on newer runtimes. |
| `RingBuffer<T>` | Last N items (input history, frame times). Index 0 is the oldest; `foreach` uses a struct enumerator. |
