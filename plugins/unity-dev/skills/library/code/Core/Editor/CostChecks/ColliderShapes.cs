using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ProjectName.Core.Editor.CostChecks
{
    // The geometry ColliderAudit reads: where a collider is, as physics has it, and what a mesh has where.
    internal static class ColliderShapes
    {
        public static string PathOf(Transform element)
        {
            var path = element.name;
            for (var parent = element.parent; parent != null; parent = parent.parent) path = parent.name + "/" + path;
            return path;
        }

        public static Bounds BoundsOf(Collider collider)
        {
            var extent = new Extent(Quaternion.identity);
            extent.Add(collider);
            return extent.ToBounds();
        }

        public static Vector3 AxisOf(CapsuleCollider capsule)
        {
            var axis = capsule.direction == 0 ? Vector3.right : capsule.direction == 1 ? Vector3.up : Vector3.forward;
            return (capsule.transform.rotation * axis).normalized;
        }

        // The middles of a capsule's two round ends, and its radius, in metres. Its length scales along its axis, its radius by the larger of the other two.
        public static void CapsuleEnds(CapsuleCollider capsule, out Vector3 start, out Vector3 end, out float radius)
        {
            var transform = capsule.transform;
            var scale = transform.lossyScale;
            var along = Mathf.Abs(scale[capsule.direction]);
            var across = Mathf.Max(Mathf.Abs(scale[(capsule.direction + 1) % 3]), Mathf.Abs(scale[(capsule.direction + 2) % 3]));
            radius = capsule.radius * across;
            var half = Mathf.Max(0f, capsule.height * along / 2f - radius);
            var middle = transform.TransformPoint(capsule.center);
            start = middle - AxisOf(capsule) * half;
            end = middle + AxisOf(capsule) * half;
        }

        public static float MaxScale(Transform transform)
        {
            var scale = transform.lossyScale;
            return Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.y), Mathf.Abs(scale.z));
        }

        public static bool Contains(Collider collider, Vector3 point, float tolerance)
        {
            var transform = collider.transform;
            switch (collider)
            {
                case BoxCollider box:
                    return InBox(transform, box.center, box.size, point, tolerance);
                case MeshCollider mesh when mesh.sharedMesh != null:
                    return InBox(transform, mesh.sharedMesh.bounds.center, mesh.sharedMesh.bounds.size, point, tolerance);
                case SphereCollider sphere:
                    return (point - transform.TransformPoint(sphere.center)).magnitude <= sphere.radius * MaxScale(transform) + tolerance;
                case CapsuleCollider capsule:
                    CapsuleEnds(capsule, out var start, out var end, out var radius);
                    var along = Mathf.Clamp01(Vector3.Dot(point - start, end - start) / Mathf.Max((end - start).sqrMagnitude, 1e-9f));
                    return (point - Vector3.Lerp(start, end, along)).magnitude <= radius + tolerance;
                default:
                    return false;
            }
        }

        private static bool InBox(Transform transform, Vector3 center, Vector3 size, Vector3 point, float tolerance)
        {
            var scale = transform.lossyScale;
            var local = transform.InverseTransformPoint(point) - center;
            return Mathf.Abs(local.x) <= size.x / 2f + tolerance / Mathf.Max(Mathf.Abs(scale.x), 1e-6f)
                   && Mathf.Abs(local.y) <= size.y / 2f + tolerance / Mathf.Max(Mathf.Abs(scale.y), 1e-6f)
                   && Mathf.Abs(local.z) <= size.z / 2f + tolerance / Mathf.Max(Mathf.Abs(scale.z), 1e-6f);
        }
    }

    // A box along a frame, around what is added to it, in metres.
    internal sealed class Extent
    {
        private readonly Quaternion _frame;
        private Vector3 _min = Vector3.positiveInfinity;
        private Vector3 _max = Vector3.negativeInfinity;

        public Extent(Quaternion frame) => _frame = frame;

        public float LargestSide => Mathf.Max(_max.x - _min.x, Mathf.Max(_max.y - _min.y, _max.z - _min.z));

        public Vector3 WorldCenter => Quaternion.Inverse(_frame) * ((_min + _max) / 2f);

        public Bounds ToBounds()
        {
            var bounds = new Bounds();
            bounds.SetMinMax(_min, _max);
            return bounds;
        }

        public void Add(Renderer renderer)
        {
            if (renderer is MeshRenderer && renderer.TryGetComponent(out MeshFilter filter) && filter.sharedMesh != null)
                AddBox(renderer.transform, filter.sharedMesh.bounds.center, filter.sharedMesh.bounds.size);
            else
                AddWorld(renderer.bounds);
        }

        public void Add(Collider collider)
        {
            var transform = collider.transform;
            switch (collider)
            {
                case BoxCollider box:
                    AddBox(transform, box.center, box.size);
                    break;
                case MeshCollider mesh when mesh.sharedMesh != null:
                    AddBox(transform, mesh.sharedMesh.bounds.center, mesh.sharedMesh.bounds.size);
                    break;
                case SphereCollider sphere:
                    AddPoint(transform.TransformPoint(sphere.center), sphere.radius * ColliderShapes.MaxScale(transform));
                    break;
                case CapsuleCollider capsule:
                    ColliderShapes.CapsuleEnds(capsule, out var start, out var end, out var radius);
                    AddPoint(start, radius);
                    AddPoint(end, radius);
                    break;
                default:
                    AddPoint(transform.position, 0f);
                    break;
            }
        }

        public bool Touches(Extent other, float tolerance) =>
            _min.x <= other._max.x + tolerance && other._min.x <= _max.x + tolerance && _min.y <= other._max.y + tolerance && other._min.y <= _max.y + tolerance && _min.z <= other._max.z + tolerance && other._min.z <= _max.z + tolerance;

        // How far the other reaches past this one on a side where it is more than allowed: a share of this one's own width that way, so a thin fence's box is held to the
        // fence's thickness. Below it nobody sees: a floor's collider may be thick. 0 if it stays within.
        public float ReachBeyond(Extent other, float minimum, float share)
        {
            var reach = 0f;
            var down = _frame * Vector3.down;
            for (var axis = 0; axis < 3; axis++)
            {
                var allowed = Mathf.Max(minimum, share * (_max[axis] - _min[axis]));
                if (down[axis] < 0.5f && other._max[axis] - _max[axis] > allowed) reach = Mathf.Max(reach, other._max[axis] - _max[axis]);
                if (down[axis] > -0.5f && _min[axis] - other._min[axis] > allowed) reach = Mathf.Max(reach, _min[axis] - other._min[axis]);
            }

            return reach;
        }

        private void AddBox(Transform transform, Vector3 center, Vector3 size)
        {
            for (var x = -0.5f; x <= 0.5f; x += 1f)
            for (var y = -0.5f; y <= 0.5f; y += 1f)
            for (var z = -0.5f; z <= 0.5f; z += 1f)
                AddPoint(transform.TransformPoint(center + Vector3.Scale(size, new Vector3(x, y, z))), 0f);
        }

        private void AddWorld(Bounds bounds)
        {
            for (var x = -1f; x <= 1f; x += 2f)
            for (var y = -1f; y <= 1f; y += 2f)
            for (var z = -1f; z <= 1f; z += 2f)
                AddPoint(bounds.center + Vector3.Scale(bounds.extents, new Vector3(x, y, z)), 0f);
        }

        private void AddPoint(Vector3 world, float radius)
        {
            var point = _frame * world;
            _min = Vector3.Min(_min, point - Vector3.one * radius);
            _max = Vector3.Max(_max, point + Vector3.one * radius);
        }
    }

    internal readonly struct SurfaceTriangle
    {
        public readonly Vector3 A;
        public readonly Vector3 B;
        public readonly Vector3 C;
        private readonly Vector3 _ab;
        private readonly Vector3 _ac;

        public SurfaceTriangle(Vector3 a, Vector3 b, Vector3 c)
        {
            A = a;
            B = b;
            C = c;
            _ab = b - a;
            _ac = c - a;
        }

        // Where a line from `origin` along `way` meets it, and whether from behind: a mesh's faces are clockwise from their front.
        public bool Hit(Vector3 origin, Vector3 way, float reach, out float distance, out bool fromBehind)
        {
            distance = 0f;
            fromBehind = false;
            var p = Vector3.Cross(way, _ac);
            var determinant = Vector3.Dot(_ab, p);
            if (Mathf.Abs(determinant) < 1e-9f) return false;
            var inverse = 1f / determinant;
            var toOrigin = origin - A;
            var u = Vector3.Dot(toOrigin, p) * inverse;
            if (u < 0f || u > 1f) return false;
            var q = Vector3.Cross(toOrigin, _ab);
            var v = Vector3.Dot(way, q) * inverse;
            if (v < 0f || u + v > 1f) return false;
            distance = Vector3.Dot(_ac, q) * inverse;
            fromBehind = Vector3.Dot(Vector3.Cross(_ab, _ac), way) > 0f;
            return distance > 0f && distance < reach;
        }

        // How far a point is from it, squared: the nearest of its face, its sides and its corners.
        public float SquaredDistanceTo(Vector3 point)
        {
            var ap = point - A;
            float d1 = Vector3.Dot(_ab, ap), d2 = Vector3.Dot(_ac, ap);
            if (d1 <= 0f && d2 <= 0f) return ap.sqrMagnitude;
            var bp = point - B;
            float d3 = Vector3.Dot(_ab, bp), d4 = Vector3.Dot(_ac, bp);
            if (d3 >= 0f && d4 <= d3) return bp.sqrMagnitude;
            var vc = d1 * d4 - d3 * d2;
            if (vc <= 0f && d1 >= 0f && d3 <= 0f) return (ap - _ab * (d1 / (d1 - d3))).sqrMagnitude;
            var cp = point - C;
            float d5 = Vector3.Dot(_ab, cp), d6 = Vector3.Dot(_ac, cp);
            if (d6 >= 0f && d5 <= d6) return cp.sqrMagnitude;
            var vb = d5 * d2 - d1 * d6;
            if (vb <= 0f && d2 >= 0f && d6 <= 0f) return (ap - _ac * (d2 / (d2 - d6))).sqrMagnitude;
            var va = d3 * d6 - d5 * d4;
            if (va <= 0f && d4 - d3 >= 0f && d5 - d6 >= 0f) return (bp - (C - B) * ((d4 - d3) / (d4 - d3 + (d5 - d6)))).sqrMagnitude;
            var denominator = 1f / Mathf.Max(va + vb + vc, 1e-12f);
            return (ap - _ab * (vb * denominator) - _ac * (vc * denominator)).sqrMagnitude;
        }
    }

    // Triangles in cells on the ground plan, so that a line meets only what lies along it.
    internal sealed class TriangleGrid
    {
        private readonly List<SurfaceTriangle> _triangles;
        private readonly Dictionary<long, List<int>> _cells = new Dictionary<long, List<int>>();
        private readonly float _cell;
        private readonly int[] _stamps;
        private int _stamp;

        public TriangleGrid(List<SurfaceTriangle> triangles)
        {
            _triangles = triangles;
            _stamps = new int[triangles.Count];
            var low = new Vector2(float.PositiveInfinity, float.PositiveInfinity);
            var high = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
            foreach (var triangle in triangles)
            {
                low = Vector2.Min(low, Vector2.Min(Plan(triangle.A), Vector2.Min(Plan(triangle.B), Plan(triangle.C))));
                high = Vector2.Max(high, Vector2.Max(Plan(triangle.A), Vector2.Max(Plan(triangle.B), Plan(triangle.C))));
            }

            _cell = Mathf.Max(0.5f, Mathf.Max(high.x - low.x, high.y - low.y) / 64f);
            for (var index = 0; index < triangles.Count; index++)
            {
                var triangle = triangles[index];
                var from = Vector2.Min(Plan(triangle.A), Vector2.Min(Plan(triangle.B), Plan(triangle.C)));
                var to = Vector2.Max(Plan(triangle.A), Vector2.Max(Plan(triangle.B), Plan(triangle.C)));
                for (var x = Mathf.FloorToInt(from.x / _cell); x <= Mathf.FloorToInt(to.x / _cell); x++)
                for (var z = Mathf.FloorToInt(from.y / _cell); z <= Mathf.FloorToInt(to.y / _cell); z++)
                {
                    if (!_cells.TryGetValue(Key(x, z), out var list)) _cells[Key(x, z)] = list = new List<int>();
                    list.Add(index);
                }
            }
        }

        private static Vector2 Plan(Vector3 point) => new Vector2(point.x, point.z);

        private static long Key(int x, int z) => ((long)x << 32) ^ (uint)z;

        // The heights at which a line straight up meets the triangles, lowest first, and whether each from behind: it leaves a solid there, or passes under a sheet.
        public List<(float height, bool fromBehind)> HeightsAt(float x, float z, float from, float to)
        {
            var heights = new List<(float height, bool fromBehind)>();
            var origin = new Vector3(x, from, z);
            if (!_cells.TryGetValue(Key(Mathf.FloorToInt(x / _cell), Mathf.FloorToInt(z / _cell)), out var list)) return heights;
            foreach (var index in list)
            {
                if (_triangles[index].Hit(origin, Vector3.up, to - from, out var distance, out var behind)) heights.Add((from + distance, behind));
            }

            heights.Sort((a, b) => a.height.CompareTo(b.height));
            return heights;
        }

        // The nearest thing a line meets, walking the cells along it, and whether it is met from behind.
        public bool Nearest(Vector3 origin, Vector3 way, float reach, out float distance, out bool fromBehind)
        {
            _stamp++;
            distance = float.PositiveInfinity;
            fromBehind = false;
            var plan = new Vector2(way.x, way.z).magnitude;
            var step = plan > 1e-5f ? 0.5f * _cell / plan : reach + 1f;
            var last = long.MinValue;
            for (var walked = 0f; walked <= reach + step; walked += step)
            {
                var at = origin + way * Mathf.Min(walked, reach);
                var key = Key(Mathf.FloorToInt(at.x / _cell), Mathf.FloorToInt(at.z / _cell));
                if (key != last && _cells.TryGetValue(key, out var list))
                {
                    last = key;
                    foreach (var index in list)
                    {
                        if (_stamps[index] == _stamp) continue;
                        _stamps[index] = _stamp;
                        if (_triangles[index].Hit(origin, way, reach, out var here, out var behind) && here < distance)
                        {
                            distance = here;
                            fromBehind = behind;
                        }
                    }
                }

                if (distance < walked) break;
            }

            return !float.IsPositiveInfinity(distance);
        }

        public bool AnyHit(Vector3 origin, Vector3 way, float reach) => Nearest(origin, way, reach, out _, out _);

        // Whether anything lies within a distance of a point.
        public bool AnyWithin(Vector3 center, float radius)
        {
            var squared = radius * radius;
            for (var x = Mathf.FloorToInt((center.x - radius) / _cell); x <= Mathf.FloorToInt((center.x + radius) / _cell); x++)
            for (var z = Mathf.FloorToInt((center.z - radius) / _cell); z <= Mathf.FloorToInt((center.z + radius) / _cell); z++)
            {
                if (!_cells.TryGetValue(Key(x, z), out var list)) continue;
                foreach (var index in list)
                {
                    if (_triangles[index].SquaredDistanceTo(center) <= squared) return true;
                }
            }

            return false;
        }
    }

    // Where a person fits around a collider, on the ground, stepping over what is low: taken along the collider's own length and width, however it stands, so a long thin
    // wall is walked along and not sampled past. What has only backs around it is the hollow behind a wall that only has a front, and doesn't count.
    internal sealed class OpeningWalk
    {
        private const float PersonRadius = 0.3f;
        private const float PersonHeight = 1.5f;
        private const float StepHeight = 0.5f;
        private const float Margin = 0.75f;
        private const int MostPlaces = 2500;

        private readonly TriangleGrid _grid;
        private readonly Collider _collider;
        private readonly float _ground;
        private readonly Bounds _model;
        private readonly float _reach;
        private readonly Vector3 _along;
        private readonly Vector3 _across;
        private readonly Vector3[] _ways = new Vector3[8];
        private readonly int _countAlong;
        private readonly int _countAcross;
        private readonly float _cellAlong;
        private readonly float _cellAcross;
        private readonly float _spanAlong;
        private readonly float _spanAcross;
        private readonly Vector3 _middle;
        private readonly Dictionary<(int, int), Vector3> _free = new Dictionary<(int, int), Vector3>();

        public OpeningWalk(TriangleGrid grid, Collider collider, float ground, Bounds model)
        {
            _grid = grid;
            _collider = collider;
            _ground = ground;
            _model = model;
            _reach = model.size.magnitude + 1f;
            var transform = collider.transform;
            GetLocalBox(collider, out var center, out var size);
            _along = Flat(transform.right);
            _across = Flat(transform.forward);
            var scale = transform.lossyScale;
            var lengthAlong = Mathf.Abs(size.x * scale.x);
            var lengthAcross = Mathf.Abs(size.z * scale.z);
            Footprint = lengthAlong * lengthAcross;
            for (var k = 0; k < 8; k++) _ways[k] = Quaternion.AngleAxis(22.5f * k, Vector3.up) * _along;
            _spanAlong = lengthAlong + 2f * Margin;
            _spanAcross = lengthAcross + 2f * Margin;
            var step = 0.25f;
            while (Mathf.Ceil(_spanAlong / step) * Mathf.Ceil(_spanAcross / step) > MostPlaces) step *= 1.25f;
            _countAlong = Mathf.CeilToInt(_spanAlong / step);
            _countAcross = Mathf.CeilToInt(_spanAcross / step);
            _cellAlong = _spanAlong / _countAlong;
            _cellAcross = _spanAcross / _countAcross;
            _middle = transform.TransformPoint(center);
        }

        public float Footprint { get; }

        private Vector3 PlaceAt(int i, int j) => _middle + _along * ((i + 0.5f) * _cellAlong - _spanAlong / 2f) + _across * ((j + 0.5f) * _cellAcross - _spanAcross / 2f);

        // Whether a person's height is left anywhere inside the collider: on a solid wall with a box on it, nowhere, and nothing else has to be looked at.
        public bool HasRoomInside()
        {
            for (var i = 0; i < _countAlong; i++)
            for (var j = 0; j < _countAcross; j++)
            {
                var place = PlaceAt(i, j);
                if (HeadRoom(place.x, place.z, out var floor) && ColliderShapes.Contains(_collider, new Vector3(place.x, floor + StepHeight, place.z), 0f)) return true;
            }

            return false;
        }

        public void WalkAround()
        {
            for (var i = 0; i < _countAlong; i++)
            for (var j = 0; j < _countAcross; j++)
            {
                var place = PlaceAt(i, j);
                if (TryStand(place.x, place.z, out var floor)) _free[(i, j)] = new Vector3(place.x, floor, place.z);
            }
        }

        private static Vector3 Flat(Vector3 axis)
        {
            axis.y = 0f;
            return axis.sqrMagnitude > 1e-6f ? axis.normalized : Vector3.right;
        }

        private static void GetLocalBox(Collider collider, out Vector3 center, out Vector3 size)
        {
            if (collider is BoxCollider box)
            {
                center = box.center;
                size = box.size;
            }
            else
            {
                var bounds = ((MeshCollider)collider).sharedMesh.bounds;
                center = bounds.center;
                size = bounds.size;
            }
        }

        // Up through what is underfoot: a slab or a sill is stepped onto, and the inside of a solid wall is no room however high it goes.
        private bool HeadRoom(float x, float z, out float floor)
        {
            floor = _ground;
            var ceiling = float.PositiveInfinity;
            var inSolid = false;
            foreach (var (height, fromBehind) in _grid.HeightsAt(x, z, _ground, _model.max.y + PersonHeight))
            {
                if (inSolid)
                {
                    if (!fromBehind) continue;
                    inSolid = false;
                    floor = height + 0.001f;
                    if (height - _ground >= StepHeight) return false;
                }
                else if (height - _ground >= StepHeight)
                {
                    ceiling = height;
                    break;
                }
                else if (fromBehind)
                {
                    floor = height + 0.001f;
                }
                else
                {
                    inSolid = true;
                }
            }

            return !inSolid && ceiling - floor >= PersonHeight;
        }

        // Clear all round, whatever stands there: a line up runs along a post's sides, and rays pass either side of a thin bar.
        private bool BodyFits(float x, float z, float floor) =>
            !_grid.AnyWithin(new Vector3(x, floor + StepHeight + PersonRadius, z), PersonRadius) && !_grid.AnyWithin(new Vector3(x, floor + PersonHeight - PersonRadius, z), PersonRadius);

        private bool TryStand(float x, float z, out float floor)
        {
            if (!HeadRoom(x, z, out floor) || !BodyFits(x, z, floor)) return false;
            var chest = new Vector3(x, floor + 0.75f * PersonHeight, z);
            for (var k = 0; k < 8; k++)
            {
                // A back in sight: the inside of a shell.
                if (_grid.Nearest(chest, Quaternion.AngleAxis(45f * k, Vector3.up) * Vector3.right, _reach, out _, out var behind) && behind) return false;
            }

            return true;
        }

        // A way clear both ways for a whole person, with the model to both sides of it, as a door or a gap in a fence has at any angle, that this collider blocks.
        public Vector3? FindClosedWay()
        {
            foreach (var place in _free.Values)
            {
                var chest = new Vector3(place.x, place.y + 0.75f * PersonHeight, place.z);
                for (var k = 0; k < 8; k++)
                {
                    var way = _ways[k];
                    if (_grid.AnyHit(chest, way, _reach) || _grid.AnyHit(chest, -way, _reach)) continue;
                    if (!SideHit(chest, way, 90f) || !SideHit(chest, way, -90f)) continue;
                    if (Blocks(chest, way) && PersonPasses(place, way)) return chest;
                }
            }

            return null;
        }

        private bool SideHit(Vector3 chest, Vector3 way, float turn)
        {
            for (var shift = -22.5f; shift <= 22.5f; shift += 22.5f)
            {
                if (_grid.AnyHit(chest, Quaternion.AngleAxis(turn + shift, Vector3.up) * way, _reach)) return true;
            }

            return false;
        }

        // A whole body along a line, both ways, as far as the model goes: a sill stops it, and a gap between posts, where thin rays each find their way.
        private bool PersonPasses(Vector3 place, Vector3 way)
        {
            for (var sign = -1f; sign <= 1f; sign += 2f)
            {
                for (var step = 0.1f; step < _reach; step += 0.1f)
                {
                    var at = place + way * (sign * step);
                    if (!Inside2D(at) && step > 2f * PersonRadius) break;
                    if (!BodyFits(at.x, at.z, place.y)) return false;
                }
            }

            return true;
        }

        private bool Inside2D(Vector3 at) => at.x >= _model.min.x && at.x <= _model.max.x && at.z >= _model.min.z && at.z <= _model.max.z;

        // As far as the model reaches along the way: what lies beyond it isn't this door's.
        private bool Blocks(Vector3 chest, Vector3 way)
        {
            if (_collider is MeshCollider mesh && mesh.convex) return true; // a hull holds whatever lies between parts of what it wraps
            return Reaches(chest, way) || Reaches(chest, -way);
        }

        private bool Reaches(Vector3 from, Vector3 way)
        {
            var span = 0.05f;
            while (span < _reach)
            {
                var at = from + way * span;
                if (!_model.Contains(at) && span > 0.5f) return false;
                if (ColliderShapes.Contains(_collider, at, 0f)) return true;
                span += 0.02f;
            }

            return false;
        }

        // What of the collider a person can walk to from outside it.
        public float FilledArea()
        {
            if (!(_collider is BoxCollider)) return 0f;
            var reached = new HashSet<(int, int)>();
            var stack = new Stack<(int, int)>();
            foreach (var pair in _free)
            {
                if (ColliderShapes.Contains(_collider, Knee(pair.Value), 0f)) continue;
                reached.Add(pair.Key);
                stack.Push(pair.Key);
            }

            var neighbors = new[] { (1, 0), (-1, 0), (0, 1), (0, -1) };
            while (stack.Count > 0)
            {
                var (i, j) = stack.Pop();
                var from = Chest(_free[(i, j)]);
                foreach (var (di, dj) in neighbors)
                {
                    var next = (i + di, j + dj);
                    if (reached.Contains(next) || !_free.TryGetValue(next, out var place)) continue;
                    var towards = Chest(place) - from;
                    if (_grid.AnyHit(from, towards.normalized, towards.magnitude)) continue;
                    reached.Add(next);
                    stack.Push(next);
                }
            }

            return _cellAlong * _cellAcross * reached.Count(key => ColliderShapes.Contains(_collider, Knee(_free[key]), 0f));
        }

        private static Vector3 Knee(Vector3 place) => new Vector3(place.x, place.y + StepHeight, place.z);

        private static Vector3 Chest(Vector3 place) => new Vector3(place.x, place.y + 0.75f * PersonHeight, place.z);
    }

    // Points over what is drawn, by the size of each face: a wall of two triangles has its middle too. The Editor reads any mesh, Read/Write or not, except in Play Mode:
    // there one without it gives none, and the checks that need them say nothing. The bounds still count.
    internal sealed class SurfacePoints
    {
        private const int PerMesh = 600;

        // By mesh and how it is stretched: a wall that is a stretched cube has its points on its faces, by their size there, and few on its ends.
        private readonly Dictionary<(Mesh, Vector3Int), Vector3[]> _byMesh = new Dictionary<(Mesh, Vector3Int), Vector3[]>();

        public List<Vector3> PointsOn(Renderer renderer)
        {
            var points = new List<Vector3>();
            if (!(renderer is MeshRenderer) || !renderer.TryGetComponent(out MeshFilter filter) || filter.sharedMesh == null) return points;
            var scale = renderer.transform.lossyScale;
            var key = (filter.sharedMesh, Vector3Int.RoundToInt(scale * 100f));
            if (!_byMesh.TryGetValue(key, out var local))
            {
                local = Sample(filter.sharedMesh, scale);
                _byMesh[key] = local;
            }

            var matrix = renderer.transform.localToWorldMatrix;
            foreach (var point in local) points.Add(matrix.MultiplyPoint3x4(point));
            return points;
        }

        public static List<SurfaceTriangle> Triangles(IEnumerable<Renderer> models, int most)
        {
            var triangles = new List<SurfaceTriangle>();
            foreach (var renderer in models)
            {
                if (!(renderer is MeshRenderer) || !renderer.TryGetComponent(out MeshFilter filter) || filter.sharedMesh == null) continue;
                var mesh = filter.sharedMesh;
                if (!CanRead(mesh)) return null;
                var vertices = mesh.vertices;
                var indices = IndicesOf(mesh);
                if (triangles.Count + indices.Count / 3 > most) return null;
                var matrix = renderer.transform.localToWorldMatrix;
                // Mirrored in the game, its faces still look outward.
                var mirrored = matrix.determinant < 0f;
                for (var i = 0; i < indices.Count; i += 3)
                {
                    var a = matrix.MultiplyPoint3x4(vertices[indices[i]]);
                    var b = matrix.MultiplyPoint3x4(vertices[indices[i + 1]]);
                    var c = matrix.MultiplyPoint3x4(vertices[indices[i + 2]]);
                    triangles.Add(mirrored ? new SurfaceTriangle(a, c, b) : new SurfaceTriangle(a, b, c));
                }
            }

            return triangles;
        }

        private static bool CanRead(Mesh mesh) => mesh.isReadable || !Application.isPlaying;

        // A mesh may hold lines or points too, and asking for their triangles logs an error.
        private static List<int> IndicesOf(Mesh mesh)
        {
            var indices = new List<int>();
            for (var i = 0; i < mesh.subMeshCount; i++)
            {
                if (mesh.GetTopology(i) == MeshTopology.Triangles) indices.AddRange(mesh.GetTriangles(i));
            }

            return indices;
        }

        private static Vector3[] Sample(Mesh mesh, Vector3 scale)
        {
            if (!CanRead(mesh)) return new Vector3[0];
            var vertices = mesh.vertices;
            var indices = IndicesOf(mesh);
            var total = 0f;
            for (var i = 0; i < indices.Count; i += 3)
                total += Vector3.Cross(Vector3.Scale(vertices[indices[i + 1]] - vertices[indices[i]], scale), Vector3.Scale(vertices[indices[i + 2]] - vertices[indices[i]], scale)).magnitude;
            var points = new List<Vector3>();
            if (total <= 0f) return points.ToArray();
            for (var i = 0; i < indices.Count; i += 3)
            {
                Vector3 a = vertices[indices[i]], b = vertices[indices[i + 1]], c = vertices[indices[i + 2]];
                var share = Vector3.Cross(Vector3.Scale(b - a, scale), Vector3.Scale(c - a, scale)).magnitude / total;
                var steps = Mathf.CeilToInt(Mathf.Sqrt(share * PerMesh));
                for (var u = 0; u < steps; u++)
                for (var v = 0; v < steps - u; v++)
                    points.Add(a + (b - a) * ((u + 0.33f) / steps) + (c - a) * ((v + 0.33f) / steps));
            }

            return points.ToArray();
        }
    }
}
