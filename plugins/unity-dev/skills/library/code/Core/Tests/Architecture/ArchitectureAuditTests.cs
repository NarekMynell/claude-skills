using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using ProjectName.Core.Editor.Architecture;
using UnityEngine;
using VContainer;

namespace ProjectName.Core.Tests.Architecture
{
    // Not nested, so it stands for a domain's own interface or a type in Assembly-CSharp.
    public interface StandaloneContract { }

    public sealed class ArchitectureAuditTests
    {
        private static ArchitectureAuditOptions Options(ArchitectureAuditOptions options = null) =>
            options ?? new ArchitectureAuditOptions("Game") { SourceFolder = null };

        private static ArchitectureReport Audit(params Type[] types) => ArchitectureAudit.Analyze(types, Options());

        private static string[] Rules(ArchitectureReport report) => report.Findings.Select(f => f.Rule).Distinct().ToArray();

        // A drone flies and shoots, a tower only shoots, and each consumer sees only the capability it uses.
        public interface IFlying { void Fly(float height); }

        public interface IShooter { void Shoot(); }

        internal sealed class Drone : IFlying, IShooter
        {
            public void Fly(float height) { }

            public void Shoot() { }
        }

        internal sealed class Tower : IShooter
        {
            public void Shoot() { }
        }

        public interface IFireControl { void FireAll(); }

        internal sealed class FireControl : IFireControl
        {
            private readonly IReadOnlyList<IShooter> _shooters;

            public FireControl(IReadOnlyList<IShooter> shooters) => _shooters = shooters;

            public void FireAll()
            {
                foreach (var shooter in _shooters) shooter.Shoot();
            }
        }

        [Test]
        public void CapabilityInterfaces_Pass()
        {
            var report = Audit(typeof(IFlying), typeof(IShooter), typeof(IFireControl), typeof(Drone), typeof(Tower), typeof(FireControl));

            Assert.That(report.IsClean, report.ToString());
        }

        internal sealed class Engine
        {
            public void Run() { }
        }

        internal sealed class CarWithConcreteEngine
        {
            private readonly Engine _engine;

            public CarWithConcreteEngine(Engine engine) => _engine = engine;

            public void Drive() => _engine.Run();
        }

        [Test]
        public void ConstructorTakingAConcreteClass_IsReported()
        {
            var report = Audit(typeof(Engine), typeof(CarWithConcreteEngine));

            Assert.That(Rules(report), Does.Contain("concrete-dependency"));
            Assert.That(report.Findings.First(f => f.Rule == "concrete-dependency").Subject, Does.Contain(nameof(CarWithConcreteEngine)));
        }

        internal sealed class CarWithEngineList
        {
            private readonly IReadOnlyList<Engine> _engines;

            public CarWithEngineList(IReadOnlyList<Engine> engines) => _engines = engines;

            public int Count() => _engines.Count;
        }

        [Test]
        public void ListOfAConcreteClass_IsReported()
        {
            Assert.That(Rules(Audit(typeof(Engine), typeof(CarWithEngineList))), Does.Contain("concrete-dependency"));
        }

        internal sealed class InjectedView : MonoBehaviour
        {
            private Engine _engine;

            [Inject]
            public void Construct(Engine engine) => _engine = engine;
        }

        [Test]
        public void InjectMethodTakingAConcreteClass_IsReported()
        {
            Assert.That(Rules(Audit(typeof(Engine), typeof(InjectedView))), Does.Contain("concrete-dependency"));
        }

        public readonly struct Damage
        {
            public readonly int Amount;

            public Damage(int amount) => Amount = amount;
        }

        internal sealed class EnemyData
        {
            public int Health { get; set; }

            public string Name;
        }

        internal sealed class GameSettings : ScriptableObject
        {
            [SerializeField] private int _lives;

            public int Lives => _lives;

            private void OnValidate() => _lives = Mathf.Max(_lives, 1);
        }

