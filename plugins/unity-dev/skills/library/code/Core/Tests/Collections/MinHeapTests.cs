using System;
using System.Collections.Generic;
using Company.Product.Core.Collections;
using NUnit.Framework;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.Collections
{
    public sealed class MinHeapTests
    {
        [Test]
        public void Dequeue_ReturnsElementsInPriorityOrder()
        {
            var heap = new MinHeap<string, int>(2);
            var random = new Random(7);
            var expected = new List<int>();
            for (var i = 0; i < 200; i++)
            {
                var priority = random.Next(1000);
                heap.Enqueue(priority.ToString(), priority);
                expected.Add(priority);
            }

            expected.Sort();
            foreach (var priority in expected) Assert.That(heap.Dequeue(), Is.EqualTo(priority.ToString()));
            Assert.That(heap.Count, Is.Zero);
        }

        [Test]
        public void CustomComparer_TurnsItIntoAMaxHeap()
        {
            var heap = new MinHeap<int, int>(comparer: Comparer<int>.Create((a, b) => b.CompareTo(a)));
            heap.Enqueue(1, 1);
            heap.Enqueue(3, 3);
            heap.Enqueue(2, 2);

            Assert.That(heap.Dequeue(), Is.EqualTo(3));
        }

        [Test]
        public void EmptyHeap_TryMethodsFail_AndDequeueThrows()
        {
            var heap = new MinHeap<int, float>();

            Assert.That(heap.TryDequeue(out _, out _), Is.False);
            Assert.That(heap.TryPeek(out _, out _), Is.False);
            Assert.Throws<InvalidOperationException>(() => heap.Dequeue());
        }

        [Test]
        public void EnqueueAndDequeue_AfterWarmup_DoNotAllocate()
        {
            var heap = new MinHeap<int, float>(64);

            Assert.That(() =>
            {
                for (var i = 0; i < 64; i++) heap.Enqueue(i, 64 - i);
                while (heap.TryDequeue(out _, out _)) { }
            }, Is.Not.AllocatingGCMemory());
        }
    }
}
