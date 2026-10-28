using System;
using System.Collections.Generic;
using Company.Product.Core.Logging;

namespace Company.Product.Core.Providers
{
    // Main-thread state holder. A subscriber that throws is logged and doesn't stop the others.
    // A Set from inside a notification restarts delivery, so every subscriber ends on the newest value.
    public sealed class Provider<T> : IProviderSetter<T>
    {
        private readonly IEqualityComparer<T> _comparer;
        private readonly List<Subscription> _subscriptions = new List<Subscription>();
        private int _notifyDepth;
        private int _version;
        private bool _hasInactiveSubscriptions;

        public Provider(T initialValue = default, IEqualityComparer<T> comparer = null)
        {
            Value = initialValue;
            _comparer = comparer ?? EqualityComparer<T>.Default;
        }

        public T Value { get; private set; }

        public IDisposable Subscribe(Action<T> onChanged, bool notifyCurrentValue = true)
        {
            if (onChanged == null) throw new ArgumentNullException(nameof(onChanged));

            var subscription = new Subscription(this, onChanged);
            _subscriptions.Add(subscription);
            if (notifyCurrentValue) Invoke(subscription, Value);
            return subscription;
        }

        public void Set(T value)
        {
            if (_comparer.Equals(Value, value)) return;

            Value = value;
            Notify();
        }

        public void SetWithoutNotify(T value) => Value = value;

        public void ForceNotify() => Notify();

        private void Notify()
        {
            var version = ++_version;
            var value = Value;
            var count = _subscriptions.Count;
            _notifyDepth++;
            try
            {
                for (var i = 0; i < count && version == _version; i++)
                {
                    var subscription = _subscriptions[i];
                    if (subscription.IsActive) Invoke(subscription, value);
                }
            }
            finally
            {
                _notifyDepth--;
                if (_notifyDepth == 0 && _hasInactiveSubscriptions)
                {
                    _subscriptions.RemoveAll(subscription => !subscription.IsActive);
                    _hasInactiveSubscriptions = false;
                }
            }
        }

        private static void Invoke(Subscription subscription, T value)
        {
            try
            {
                subscription.Callback(value);
            }
            catch (Exception exception)
            {
                Log.Exception(exception);
            }
        }

        private void Remove(Subscription subscription)
        {
            if (_notifyDepth > 0)
                _hasInactiveSubscriptions = true;
            else
                _subscriptions.Remove(subscription);
        }

        private sealed class Subscription : IDisposable
        {
            private readonly Provider<T> _owner;

            public Subscription(Provider<T> owner, Action<T> callback)
            {
                _owner = owner;
                Callback = callback;
            }

            public Action<T> Callback { get; }

            public bool IsActive { get; private set; } = true;

            public void Dispose()
            {
                if (!IsActive) return;

                IsActive = false;
                _owner.Remove(this);
            }
        }
    }
}
