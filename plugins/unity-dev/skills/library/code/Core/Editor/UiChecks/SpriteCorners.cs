using System.Collections.Generic;
using UnityEngine;

namespace ProjectName.Core.Editor.UiChecks
{
    // Measures how round a sprite's corners really are, from its alpha. Works on textures that aren't readable,
    // by copying them through a render texture. Sprite borders only say where slicing happens, not the shape.
    internal sealed class SpriteCorners
    {
        private const float Opaque = 0.5f;

        private readonly Dictionary<Sprite, float> _cache = new Dictionary<Sprite, float>();

        // The corner radius in sprite pixels; 0 for a square corner, a negative value when it can't be measured.
        public float RadiusPixels(Sprite sprite)
        {
            if (_cache.TryGetValue(sprite, out var known)) return known;
            var radius = Measure(sprite);
            _cache[sprite] = radius;
            return radius;
        }

        private static float Measure(Sprite sprite)
        {
            var texture = sprite.texture;
            if (texture == null) return -1f;
            var rect = sprite.textureRect;
            var width = (int)rect.width;
            var height = (int)rect.height;
            if (width < 3 || height < 3) return 0f;

            var active = RenderTexture.active;
            var target = RenderTexture.GetTemporary(texture.width, texture.height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear);
            var copy = new Texture2D(width, height, TextureFormat.RGBA32, false, true);
            try
            {
                Graphics.Blit(texture, target);
                RenderTexture.active = target;
                copy.ReadPixels(new Rect(rect.x, rect.y, width, height), 0, 0);
                copy.Apply(false);
                return RadiusFrom(copy.GetPixels32(), width, height);
            }
            finally
            {
                RenderTexture.active = active;
                RenderTexture.ReleaseTemporary(target);
                Object.DestroyImmediate(copy);
            }
        }

        // Where the shape's own bounds begin: padding around it doesn't count as roundness. On a circular corner of radius
        // r, the top row's first opaque pixel sits d in from the edge, where (r - d)^2 + (r - 0.5)^2 = r^2, so
        // r = d + 0.5 + sqrt(d).
        private static float RadiusFrom(Color32[] pixels, int width, int height)
        {
            var threshold = (byte)(Opaque * 255f);
            int top = -1, left = width;
            for (var y = height - 1; y >= 0; y--)
            {
                for (var x = 0; x < width; x++)
                {
                    if (pixels[y * width + x].a < threshold) continue;
                    if (top < 0) top = y;
                    if (x < left) left = x;
                }
            }

            if (top < 0) return -1f;
            for (var x = left; x < width; x++)
            {
                if (pixels[top * width + x].a < threshold) continue;
                var inset = x - left;
                return inset == 0 ? 0f : inset + 0.5f + Mathf.Sqrt(inset);
            }

            return -1f;
        }
    }
}
