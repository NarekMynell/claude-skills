using UnityEngine;

namespace ProjectName.Core.Motion
{
    // What a body's size says about its walk. Bodies of different sizes move alike at the same Froude number.
    public static class Gait
    {
        private const float Gravity = 9.81f;
        private const float ComfortableFroude = 0.2f;

        // A human must break into a run above this, whatever the leg's length.
        public const float MaxWalkingFroude = 0.5f;

        public static float Froude(float speed, float legLength) => speed * speed / (Gravity * legLength);

        // About 1.3 m/s on human legs, 0.75 m/s on a chibi's 0.3 m.
        public static float ComfortableWalkSpeed(float legLength) => Mathf.Sqrt(ComfortableFroude * Gravity * legLength);

        // Full cycles per second of a comfortable walk, from Alexander's stride formula: about 1 for a person, and faster
        // on shorter legs. A clip played far above this patters, far below it floats.
        public static float ComfortableCyclesPerSecond(float legLength) =>
            ComfortableWalkSpeed(legLength) / (2.3f * Mathf.Pow(ComfortableFroude, 0.3f) * legLength);

        // Thigh and shin, as this character really is, scale included.
        public static float LegLength(Animator animator)
        {
            var hip = animator.GetBoneTransform(HumanBodyBones.LeftUpperLeg).position;
            var knee = animator.GetBoneTransform(HumanBodyBones.LeftLowerLeg).position;
            var ankle = animator.GetBoneTransform(HumanBodyBones.LeftFoot).position;
            return (knee - hip).magnitude + (ankle - knee).magnitude;
        }
    }
}