        internal sealed class UsesData
        {
            private readonly int _sum;

            public UsesData(Damage damage, EnemyData data, GameSettings settings, Camera camera) =>
                _sum = damage.Amount + data.Health + settings.Lives + camera.pixelWidth;

            public int Sum() => _sum;
        }

        [Test]
        public void DataConfigsAndUnityTypes_NeedNoInterface()
        {
            var report = Audit(typeof(Damage), typeof(EnemyData), typeof(GameSettings), typeof(UsesData));

            Assert.That(Rules(report), Does.Not.Contain("concrete-dependency"), report.ToString());
        }

        internal abstract class ScopeInstaller : MonoBehaviour { }

        internal sealed class CombatInstaller : ScopeInstaller
        {
            [SerializeField] private InjectedView _view;

            public void Install(Engine engine) => _view.Construct(engine);
        }

        [Test]
        public void Installers_MayNameConcreteTypes()
        {
            var report = Audit(typeof(Engine), typeof(CombatInstaller));

            Assert.That(report.Findings.Where(f => f.Subject.Contains(nameof(CombatInstaller))), Is.Empty, report.ToString());
        }

        internal sealed class ServiceA { public void A() { } }

        internal sealed class ServiceB { public void B() { } }

        internal sealed class ServiceC { public void C() { } }

        [Test]
        public void AnAssemblyWithClassesAndNoInterface_IsReported()
        {
            Assert.That(Rules(Audit(typeof(ServiceA), typeof(ServiceB), typeof(ServiceC))), Does.Contain("no-interfaces"));
        }

        internal class ConcreteAnimal { public void Eat() { } }

        internal sealed class Dog : ConcreteAnimal { public void Bark() { } }

        [Test]
        public void InheritingAConcreteClass_IsReported()
        {
            Assert.That(Rules(Audit(typeof(ConcreteAnimal), typeof(Dog))), Does.Contain("concrete-base"));
        }

        internal abstract class Shape { public abstract float Area(); }

        internal sealed class Circle : Shape { public override float Area() => 1f; }

        [Test]
        public void AnAbstractBase_NeedsItsReason()
        {
            var report = Audit(typeof(Shape), typeof(Circle));
            Assert.That(report.Findings.Single(f => f.Rule == "base-class").Subject, Is.EqualTo(typeof(Shape).FullName));

            var options = Options().Allow("base-class", typeof(Shape).FullName, "Every shape shares the same outline code.");
            Assert.That(Rules(ArchitectureAudit.Analyze(new[] { typeof(Shape), typeof(Circle) }, options)), Does.Not.Contain("base-class"));
        }

        internal abstract class MiddleShape : Shape { }

        internal sealed class Square : MiddleShape { public override float Area() => 1f; }

        [Test]
        public void TwoLevelsOfProjectBases_AreReported()
        {
            Assert.That(Rules(Audit(typeof(Shape), typeof(MiddleShape), typeof(Square))), Does.Contain("deep-inheritance"));
        }

        internal static class Counter
        {
            public static int Count;
            public static readonly int Limit = 3;
            public const int Max = 4;
        }

        internal static class Registry
        {
            public static readonly List<int> Items = new List<int>();
        }

        [Test]
        public void MutableStaticFieldAndStaticCollection_AreReported()
        {
            var report = Audit(typeof(Counter), typeof(Registry));

            Assert.That(report.Findings.Where(f => f.Rule == "mutable-static").Select(f => f.Subject),
                Is.EquivalentTo(new[] { typeof(Counter).FullName, typeof(Registry).FullName }));
        }

        internal sealed class Ticking : MonoBehaviour
        {
            private void Update() { }
        }

        internal sealed class GameManager
        {
            public static GameManager Instance { get; private set; }

            public void Run() { }
        }

        internal sealed class ReadOnlySingleton
        {
            public static readonly ReadOnlySingleton Shared = new ReadOnlySingleton();

