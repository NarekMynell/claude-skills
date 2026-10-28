# UI

`SafeArea` fits its RectTransform to `Screen.safeArea` and reapplies it whenever the safe area changes. It checks before canvases render instead of on resize, because a 180° rotation moves a notch without changing the screen size.

- **Destination:** `Core/UI/`
- **Depends on:** nothing.

Put it on a full-screen container under a screen-space canvas and place the interactive content inside it. Backgrounds stay outside the container, so they still fill the screen. Check it in the Device Simulator with notched devices.
