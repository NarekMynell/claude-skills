// Every C# snippet from the unity-dev guides and library READMEs, verbatim inside the smallest context that
// compiles it, so a snippet that stops compiling fails the test run. Types the snippets take from a game
// (configs, enemies, steps) are stubs marked "stub". A changed snippet is changed here too.
using System;
using System.Collections.Generic;
using System.Threading;
using ProjectName.Audio;
using ProjectName.Core.Algorithms;
using ProjectName.Core.Bootstrap;
using ProjectName.Core.ContentLoading;
using ProjectName.Core.Culling;
using ProjectName.Core.DI;
using ProjectName.Core.Lifecycle;
using ProjectName.Core.Logging;
using ProjectName.Core.Motion;
using ProjectName.Core.Pooling;
using ProjectName.Core.Providers;
using ProjectName.Core.Scenes;
using ProjectName.Core.Serialization;
using ProjectName.Persistence;
using Cysharp.Threading.Tasks;
using MessagePipe;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.AddressableAssets;
using VContainer;
using VContainer.Unity;
using Object = UnityEngine.Object;

namespace LibraryTests.SnippetCheck.Messaging
{
    // messaging-and-state.md #1
    public readonly struct LevelCompleted
    {
        public readonly int LevelIndex;
        public readonly float Time;

        public LevelCompleted(int levelIndex, float time)
        {
            LevelIndex = levelIndex;
            Time = time;
        }
    }

    // messaging-and-state.md #2
    internal sealed class ProgressService : IStartable, IDisposable
    {
        private readonly ISubscriber<LevelCompleted> _levelCompleted;
        private IDisposable _subscriptions;

        public ProgressService(ISubscriber<LevelCompleted> levelCompleted) => _levelCompleted = levelCompleted;

        public void Start()
        {
            var bag = DisposableBag.CreateBuilder();
            _levelCompleted.Subscribe(OnLevelCompleted).AddTo(bag);
            _subscriptions = bag.Build();
        }

        public void Dispose() => _subscriptions?.Dispose();

        private void OnLevelCompleted(LevelCompleted message) { }
    }

    // messaging-and-state.md #3 must match the library's interfaces: assign the library's to the snippet's shape.
    public interface IProviderSnippet<T>
    {
        T Value { get; }
        IDisposable Subscribe(Action<T> onChanged, bool notifyCurrentValue = true);
    }

    public interface IProviderSetterSnippet<T> : IProviderSnippet<T>
    {
        void Set(T value);              // notifies only when the value changed
        void SetWithoutNotify(T value);
        void ForceNotify();
    }

    internal sealed class ProviderShapeCheck<T> : IProviderSetterSnippet<T>
    {
        private readonly IProviderSetter<T> _library;

        public ProviderShapeCheck(IProviderSetter<T> library) => _library = library;

        public T Value => _library.Value;
        public IDisposable Subscribe(Action<T> onChanged, bool notifyCurrentValue = true) => _library.Subscribe(onChanged, notifyCurrentValue);
        public void Set(T value) => _library.Set(value);
        public void SetWithoutNotify(T value) => _library.SetWithoutNotify(value);
        public void ForceNotify() => _library.ForceNotify();
    }

    // messaging-and-state.md #4
    public readonly struct SelectionState : IEquatable<SelectionState>
    {
        public readonly int SelectedId;

        public SelectionState(int selectedId) => SelectedId = selectedId;

        public bool Equals(SelectionState other) => SelectedId == other.SelectedId;
        public override bool Equals(object obj) => obj is SelectionState other && Equals(other);
        public override int GetHashCode() => SelectedId;
    }
}

namespace LibraryTests.SnippetCheck.Injection
{
    public sealed class CombatConfig : ScriptableObject { }               // stub
    public sealed class CombatHud : MonoBehaviour { }                     // stub
    public interface IDamageService { }                                   // stub
    internal sealed class DamageService : IDamageService { }              // stub
    public interface IProjectilePool { void ReleaseAll(); }               // stub
    public interface IEnemy { void Initialize(EnemyDefinition definition); } // stub
    public sealed class Enemy : MonoBehaviour, IEnemy { public void Initialize(EnemyDefinition definition) { } } // stub
    public sealed class EnemyDefinition : ScriptableObject { public Enemy Prefab; } // stub