            public void Run() { }
        }

        internal static class SharedThings
        {
            public static readonly int[] Scores = new int[4];
            private static readonly int[] Table = { 1, 2, 3 };

            public static event System.Action Changed;

            public static int First() => Table[0] + (Changed == null ? 0 : 1);
        }

        [Test]
        public void SingletonsAndSharedStaticState_AreReported()
        {
            var details = Audit(typeof(GameManager), typeof(ReadOnlySingleton), typeof(SharedThings)).Findings.Where(f => f.Rule == "mutable-static").Select(f => f.Detail).ToList();

            Assert.That(details, Has.Some.Contains("Instance"));
            Assert.That(details, Has.Some.Contains("a singleton"));
            Assert.That(details, Has.Some.Contains("Scores"));
            Assert.That(details, Has.Some.Contains("event Changed"));
            Assert.That(details, Has.None.Contains("Table"));
        }

        internal sealed class StatefulAsset : ScriptableObject
        {
            [SerializeField] private int _lives;
            [System.NonSerialized] private int _current;

            public int Lives => _lives + _current;
        }

        internal sealed class InjectedAsset : ScriptableObject
        {
            [Inject]
            public void Construct(IShooter shooter) => shooter.Shoot();
        }

        [Test]
        public void AScriptableObjectWithRuntimeState_OrInjection_IsReported()
        {
            var subjects = Audit(typeof(StatefulAsset), typeof(InjectedAsset), typeof(GameSettings), typeof(IShooter)).Findings.Where(f => f.Rule == "stateful-asset").Select(f => f.Subject).ToList();

            Assert.That(subjects, Does.Contain(typeof(StatefulAsset).FullName));
            Assert.That(subjects, Does.Contain(typeof(InjectedAsset).FullName));
            Assert.That(subjects, Does.Not.Contain(typeof(GameSettings).FullName));
        }

        internal sealed class ExposesConcrete
        {
            public Engine Motor { get; set; }

            public Engine Build() => Motor;
        }

        internal interface IReturnsConcrete
        {
            Engine Engine { get; }
        }

        [Test]
        public void ConcreteClassesInPropertiesAndReturnValues_AreReported()
        {
            var report = Audit(typeof(Engine), typeof(ExposesConcrete), typeof(IReturnsConcrete));

            var details = report.Findings.Where(f => f.Rule == "concrete-dependency").Select(f => f.Detail).ToList();
            Assert.That(details, Has.Some.Contains("property Motor"));
            Assert.That(details, Has.Some.Contains("Build returns"));
            Assert.That(report.Findings.Any(f => f.Subject == typeof(IReturnsConcrete).FullName), report.ToString());
        }

        internal sealed class LeafA { public void A() { } }

        internal sealed class MiddleB
        {
            private readonly LeafA _leaf = new LeafA();

            public void B() => _leaf.A();
        }

        internal sealed class TopC
        {
            private readonly MiddleB _middle = new MiddleB();

            public void C() => _middle.B();
        }

        [Test]
        public void ATreeOfClassesCreatingEachOther_IsNotAHelper()
        {
            var report = Audit(typeof(LeafA), typeof(MiddleB), typeof(TopC));

            Assert.That(report.Findings.Any(f => f.Rule == "concrete-dependency" && f.Subject == typeof(TopC).FullName), report.ToString());
        }

        [Test]
        public void AnAuditOfNothing_CannotPass()
        {
            var report = ArchitectureAudit.Run(new ArchitectureAuditOptions("NoSuchProject") { SourceFolder = "No/Such/Folder", CapabilityMapFile = null }.Allow("loosened-limit", "CapabilityMapFile", "Test."));

            Assert.That(report.Findings.Count(f => f.Rule == "nothing-audited"), Is.EqualTo(2), report.ToString());
        }

