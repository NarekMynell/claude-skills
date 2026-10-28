using System;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.StateMachines;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.StateMachines
{
    public sealed class StateMachineTests
    {
        private sealed class RecordingState : IState
        {
            private readonly string _name;
            private readonly List<string> _log;

            public RecordingState(string name, List<string> log)
            {
                _name = name;
                _log = log;
            }

            public Action OnEnter { get; set; }

            public bool FailsOnEnter { get; set; }

            public void Enter()
            {
                _log.Add($"enter {_name}");
                if (FailsOnEnter) throw new InvalidOperationException($"{_name} failed");
                OnEnter?.Invoke();
            }

            public void Exit() => _log.Add($"exit {_name}");
        }

        private sealed class AsyncState : IAsyncState
        {
            public UniTaskCompletionSource EnterGate { get; set; }

            public bool FailsOnEnter { get; set; }

            public int Entered { get; private set; }

            public int Exited { get; private set; }

            public UniTask EnterAsync(CancellationToken cancellationToken)
            {
                Entered++;
                if (FailsOnEnter) throw new InvalidOperationException("enter failed");
                return EnterGate?.Task ?? UniTask.CompletedTask;
            }

            public UniTask ExitAsync(CancellationToken cancellationToken)
            {
                Exited++;
                return UniTask.CompletedTask;
            }
        }

        [Test]
        public void ChangeState_ExitsThePreviousState_ThenEntersTheNext()
        {
            var log = new List<string>();
            var machine = new StateMachine<RecordingState>();
            var changes = new List<string>();
            machine.Changed += (from, to) => changes.Add($"{(from == null ? "none" : "a")}->b");

            machine.ChangeState(new RecordingState("a", log));
            machine.ChangeState(new RecordingState("b", log));

            Assert.That(log, Is.EqualTo(new[] { "enter a", "exit a", "enter b" }));
            Assert.That(changes.Count, Is.EqualTo(2));
        }

        [Test]
        public void ChangeRequestedFromEnter_RunsAfterTheCurrentTransition()
        {
            var log = new List<string>();
            var machine = new StateMachine<RecordingState>();
            var menu = new RecordingState("menu", log);
            var splash = new RecordingState("splash", log) { OnEnter = () => machine.ChangeState(menu) };

            machine.ChangeState(splash);

            Assert.That(log, Is.EqualTo(new[] { "enter splash", "exit splash", "enter menu" }));
            Assert.That(machine.Current, Is.SameAs(menu));
        }

        [Test]
        public void ChangeToTheCurrentState_DoesNothing()
        {
            var log = new List<string>();
            var machine = new StateMachine<RecordingState>();
            var state = new RecordingState("a", log);

            machine.ChangeState(state);
            machine.ChangeState(state);

            Assert.That(log, Is.EqualTo(new[] { "enter a" }));
        }

        [Test]
        public void FailedEnter_LeavesNoCurrentState_SoARetryEntersAgain()
        {
            var log = new List<string>();
            var machine = new StateMachine<RecordingState>();
            var state = new RecordingState("a", log) { FailsOnEnter = true };

            Assert.Throws<InvalidOperationException>(() => machine.ChangeState(state));
            Assert.That(machine.Current, Is.Null);

            state.FailsOnEnter = false;
            machine.ChangeState(state);
            Assert.That(log, Is.EqualTo(new[] { "enter a", "enter a" }));
        }

        [Test]
        public void AsyncMachine_FailedEnter_LeavesNoCurrentState_AndNeverExitsIt()
        {
            var machine = new AsyncStateMachine<AsyncState>();
            var broken = new AsyncState { FailsOnEnter = true };

            Assert.Throws<InvalidOperationException>(() => machine.ChangeStateAsync(broken, CancellationToken.None).GetAwaiter().GetResult());
            Assert.That(machine.Current, Is.Null);
            Assert.That(machine.IsTransitioning, Is.False);

            machine.ChangeStateAsync(new AsyncState(), CancellationToken.None).GetAwaiter().GetResult();
            Assert.That(broken.Exited, Is.Zero);
        }

        [Test]
        public void AsyncMachine_RejectsASecondTransitionWhileOneRuns()
        {
            var machine = new AsyncStateMachine<AsyncState>();
            var slow = new AsyncState { EnterGate = new UniTaskCompletionSource() };
            var first = machine.ChangeStateAsync(slow, CancellationToken.None);

            Assert.That(machine.IsTransitioning, Is.True);
            Assert.Throws<InvalidOperationException>(() => machine.ChangeStateAsync(new AsyncState(), CancellationToken.None).GetAwaiter().GetResult());

            slow.EnterGate.TrySetResult();
            first.GetAwaiter().GetResult();
            Assert.That(machine.IsTransitioning, Is.False);
            Assert.That(machine.Current, Is.SameAs(slow));
        }
    }
}
