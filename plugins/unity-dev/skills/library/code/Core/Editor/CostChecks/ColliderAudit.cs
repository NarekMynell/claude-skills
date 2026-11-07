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
        private const float BeyondModelMinimum = 0.25f;
        private const float TouchTolerance = 0.1f;
        private const float SameSizeFactor = 2f;
        private const float CoveredShare = 0.3f;
        private const float GroundShare = 0.15f;
        private const float WalkingHeight = 2f;
        private const float FeetShare = 0.05f;
        private const float MinCapsuleHeightShare = 0.6f;
        private const float MaxCapsuleHeightShare = 1.25f;
        private const float FlatShare = 0.02f;
        private const float ArmsShare = 0.6f;
        private const float HoverOffset = 0.5f;
        private const float ShearCosine = 0.02f;
        private const int MaxTrianglesForOpenings = 20000;
        private const float FilledMinimum = 2f;
        private const float FilledShare = 0.15f;

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
            var audit = new Audit(rootList, findings);
            audit.CheckEach();
            audit.CheckFits();
            audit.CheckCharacters();
            foreach (var body in rootList.SelectMany(root => root.GetComponentsInChildren<Rigidbody>(false)))
            {
                if (body.gameObject.isStatic && !body.isKinematic)
                    findings.Add(new CostFinding("static-rigidbody", ColliderShapes.PathOf(body.transform), "marked static and moved by physics: it is drawn where it was baked while it moves"));
            }

            if (solidRoots != null) audit.CheckSolid(solidRoots);
            return new SceneCostReport(findings, options);
        }

        private sealed class Audit
        {
            private readonly List<GameObject> _roots;
            private readonly List<CostFinding> _findings;
            private readonly List<Collider> _colliders;
            // What has a shape to compare. A terrain is the ground itself, and a wheel a ray; a character's capsule is judged as one.
            private readonly List<Collider> _solid;
            private readonly Dictionary<Collider, Bounds> _boundsOf = new Dictionary<Collider, Bounds>();
            private readonly HashSet<Transform> _bones;
            private readonly SurfacePoints _surfaces = new SurfacePoints();
            private readonly List<Renderer> _allModels;

            public Audit(List<GameObject> roots, List<CostFinding> findings)
            {
                _roots = roots;
                _findings = findings;
                _colliders = roots.SelectMany(root => root.GetComponentsInChildren<Collider>(false)).Where(c => c.enabled).ToList();
                _solid = _colliders.Where(c => !c.isTrigger && (c is BoxCollider || c is SphereCollider || c is CapsuleCollider || c is MeshCollider)).ToList();
                _bones = new HashSet<Transform>(roots.SelectMany(root => root.GetComponentsInChildren<SkinnedMeshRenderer>(false)).SelectMany(skin => skin.bones).Where(bone => bone != null));
                _allModels = roots.SelectMany(root => Models(root.transform)).ToList();
                foreach (var collider in _solid) _boundsOf[collider] = ColliderShapes.BoundsOf(collider);
            }

            public void CheckEach()
            {
                var sheared = new HashSet<Transform>();
                foreach (var collider in _solid)
                {
                    // Told once, at the top of what is sheared: a limb's every bone says the same.
                    if (!(collider is MeshCollider) && IsSheared(collider.transform))
                    {
                        var top = collider.transform;
                        while (top.parent != null && IsSheared(top.parent)) top = top.parent;
                        if (sheared.Add(top))
                            _findings.Add(new CostFinding("sheared-collider", ColliderShapes.PathOf(top), "turned under a parent scaled unevenly: what is drawn is sheared, and a collider can't be, so the player walks through one and stops at the other"));
                    }

                    if (!(collider is MeshCollider mesh)) continue;
                    if (mesh.sharedMesh == null)
                    {
                        _findings.Add(new CostFinding("no-collision-mesh", ColliderShapes.PathOf(mesh.transform), "a Mesh Collider with no mesh: the player walks through it"));
                        continue;
                    }

                    var triangles = TriangleCount(mesh.sharedMesh);
                    var body = mesh.GetComponentInParent<Rigidbody>();
                    if (!mesh.convex && body != null && !body.isKinematic)
                        _findings.Add(new CostFinding("moving-concave", ColliderShapes.PathOf(mesh.transform), "a concave Mesh Collider on a moving Rigidbody: Unity doesn't simulate it, so it falls through or doesn't move. Make it convex, or use primitives"));
                    if (mesh.convex && triangles > MaxConvexTriangles)
                        _findings.Add(new CostFinding("convex-too-big", ColliderShapes.PathOf(mesh.transform), $"{triangles} triangles on a convex collider: Unity builds a hull of at most {MaxConvexTriangles}, which isn't this shape"));
                    if (!mesh.convex && triangles > HeavyMeshTriangles)
                        _findings.Add(new CostFinding("heavy-mesh-collider", ColliderShapes.PathOf(mesh.transform), $"{triangles} triangles to collide with: give it a simple collision mesh, or primitives"));
                }
            }

            public void CheckFits()
            {
                foreach (var group in _solid.Where(c => !(c is MeshCollider m) || m.sharedMesh != null).GroupBy(c => Owner(c.transform)))
                    CheckFit(group.Key, group.ToList());
            }

            // Colliders count together on the thing they belong to: a compound of boxes is one shape, and a ragdoll's bones are the character's.
            private Transform Owner(Transform collider)
            {
                if (_bones.Contains(collider))
                {
                    var rig = collider.GetComponentInParent<Animator>();
                    return rig != null ? rig.transform : collider.root;
                }

                var body = collider.GetComponentInParent<Rigidbody>();
                if (body != null) return body.transform;
                var prefab = PrefabUtility.GetNearestPrefabInstanceRoot(collider.gameObject);
                if (prefab != null)
                {
                    // A nested prefab that only holds a collider belongs to what it is nested in.
                    if (Models(prefab.transform).Any()) return prefab.transform;
                    var outermost = PrefabUtility.GetOutermostPrefabInstanceRoot(collider.gameObject);
                    return outermost != null ? outermost.transform : prefab.transform;
                }

                return Models(collider).Any() || collider.parent == null ? collider : collider.parent;
            }

            private void CheckFit(Transform owner, List<Collider> colliders)
            {
                // Beside a model with a collider of its own, a collider is something else: a ramp beside a crate. A ragdoll's bones fit the skin, not the sword it carries.
                var candidates = colliders.All(c => _bones.Contains(c.transform)) ? Body(owner) : Models(owner).ToList();
                var models = candidates.Where(m => !m.GetComponents<Collider>().Any(c => c.enabled && !c.isTrigger && !colliders.Contains(c))).ToList();
                if (models.Count == 0) return; // Drawn by nothing: an invisible ramp or a wall the design wants.

                // Along the model, so a wall at 45 degrees doesn't hide a box two metres off its face inside a large square around both.
                var frame = Quaternion.Inverse(models.OrderByDescending(m => m.bounds.size.sqrMagnitude).First().transform.rotation);
                var model = new Extent(frame);
                foreach (var renderer in models) model.Add(renderer);
                var solid = new Extent(frame);
                foreach (var collider in colliders) solid.Add(collider);

                if (!model.Touches(solid, Mathf.Min(TouchTolerance, 0.1f * model.LargestSide)))
                {
                    // On the model, or of its size. An 8 m boundary beside a bush is a boundary.
                    var onModel = colliders.Any(c => models.Any(m => c.transform == m.transform || c.transform.IsChildOf(m.transform)));
                    if (onModel || (model.LargestSide <= SameSizeFactor * solid.LargestSide && solid.LargestSide <= SameSizeFactor * model.LargestSide))
                        _findings.Add(new CostFinding("collider-off-model", ColliderShapes.PathOf(owner), $"the collider is at {solid.WorldCenter}, the model at {model.WorldCenter}: the player walks through the model and hits air"));
                    return;
                }

                var touched = CheckStrays(colliders, models);
                var beyond = model.ReachBeyond(solid, BeyondModelMinimum, BeyondModelShare);
                if (beyond > 0f)
                    _findings.Add(new CostFinding("collider-beyond-model", ColliderShapes.PathOf(owner), $"the collider reaches {beyond:0.00} m past the model: the player stops at nothing"));
                else
                    CheckOpenings(colliders.Where(touched.Contains).ToList(), models);
            }

            // How close a collider has to be to count on a model: a rock's sphere sits well inside it, a wall's box on it.
            private static float ToleranceFor(Renderer model)
            {
                var size = model.bounds.size;
                return Mathf.Max(TouchTolerance, 0.3f * Mathf.Min(size.x, size.y, size.z));
            }

            // Whether the part of a model that stands at walking height has a collider on it: its foot on a floor's collider isn't that, nor a tree's crown overhead.
            private float CoveredShareOf(Renderer model, IReadOnlyCollection<Collider> colliders)
            {
                var bounds = model.bounds;
                var above = bounds.min.y + GroundShare * bounds.size.y;
                var points = _surfaces.PointsOn(model).Where(point => point.y >= above && point.y <= bounds.min.y + WalkingHeight).ToList();
                if (points.Count == 0) return 1f;
                var tolerance = ToleranceFor(model);
                var reach = bounds;
                reach.Expand(2f * tolerance);
                var near = colliders.Where(c => _boundsOf[c].Intersects(reach)).ToList();
                return points.Count(point => near.Any(c => ColliderShapes.Contains(c, point, tolerance))) / (float)points.Count;
            }

            // A box that touches nothing is a stray only where a part of the model of its size is left without one: else it is a boundary the design wants, beside a bush.
            private HashSet<Collider> CheckStrays(List<Collider> colliders, List<Renderer> models)
            {
                var touched = new HashSet<Collider>();
                var uncovered = new List<Renderer>();
                foreach (var model in models)
                {
                    var points = _surfaces.PointsOn(model);
                    if (points.Count == 0) continue;
                    var tolerance = ToleranceFor(model);
                    var reach = model.bounds;
                    reach.Expand(2f * tolerance);
                    var covered = false;
                    foreach (var collider in colliders)
                    {
                        if (!_boundsOf[collider].Intersects(reach) || !points.Any(point => ColliderShapes.Contains(collider, point, tolerance))) continue;
                        touched.Add(collider);
                        covered = true;
                    }

                    if (!covered) uncovered.Add(model);
                }

                foreach (var collider in colliders.Where(c => !touched.Contains(c)))
                {
                    var size = LongestSide(_boundsOf[collider]);
                    if (uncovered.Any(m => LongestSide(m.bounds) <= SameSizeFactor * size && size <= SameSizeFactor * LongestSide(m.bounds)))
                        _findings.Add(new CostFinding("collider-off-model", ColliderShapes.PathOf(collider.transform), "this collider touches nothing of the model around it, and a part of the model has none: the player walks through that, and stops at air here"));
                }

                return touched;
            }

            // A person fits through the model, or can walk into what it leaves open, and a collider fills it: an arch, a gate, a gap in a fence, the room behind a door, a yard.
            private void CheckOpenings(List<Collider> colliders, List<Renderer> models)
            {
                var closing = colliders.Where(c => c is BoxCollider || (c is MeshCollider m && m.sharedMesh != null && !(models.Any(r => r.TryGetComponent(out MeshFilter f) && f.sharedMesh == m.sharedMesh) && !m.convex))).ToList();
                if (closing.Count == 0) return;
                var reach = _boundsOf[closing[0]];
                foreach (var collider in closing.Skip(1)) reach.Encapsulate(_boundsOf[collider]);
                reach.Expand(1f);
                // All there is around it: a gate of its own, shut, closes the way, whoever owns it.
                var around = models.Concat(_allModels.Where(m => m.bounds.Intersects(reach))).Distinct().ToList();
                var triangles = SurfacePoints.Triangles(around, MaxTrianglesForOpenings);
                if (triangles == null || triangles.Count == 0) return;
                var grid = new TriangleGrid(triangles);
                var ground = models.Min(m => m.bounds.min.y) - 0.01f;
                var model = Union(models);
                foreach (var collider in closing)
                {
                    var walk = new OpeningWalk(grid, collider, ground, model);
                    if (!walk.HasRoomInside()) continue;
                    walk.WalkAround();
                    var door = walk.FindClosedWay();
                    if (door.HasValue)
                    {
                        _findings.Add(new CostFinding("collider-closes-opening", ColliderShapes.PathOf(collider.transform), $"a person fits through the model at {door.Value}, and this collider closes it: the player stops at air. Give each part its own"));
                        continue;
                    }

                    var filled = walk.FilledArea();
                    if (filled >= Mathf.Max(FilledMinimum, FilledShare * walk.Footprint))
                        _findings.Add(new CostFinding("collider-fills-space", ColliderShapes.PathOf(collider.transform), $"{filled:0.0} m2 a person can walk to are filled in by this collider, a corner of a yard or the room behind a door: the player stops at air. Follow the model's outline"));
                }
            }

            public void CheckCharacters()
            {
                // Also when off in the prefab, as a controller is until it spawns.
                foreach (var controller in _roots.SelectMany(root => root.GetComponentsInChildren<CharacterController>(false)))
                {
                    var scale = controller.transform.lossyScale;
                    var radius = controller.radius * Mathf.Max(Mathf.Abs(scale.x), Mathf.Abs(scale.z));
                    // Never shorter than its two round ends, and scaled the way physics does.
                    var height = Mathf.Max(controller.height * Mathf.Abs(scale.y), 2f * radius);
                    var bottom = controller.transform.TransformPoint(controller.center).y - height / 2f;
                    CheckStanding(controller.transform, bottom - controller.skinWidth, height);
                }

                // On a Rigidbody: one capsule or ball, with a skin on it, or that physics keeps upright. A car, a door or a log has a collider too, and doesn't stand on its bottom.
                foreach (var group in _solid.Where(c => !_bones.Contains(c.transform) && c.attachedRigidbody != null).GroupBy(c => c.attachedRigidbody))
                {
                    var body = group.Key;
                    if (group.Count() != 1 || !(group.First() is CapsuleCollider || group.First() is SphereCollider)) continue;
                    var frozen = (body.constraints & RigidbodyConstraints.FreezeRotationX) != 0 && (body.constraints & RigidbodyConstraints.FreezeRotationZ) != 0;
                    if (!frozen && !Body(body.transform).Any(m => m is SkinnedMeshRenderer)) continue;
                    var bounds = _boundsOf[group.First()];
                    // A capsule along the back, as on an animal, says where the feet are and not how tall it is.
                    var standing = group.First() is CapsuleCollider capsule && Mathf.Abs(Vector3.Dot(ColliderShapes.AxisOf(capsule), Vector3.up)) > 0.9f;
                    CheckStanding(body.transform, bounds.min.y, standing ? bounds.size.y : (float?)null);
                }

                // Read by name, so that a project without the navigation module still compiles this. A missing script comes back as null. One that hovers on purpose has no body of its own.
                foreach (var agent in _roots.SelectMany(root => root.GetComponentsInChildren<Behaviour>(false)).Where(b => b != null && b.GetType().Name == "NavMeshAgent"))
                {
                    using (var read = new SerializedObject(agent))
                    {
                        var offset = read.FindProperty("m_BaseOffset");
                        if (offset == null) continue;
                        // Held well off its surface, with no rig to walk with, it flies.
                        var hasRig = agent.GetComponentInChildren<Animator>() != null || agent.GetComponentInChildren<SkinnedMeshRenderer>() != null || agent.GetComponentInParent<Animator>() != null;
                        if (!hasRig && Mathf.Abs(offset.floatValue) > HoverOffset) continue;
                        CheckStanding(agent.transform, agent.transform.position.y - offset.floatValue * Mathf.Abs(agent.transform.lossyScale.y), null);
                    }
                }
            }

            private void CheckStanding(Transform transform, float bottom, float? height)
            {
                var models = Body(transform);
                // The controller and the model side by side under one object.
                if (models.Count == 0 && transform.parent != null) models = Body(transform.parent);
                if (models.Count == 0) return;
                var model = Union(models);
                var tall = model.size.y;
                if (tall <= 0f) return;
                // Arms on a first-person camera aren't a body, and say nothing of the feet. A whole body high above its capsule is a character floating.
                if (height.HasValue && tall < ArmsShare * height.Value && model.min.y > bottom + height.Value / 2f) return;

                var feet = model.min.y - bottom;
                if (Mathf.Abs(feet) > FeetShare * tall)
                    _findings.Add(new CostFinding("feet-off-ground", ColliderShapes.PathOf(transform), feet > 0f
                        ? $"the feet stay {feet * 100f:0} cm above where it stands: the character floats"
                        : $"the feet go {-feet * 100f:0} cm below where it stands: the character sinks into the ground"));
                if (!height.HasValue) return;
                var share = height.Value / tall;
                if (share < MinCapsuleHeightShare || share > MaxCapsuleHeightShare)
                    _findings.Add(new CostFinding("capsule-size", ColliderShapes.PathOf(transform), $"the capsule is {height.Value:0.00} m, the model {tall:0.00} m: the head goes through ceilings, or it can't pass doors it fits"));
            }

            public void CheckSolid(IEnumerable<string> solidRoots)
            {
                var wanted = solidRoots.ToList();
                foreach (var model in _allModels)
                {
                    var path = ColliderShapes.PathOf(model.transform);
                    if (!wanted.Any(prefix => path == prefix || path.StartsWith(prefix + "/", System.StringComparison.Ordinal))) continue;
                    if (!IsCovered(model))
                        _findings.Add(new CostFinding("solid-without-collider", path, "it looks solid and nothing stops the player at most of it"));
                }
            }

            // Whatever the collider hangs on: what counts is that it is there. A collider for the whole level, or for the floor, doesn't make a wall solid.
            private bool IsCovered(Renderer model)
            {
                var reach = model.bounds;
                reach.Expand(2f * ToleranceFor(model));
                var near = _solid.Where(c => _boundsOf[c].Intersects(reach)).ToList();
                if (near.Count == 0) return false;
                return _surfaces.PointsOn(model).Count == 0 || CoveredShareOf(model, near) >= CoveredShare;
            }
        }

        private static IEnumerable<Renderer> Models(Transform root)
        {
            // The far levels of a LOD group are the same thing again, and a card across an arch isn't there up close.
            var far = new HashSet<Renderer>(root.GetComponentsInChildren<LODGroup>(false).SelectMany(group => group.GetLODs().Skip(1)).SelectMany(level => level.renderers).Where(r => r != null));
            return root.GetComponentsInChildren<Renderer>(false).Where(r => r.enabled && (r is MeshRenderer || r is SkinnedMeshRenderer) && !far.Contains(r));
        }

        // What a character's body is: the skin if it stands taller than what is rigid, so a sword's tip doesn't hide floating feet and a cape isn't a robot. A blob shadow on the ground isn't a body either.
        private static List<Renderer> Body(Transform root)
        {
            var models = Models(root).ToList();
            if (models.Count == 0) return models;
            var skins = models.Where(m => m is SkinnedMeshRenderer).ToList();
            var rigid = models.Where(m => !(m is SkinnedMeshRenderer)).ToList();
            if (skins.Count > 0 && (rigid.Count == 0 || Union(skins).size.y >= Union(rigid).size.y)) return skins;
            var tall = Union(models).size.y;
            return rigid.Where(m => m.bounds.size.y > FlatShare * tall).ToList();
        }

        private static Bounds Union(List<Renderer> models)
        {
            var bounds = models[0].bounds;
            foreach (var renderer in models.Skip(1)) bounds.Encapsulate(renderer.bounds);
            return bounds;
        }

        private static float LongestSide(Bounds bounds) => Mathf.Max(bounds.size.x, Mathf.Max(bounds.size.y, bounds.size.z));

        private static bool IsSheared(Transform transform)
        {
            var matrix = transform.localToWorldMatrix;
            Vector3 x = matrix.GetColumn(0), y = matrix.GetColumn(1), z = matrix.GetColumn(2);
            return Mathf.Abs(Vector3.Dot(x.normalized, y.normalized)) > ShearCosine || Mathf.Abs(Vector3.Dot(y.normalized, z.normalized)) > ShearCosine || Mathf.Abs(Vector3.Dot(z.normalized, x.normalized)) > ShearCosine;
        }

        private static int TriangleCount(Mesh mesh)
        {
            long count = 0;
            for (var i = 0; i < mesh.subMeshCount; i++) count += mesh.GetIndexCount(i) / 3;
            return (int)count;
        }
    }
}