        [Test]
        public void MonoBehaviourWithUpdate_IsReported()
        {
            Assert.That(Rules(Audit(typeof(Ticking))), Does.Contain("frame-method"));
        }

        internal sealed class Crowded
        {
            public Crowded(int a, int b, int c, int d, int e, int f, int g) { }

            public void Work() { }
        }

        [Test]
        public void TooManyDependencies_AreReported()
        {
            Assert.That(Rules(Audit(typeof(Crowded))), Does.Contain("too-many-dependencies"));
        }

        public interface IEverything
        {
            void A();
            void B();
            void C();
            void D();
            void E();
            void F();
            void G();
            void H();
            void I();
        }

        [Test]
        public void FatInterface_IsReported()
        {
            Assert.That(Rules(Audit(typeof(IEverything))), Does.Contain("fat-interface"));
        }

        [Test]
        public void AnException_MovesTheFindingToTheAcceptedList_WithItsReason()
        {
            var options = Options().Allow("concrete-dependency", typeof(CarWithConcreteEngine).FullName, "Test reason.");

            var report = ArchitectureAudit.Analyze(new[] { typeof(Engine), typeof(CarWithConcreteEngine) }, options);

            Assert.That(Rules(report), Does.Not.Contain("concrete-dependency"));
            Assert.That(report.Excepted.Single().Detail, Does.Contain("Test reason."));
            Assert.That(report.ToString(), Does.Contain("Test reason."));
        }

        [Test]
        public void AnExceptionThatMatchesNothing_MakesTheReportUnclean()
        {
            var options = Options().Allow("concrete-dependency", "No.Such.Type", "Stale.");

            var report = ArchitectureAudit.Analyze(new[] { typeof(IShooter), typeof(Tower) }, options);

            Assert.That(report.IsClean, Is.False);
            Assert.That(report.UnusedExceptions.Single().Subject, Is.EqualTo("No.Such.Type"));
        }

        [Test]
        public void ManyExceptions_AreAFindingOfTheirOwn()
        {
            var options = Options();
            options.MaxExceptions = 1;
            options.Allow("concrete-dependency", typeof(CarWithConcreteEngine).FullName, "One.");
            options.Allow("no-interfaces", "Some.Assembly", "Two.");

            var report = ArchitectureAudit.Analyze(new[] { typeof(Engine), typeof(CarWithConcreteEngine) }, options);

            Assert.That(Rules(report), Does.Contain("too-many-exceptions"));
        }

        [Test]
        public void AnExceptionWithoutAReason_IsRefused()
        {
            Assert.Throws<ArgumentException>(() => Options().Allow("mutable-static", "A.B", " "));
        }

        [Test]
        public void CoreReferencingADomain_AndAnythingReferencingApp_AreReported()
        {
            var layout = new (string, IEnumerable<string>)[]
            {
                ("Game.Core", new[] { "Game.Combat", "VContainer" }),
                ("Game.Combat", new[] { "Game.Core", "Game.App" }),
                ("Game.App", new[] { "Game.Core", "Game.Combat" }),
            };

            var findings = ArchitectureAudit.CheckReferences(layout, "Game").ToList();

            Assert.That(findings.Select(f => f.Subject), Is.EquivalentTo(new[] { "Game.Core", "Game.Combat" }));
            Assert.That(findings.All(f => f.Rule == "dependency-direction"));
        }

        // The shapes a project without contracts takes: everything internal, in one assembly, created with new.
        internal sealed class WallOfConcreteClasses
        {
            private readonly CarWithConcreteEngine _car = new CarWithConcreteEngine(new Engine());

            public void Run() => _car.Drive();
        }

        [Test]
        public void AFieldHoldingAClassThatNeedsOtherClasses_IsReported_InTheSameAssembly()
        {
            var report = Audit(typeof(Engine), typeof(CarWithConcreteEngine), typeof(WallOfConcreteClasses));

            Assert.That(report.Findings.Any(f => f.Rule == "concrete-dependency" && f.Subject.Contains(nameof(WallOfConcreteClasses))), report.ToString());
        }

