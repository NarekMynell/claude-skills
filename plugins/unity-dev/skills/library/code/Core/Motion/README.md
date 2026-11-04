# Motion

Measures of how characters and animals move in the running game. Clip checks can't see what real movement code does to a clip: wrong speeds, blends, avoidance pushing a character sideways.

- **Destination:** `Core/Motion/`
- **Depends on:** nothing. The test below also uses Proofs.

## FootSlideMeter

It finds each step, where the foot is at its lowest, and measures how far the foot wandered during it, in metres, by the same rule as `inspect_animation.py`. The limit comes from the leg's length, about 3 cm per step for a person. `WorstSlide` stays infinite until two steps are measured, so a character that never moved can't pass. Measure on flat ground.

`Gait` holds what a body's size says about its walk: `LegLength(animator)`, `Froude(speed, leg)`, `MaxWalkingFroude`, `ComfortableWalkSpeed(leg)` and `ComfortableCyclesPerSecond(leg)`.

`LocomotionTests`, in the project's Play Mode tests, walks each kind of mover through the real movement code at each speed it uses, at the scale it really has. It checks both feet, that the speed fits the body, and that the cadence neither patters nor floats:

```csharp
[UnityTest]
public IEnumerator Walking_LooksLikeWalking([Values(1.0f, 1.4f)] float speed)
{
    IMovable mover = SpawnVisitor();    // through the game's own factory
    Animator animator = AnimatorOf(mover);
    mover.MoveAtSpeed(Vector3.forward, speed);
    yield return new WaitForSeconds(1f);  // past the start of the walk

    float leg = Gait.LegLength(animator);
    var left = new FootSlideMeter(leg);
    var right = new FootSlideMeter(leg);
    Transform leftFoot = animator.GetBoneTransform(HumanBodyBones.LeftFoot);
    Transform rightFoot = animator.GetBoneTransform(HumanBodyBones.RightFoot);
    var elapsed = 0f;
    while (elapsed < 4f)
    {
        left.Sample(leftFoot.position);
        right.Sample(rightFoot.position);
        elapsed += Time.deltaTime;
        yield return null;
    }

    float slide = Mathf.Max(left.WorstSlide, right.WorstSlide);
    float froude = Gait.Froude(speed, leg);
    float cadence = left.Steps / elapsed / Gait.ComfortableCyclesPerSecond(leg);
    bool passed = slide <= left.AllowedSlide && froude <= Gait.MaxWalkingFroude && cadence >= 0.5f && cadence <= 1.6f;
    ProofReceipt.Write($"locomotion-visitor-{speed}", passed, $"leg {leg:0.00} m, worst slide {slide:0.000} m, limit {left.AllowedSlide:0.000} m, Froude {froude:0.00}, cadence {cadence:0.00} of comfortable");
    Assert.That(passed, $"slide {slide}, Froude {froude}, cadence {cadence}");
}
```

The cadence range is a working default from the stride formula, and a cartoon's timing may leave it on purpose: state that in the test, with the reason. The Animator must not be culled during the test: the test's camera looks at the mover, or its culling mode is Always Animate. For skinning done in a shader there is no bone to read: compute the foot's world position from the clip's table and the actor's transform, and feed that. Run the same meters on a few actors inside a crowd at peak density too: avoidance that shoves a character sideways only shows there.

## CrowdOverlapMeter

Takes all actors' positions once per frame, at the density the balance simulation predicts:

```csharp
var overlaps = new CrowdOverlapMeter(minimumDistance: 0.5f);
// Every frame:
overlaps.Sample(positions, Time.deltaTime);
// Afterwards, pairs closer than the minimum, per second:
ProofReceipt.Write("crowd-peak", overlaps.PairsPerSecond < 1f, $"{overlaps.PairsPerSecond:0.00} overlapping pairs per second");
Assert.That(overlaps.PairsPerSecond, Is.LessThan(1f));
```

`minimumDistance` is the distance at which the bodies touch; the allowed rate is the project's, for what can't be seen at game distance.

## ActivityShares

How an actor spends its time, against the species' activity budget in `docs/`, over a long run of the behavior code:

```csharp
var shares = new ActivityShares();
// Every step of the behavior code:
shares.Add(animal.CurrentState, deltaTime);
// Afterwards:
Assert.That(shares.ShareOf("Resting"), Is.GreaterThan(0.4f));
```
