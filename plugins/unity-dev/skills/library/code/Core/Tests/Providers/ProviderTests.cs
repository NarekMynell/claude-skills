using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Company.Product.Core.Providers;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.Providers
{
    public sealed class ProviderTests
    {
        private readonly struct Score : IEquatable<Score>
        {
            public readonly int Value;

            public Score(int value) => Value = value;

            public bool Equals(Score other) => Value == other.Value;

            public override bool Equals(object obj) => obj is Score other && Equals(other);

            public override int GetHashCode() => Value;
        }

        [Test]
        public void Subscribe_ReceivesTheCurrentValue_ThenEachChange()
        {
            var provider = new Provider<Score>(new Score(1));
            var received = new List<int>();
            provider.Subscribe(score => received.Add(score.Value));

            provider.Set(new Score(2));
            provider.Set(new Score(2));
            provider.Set(new Score(3));

            Assert.That(received, Is.EqualTo(new[] { 1, 2, 3 }));
        }

        [Test]
        public void SetWithoutNotify_ChangesSilently_AndForceNotifyDelivers()
        {
            var provider = new Provider<Score>();
            var calls = 0;
            provider.Subscribe(_ => calls++, notifyCurrentValue: false);

            provider.SetWithoutNotify(new Score(5));
            Assert.That(calls, Is.Zero);
            Assert.That(provider.Value.Value, Is.EqualTo(5));

            provider.ForceNotify();
            Assert.That(calls, Is.EqualTo(1));
        }

        [Test]
        public void DisposedSubscription_StopsReceiving_EvenWhenDisposedDuringNotification()
        {
            var provider = new Provider<Score>();
            IDisposable second = null;
            var secondCalls = 0;
            provider.Subscribe(_ => second.Dispose(), notifyCurrentValue: false);
            second = provider.Subscribe(_ => secondCalls++, notifyCurrentValue: false);

            provider.Set(new Score(1));
            provider.Set(new Score(2));

            Assert.That(secondCalls, Is.Zero);
        }

        [Test]
        public void ThrowingSubscriber_IsLogged_AndOthersStillReceive()
        {
            var provider = new Provider<Score>();
            var received = 0;
            provider.Subscribe(_ => throw new InvalidOperationException("boom"), notifyCurrentValue: false);
            provider.Subscribe(_ => received++, notifyCurrentValue: false);

            LogAssert.Expect(LogType.Exception, new Regex("boom"));
            provider.Set(new Score(1));

            Assert.That(received, Is.EqualTo(1));
        }

        [Test]
        public void SetDuringNotification_EverySubscriberEndsOnTheNewestValue()
        {
            var provider = new Provider<Score>();
            var last = new int[2];
            provider.Subscribe(score =>
            {
                last[0] = score.Value;
                if (score.Value == 1) provider.Set(new Score(2));
            }, notifyCurrentValue: false);
            provider.Subscribe(score => last[1] = score.Value, notifyCurrentValue: false);

            provider.Set(new Score(1));

            Assert.That(last, Is.EqualTo(new[] { 2, 2 }));
        }

        [Test]
        public void Set_WithEquatableStruct_DoesNotAllocate()
        {
            var provider = new Provider<Score>();
            var sum = 0;
            provider.Subscribe(score => sum += score.Value);
            var value = 0;

            Assert.That(() => provider.Set(new Score(++value)), Is.Not.AllocatingGCMemory());
        }
    }
}
