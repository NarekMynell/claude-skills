# Unity setup for character animation

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require. Check each API against the project's Unity version before using it.

The components below are thin views, as the [code standards](../../code-standards/SKILL.md) want: they read the Animator and move the character, and gameplay decides what they do.

## Root motion and speed

**Root motion through a CharacterController.** A script with `OnAnimatorMove` replaces Unity's own root motion handling, whatever Apply Root Motion is set to. The Animator computes `deltaPosition` and `velocity` only while root motion is applied this way or by the checkbox.

```csharp
[RequireComponent(typeof(Animator), typeof(CharacterController))]
public sealed class RootMotionMover : MonoBehaviour
{
    private const float GroundedFallSpeed = -2f; // keeps the controller on the ground down slopes and steps

    private Animator _animator;
    private CharacterController _controller;
    private float _fallSpeed;

    private void Awake()
    {
        _animator = GetComponent<Animator>();
        _controller = GetComponent<CharacterController>();
    }

    private void OnAnimatorMove()
    {
        _fallSpeed = _controller.isGrounded ? GroundedFallSpeed : _fallSpeed + Physics.gravity.y * Time.deltaTime;
        Vector3 delta = _animator.deltaPosition; // root motion, upward included: jumps and stair clips
        delta.y += _fallSpeed * Time.deltaTime;
        _controller.Move(delta);
        transform.rotation *= _animator.deltaRotation;
    }
}
```

**In-place clips at the controller's speed.** The blend tree's thresholds are each clip's measured speed in m/s at scale 1. Feed it the real horizontal speed, and past the fastest clip raise the state's speed multiplier, a float parameter set as the state's Multiplier:

```csharp
private static readonly int SpeedId = Animator.StringToHash("Speed");
private static readonly int PlaybackId = Animator.StringToHash("Playback");

[SerializeField, Min(0.01f)] private float _fastestClipSpeed = 5.5f; // the run clip's speed at scale 1, m/s

private void UpdateLocomotion(Vector3 velocity)
{
    // In the clip's terms: a character scaled up covers more ground per step.
    float speed = new Vector3(velocity.x, 0f, velocity.z).magnitude / transform.lossyScale.y;
    _animator.SetFloat(SpeedId, speed);
    _animator.SetFloat(PlaybackId, speed > _fastestClipSpeed ? speed / _fastestClipSpeed : 1f);
}
```

**Rate.** Playback rate stays near 1, or another clip takes over.

**Measuring a clip's speed on the character.** Play the clip on the character in Play Mode with root motion applied and read `Animator.velocity`. Humanoid root motion is stored relative to the avatar's size and scaled to the character playing it, so the average velocity in the clip's import inspector can differ from its speed on this character. Measure in-place clips in Blender with `inspect_animation.py` on the character's rig (`stride_speed_mps`).

## Feet on slopes and stairs

Turn **IK Pass** on for the layer. Add float parameters `LeftFootIK` and `RightFootIK` to the controller, and curves of the same names to the locomotion clips (the clip's Curves list on the Animation tab): 1 while the foot is planted, 0 while it swings. The ground mask leaves out the stairs' ramp colliders.

```csharp
[RequireComponent(typeof(Animator))]
public sealed class FootPlacement : MonoBehaviour
{
    private static readonly int LeftFootWeightId = Animator.StringToHash("LeftFootIK");
    private static readonly int RightFootWeightId = Animator.StringToHash("RightFootIK");

    [SerializeField] private LayerMask _ground;
    [SerializeField, Min(0f)] private float _reach = 0.5f;      // how far above and below a foot to look for ground
    [SerializeField, Min(0f)] private float _maxDrop = 0.4f;    // how far the body may lower for a low foot
    [SerializeField, Min(0f)] private float _bodySpeed = 1.5f;  // how fast the body follows, m/s

    private Animator _animator;
    private float _bodyDrop;

    private void Awake() => _animator = GetComponent<Animator>();

    private void OnAnimatorIK(int layerIndex)
    {
        float left = Place(AvatarIKGoal.LeftFoot, _animator.GetFloat(LeftFootWeightId), _animator.leftFeetBottomHeight);
        float right = Place(AvatarIKGoal.RightFoot, _animator.GetFloat(RightFootWeightId), _animator.rightFeetBottomHeight);
        float drop = Mathf.Min(Mathf.Max(left, right), _maxDrop);
        _bodyDrop = Mathf.MoveTowards(_bodyDrop, drop, _bodySpeed * Time.deltaTime);
        _animator.bodyPosition += Vector3.down * _bodyDrop;
    }

    // Puts a planted foot on the ground under it. Returns how far below the animated foot that ground is.
    private float Place(AvatarIKGoal goal, float weight, float soleHeight)
    {
        Vector3 foot = _animator.GetIKPosition(goal);
        var ray = new Ray(foot + Vector3.up * _reach, Vector3.down);
        if (weight <= 0f || !Physics.Raycast(ray, out RaycastHit hit, _reach * 2f, _ground, QueryTriggerInteraction.Ignore))
        {
            _animator.SetIKPositionWeight(goal, 0f);
            _animator.SetIKRotationWeight(goal, 0f);
            return 0f;
        }

        Vector3 target = hit.point + Vector3.up * soleHeight;
        _animator.SetIKPositionWeight(goal, weight);
        _animator.SetIKRotationWeight(goal, weight);
        _animator.SetIKPosition(goal, target);
        _animator.SetIKRotation(goal, Quaternion.FromToRotation(Vector3.up, hit.normal) * _animator.GetIKRotation(goal));
        return Mathf.Max(0f, foot.y - target.y) * weight;
    }
}
```

`bodyPosition` is the body's center of mass, set only inside `OnAnimatorIK`. `leftFeetBottomHeight` and `rightFeetBottomHeight` are each foot's sole height under its IK goal.

## Held props

- **Sockets:** an empty under each hand bone at the grip point, with the project's axis convention: for example +Z along the handle toward the thumb and +Y out of the back of the hand. A prop's origin is its grip, with the same axes, so `prop.SetParent(socket, false)` holds it exactly. With Optimize Game Objects on, the socket stays only when it's listed in Extra Transforms to Expose.
- **Grip pose layer:** an override layer above locomotion with an Avatar Mask that enables only the fingers (LeftFingers and RightFingers). It plays a one-frame clip per grip (sword, rifle, cup), and its weight goes to 1 while a prop is held.
- **Second hand:** in `OnAnimatorIK`, `SetIKPosition` and `SetIKRotation` for the other hand's goal at the prop's second grip transform, with a hint (`SetIKHintPosition`) or a Two Bone IK constraint so the elbow bends the right way.

## Arms that cut the body

On the character's own avatar, Configure Avatar > Muscles & Settings: narrow the arm ranges until the retargeted clips keep the hands outside the body. Never change the clips' avatars. Then check the clips again in Play Mode.
