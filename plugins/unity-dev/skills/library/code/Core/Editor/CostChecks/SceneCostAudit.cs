using System.Collections.Generic;
using System.Linq;
using System.Text;
using ProjectName.Core.Proofs;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace ProjectName.Core.Editor.CostChecks
{
    // Lists what a scene pays for and might not need to: realtime lights, objects that never move but aren't static,
    // animation and particles that run off screen, readable meshes, uncompressed textures. Each finding is fixed, or
    // accepted with its reason, such as "the look needs it". Costs on the device come from the Profiler.
    public static class SceneCostAudit
    {
        [MenuItem("Tools/Audit Scene Cost")]
        private static void AuditOpenScenes() => Debug.Log(AuditLoadedScenes());

        // For the Unity CLI. receiptName, such as "main", writes docs/proofs/scene-cost-<name>.txt.
        public static string AuditLoadedScenes(string receiptName = null, CostAuditOptions options = null)
        {
            options = options ?? new CostAuditOptions();
            var text = new StringBuilder();
            var clean = true;
            for (var i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;
                var report = Run(scene.GetRootGameObjects(), options);
                clean &= report.IsClean;
                text.Append(scene.name).Append(": ").AppendLine(report.ToString());
            }

            if (receiptName != null) ProofReceipt.Write("scene-cost-" + receiptName, clean, text.ToString());
            return text.ToString();
        }

        public static SceneCostReport Run(IEnumerable<GameObject> roots, CostAuditOptions options)
        {
            var findings = new List<CostFinding>();
            var rootList = roots.ToList();
            foreach (var light in Components<Light>(rootList)) CheckLight(light, findings);
            foreach (var animator in Components<Animator>(rootList)) CheckAnimator(animator, findings);
            foreach (var skinned in Components<SkinnedMeshRenderer>(rootList)) CheckSkinned(skinned, findings);
            foreach (var particles in Components<ParticleSystem>(rootList)) CheckParticles(particles, findings);
            foreach (var filter in Components<MeshFilter>(rootList)) CheckMesh(filter, findings);
            var textures = new HashSet<Texture>();
            foreach (var renderer in Components<Renderer>(rootList))
            {
                CheckStatic(renderer, findings);
                foreach (var material in renderer.sharedMaterials) CollectTextures(material, textures);
            }

            foreach (var texture in textures) CheckTexture(texture, findings);
            return new SceneCostReport(findings, options);
        }

        private static IEnumerable<T> Components<T>(List<GameObject> roots) where T : Component =>
            roots.SelectMany(root => root.GetComponentsInChildren<T>(false));

        private static void CheckLight(Light light, List<CostFinding> findings)
        {
            if (!light.enabled) return;
            if (light.lightmapBakeType != LightmapBakeType.Baked)
                findings.Add(new CostFinding("runtime-light", Path(light.transform), $"{light.lightmapBakeType} {light.type} light: can its light be baked, into a lightmap, a texture or vertex colors?"));
            if (light.lightmapBakeType != LightmapBakeType.Baked && light.shadows != LightShadows.None)
                findings.Add(new CostFinding("runtime-shadow", Path(light.transform), $"{light.shadows} shadows render the scene again: can baked shadows, with a blob or planar shadow under what moves, give the look?"));
        }

        private static void CheckAnimator(Animator animator, List<CostFinding> findings)
        {
            if (animator.enabled && animator.cullingMode == AnimatorCullingMode.AlwaysAnimate)
                findings.Add(new CostFinding("animates-off-screen", Path(animator.transform), "Animator culling mode is Always Animate: use Cull Update Transforms or Cull Completely unless gameplay reads its bones off screen"));
        }

        private static void CheckSkinned(SkinnedMeshRenderer skinned, List<CostFinding> findings)
        {
            if (skinned.updateWhenOffscreen)
                findings.Add(new CostFinding("skins-off-screen", Path(skinned.transform), "Update When Offscreen is on: it keeps skinning a mesh nobody sees"));
        }

        private static void CheckParticles(ParticleSystem particles, List<CostFinding> findings)
        {
            if (particles.main.cullingMode == ParticleSystemCullingMode.AlwaysSimulate)
                findings.Add(new CostFinding("particles-off-screen", Path(particles.transform), "culling mode is Always Simulate: use Pause, or Pause And Catch-up"));
        }

        private static void CheckMesh(MeshFilter filter, List<CostFinding> findings)
        {
            var mesh = filter.sharedMesh;
            if (mesh == null || !mesh.isReadable) return;
            var path = AssetDatabase.GetAssetPath(mesh);
            if (string.IsNullOrEmpty(path) || path.StartsWith("Library/", System.StringComparison.Ordinal)) return;
            if (filter.GetComponent<MeshCollider>() == null)
                findings.Add(new CostFinding("readable-mesh", path, "Read/Write is on, which keeps a second copy in memory: does the CPU read this mesh?"));
        }

        // No script on it, and no Animator, animation or physics on it or its parents. A script on a parent doesn't count,
        // because one script on a level's root would hide every prop under it: NeverMovedProbe settles the doubtful ones.
        private static void CheckStatic(Renderer renderer, List<CostFinding> findings)
        {
            if (renderer is SkinnedMeshRenderer || renderer is ParticleSystemRenderer) return;
            var gameObject = renderer.gameObject;
            if (gameObject.isStatic || gameObject.GetComponents<MonoBehaviour>().Length > 0) return;
            for (var current = renderer.transform; current != null; current = current.parent)
            {
                var hasMover = current.GetComponents<Component>().Any(c => c is Animator || c is Animation || c is Rigidbody);
                if (hasMover) return;
            }

            findings.Add(new CostFinding("could-be-static", Path(renderer.transform), "nothing on it moves it, and it isn't marked static"));
        }

        private static void CollectTextures(Material material, HashSet<Texture> textures)
        {
            if (material == null || material.shader == null) return;
            foreach (var name in material.GetTexturePropertyNames())
            {
                var texture = material.GetTexture(name);
                if (texture != null) textures.Add(texture);
            }
        }

        private static void CheckTexture(Texture texture, List<CostFinding> findings)
        {
            var path = AssetDatabase.GetAssetPath(texture);
            if (!(AssetImporter.GetAtPath(path) is TextureImporter importer)) return;
            if (importer.textureCompression == TextureImporterCompression.Uncompressed)
                findings.Add(new CostFinding("uncompressed-texture", path, $"{texture.width} x {texture.height}, uncompressed"));
            if (!Mathf.IsPowerOfTwo(texture.width) || !Mathf.IsPowerOfTwo(texture.height))
                findings.Add(new CostFinding("not-power-of-two", path, $"{texture.width} x {texture.height}: some compression formats and mobile GPUs need powers of two"));
        }

        private static string Path(Transform element)
        {
            var path = element.name;
            for (var parent = element.parent; parent != null; parent = parent.parent) path = parent.name + "/" + path;
            return path;
        }
    }
}