        internal sealed class Cooldown
        {
            private float _left;

            public bool Tick(float dt) => (_left -= dt) <= 0f;
        }

        internal sealed class GunWithHelper : IShooter
        {
            private readonly Cooldown _cooldown = new Cooldown();

            public void Shoot() => _cooldown.Tick(0f);
        }

        [Test]
        public void ASmallHelperAClassOwns_IsFine()
        {
            var report = Audit(typeof(IShooter), typeof(Cooldown), typeof(GunWithHelper));

            Assert.That(Rules(report), Does.Not.Contain("concrete-dependency"), report.ToString());
        }

        internal sealed class ViewWithConcreteView : MonoBehaviour
        {
            [SerializeField] private Ticking _other;

            public Ticking Other => _other;
        }

        [Test]
        public void ASerializedConcreteMonoBehaviour_IsReported()
        {
            Assert.That(Rules(Audit(typeof(Ticking), typeof(ViewWithConcreteView))), Does.Contain("concrete-dependency"));
        }

        internal sealed class InitWithConcrete
        {
            public void Init(Engine engine) => engine.Run();
        }

        internal interface ILeakyContract
        {
            void Attach(Engine engine);
        }

        [Test]
        public void AMethodTakingAConcreteClass_IsReported_InClassesAndInInterfaces()
        {
            var report = Audit(typeof(Engine), typeof(InitWithConcrete), typeof(ILeakyContract));

            var subjects = report.Findings.Where(f => f.Rule == "concrete-dependency").Select(f => f.Subject).ToList();
            Assert.That(subjects, Does.Contain(typeof(InitWithConcrete).FullName));
            Assert.That(subjects, Does.Contain(typeof(ILeakyContract).FullName));
        }

        internal sealed class InternalService
        {
            private readonly IShooter _shooter;

            public InternalService(IShooter shooter) => _shooter = shooter;

            public void Run() => _shooter.Shoot();
        }

        [Test]
        public void AnInternalServiceWithoutAnInterface_HasNoContract()
        {
            Assert.That(Rules(Audit(typeof(IShooter), typeof(InternalService))), Does.Contain("no-contract"));
        }

        [Test]
        public void OneInterfaceAmongManyClasses_IsTooFew()
        {
            var report = Audit(typeof(IShooter), typeof(ServiceA), typeof(ServiceB), typeof(ServiceC), typeof(Engine), typeof(Cooldown), typeof(Ticking));

            Assert.That(Rules(report), Does.Contain("few-interfaces"), report.ToString());
        }

        [Test]
        public void TheCapabilityMap_IsComparedWithTheCode()
        {
            string[] map =
            {
                "# Architecture",
                "| Capability | Interface | Implemented by |",
                "|---|---|---|",
                "| Shoots | `IShooter` | `Tower` |",
                "| Vanished | `IGone` | nothing |",
                "",
                "| Other table | `INotAMapEntry` |",
            };
            var findings = ArchitectureAudit.CheckCapabilityMap(map, new[] { typeof(IShooter), typeof(StandaloneContract) }, Options()).ToList();

            Assert.That(findings.Where(f => f.Rule == "map-without-type").Select(f => f.Subject), Is.EquivalentTo(new[] { "IGone" }));
        }

        [Test]
        public void ADomainInterfaceOutsideTheMap_IsReported()
        {
            var options = new ArchitectureAuditOptions("Elsewhere") { SourceFolder = null };

            var findings = ArchitectureAudit.CheckCapabilityMap(new[] { "| Interface |", "|---|" }, new[] { typeof(StandaloneContract) }, options).ToList();

            Assert.That(findings.Single().Rule, Is.EqualTo("capability-not-in-map"));
        }