    // dependency-injection.md #1
    internal sealed class CombatInstaller : ScopeInstaller
    {
        [SerializeField] private CombatConfig _config;
        [SerializeField] private CombatHud _hud;

        public override void Install(IContainerBuilder builder)
        {
            builder.RegisterInstance(_config);
            builder.Register<IDamageService, DamageService>(Lifetime.Singleton);
            builder.RegisterEntryPoint<ProjectileSystem>();
            builder.RegisterComponent(_hud);
        }
    }

    // dependency-injection.md #2
    internal sealed class ProjectileSystem : ITickable, IDisposable
    {
        private readonly IProjectilePool _pool;

        public ProjectileSystem(IProjectilePool pool) => _pool = pool;

        public void Tick() { /* iterate active projectiles; no allocations */ }

        public void Dispose() => _pool.ReleaseAll();
    }

    // dependency-injection.md #3
    public interface IEnemyFactory
    {
        IEnemy Create(EnemyDefinition definition, Vector3 position);
    }

    internal sealed class EnemyFactory : IEnemyFactory
    {
        private readonly IObjectResolver _resolver;
        private readonly Transform _enemyRoot;

        public EnemyFactory(IObjectResolver resolver, Transform enemyRoot)
        {
            _resolver = resolver;
            _enemyRoot = enemyRoot;
        }

        public IEnemy Create(EnemyDefinition definition, Vector3 position)
        {
            var enemy = _resolver.Instantiate(definition.Prefab, position, Quaternion.identity, _enemyRoot);
            enemy.Initialize(definition);
            return enemy;
        }
    }

    internal sealed class FactoryInstaller : ScopeInstaller
    {
        [SerializeField] private Transform _enemyRoot;

        // dependency-injection.md, the factory registration line
        public override void Install(IContainerBuilder builder)
        {
            builder.Register<IEnemyFactory>(resolver => new EnemyFactory(resolver, _enemyRoot), Lifetime.Singleton);
        }
    }

    internal sealed class RootInstaller : ScopeInstaller
    {
        public override void Install(IContainerBuilder builder)
        {
            // dependency-injection.md #4
            var options = builder.RegisterMessagePipe();
            // The MessagePipe Diagnostics window and GlobalMessagePipe need the global provider.
            builder.RegisterBuildCallback(c => GlobalMessagePipe.SetProvider(c.AsServiceProvider()));
        }
    }
}

