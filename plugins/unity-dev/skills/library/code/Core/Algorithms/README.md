# Algorithms

- **Destination:** `Core/Algorithms/`
- **Depends on:** Collections, Extensions.

| Type | Use |
|---|---|
| `ShuffleExtensions.Shuffle(list, random)` | Fisher–Yates; the same seed gives the same order |
| `WeightedPicker<T>` | Random choice proportional to weights; zero weights are never picked |
| `GridPathfinder` | A* over an `IWalkableGrid`, optional diagonals that never cut corners. The first search on a grid size allocates buffers for the whole grid; later searches allocate nothing unless the open list outgrows the cell count, which needs many cheaper paths found to the same cells |
| `GridFloodFill` | Cells connected to a start cell |
| `SpatialHash<T>` | Neighbour queries by radius; cell size close to the usual query radius. A radius that spans more cells than there are items, infinity included, scans the items instead |
| `PoissonDiskSampling.Sample` | Evenly spread random points with a minimum distance; allocates, so use it while generating content |

```csharp
var pathfinder = new GridPathfinder(allowDiagonals: true);   // keep one instance and reuse it
if (pathfinder.TryFindPath(grid, start, goal, _path)) FollowPath(_path);
```

All randomness takes a `System.Random`, so results are reproducible with a seed and testable.
