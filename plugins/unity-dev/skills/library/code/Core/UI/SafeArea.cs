using UnityEngine;

namespace Company.Product.Core.UI
{
    // Fits this RectTransform to Screen.safeArea. Put it on a full-screen container under a screen-space canvas,
    // with the interactive content inside it; backgrounds stay outside so they still fill the screen.
    // Checked before canvases render rather than on resize: a 180° rotation moves the notch without changing the size.
    [RequireComponent(typeof(RectTransform))]
    [DisallowMultipleComponent]
    public sealed class SafeArea : MonoBehaviour
    {
        private RectTransform _rectTransform;
        private Rect _appliedSafeArea;
        private Vector2Int _appliedScreenSize;

        private void Awake() => _rectTransform = (RectTransform)transform;

        private void OnEnable()
        {
            Canvas.preWillRenderCanvases += Apply;
            Apply();
        }

        private void OnDisable() => Canvas.preWillRenderCanvases -= Apply;

        private void Apply()
        {
            var safeArea = Screen.safeArea;
            var screenSize = new Vector2Int(Screen.width, Screen.height);
            if (screenSize.x <= 0 || screenSize.y <= 0) return;
            if (safeArea == _appliedSafeArea && screenSize == _appliedScreenSize) return;

            _appliedSafeArea = safeArea;
            _appliedScreenSize = screenSize;
            var (anchorMin, anchorMax) = CalculateAnchors(safeArea, screenSize);
            _rectTransform.anchorMin = anchorMin;
            _rectTransform.anchorMax = anchorMax;
            _rectTransform.offsetMin = Vector2.zero;
            _rectTransform.offsetMax = Vector2.zero;
        }

        internal static (Vector2 AnchorMin, Vector2 AnchorMax) CalculateAnchors(Rect safeArea, Vector2Int screenSize)
        {
            var anchorMin = new Vector2(safeArea.xMin / screenSize.x, safeArea.yMin / screenSize.y);
            var anchorMax = new Vector2(safeArea.xMax / screenSize.x, safeArea.yMax / screenSize.y);
            return (Vector2.Max(Vector2.zero, anchorMin), Vector2.Min(Vector2.one, anchorMax));
        }
    }
}