namespace LibraryTests.SnippetCheck.Library
{
    public sealed class LoadSavesStep : IBootstrapStep { public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken) => UniTask.CompletedTask; } // stub
    public sealed class FadeTransition : ISceneTransition                // stub
    {
        public UniTask ShowAsync(CancellationToken cancellationToken) => UniTask.CompletedTask;
        public UniTask HideAsync(CancellationToken cancellationToken) => UniTask.CompletedTask;
    }
    public sealed class ProgressData { }                                  // stub
    public sealed class ProgressState { public ProgressData ToSaveData() => new ProgressData(); } // stub
    public sealed class ProgressV1ToV2 : ISaveMigration { public int FromVersion => 1; public void Migrate(JObject data) { } } // stub
    public sealed class EnemyAgent : MonoBehaviour, IPausable { public Vector3 Position => transform.position; public void Pause() { } public void Resume() { } } // stub
    public interface IDamageable { }                                      // stub
    public interface IEnemyBehaviour { }                                  // stub

    internal sealed class SnippetInstaller : ScopeInstaller
    {
        [SerializeField] private AudioServiceSettings _audioServiceSettings;
        [SerializeField] private FrameRateConfig _frameRateConfig;
        [SerializeField] private FirstSceneConfig _firstSceneConfig;
        [SerializeField] private Transform _poolContainer;

        public override void Install(IContainerBuilder builder)
        {
            // Audio README
            builder.RegisterAudio(_audioServiceSettings);   // IAudioService, ticked and disposed by the container

            // Bootstrap README
            builder.RegisterInstance(_frameRateConfig);
            builder.RegisterInstance(_firstSceneConfig);
            builder.Register<IBootstrapStep, FrameRateStep>(Lifetime.Singleton);
            builder.Register<IBootstrapStep, LoadSavesStep>(Lifetime.Singleton);       // project steps
            builder.Register<IBootstrapStep, LoadFirstSceneStep>(Lifetime.Singleton);  // always last
            builder.RegisterBootstrapFlow();

            // ContentLoading README
            builder.Register<IContentLoader, AddressablesContentLoader>(Lifetime.Singleton);

            // Pooling README
            builder.Register(resolver => new PrefabPoolRegistry(resolver, _poolContainer), Lifetime.Singleton);

            // Providers README
            builder.RegisterProvider(new LibraryTests.SnippetCheck.Messaging.SelectionState(-1));

            // Scenes README
            builder.Register<ISceneTransition, FadeTransition>(Lifetime.Singleton);   // or NoSceneTransition
            builder.Register<ISceneLoader, SceneLoader>(Lifetime.Singleton);

            // Persistence README
            builder.RegisterFileSaveStorage();
            builder.RegisterJsonSave(new SaveSchema<ProgressData>("progress", currentVersion: 2,
                new ISaveMigration[] { new ProgressV1ToV2() }));
        }
    }

    internal sealed class SnippetUser : MonoBehaviour
    {
        [SerializeField] private AudioCue _impactCue;
        [SerializeField] private AssetReference _levelPrefab;
        [SerializeField] private Transform _levelRoot;
        [SerializeField] private Bullet _bulletPrefab;
        [SerializeField] private Transform muzzle;
        [SerializeField] private SceneReference _levelScene;
        [SerializeField] private EnemyAgent enemy;
        [SerializeField] private Camera camera;

        // Serialization README (the first line is also serialization.md's example)
        [SerializeField] private SerializedInterface<IDamageable> _target;
        [SerializeReference, SubclassSelector] private IEnemyBehaviour _behaviour;
        [SerializeField] private SerializableDictionary<string, int> _prices;
        [SerializeField] private SceneReference _menuScene;

        private IAudioService _audio;
        private IContentLoader _content;
        private IObjectResolver _resolver;
        private PrefabPoolRegistry _pools;
        private IProviderSetter<LibraryTests.SnippetCheck.Messaging.SelectionState> _selection;
        private IDisposable _subscription;
        private ISceneLoader _sceneLoader;
        private ISaveService<ProgressData> _saves;
        private ISaveStorage _storage;
        private ProgressState _progress;
        private VisibilityPauser _pauser;
        private readonly List<Vector2Int> _path = new List<Vector2Int>();

        public sealed class Bullet : MonoBehaviour { }                    // stub

        private void OnValidate()
        {
            if (_prices.InvalidEntryCount > 0) Debug.LogWarning($"{name}: repeated or empty price keys.", this);
        }

        private void AudioSnippet(RaycastHit hit)
        {
            var handle = _audio.PlayAt(_impactCue, hit.point);
            _audio.Stop(handle);
        }

        private void PathSnippet(IWalkableGrid grid, Vector2Int start, Vector2Int goal)
        {
            var pathfinder = new GridPathfinder(allowDiagonals: true);   // keep one instance and reuse it
            if (pathfinder.TryFindPath(grid, start, goal, _path)) FollowPath(_path);
        }

        private void FollowPath(List<Vector2Int> path) { }                // stub

        private async UniTask ContentSnippet(CancellationToken cancellationToken)
        {
            var prefab = await _content.LoadAsync<GameObject>(_levelPrefab, cancellationToken);
            var level = _resolver.Instantiate(prefab, _levelRoot);   // through the resolver for injection, under a parent
            // ...when the level ends
            Object.Destroy(level);
            _content.Release(_levelPrefab);
        }

        private void CullingSnippet()
        {
            _pauser = new VisibilityPauser(camera);
            _pauser.Register(enemy, enemy.Position, radius: 1.5f);
            _pauser.UpdatePosition(enemy, enemy.Position);   // for moving targets, from the system that moves them
            _pauser.Unregister(enemy);
            _pauser.Dispose();
        }

        private void LoggingSnippet(int count, Exception exception)
        {
            Log.Debug($"Spawned {count} enemies", this);   // removed with its argument in release builds
            Log.Exception(exception, this);
        }

        private void PoolingSnippet()
        {
            // During loading
            var bullets = _pools.Register(_bulletPrefab, prewarmCount: 64);

            // Gameplay
            var bullet = _pools.Get(_bulletPrefab).Spawn(muzzle.position, muzzle.rotation);
            _pools.Get(_bulletPrefab).Despawn(bullet);
        }

        private void ProviderSnippet(int id)
        {
            // Reader
            _subscription = _selection.Subscribe(OnSelectionChanged);   // receives the current value first
            // Owner
            _selection.Set(new LibraryTests.SnippetCheck.Messaging.SelectionState(id));                      // notifies only on change
        }

        private void OnSelectionChanged(LibraryTests.SnippetCheck.Messaging.SelectionState state) { }

        private async UniTask ScenesSnippet(IProgress<float> progress, CancellationToken cancellationToken)
        {
            await _sceneLoader.LoadAsync(_levelScene.ScenePath, progress, cancellationToken);
        }

        // Persistence README, saving when the app pauses
        private void OnApplicationPause(bool paused)
        {
            if (!paused) return;

            _saves.SaveAsync(_progress.ToSaveData(), CancellationToken.None).Forget();
            _storage.Flush(TimeSpan.FromSeconds(2));
        }

        private async UniTask PersistenceSnippet(CancellationToken cancellationToken)
        {
            var progress = await _saves.LoadAsync(cancellationToken) ?? new ProgressData();
            await _saves.SaveAsync(progress, cancellationToken);
        }
    }
}

