using System;
using System.Collections.Generic;
using Company.Product.Core.Collections;
using NUnit.Framework;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.Collections
{
    public sealed class RingBufferTests
    {
        [Test]
        public void Add_BeyondCapacity_OverwritesTheOldest()
        {
            var buffer = new RingBuffer<int>(3);
            for (var i = 1; i <= 5; i++) buffer.Add(i);

            Assert.That(buffer.IsFull, Is.True);
            Assert.That(new List<int>(buffer), Is.EqualTo(new[] { 3, 4, 5 }));
            Assert.That(buffer[0], Is.EqualTo(3));
        }

        [Test]
        public void Indexer_OutsideCount_Throws()
        {
            var buffer = new RingBuffer<int>(4);
            buffer.Add(1);

            Assert.Throws<ArgumentOutOfRangeException>(() => _ = buffer[1]);
            Assert.Throws<ArgumentOutOfRangeException>(() => _ = buffer[-1]);
        }

        [Test]
        public void Clear_EmptiesTheBuffer()
        {
            var buffer = new RingBuffer<int>(2);
            buffer.Add(1);
            buffer.Add(2);
            buffer.Clear();
            buffer.Add(9);

            Assert.That(buffer.Count, Is.EqualTo(1));
            Assert.That(buffer[0], Is.EqualTo(9));
        }

        [Test]
        public void AddAndEnumerate_DoNotAllocate()
        {
            var buffer = new RingBuffer<int>(8);

            Assert.That(() =>
            {
                var sum = 0;
                for (var i = 0; i < 20; i++) buffer.Add(i);
                foreach (var item in buffer) sum += item;
            }, Is.Not.AllocatingGCMemory());
        }
    }
}
