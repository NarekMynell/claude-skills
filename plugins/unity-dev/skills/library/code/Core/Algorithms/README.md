# Algorithms

- **Destination:** `Core/Algorithms/`
- **Depends on:** Collections, Extensions.

| Type | Use |
|---|---|
| `ShuffleExtensions.Shuffle(list, random)` | Fisher–Yates; the same seed gives the same order |
| `WeightedPicker<T>` | Random choice proportional to weights; zero weights are never picked |
| `GridPathfinder` | A* over an `IWalkableGrid`, optional diagonals that never cut corners; no allocations after the first search on a grid size |
| `GridFloodFill` | Cells connected to a start cell |
| `SpatialHash<T>` | Neighbour queries by radius; cell size close to the usual query radius |
| `PoissonDiskSampling.Sample` | Evenly spread random points with a minimum distance; allocates, so use it while generating content |

```csharp
var pathfinder = new GridPathfinder(allowDiagonals: true);   // keep one instance and reuse it
if (pathfinder.TryFindPath(grid, start, goal, _path)) FollowPath(_path);
```

All randomness takes a `System.Random`, so results are reproducible with a seed and testable.