namespace LibraryTests.SnippetCheck.Animation
{
    // unity-setup.md (animation) #1
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

    internal sealed class LocomotionView : MonoBehaviour
    {
        private Animator _animator; // stub

        // unity-setup.md (animation) #2
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

        private void Update() => UpdateLocomotion(Vector3.zero);
    }

    // unity-setup.md (animation) #3
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
}

namespace LibraryTests.SnippetCheck.Capabilities
{
    // Stubs the snippets take from a game.
    public interface IMover
    {
        void MoveTo(Transform body, Vector3 destination);
    }

    public interface IGun
    {
        void Fire(Vector3 from, Vector3 target);
    }

    public interface IHealth
    {
        void Reduce(int amount);
    }

    public enum AnimalAction
    {
        Rest,
        Graze,
    }

    public readonly struct AnimalContext
    {
        public readonly float Random01;

        public AnimalContext(float random01) => Random01 = random01;
    }

    // capabilities.md #1
    public interface IMovable
    {
        Vector3 Position { get; }
        void MoveTo(Vector3 destination);
    }

    public interface IFlying
    {
        float Altitude { get; set; }
    }

    public interface IShooter
    {
        void ShootAt(Vector3 target);
    }

    public interface IDamageable
    {
        void TakeDamage(int amount);
    }

    internal sealed class Drone : MonoBehaviour, IMovable, IFlying, IShooter, IDamageable
    {
        private IMover _mover;
        private IGun _gun;
        private IHealth _health;

        [Inject]
        public void Construct(IMover mover, IGun gun, IHealth health)
        {
            _mover = mover;
            _gun = gun;
            _health = health;
        }

        public Vector3 Position => transform.position;
        public float Altitude { get; set; }

        public void MoveTo(Vector3 destination) => _mover.MoveTo(transform, destination);
        public void ShootAt(Vector3 target) => _gun.Fire(transform.position, target);
        public void TakeDamage(int amount) => _health.Reduce(amount);
    }

    internal sealed class Turret : MonoBehaviour, IShooter, IDamageable
    {
        private IGun _gun;
        private IHealth _health;

