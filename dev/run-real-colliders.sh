#!/usr/bin/env bash
# Runs ColliderAudit over the prefabs and scenes in Unity's built-in package samples, and compares what it says with
# dev/library-tests/real_colliders_expected.txt: the same idea as dev/run-real-assets.sh, for colliders. A check gets its clean cases from
# work it didn't help build. Only prefabs, scenes and models are copied into the test project, for the length of the run; nothing of Unity's stays.
# Usage: dev/run-real-colliders.sh [path-to-Unity-binary] [path-to-BuiltInPackages]
set -uo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
project="$root/dev/library-tests"
version="$(sed -n 's/^m_EditorVersion: *//p' "$project/ProjectSettings/ProjectVersion.txt")"
unity="${1:-/Applications/Unity/Hub/Editor/$version/Unity.app/Contents/MacOS/Unity}"
packages="${2:-/Applications/Unity/Hub/Editor/$version/Unity.app/Contents/Resources/PackageManager/BuiltInPackages}"
if [ ! -d "$packages" ]; then
  echo "no Unity packages at $packages: pass the folder as the second argument"
  exit 0
fi
expected="$project/real_colliders_expected.txt"
temp="$project/Assets/RealAssetsTemp"
out="$(mktemp)"
trap 'rm -rf "$temp" "$temp.meta" "$out"' EXIT

rsync -a --delete --exclude '*.meta' "$root/plugins/unity-dev/skills/library/code/" "$project/Assets/_Project/Scripts/"
mkdir -p "$temp/Editor"
# Unity skips what ends in a tilde, so each package's Samples~ comes in as Samples.
for samples in "$packages"/*/Samples~; do
  [ -d "$samples" ] || continue
  package="$(basename "$(dirname "$samples")")"
  rsync -a --prune-empty-dirs --include='*/' --include='*.prefab' --include='*.prefab.meta' --include='*.unity' --include='*.unity.meta' \
    --include='*.fbx' --include='*.fbx.meta' --include='*.FBX' --include='*.FBX.meta' --exclude='*' "$samples/" "$temp/Packages/$package/Samples/"
done
cat > "$temp/Editor/RealColliders.asmdef" <<'ASMDEF'
{ "name": "RealColliders", "references": ["ProjectName.Core", "ProjectName.Core.Editor"], "includePlatforms": ["Editor"] }
ASMDEF
cat > "$temp/Editor/RealColliders.cs" <<'CODE'
using System.IO;
using System.Linq;
using ProjectName.Core.Editor.CostChecks;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class RealColliders
{
    public static void Run()
    {
        var lines = new System.Collections.Generic.List<string>();
        var checkedCount = 0;
        foreach (var guid in AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/RealAssetsTemp/Packages" }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null || prefab.GetComponentInChildren<Collider>(true) == null) continue;
            var preview = EditorSceneManager.NewPreviewScene();
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab, preview);
            checkedCount++;
            Say(lines, path, instance == null ? new GameObject[0] : new[] { instance });
            EditorSceneManager.ClosePreviewScene(preview);
        }

        foreach (var guid in AssetDatabase.FindAssets("t:Scene", new[] { "Assets/RealAssetsTemp/Packages" }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            var scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
            var roots = scene.GetRootGameObjects();
            if (!roots.Any(r => r.GetComponentInChildren<Collider>(true) != null)) continue;
            checkedCount++;
            Say(lines, path, roots);
        }

        lines.Add("REAL checked\t" + checkedCount);
        File.WriteAllLines(System.Environment.GetEnvironmentVariable("REAL_COLLIDERS_OUT"), lines);
    }

    private static void Say(System.Collections.Generic.List<string> lines, string path, GameObject[] roots)
    {
        var report = ColliderAudit.Run(roots, new CostAuditOptions());
        var name = path.Substring("Assets/RealAssetsTemp/Packages/".Length);
        foreach (var finding in report.Findings)
        {
            lines.Add("REAL\t" + name + "\t" + finding.Rule + "\t" + finding.Subject);
            lines.Add("DETAIL\t" + name + "\t" + finding);
        }
    }
}
CODE
REAL_COLLIDERS_OUT="$out" perl -e 'alarm shift; exec @ARGV' 3600 "$unity" -batchmode -quit -projectPath "$project" -executeMethod RealColliders.Run -logFile "$project/Logs/real-colliders.log"
if ! grep -q '^REAL checked' "$out"; then
  echo "nothing ran: see $project/Logs/real-colliders.log"
  grep -E 'error CS|Exception' "$project/Logs/real-colliders.log" | head -n 20
  exit 1
fi
grep '^DETAIL	' "$out" | cut -f 2- > "$project/Logs/real-colliders.txt"
found="$(grep '^REAL	' "$out" | cut -f 2- | LC_ALL=C sort -u)"
echo "$(grep '^REAL checked' "$out" | cut -f 2) prefabs and scenes with colliders, $(printf '%s' "$found" | grep -c '') findings"
if [ "${UPDATE:-}" = 1 ]; then
  { sed -n '/^#/p' "$expected" 2> /dev/null; printf '%s\n' "$found"; } > "$expected.new"
  mv "$expected.new" "$expected"
  echo "updated the list"
  exit 0
fi
if diff <(sed '/^#/d' "$expected" 2> /dev/null) <(printf '%s\n' "$found"); then
  echo "as expected"
else
  echo "differs from $expected (< expected, > now)"
  exit 1
fi
