using System;
using NUnit.Framework;
using ProjectName.Core.Motion;
using UnityEngine;

namespace ProjectName.Core.Tests.Motion
{
    public sealed class FootSlideMeterTests
    {
        private const float Dt = 1f / 60f;
        private const float Leg = 0.8f;
        private const float Cycle = 1f;
        private const float Stance = 0.6f;
        private const float Lift = 0.1f;

        // A foot over a few cycles: on the ground for 60% of each, lifted in the rest, while the body moves at bodySpeed.
        // In stance it moves at slideSpeed for the part of the stance that slideWindow covers.
        private static FootSlideMeter Walk(float slideSpeed, float slideWindow = 1f, float seconds = 4f, float swingSpeed = 3f)
        {
            var meter = new FootSlideMeter(Leg);
            var position = 0f;
            for (var t = 0f; t < seconds; t += Dt)
            {
                var phase = t % Cycle / Cycle;
                var planted = phase < Stance;
                var height = planted ? 0f : Lift * Mathf.Sin(Mathf.PI * (phase - Stance) / (1f - Stance));
                position += (planted ? (phase < Stance * slideWindow ? slideSpeed : 0f) : swingSpeed) * Dt;
                meter.Sample(new Vector3(0f, height, position));
            }

            return meter;
        }

        [Test]
        public void AFootThatStaysPut_Passes()
        {
            var meter = Walk(slideSpeed: 0f);

            Assert.That(meter.Steps, Is.GreaterThanOrEqualTo(2));
            Assert.That(meter.WorstSlide, Is.LessThan(meter.AllowedSlide));
        }

        [Test]
        public void AUniformSlide_IsMeasuredPerStep()
        {
            var meter = Walk(slideSpeed: 0.5f);

            Assert.That(meter.WorstSlide, Is.EqualTo(0.5f * Stance * Cycle).Within(0.06f));
            Assert.That(meter.WorstSlide, Is.GreaterThan(meter.AllowedSlide));
        }

        // A slide over part of the stance is still a slide: the slowest stretch of the stance would hide it.
        [Test]
        public void ASlideOverPartOfTheStance_IsCaught()
        {
            var meter = Walk(slideSpeed: 1.8f, slideWindow: 0.4f);

            Assert.That(meter.WorstSlide, Is.GreaterThan(0.3f));
        }

        [Test]
        public void ASmallUniformSlideAboveTheLimit_IsCaught()
        {
            Assert.That(Walk(slideSpeed: 0.16f).WorstSlide, Is.GreaterThan(new FootSlideMeter(Leg).AllowedSlide));
        }

        [Test]
        public void AFootSlidingForwardAndBack_IsCaught()
        {
            var meter = new FootSlideMeter(Leg);
            for (var t = 0f; t < 4f; t += Dt)
            {
                var phase = t % Cycle / Cycle;
                var planted = phase < Stance;
                var wander = planted ? 0.2f * Mathf.Sin(2f * Mathf.PI * phase / Stance) : 0f;
                meter.Sample(new Vector3(0f, planted ? 0f : Lift, wander));
            }

            Assert.That(meter.WorstSlide, Is.GreaterThan(0.1f));
        }

        [Test]
        public void ACharacterThatNeverMoved_CannotPass()
        {
            var meter = new FootSlideMeter(Leg);
            for (var i = 0; i < 300; i++) meter.Sample(Vector3.zero);

            Assert.That(meter.Steps, Is.LessThan(2));
            Assert.That(meter.WorstSlide, Is.EqualTo(float.PositiveInfinity));
        }

        [Test]
        public void NoSamples_CannotPass() => Assert.That(new FootSlideMeter(Leg).WorstSlide, Is.EqualTo(float.PositiveInfinity));

        [Test]
        public void TheLimit_ComesFromTheLeg()
        {
            Assert.That(new FootSlideMeter(0.8f).AllowedSlide, Is.EqualTo(0.028f).Within(0.0001f));
            Assert.That(new FootSlideMeter(0.1f).AllowedSlide, Is.EqualTo(0.01f).Within(0.0001f));
        }

        [Test]
        public void ALegOfNoLength_IsRefused() => Assert.Throws<ArgumentOutOfRangeException>(() => new FootSlideMeter(0f));

        [Test]
        public void TwoActorsInsideEachOther_CountAsOnePairPerSecond_WhileTheyAreClose()
        {
            var meter = new CrowdOverlapMeter(minimumDistance: 0.5f);
            Vector3[] apart = { Vector3.zero, new Vector3(1f, 0f, 0f) };
            Vector3[] close = { Vector3.zero, new Vector3(0.2f, 3f, 0f) };

            meter.Sample(apart, 1f);
            Assert.That(meter.PairsPerSecond, Is.EqualTo(0f));

            meter.Sample(close, 1f);
            Assert.That(meter.PairsPerSecond, Is.EqualTo(0.5f));
        }

        [Test]
        public void Gait_FollowsTheBodysSize()
        {
            Assert.That(Gait.Froude(2.1f, 0.9f), Is.EqualTo(0.5f).Within(0.01f));
            Assert.That(Gait.ComfortableWalkSpeed(0.3f), Is.EqualTo(0.77f).Within(0.01f));
            Assert.That(Gait.ComfortableCyclesPerSecond(0.9f), Is.EqualTo(1.04f).Within(0.02f));
            Assert.That(Gait.ComfortableCyclesPerSecond(0.3f), Is.GreaterThan(Gait.ComfortableCyclesPerSecond(0.9f)));
        }

        [Test]
        public void ActivityShares_AddUpByState()
        {
            var shares = new ActivityShares();
            shares.Add("Resting", 3f);
            shares.Add("Walking", 1f);

            Assert.That(shares.ShareOf("Resting"), Is.EqualTo(0.75f));
            Assert.That(shares.ShareOf("Flying"), Is.EqualTo(0f));
        }
    }
}