        [Inject]
        public void Construct(IGun gun, IHealth health)
        {
            _gun = gun;
            _health = health;
        }

        public void ShootAt(Vector3 target) => _gun.Fire(transform.position, target);
        public void TakeDamage(int amount) => _health.Reduce(amount);
    }

    public interface IFireControl
    {
        void FireAll(Vector3 target);
    }

    internal sealed class FireControl : IFireControl
    {
        private readonly IReadOnlyList<IShooter> _shooters;

        public FireControl(IReadOnlyList<IShooter> shooters) => _shooters = shooters;

        public void FireAll(Vector3 target)
        {
            foreach (var shooter in _shooters) shooter.ShootAt(target);
        }
    }

    // capabilities.md #2
    public interface IAnimalBehavior
    {
        AnimalAction ChooseAction(in AnimalContext context);
    }

    [Serializable]
    internal sealed class Grazer : IAnimalBehavior
    {
        [SerializeField, Range(0f, 1f)] private float _restShare = 0.5f;

        public AnimalAction ChooseAction(in AnimalContext context) =>
            context.Random01 < _restShare ? AnimalAction.Rest : AnimalAction.Graze;
    }

    [CreateAssetMenu(menuName = "Game/Animal")]
    internal sealed class AnimalDefinition : ScriptableObject
    {
        [SerializeReference] private IAnimalBehavior _behavior;

        public IAnimalBehavior Behavior => _behavior;
    }

    // capabilities.md #3
    public interface ICrowdPositions
    {
        int Count { get; }
        Vector3 PositionOf(int actor);
    }

    public interface ICrowdOrders
    {
        void WalkTo(int actor, Vector3 destination);
    }

    internal sealed class CrowdSystem : ICrowdPositions, ICrowdOrders, ITickable
    {
        private Vector3[] _positions = new Vector3[1024];
        private Vector3[] _destinations = new Vector3[1024];

        public int Count { get; private set; }

        public Vector3 PositionOf(int actor) => _positions[actor];

        public void WalkTo(int actor, Vector3 destination) => _destinations[actor] = destination;

        public void Tick()
        {
            // Tight loops over the arrays: no interface calls per actor, no allocations.
        }
    }

    // capabilities.md #4
    public interface IAdvancing
    {
        void Advance(float deltaTime);
    }

    public struct WalkingActor : IAdvancing
    {
        public float Phase;

        public void Advance(float deltaTime) => Phase += deltaTime;
    }

    public static class ActorUpdate
    {
        public static void AdvanceAll<T>(T[] actors, int count, float deltaTime) where T : struct, IAdvancing
        {
            for (var i = 0; i < count; i++) actors[i].Advance(deltaTime);
        }
    }
}

namespace LibraryTests.SnippetCheck.OffScreen
{
    // stub: DOTween isn't in the test project.
    public sealed class Tween
    {
        public void Pause() { }

        public void Play() { }
    }

    // Culling README and performance guide
    public sealed class SwayingTree : MonoBehaviour, IPausable
    {
        private Tween _sway;

        public void Pause() => _sway.Pause();

        public void Resume() => _sway.Play();
    }

    internal sealed class SceneInstaller : ScopeInstaller
    {
        [SerializeField] private Camera _camera;

        public override void Install(IContainerBuilder builder)
        {
            // Culling README
            builder.RegisterVisibilityPauser(_camera);
        }
    }

    // Motion README
    internal sealed class SlideMeasure
    {
        public float Overlaps(IReadOnlyList<Vector3> positions)
        {
            var overlaps = new CrowdOverlapMeter(minimumDistance: 0.5f);
            // Every frame:
            overlaps.Sample(positions, Time.deltaTime);
            // Afterwards, pairs closer than the minimum, per second:
            return overlaps.PairsPerSecond;
        }

        public float Activity(string state, float deltaTime)
        {
            var shares = new ActivityShares();
            // Every step of the behavior code:
            shares.Add(state, deltaTime);
            // Afterwards:
            return shares.ShareOf("Resting");
        }
    }
}