        [Test]
        public void LooseningALimitOrTurningACheckOff_IsReported()
        {
            var options = new ArchitectureAuditOptions("Game") { MaxFileLines = 5000, SourceFolder = null, MaxMethods = 10 };

            options.CapabilityMapFile = "docs/map.md";
            var findings = ArchitectureAudit.CheckLimits(options).ToList();

            Assert.That(findings.Select(f => f.Subject), Is.EquivalentTo(new[] { "MaxFileLines", "SourceFolder" }));
            Assert.That(findings.All(f => f.Rule == "loosened-limit"));
        }

        [Test]
        public void CodeInAssemblyCSharp_IsReported_WhateverItsNamespace()
        {
            var findings = ArchitectureAudit.FindCodeOutsideAssemblies(new[] { typeof(Engine) }).ToList();
            Assert.That(findings, Is.Empty, "a nested type is reported through its parent");

            findings = ArchitectureAudit.FindCodeOutsideAssemblies(new[] { typeof(StandaloneContract) }).ToList();
            Assert.That(findings.Single().Rule, Is.EqualTo("no-assembly"));
        }

        [Test]
        public void NewOnAService_IsReported_OutsideFactories()
        {
            var services = ArchitectureAudit.ServiceNames(new[] { typeof(Engine), typeof(CarWithConcreteEngine) }, "Game");
            Assert.That(services, Does.Contain(nameof(CarWithConcreteEngine)));
            Assert.That(services, Does.Not.Contain(nameof(Engine)));

            var line = new[] { "var car = new CarWithConcreteEngine(engine);" };
            Assert.That(ArchitectureAudit.ScanSource("Assets/Game.cs", line, Options(), services).Select(f => f.Rule), Does.Contain("hidden-dependency"));
            Assert.That(ArchitectureAudit.ScanSource("Assets/CarFactory.cs", line, Options(), services), Is.Empty);
        }

        [TestCase("var e = FindObjectOfType<Enemy>();", "scene-search")]
        [TestCase("var g = GameObject.Find(\"Hero\");", "scene-search")]
        [TestCase("SendMessage(\"Hit\");", "string-messaging")]
        [TestCase("StartCoroutine(Run());", "coroutine")]
        [TestCase("private async void Load() { }", "async-void")]
        [TestCase("var a = Resources.Load<Sprite>(\"x\");", "resources-load")]
        [TestCase("var o = new GameObject(\"x\");", "creation-outside-factory")]
        [TestCase("var c = go.AddComponent<Light>();", "creation-outside-factory")]
        [TestCase("var b = Instantiate(prefab);", "creation-outside-factory")]
        [TestCase("var b = GameObject.Instantiate(prefab);", "creation-outside-factory")]
        public void ForbiddenCalls_AreReported(string line, string rule)
        {
            var findings = ArchitectureAudit.ScanSource("Assets/Combat/Enemy.cs", new[] { line }, Options()).ToList();

            Assert.That(findings.Select(f => f.Rule), Does.Contain(rule));
        }

        [Test]
        public void CommentsFactoriesAndTheResolver_AreNotReported()
        {
            var options = Options();
            string[] comments = { "// new GameObject(\"x\")", "/* StartCoroutine(a);", "SendMessage(\"x\");", "*/ var a = 1;", "var e = _resolver.Instantiate(prefab);" };

            Assert.That(ArchitectureAudit.ScanSource("Assets/Enemy.cs", comments, options), Is.Empty);
            Assert.That(ArchitectureAudit.ScanSource("Assets/EnemyFactory.cs", new[] { "var o = new GameObject(\"x\");" }, options), Is.Empty);
        }

        [Test]
        public void ALongFile_IsReported()
        {
            var options = Options();
            options.MaxFileLines = 2;

            var findings = ArchitectureAudit.ScanSource("Assets/Big.cs", new[] { "a", "b", "c" }, options);

            Assert.That(findings.Select(f => f.Rule), Does.Contain("long-file"));
        }
    }
}
