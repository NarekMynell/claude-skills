using System.Collections.Generic;
using System.Linq;
using System.Text;
using ProjectName.Core.Proofs;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ProjectName.Core.Editor.CostChecks
{
    // What colliders do wrong that the player runs into: walking through what looks solid, stopping at nothing, a character
    // floating over the ground or sunk in it. It reads the components and the meshes, so it needs no physics step and sees prefabs too.
    public static class ColliderAudit
    {
        private const int MaxConvexTriangles = 255;
        private const int HeavyMeshTriangles = 5000;
        private const float BeyondModelShare = 0.25f;
        private const float BeyondModelMinimum = 0.1f;
        private const float TouchTolerance = 0.1f;
        private const float CoveredShare = 0.05f;
        private const float GroundShare = 0.15f;
        private const float FeetShare = 0.05f;
        private const float MinCapsuleHeightShare = 0.6f;
        private const float MaxCapsuleHeightShare = 1.25f;
        private const float FlatShare = 0.02f;
        private const int SurfaceSamples = 600;
        private const int MaxTrianglesForOpenings = 5000;
        private const int ColumnsPerSide = 40;
        private const float PersonRadius = 0.3f;
        private const float PersonHeight = 1.5f;

        [MenuItem("Tools/Audit Colliders")]
        private static void AuditOpenScenes() => Debug.Log(AuditLoadedScenes());

        // For the Unity CLI. receiptName, such as "main", writes docs/proofs/colliders-<name>.txt. solidRoots: paths of objects under
        // which everything drawn must also stop the player, such as "Level/Walls".
        public static string AuditLoadedScenes(string receiptName = null, CostAuditOptions options = null, IEnumerable<string> solidRoots = null)
        {
            options = options ?? new CostAuditOptions();
            var text = new StringBuilder();
            var clean = true;
            for (var i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;
                var report = Run(scene.GetRootGameObjects(), options, solidRoots);
                clean &= report.IsClean;
                text.Append(scene.name).Append(": ").AppendLine(report.ToString());
            }

            if (receiptName != null) ProofReceipt.Write("colliders-" + receiptName, clean, text.ToString());
            return text.ToString();
        }

        // Actors and props that exist only as prefabs until the game spawns them.
        public static string AuditPrefabs(string folder, string receiptName = null, CostAuditOptions options = null)
        {
            options = options ?? new CostAuditOptions();
            var findings = new List<CostFinding>();
            var preview = EditorSceneManager.NewPreviewScene();
            try
            {
                foreach (var guid in AssetDatabase.FindAssets("t:Prefab", new[] { folder }))
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(AssetDatabase.GUIDToAssetPath(guid));
                    var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab, preview);
                    findings.AddRange(Run(new[] { instance }, new CostAuditOptions(), null).Findings);
                    Object.DestroyImmediate(instance);
                }
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(preview);
            }

            var report = new SceneCostReport(findings, options);
            if (receiptName != null) ProofReceipt.Write("colliders-" + receiptName, report.IsClean, report.ToString());
            return report.ToString();
        }

        public static SceneCostReport Run(IEnumerable<GameObject> roots, CostAuditOptions options, IEnumerable<string> solidRoots = null)
        {
            var findings = new List<CostFinding>();
            var rootList = roots.ToList();
            var surfaces = new Surfaces();
            var colliders = rootList.SelectMany(root => root.GetComponentsInChildren<Collider>(false)).Where(c => c.enabled).ToList();
            var bones = new HashSet<Transform>(rootList.SelectMany(root => root.GetComponentsInChildren<SkinnedMeshRenderer>(false)).SelectMany(skin => skin.bones).Where(bone => bone != null));
            // What has a shape to compare. A terrain is the ground itself, and a wheel a ray; a character's capsule is judged as one.
            var solid = colliders.Where(c => !c.isTrigger && (c is BoxCollider || c is SphereCollider || c is CapsuleCollider || c is MeshCollider)).ToList();
            foreach (var collider in colliders) CheckOne(collider, findings);
            foreach (var group in solid.GroupBy(c => Owner(c.transform, bones)))
                CheckFit(group.Key, group.ToList(), surfaces, findings);
            CheckCharacters(rootList, solid, bones, findings);
            foreach (var body in rootList.SelectMany(root => root.GetComponentsInChildren<Rigidbody>(false)))
            {
                if (body.gameObject.isStatic && !body.isKinematic)
                    findings.Add(new CostFinding("static-rigidbody", Path(body.transform), "marked static and moved by physics: it is drawn where it was baked while it moves"));
            }

            if (solidRoots != null) CheckSolid(rootList, solidRoots, solid, surfaces, findings);
            return new SceneCostReport(findings, options);
        }

        private static void CheckOne(Collider collider, List<CostFinding> findings)
        {
            if (!(collider is MeshCollider mesh)) return;
            if (mesh.sharedMesh == null)
            {
                findings.Add(new CostFinding("no-collision-mesh", Path(mesh.transform), "a Mesh Collider with no mesh: the player walks through it"));
                return;
            }

            var triangles = TriangleCount(mesh.sharedMesh);
            var body = mesh.GetComponentInParent<Rigidbody>();
            if (!mesh.convex && body != null && !body.isKinematic)
                findings.Add(new CostFinding("moving-concave", Path(mesh.transform), "a concave Mesh Collider on a moving Rigidbody: Unity doesn't simulate it, so it falls through or doesn't move. Make it convex, or use primitives"));
            if (mesh.convex && triangles > MaxConvexTriangles)
                findings.Add(new CostFinding("convex-too-big", Path(mesh.transform), $"{triangles} triangles on a convex collider: Unity builds a hull of at most {MaxConvexTriangles}, which isn't this shape"));
            if (!mesh.convex && triangles > HeavyMeshTriangles)
                findings.Add(new CostFinding("heavy-mesh-collider", Path(mesh.transform), $"{triangles} triangles to collide with: give it a simple collision mesh, or primitives"));
        }

        // Colliders count together on the thing they belong to: a compound of boxes is one shape, and a ragdoll's bones are the character's.
        private static Transform Owner(Transform collider, HashSet<Transform> bones)
        {
            if (bones.Contains(collider))
            {
                var rig = collider.GetComponentInParent<Animator>();
                return rig != null ? rig.transform : collider.root;
            }

            var body = collider.GetComponentInParent<Rigidbody>();
            if (body != null) return body.transform;
            var prefab = PrefabUtility.GetNearestPrefabInstanceRoot(collider.gameObject);
            if (prefab != null) return prefab.transform;
            return Models(collider).Any() || collider.parent == null ? collider : collider.parent;
        }

        private static IEnumerable<Renderer> Models(Transform root) =>
            root.GetComponentsInChildren<Renderer>(false).Where(r => r.enabled && (r is MeshRenderer || r is SkinnedMeshRenderer));

        // What a character's body is: its skin if it has one, so a sword's tip doesn't hide floating feet. A blob shadow on the ground isn't a body either.
        private static List<Renderer> Body(Transform root)
        {
            var models = Models(root).ToList();
            var skins = models.Where(m => m is SkinnedMeshRenderer).ToList();
            if (skins.Count > 0) return skins;
            if (models.Count == 0) return models;
            var tallest = models.Max(m => m.bounds.size.y);
            return models.Where(m => m.bounds.size.y > FlatShare * tallest).ToList();
        }

        private static void CheckFit(Transform owner, List<Collider> colliders, Surfaces surfaces, List<CostFinding> findings)
        {
            // Beside a model with a collider of its own, a collider is something else: a ramp beside a crate.
            var models = Body(owner).Where(m => !m.GetComponents<Collider>().Any(c => c.enabled && !c.isTrigger && !colliders.Contains(c))).ToList();
            if (models.Count == 0) return; // Drawn by nothing: an invisible ramp or a wall the design wants.

            // Along the model, so a wall at 45 degrees doesn't hide a box two metres off its face inside a large square around both.
            var frame = Quaternion.Inverse(models.OrderByDescending(m => m.bounds.size.sqrMagnitude).First().transform.rotation);
            var model = new Extent(frame);
            foreach (var renderer in models) model.Add(renderer);
            var solid = new Extent(frame);
            foreach (var collider in colliders) solid.Add(collider);

            if (!model.Touches(solid, TouchTolerance))
            {
                findings.Add(new CostFinding("collider-off-model", Path(owner), $"the collider is at {solid.WorldCenter}, the model at {model.WorldCenter}: the player walks through the model and hits air"));
                return;
            }

            var limit = Mathf.Max(BeyondModelMinimum, BeyondModelShare * model.LargestSide);
            var beyond = model.ReachBeyond(solid);
            if (beyond > limit)
                findings.Add(new CostFinding("collider-beyond-model", Path(owner), $"the collider reaches {beyond:0.00} m past the model: the player stops at nothing"));

            CheckStrays(colliders, models, surfaces, findings);
            CheckOpenings(colliders, models, findings);
        }

        // A box that touches nothing is a stray only where a part of the model is left without one: else it is a boundary the design wants.
        private static void CheckStrays(List<Collider> colliders, List<Renderer> models, Surfaces surfaces, List<CostFinding> findings)
        {
            var near = colliders.Select(c => (collider: c, bounds: BoundsOf(c))).ToList();
            var touched = new HashSet<Collider>();
            var uncovered = false;
            foreach (var model in models)
            {
                var points = surfaces.PointsOn(new[] { model });
                if (points.Count == 0) return;
                var reach = model.bounds;
                reach.Expand(2f * TouchTolerance);
                var covered = false;
                foreach (var (collider, bounds) in near)
                {
                    if (!bounds.Intersects(reach) || !points.Any(point => Contains(collider, point, TouchTolerance))) continue;
                    touched.Add(collider);
                    covered = true;
                }

                uncovered |= !covered;
            }

            if (!uncovered) return;
            foreach (var collider in colliders.Where(c => !touched.Contains(c)))
                findings.Add(new CostFinding("collider-off-model", Path(collider.transform), "this collider touches nothing of the model around it, and a part of the model has none: the player walks through that, and stops at air here"));
        }

        // A person fits through the model, and a box closes the way: an arch, a gate or a gap in a fence behind one collider.
        private static void CheckOpenings(List<Collider> colliders, List<Renderer> models, List<CostFinding> findings)
        {
            var boxes = colliders.OfType<BoxCollider>().ToList();
            if (boxes.Count == 0) return;
            var triangles = Surfaces.Triangles(models, MaxTrianglesForOpenings);
            if (triangles == null || triangles.Count == 0) return;
            foreach (var box in boxes)
            {
                var bounds = BoundsOf(box);
                if (bounds.size.y < PersonHeight) continue;
                var where = FindOpening(box, bounds, models, triangles);
                if (where.HasValue)
                    findings.Add(new CostFinding("collider-closes-opening", Path(box.transform), $"a person fits through the model at {where.Value}, and this collider closes it: the player stops at air. Give each part its own"));
            }
        }

        private static Vector3? FindOpening(BoxCollider box, Bounds bounds, List<Renderer> models, List<Triangle> triangles)
        {
            var step = Mathf.Max(0.2f, Mathf.Max(bounds.size.x, bounds.size.z) / ColumnsPerSide);
            var reach = bounds.size.magnitude + 1f;
            // From where the model starts: what a floor's thick collider has under it is underground.
            var ground = models.Min(m => m.bounds.min.y) - 0.01f;
            for (var x = bounds.min.x + step / 2f; x < bounds.max.x; x += step)
            for (var z = bounds.min.z + step / 2f; z < bounds.max.z; z += step)
            {
                var floor = ground;
                foreach (var ceiling in Triangle.HeightsAt(triangles, x, z, floor, bounds.max.y).Concat(new[] { bounds.max.y }))
                {
                    if (ceiling - floor >= PersonHeight)
                    {
                        var middle = new Vector3(x, floor + 0.75f * PersonHeight, z);
                        if (Contains(box, middle, 0f) && ColumnClear(triangles, x, z, floor + 0.1f, floor + PersonHeight) &&
                            (WayThrough(triangles, middle, Vector3.right, Vector3.forward, reach) || WayThrough(triangles, middle, Vector3.forward, Vector3.right, reach)))
                            return middle;
                    }

                    floor = ceiling + 0.001f;
                }
            }

            return null;
        }

        private static bool ColumnClear(List<Triangle> triangles, float x, float z, float from, float to)
        {
            foreach (var (dx, dz) in new[] { (PersonRadius, 0f), (-PersonRadius, 0f), (0f, PersonRadius), (0f, -PersonRadius) })
            {
                if (Triangle.HeightsAt(triangles, x + dx, z + dz, from, to).Any()) return false;
            }

            return true;
        }

        // Clear both ways, and the model on both sides: a door, not the hollow behind a wall that only has a front.
        private static bool WayThrough(List<Triangle> triangles, Vector3 from, Vector3 way, Vector3 side, float reach) =>
            !triangles.Any(t => t.Hit(from, way, reach, out _)) && !triangles.Any(t => t.Hit(from, -way, reach, out _)) &&
            triangles.Any(t => t.Hit(from, side, reach, out _)) && triangles.Any(t => t.Hit(from, -side, reach, out _));

        private static void CheckCharacters(List<GameObject> roots, List<Collider> solid, HashSet<Transform> bones, List<CostFinding> findings)
        {
            foreach (var controller in roots.SelectMany(root => root.GetComponentsInChildren<CharacterController>(false)).Where(c => c.enabled))
            {
                var scale = Mathf.Abs(controller.transform.lossyScale.y);
                var bottom = controller.transform.TransformPoint(controller.center).y - controller.height * scale / 2f;
                CheckStanding(controller.transform, bottom - controller.skinWidth, controller.height * scale, findings);
            }

            // On a Rigidbody: what has a rig, or what physics keeps upright. A log or a lever has a capsule too, and lies as it lies.
            foreach (var group in solid.Where(c => !bones.Contains(c.transform) && c.attachedRigidbody != null).GroupBy(c => c.attachedRigidbody))
            {
                var body = group.Key;
                var frozen = (body.constraints & RigidbodyConstraints.FreezeRotationX) != 0 && (body.constraints & RigidbodyConstraints.FreezeRotationZ) != 0;
                if (!frozen && body.GetComponentInChildren<Animator>() == null && body.GetComponentInParent<Animator>() == null && body.GetComponentInChildren<SkinnedMeshRenderer>() == null) continue;
                var bounds = BoundsOf(group.First());
                foreach (var collider in group.Skip(1)) bounds.Encapsulate(BoundsOf(collider));
                // A capsule along the back, as on an animal, says where the feet are and not how tall it is.
                var standing = group.Count() == 1 && group.First() is CapsuleCollider capsule && Mathf.Abs(Vector3.Dot(AxisOf(capsule), Vector3.up)) > 0.9f;
                CheckStanding(body.transform, bounds.min.y, standing ? bounds.size.y : (float?)null, findings);
            }

            // Read by name, so that a project without the navigation module still compiles this. A missing script comes back as null.
            foreach (var agent in roots.SelectMany(root => root.GetComponentsInChildren<Behaviour>(false)).Where(b => b != null && b.enabled && b.GetType().Name == "NavMeshAgent"))
            {
                using (var read = new SerializedObject(agent))
                {
                    var offset = read.FindProperty("m_BaseOffset");
                    if (offset != null)
                        CheckStanding(agent.transform, agent.transform.position.y - offset.floatValue * Mathf.Abs(agent.transform.lossyScale.y), null, findings);
                }
            }
        }

        private static void CheckStanding(Transform transform, float bottom, float? height, List<CostFinding> findings)
        {
            var models = Body(transform);
            if (models.Count == 0) return;
            var model = models[0].bounds;
            foreach (var renderer in models.Skip(1)) model.Encapsulate(renderer.bounds);
            var tall = model.size.y;
            if (tall <= 0f) return;
            // Arms on a first-person camera aren't a body, and neither says where the feet are.
            if (height.HasValue && model.min.y > bottom + height.Value / 2f) return;

            var feet = model.min.y - bottom;
            if (Mathf.Abs(feet) > FeetShare * tall)
                findings.Add(new CostFinding("feet-off-ground", Path(transform), feet > 0f
                    ? $"the feet stay {feet * 100f:0} cm above where it stands: the character floats"
                    : $"the feet go {-feet * 100f:0} cm below where it stands: the character sinks into the ground"));
            if (!height.HasValue) return;
            var share = height.Value / tall;
            if (share < MinCapsuleHeightShare || share > MaxCapsuleHeightShare)
                findings.Add(new CostFinding("capsule-size", Path(transform), $"the capsule is {height.Value:0.00} m, the model {tall:0.00} m: the head goes through ceilings, or it can't pass doors it fits"));
        }

        private static void CheckSolid(List<GameObject> roots, IEnumerable<string> solidRoots, List<Collider> solid, Surfaces surfaces, List<CostFinding> findings)
        {
            var wanted = solidRoots.ToList();
            foreach (var model in roots.SelectMany(root => Models(root.transform)))
            {
                var path = Path(model.transform);
                if (!wanted.Any(prefix => path == prefix || path.StartsWith(prefix + "/", System.StringComparison.Ordinal))) continue;
                if (!IsCovered(model, solid, surfaces))
                    findings.Add(new CostFinding("solid-without-collider", path, "it looks solid and nothing stops the player at it"));
            }
        }

        // Whatever the collider hangs on: what counts is that it is there. A collider for the whole level, or for the floor, doesn't make a wall solid.
        private static bool IsCovered(Renderer model, List<Collider> solid, Surfaces surfaces)
        {
            var near = solid.Where(c => BoundsOf(c).Intersects(model.bounds)).ToList();
            if (near.Count == 0) return false;
            // Above what stands on a floor: the foot of a wall touches the floor's collider and is no more solid for it.
            var above = model.bounds.min.y + GroundShare * model.bounds.size.y;
            var samples = surfaces.PointsOn(new[] { model }).Where(point => point.y >= above).ToList();
            if (samples.Count == 0) return true;
            return samples.Count(point => near.Any(c => Contains(c, point, TouchTolerance))) >= CoveredShare * samples.Count;
        }

        private static Vector3 AxisOf(CapsuleCollider capsule)
        {
            var axis = capsule.direction == 0 ? Vector3.right : capsule.direction == 1 ? Vector3.up : Vector3.forward;
            return (capsule.transform.rotation * axis).normalized;
        }

        private static bool Contains(Collider collider, Vector3 point, float tolerance)
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

        // The middles of a capsule's two round ends, and its radius, in metres. Its length scales along its axis, its radius by the larger of the other two.
        private static void CapsuleEnds(CapsuleCollider capsule, out Vector3 start, out Vector3 end, out float radius)
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

        private static bool InBox(Transform transform, Vector3 center, Vector3 size, Vector3 point, float tolerance)
        {
            var scale = transform.lossyScale;
            var local = transform.InverseTransformPoint(point) - center;
            return Mathf.Abs(local.x) <= size.x / 2f + tolerance / Mathf.Max(Mathf.Abs(scale.x), 1e-6f)
                   && Mathf.Abs(local.y) <= size.y / 2f + tolerance / Mathf.Max(Mathf.Abs(scale.y), 1e-6f)
                   && Mathf.Abs(local.z) <= size.z / 2f + tolerance / Mathf.Max(Mathf.Abs(scale.z), 1e-6f);
        }

        private static Bounds BoundsOf(Collider collider)
        {
            var extent = new Extent(Quaternion.identity);
            extent.Add(collider);
            return extent.ToBounds();
        }

        private static float MaxScale(Transform transform)
        {
            var scale = transform.lossyScale;
            return Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.y), Mathf.Abs(scale.z));
        }

        private static int TriangleCount(Mesh mesh)
        {
            long count = 0;
            for (var i = 0; i < mesh.subMeshCount; i++) count += mesh.GetIndexCount(i) / 3;
            return (int)count;
        }

        private static string Path(Transform element)
        {
            var path = element.name;
            for (var parent = element.parent; parent != null; parent = parent.parent) path = parent.name + "/" + path;
            return path;
        }

        // A box along a frame, around what is added to it, in metres.
        private sealed class Extent
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
                        AddPoint(transform.TransformPoint(sphere.center), sphere.radius * MaxScale(transform));
                        break;
                    case CapsuleCollider capsule:
                        CapsuleEnds(capsule, out var start, out var end, out var radius);
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

            // How far the other reaches past this one. Below it nobody sees: a floor's collider may be thick.
            public float ReachBeyond(Extent other)
            {
                var reach = 0f;
                var down = _frame * Vector3.down;
                for (var axis = 0; axis < 3; axis++)
                {
                    if (down[axis] < 0.7f) reach = Mathf.Max(reach, other._max[axis] - _max[axis]);
                    if (down[axis] > -0.7f) reach = Mathf.Max(reach, _min[axis] - other._min[axis]);
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

        private readonly struct Triangle
        {
            private readonly Vector3 _a;
            private readonly Vector3 _ab;
            private readonly Vector3 _ac;
            private readonly Vector2 _lowXz;
            private readonly Vector2 _highXz;

            public Triangle(Vector3 a, Vector3 b, Vector3 c)
            {
                _a = a;
                _ab = b - a;
                _ac = c - a;
                _lowXz = new Vector2(Mathf.Min(a.x, b.x, c.x), Mathf.Min(a.z, b.z, c.z));
                _highXz = new Vector2(Mathf.Max(a.x, b.x, c.x), Mathf.Max(a.z, b.z, c.z));
            }

            public bool Hit(Vector3 origin, Vector3 way, float reach, out float distance)
            {
                distance = 0f;
                var p = Vector3.Cross(way, _ac);
                var determinant = Vector3.Dot(_ab, p);
                if (Mathf.Abs(determinant) < 1e-9f) return false;
                var inverse = 1f / determinant;
                var toOrigin = origin - _a;
                var u = Dot(toOrigin, p) * inverse;
                if (u < 0f || u > 1f) return false;
                var q = Vector3.Cross(toOrigin, _ab);
                var v = Dot(way, q) * inverse;
                if (v < 0f || u + v > 1f) return false;
                distance = Dot(_ac, q) * inverse;
                return distance > 0f && distance < reach;
            }

            // The heights at which a line straight up meets the triangles, lowest first.
            public static List<float> HeightsAt(List<Triangle> triangles, float x, float z, float from, float to)
            {
                var heights = new List<float>();
                var origin = new Vector3(x, from, z);
                foreach (var triangle in triangles)
                {
                    if (x < triangle._lowXz.x || x > triangle._highXz.x || z < triangle._lowXz.y || z > triangle._highXz.y) continue;
                    if (triangle.Hit(origin, Vector3.up, to - from, out var distance)) heights.Add(from + distance);
                }

                heights.Sort();
                return heights;
            }

            private static float Dot(Vector3 a, Vector3 b) => a.x * b.x + a.y * b.y + a.z * b.z;
        }

        // Points over what is drawn, by the size of each face: a wall of two triangles has its middle too. The Editor reads any mesh, Read/Write or
        // not, except in Play Mode: there one without it gives none, and the checks that need them say nothing. The bounds still count.
        private sealed class Surfaces
        {
            private readonly Dictionary<Mesh, Vector3[]> _byMesh = new Dictionary<Mesh, Vector3[]>();

            public List<Vector3> PointsOn(IEnumerable<Renderer> models)
            {
                var points = new List<Vector3>();
                foreach (var renderer in models)
                {
                    if (!(renderer is MeshRenderer) || !renderer.TryGetComponent(out MeshFilter filter) || filter.sharedMesh == null) continue;
                    if (!_byMesh.TryGetValue(filter.sharedMesh, out var local))
                    {
                        local = Sample(filter.sharedMesh);
                        _byMesh[filter.sharedMesh] = local;
                    }

                    var matrix = renderer.transform.localToWorldMatrix;
                    foreach (var point in local) points.Add(matrix.MultiplyPoint3x4(point));
                }

                return points;
            }

            public static List<Triangle> Triangles(IEnumerable<Renderer> models, int most)
            {
                var triangles = new List<Triangle>();
                foreach (var renderer in models)
                {
                    if (!(renderer is MeshRenderer)) continue;
                    if (!renderer.TryGetComponent(out MeshFilter filter) || filter.sharedMesh == null || !CanRead(filter.sharedMesh)) return null;
                    var mesh = filter.sharedMesh;
                    var vertices = mesh.vertices;
                    var indices = mesh.triangles;
                    if (triangles.Count + indices.Length / 3 > most) return null;
                    var matrix = renderer.transform.localToWorldMatrix;
                    for (var i = 0; i < indices.Length; i += 3)
                        triangles.Add(new Triangle(matrix.MultiplyPoint3x4(vertices[indices[i]]), matrix.MultiplyPoint3x4(vertices[indices[i + 1]]), matrix.MultiplyPoint3x4(vertices[indices[i + 2]])));
                }

                return triangles;
            }

            private static bool CanRead(Mesh mesh) => mesh.isReadable || !Application.isPlaying;

            private static Vector3[] Sample(Mesh mesh)
            {
                if (!CanRead(mesh)) return new Vector3[0];
                var vertices = mesh.vertices;
                var indices = mesh.triangles;
                var total = 0f;
                for (var i = 0; i < indices.Length; i += 3)
                    total += Vector3.Cross(vertices[indices[i + 1]] - vertices[indices[i]], vertices[indices[i + 2]] - vertices[indices[i]]).magnitude;
                var points = new List<Vector3>();
                if (total <= 0f) return points.ToArray();
                for (var i = 0; i < indices.Length; i += 3)
                {
                    Vector3 a = vertices[indices[i]], b = vertices[indices[i + 1]], c = vertices[indices[i + 2]];
                    var share = Vector3.Cross(b - a, c - a).magnitude / total;
                    var steps = Mathf.Max(1, Mathf.CeilToInt(Mathf.Sqrt(share * SurfaceSamples)));
                    for (var u = 0; u < steps; u++)
                    for (var v = 0; v < steps - u; v++)
                        points.Add(a + (b - a) * ((u + 0.33f) / steps) + (c - a) * ((v + 0.33f) / steps));
                }

                return points.ToArray();
            }
        }
    }
}
