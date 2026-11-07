using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using UnityEngine;

namespace ProjectName.Core.Editor.Architecture
{
    // Checks compiled project code against what a script can tell of the architecture rules: services behind interfaces, no mutable
    // static state, one-way assembly references. Green is the floor, not a good design: whether the interfaces are real capabilities and
    // whether the next feature fits is for a review, and the signals in the report point it where to look.
    public static class ArchitectureAudit
    {
        private const BindingFlags Declared = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public |
                                              BindingFlags.NonPublic | BindingFlags.DeclaredOnly;

        private const int MaxHelperMethods = 8;
        private const int FailAtTimesLimit = 3;
        private const string SignalPrefix = "signal:";

        private static readonly string[] CompositionRoots = { "LifetimeScope", "ScopeInstaller" };
        private static readonly string[] FrameMethods = { "Update", "LateUpdate", "FixedUpdate" };
        private static readonly string[] ObjectMethods =
            { "ToString", "Equals", "GetHashCode", "Finalize", "Deconstruct", "GetType", "PrintMembers", "<Clone>$" };
        private static readonly string[] MutableCollections =
            { "List`1", "Dictionary`2", "HashSet`1", "Queue`1", "Stack`1", "LinkedList`1", "SortedList`2", "SortedDictionary`2" };

        private static readonly (string Rule, Regex Pattern, string Detail)[] ForbiddenCalls =
        {
            ("scene-search", new Regex(@"\b(FindObjectOfType|FindObjectsOfType|FindAnyObjectByType|FindFirstObjectByType|FindObjectsByType|GameObject\.Find\w*)\b"),
                "searches the scene at runtime instead of receiving the reference"),
            ("string-messaging", new Regex(@"\b(SendMessage|BroadcastMessage|SendMessageUpwards)\s*\("),
                "string-named messaging"),
            ("coroutine", new Regex(@"\bStartCoroutine\s*\("), "a coroutine instead of UniTask"),
            ("async-void", new Regex(@"\basync\s+void\b"), "async void: exceptions are lost"),
            ("resources-load", new Regex(@"\bResources\.Load"), "the Resources folder for project content"),
            ("creation-outside-factory", new Regex(@"(\bnew\s+GameObject\b|\.AddComponent\s*[<(]|\b(Object|GameObject)\.Instantiate\s*[<(]|(?<![\w.])Instantiate\s*[<(])"),
                "creates objects outside a factory, so they get no injection"),
        };

        public static ArchitectureReport Run(ArchitectureAuditOptions options)
        {
            var assemblies = AppDomain.CurrentDomain.GetAssemblies().Where(a => IsAudited(a.GetName().Name, options.RootNamespace)).ToList();
            var types = assemblies.SelectMany(LoadableTypes).Where(t => !IsCompilerGenerated(t) && !IsUnreadable(t)).ToList();
            var findings = new List<ArchitectureFinding>();
            findings.AddRange(CheckLimits(options));
            if (types.Count == 0)
                findings.Add(new ArchitectureFinding("nothing-audited", options.RootNamespace, "no loaded assembly is named after this root namespace: a test that checks nothing proves nothing"));
            if (options.SourceFolder != null && !Directory.Exists(options.SourceFolder))
                findings.Add(new ArchitectureFinding("nothing-audited", options.SourceFolder, "the source folder doesn't exist, so no source file was scanned"));
            var main = AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(a => a.GetName().Name == "Assembly-CSharp");
            if (main != null) findings.AddRange(FindCodeOutsideAssemblies(LoadableTypes(main)));
            findings.AddRange(CheckReferences(
                assemblies.Select(a => (a.GetName().Name, (IEnumerable<string>)a.GetReferencedAssemblies().Select(r => r.Name).ToList())),
                options.RootNamespace));
            if (options.SourceFolder != null) findings.AddRange(ScanSources(options.SourceFolder, options, ServiceNames(types, options.RootNamespace)));
            if (options.CapabilityMapFile != null)
            {
                findings.AddRange(File.Exists(options.CapabilityMapFile)
                    ? CheckCapabilityMap(File.ReadLines(options.CapabilityMapFile), types, options)
                    : new[] { new ArchitectureFinding("no-capability-map", options.CapabilityMapFile, "the capability map is missing: capability, interface, who implements it, who uses it") });
            }

            return Analyze(types, options, findings);
        }

        // Limits are the project's to tighten. Loosening one is an exception like any other, with its reason.
        internal static IEnumerable<ArchitectureFinding> CheckLimits(ArchitectureAuditOptions options)
        {
            var defaults = new ArchitectureAuditOptions(options.RootNamespace);
            if (options.SourceFolder == null) yield return Loosened(nameof(options.SourceFolder), "the source scan is off");
            if (options.CapabilityMapFile == null) yield return Loosened(nameof(options.CapabilityMapFile), "the capability map isn't compared");
            if (options.MaxConstructorDependencies > defaults.MaxConstructorDependencies) yield return Loosened(nameof(options.MaxConstructorDependencies), $"{options.MaxConstructorDependencies}, default {defaults.MaxConstructorDependencies}");
            if (options.MaxInterfaceMembers > defaults.MaxInterfaceMembers) yield return Loosened(nameof(options.MaxInterfaceMembers), $"{options.MaxInterfaceMembers}, default {defaults.MaxInterfaceMembers}");
            if (options.MaxMethods > defaults.MaxMethods) yield return Loosened(nameof(options.MaxMethods), $"{options.MaxMethods}, default {defaults.MaxMethods}");
            if (options.MaxFields > defaults.MaxFields) yield return Loosened(nameof(options.MaxFields), $"{options.MaxFields}, default {defaults.MaxFields}");
            if (options.MaxFileLines > defaults.MaxFileLines) yield return Loosened(nameof(options.MaxFileLines), $"{options.MaxFileLines}, default {defaults.MaxFileLines}");
            if (options.MaxExceptions > defaults.MaxExceptions) yield return Loosened(nameof(options.MaxExceptions), $"{options.MaxExceptions}, default {defaults.MaxExceptions}");
        }

        private static ArchitectureFinding Loosened(string option, string detail) => new ArchitectureFinding("loosened-limit", option, detail);

        // The map says what the code should be. Every interface it names exists, and every interface a domain has is in it.
        internal static IEnumerable<ArchitectureFinding> CheckCapabilityMap(IEnumerable<string> lines, IReadOnlyCollection<Type> types, ArchitectureAuditOptions options)
        {
            var named = InterfacesInMap(lines);
            var existing = new HashSet<string>(types.Where(t => t.IsInterface).Select(PlainName));
            foreach (var name in named.Where(n => !existing.Contains(n)))
                yield return new ArchitectureFinding("map-without-type", name, "the capability map names an interface the code doesn't have");
            foreach (var type in types.Where(t => t.IsInterface && !IsCoreAssembly(t, options.RootNamespace) && !t.IsNested))
            {
                if (!named.Contains(PlainName(type)))
                    yield return new ArchitectureFinding("capability-not-in-map", type.FullName, "a domain's interface that the capability map doesn't list");
            }
        }

        private static HashSet<string> InterfacesInMap(IEnumerable<string> lines)
        {
            var named = new HashSet<string>();
            var column = -1;
            foreach (var line in lines)
            {
                if (!line.TrimStart().StartsWith("|", StringComparison.Ordinal))
                {
                    column = -1;
                    continue;
                }

                var cells = line.Split('|');
                if (column < 0)
                {
                    column = Array.FindIndex(cells, c => c.Trim().Equals("Interface", StringComparison.OrdinalIgnoreCase));
                    continue;
                }

                if (column >= cells.Length) continue;
                foreach (Match match in Regex.Matches(cells[column], @"`(I[A-Z]\w*)")) named.Add(match.Groups[1].Value);
            }

            return named;
        }

        private static string PlainName(Type type)
        {
            var tick = type.Name.IndexOf('`');
            return tick < 0 ? type.Name : type.Name.Substring(0, tick);
        }

        // Classes that need other classes to work: creating one with new hides a dependency. Core's building blocks, such
        // as pools, are meant to be created by whoever needs one.
        internal static IReadOnlyCollection<string> ServiceNames(IReadOnlyCollection<Type> types, string root)
        {
            var known = new HashSet<Type>(types);
            return types.Where(t => t.IsClass && !t.IsAbstract && !t.IsNestedPrivate && !IsStatic(t) && !IsCoreAssembly(t, root) && HasProjectDependencies(t, known))
                .Select(PlainName).Distinct().ToList();
        }

        internal static ArchitectureReport Analyze(IEnumerable<Type> types, ArchitectureAuditOptions options, IEnumerable<ArchitectureFinding> extra = null)
        {
            var all = types.ToList();
            var audited = all.Where(t => !IsCompilerGenerated(t) && !IsUnreadable(t)).ToList();
            var known = new HashSet<Type>(audited);
            var findings = new List<ArchitectureFinding>();
            if (extra != null) findings.AddRange(extra);
            foreach (var type in all.Where(t => !IsCompilerGenerated(t) && IsUnreadable(t)))
                findings.Add(new ArchitectureFinding("unreadable-type", type.FullName, "a package it uses isn't loaded, so it can't be inspected"));

            foreach (var type in audited) CheckType(type, known, options, findings);

            var signals = findings.Where(f => f.Rule.StartsWith(SignalPrefix, StringComparison.Ordinal)).Select(f => new ArchitectureFinding(f.Rule.Substring(SignalPrefix.Length), f.Subject, f.Detail)).ToList();
            signals.AddRange(MirrorInterfaces(audited, options));
            findings.RemoveAll(f => f.Rule.StartsWith(SignalPrefix, StringComparison.Ordinal));
            return Filter(findings, signals, Stats(audited), options);
        }

        // A number can't say a class does too much, only where to look: past the limit it's a signal for the review. Far past it, nothing
        // that size has one job, and it fails.
        private static string Size(int value, int limit, string rule) => value > limit * FailAtTimesLimit ? rule : SignalPrefix + rule;

        // An interface that is one class's public methods under its name, used to pass the rules: real capabilities are named for what they
        // let others do. For the review, because a service's own interface can be right.
        private static IEnumerable<ArchitectureFinding> MirrorInterfaces(List<Type> audited, ArchitectureAuditOptions options)
        {
            foreach (var type in audited.Where(t => t.IsClass && !t.IsAbstract && !IsCoreAssembly(t, options.RootNamespace)))
            {
                var mirror = type.GetInterfaces().FirstOrDefault(i => PlainName(i) == "I" + PlainName(type));
                if (mirror == null) continue;
                var own = type.GetMethods(Declared).Where(m => m.IsPublic && IsOwnMethod(m)).Select(m => m.Name).ToList();
                if (own.Count == 0 || own.Except(mirror.GetMethods().Select(m => m.Name)).Any()) continue;
                yield return new ArchitectureFinding("mirror-interface", mirror.FullName, $"all of {type.Name}'s public methods under its own name: a capability, or a copy of one class?");
            }
        }

        private static void CheckType(Type type, HashSet<Type> known, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            if (type.IsInterface)
            {
                CheckInterface(type, options, findings);
                CheckMethodParameters(type, known, options, findings);
                return;
            }

            if (type.IsEnum || IsDelegate(type)) return;
            CheckStatics(type, known, findings);
            if (!type.IsClass) return;
            if (IsStatic(type))
            {
                CheckMethodParameters(type, known, options, findings);
                return;
            }

            CheckAsset(type, findings);
            CheckFrameMethods(type, findings);
            CheckInheritance(type, known, options, findings);
            if (IsCompositionRoot(type)) return;
            CheckDependencies(type, known, options, findings);
            CheckMethodParameters(type, known, options, findings);
            CheckFields(type, known, options, findings);
            CheckContract(type, known, options, findings);
            CheckSize(type, options, findings);
        }

        // Reference rules work on names, so a test can feed them any layout.
        internal static IEnumerable<ArchitectureFinding> CheckReferences(IEnumerable<(string Name, IEnumerable<string> References)> assemblies, string root)
        {
            var app = root + ".App";
            foreach (var (name, references) in assemblies)
            {
                var isCore = name == root + ".Core" || name.StartsWith(root + ".Core.", StringComparison.Ordinal);
                foreach (var reference in references.Where(r => IsAudited(r, root)))
                {
                    if (reference == app || reference.StartsWith(app + ".", StringComparison.Ordinal))
                    {
                        if (name != app && !name.StartsWith(app + ".", StringComparison.Ordinal))
                            yield return new ArchitectureFinding("dependency-direction", name, $"references {reference}: App composes domains, nothing depends on it");
                    }
                    else if (isCore && reference != root + ".Core" && !reference.StartsWith(root + ".Core.", StringComparison.Ordinal))
                    {
                        yield return new ArchitectureFinding("dependency-direction", name, $"references {reference}: Core knows no domain");
                    }
                }
            }
        }

        internal static IEnumerable<ArchitectureFinding> ScanSource(string path, IEnumerable<string> lines, ArchitectureAuditOptions options, IReadOnlyCollection<string> services = null)
        {
            var isFactory = Regex.IsMatch(Path.GetFileNameWithoutExtension(path), "(Factory|Pool|Installer|LifetimeScope|Registration|RegistrationExtensions)$");
            var newService = services != null && services.Count > 0 && !isFactory
                ? new Regex(@"\bnew\s+(" + string.Join("|", services.Select(Regex.Escape)) + @")\s*[(<]")
                : null;
            var count = 0;
            var inBlockComment = false;
            foreach (var raw in lines)
            {
                count++;
                var line = StripComments(raw, ref inBlockComment);
                foreach (var (rule, pattern, detail) in ForbiddenCalls)
                {
                    if (rule == "creation-outside-factory" && isFactory) continue;
                    if (pattern.IsMatch(line)) yield return new ArchitectureFinding(rule, path, $"line {count}: {detail}");
                }

                if (newService != null && newService.IsMatch(line))
                    yield return new ArchitectureFinding("hidden-dependency", path, $"line {count}: creates a service with new: register it, and receive its interface");
            }

            if (count > options.MaxFileLines)
                yield return new ArchitectureFinding(Size(count, options.MaxFileLines, "long-file"), path, $"{count} lines (limit {options.MaxFileLines}): probably more than one responsibility");
        }

        private static string StripComments(string line, ref bool inBlock)
        {
            var result = line;
            if (inBlock)
            {
                var end = result.IndexOf("*/", StringComparison.Ordinal);
                if (end < 0) return string.Empty;
                result = result.Substring(end + 2);
                inBlock = false;
            }

            var start = result.IndexOf("/*", StringComparison.Ordinal);
            if (start >= 0)
            {
                var end = result.IndexOf("*/", start + 2, StringComparison.Ordinal);
                if (end >= 0)
                {
                    result = result.Remove(start, end - start + 2);
                }
                else
                {
                    result = result.Substring(0, start);
                    inBlock = true;
                }
            }

            var comment = result.IndexOf("//", StringComparison.Ordinal);
            return comment >= 0 ? result.Substring(0, comment) : result;
        }

        private static IEnumerable<ArchitectureFinding> ScanSources(string folder, ArchitectureAuditOptions options, IReadOnlyCollection<string> services)
        {
            if (!Directory.Exists(folder)) return Enumerable.Empty<ArchitectureFinding>();
            return Directory.EnumerateFiles(folder, "*.cs", SearchOption.AllDirectories)
                .Select(path => path.Replace('\\', '/'))
                .Where(path => !path.Contains("/Editor/") && !path.Contains("/Tests/"))
                .SelectMany(path => ScanSource(path, File.ReadAllLines(path), options, services));
        }

        // All code belongs to a domain's assembly. Unity's and the compiler's generated types don't count.
        internal static IEnumerable<ArchitectureFinding> FindCodeOutsideAssemblies(IEnumerable<Type> types)
        {
            foreach (var type in types)
            {
                if (IsCompilerGenerated(type) || type.IsNested || type.Name.StartsWith("UnitySourceGenerated", StringComparison.Ordinal) ||
                    type.Name.StartsWith("__", StringComparison.Ordinal) || type.Name == "<Module>" || type.Namespace == "Microsoft.CodeAnalysis" ||
                    type.Namespace == "System.Runtime.CompilerServices") continue;
                yield return new ArchitectureFinding("no-assembly", type.FullName, "sits in Assembly-CSharp instead of a domain's assembly");
            }
        }

        private static void CheckInterface(Type type, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            var members = type.GetMethods(Declared).Count(m => !m.IsSpecialName) + type.GetProperties(Declared).Length + type.GetEvents(Declared).Length;
            if (members > options.MaxInterfaceMembers)
                findings.Add(new ArchitectureFinding(Size(members, options.MaxInterfaceMembers, "fat-interface"), type.FullName, $"{members} members (limit {options.MaxInterfaceMembers}): split it by role"));
        }

        private static void CheckStatics(Type type, HashSet<Type> known, List<ArchitectureFinding> findings)
        {
            foreach (var field in type.GetFields(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
            {
                if (field.IsLiteral) continue;
                var isBackingField = field.Name.Contains("k__BackingField");
                if (field.IsDefined(typeof(CompilerGeneratedAttribute), false) && !isBackingField) continue;
                var name = isBackingField ? field.Name.Substring(1, field.Name.IndexOf('>') - 1) : field.Name;
                var mutableCollection = field.FieldType.IsGenericType && MutableCollections.Contains(field.FieldType.GetGenericTypeDefinition().Name);
                var instance = Definition(field.FieldType);
                if (!field.IsInitOnly)
                    findings.Add(new ArchitectureFinding("mutable-static", type.FullName, $"static {name} can change: state belongs in a service"));
                else if (mutableCollection)
                    findings.Add(new ArchitectureFinding("mutable-static", type.FullName, $"static collection {name} holds state: state belongs in a service"));
                else if (known.Contains(instance) && DoesWork(instance))
                    findings.Add(new ArchitectureFinding("mutable-static", type.FullName, $"static {name} is an instance of {instance.Name}: a singleton"));
                else if (field.FieldType.IsArray && !field.IsPrivate)
                    findings.Add(new ArchitectureFinding("mutable-static", type.FullName, $"shared static array {name}: anyone can change its contents"));
            }

            foreach (var staticEvent in type.GetEvents(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
                findings.Add(new ArchitectureFinding("mutable-static", type.FullName, $"static event {staticEvent.Name}: subscribers outlive scopes and scenes"));
        }

        // Definitions hold data only: every user shares the same asset, and it's created outside DI.
        private static void CheckAsset(Type type, List<ArchitectureFinding> findings)
        {
            if (!typeof(ScriptableObject).IsAssignableFrom(type)) return;
            foreach (var field in type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
            {
                if (field.IsDefined(typeof(CompilerGeneratedAttribute), false) && !field.Name.Contains("k__BackingField")) continue;
                var serialized = !field.IsNotSerialized && (field.IsPublic || field.IsDefined(typeof(SerializeField), false) || field.IsDefined(typeof(SerializeReference), false));
                if (!serialized)
                    findings.Add(new ArchitectureFinding("stateful-asset", type.FullName, $"field {field.Name} isn't serialized: runtime state in a ScriptableObject, which every user shares"));
            }

            if (type.GetMethods(Declared).Any(HasInjectAttribute) || type.GetFields(Declared).Any(HasInjectAttribute) || type.GetProperties(Declared).Any(HasInjectAttribute))
                findings.Add(new ArchitectureFinding("stateful-asset", type.FullName, "receives injection: a service, not a definition"));
        }

        private static void CheckFrameMethods(Type type, List<ArchitectureFinding> findings)
        {
            if (!typeof(MonoBehaviour).IsAssignableFrom(type)) return;
            foreach (var name in FrameMethods)
            {
                if (type.GetMethod(name, Declared, null, Type.EmptyTypes, null) != null)
                    findings.Add(new ArchitectureFinding("frame-method", type.FullName, $"declares {name}: per-frame work runs in an ITickable system"));
            }
        }

        private static void CheckInheritance(Type type, HashSet<Type> known, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            var depth = 0;
            for (var current = Definition(type.BaseType); current != null && known.Contains(current); current = Definition(current.BaseType)) depth++;
            if (depth == 0) return;
            var parent = Definition(type.BaseType);
            if (depth > 1)
                findings.Add(new ArchitectureFinding("deep-inheritance", type.FullName, $"{depth} levels of project base classes: compose capabilities instead"));
            else if (!parent.IsAbstract)
                findings.Add(new ArchitectureFinding("concrete-base", type.FullName, $"inherits the concrete class {parent.Name}: compose it, or extract an abstract base with a reason"));
            else if (!IsCoreAssembly(parent, options.RootNamespace) && !IsCompositionRoot(type))
                findings.Add(new ArchitectureFinding(SignalPrefix + "base-class", parent.FullName, "a base class of the project's own: a true is-a with shared behavior, or capabilities by composition?"));
        }

        private static void CheckDependencies(Type type, HashSet<Type> known, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            var constructors = type.GetConstructors(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)
                .Where(c => !c.IsDefined(typeof(CompilerGeneratedAttribute), false)).ToList();
            var injected = type.GetMethods(Declared).Where(HasInjectAttribute);
            foreach (var parameters in constructors.Cast<MethodBase>().Concat(injected).Select(m => m.GetParameters()))
            {
                if (parameters.Length > options.MaxConstructorDependencies)
                    findings.Add(new ArchitectureFinding(Size(parameters.Length, options.MaxConstructorDependencies, "too-many-dependencies"), type.FullName, $"{parameters.Length} dependencies (limit {options.MaxConstructorDependencies}): it does too much"));
                foreach (var parameter in parameters)
                {
                    var dependency = Unwrap(parameter.ParameterType);
                    // A nested class holding its owner is one unit with it.
                    if (dependency == null || dependency.IsInterface || Definition(dependency) == Definition(type.DeclaringType)) continue;
                    if (known.Contains(Definition(dependency)) && DoesWork(Definition(dependency)))
                        findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"parameter {parameter.Name} is the concrete class {dependency.Name}: depend on the interface of the capability it needs"));
                }
            }

            var injectedMembers = type.GetFields(Declared).Where(HasInjectAttribute).Select(f => (f.Name, f.FieldType))
                .Concat(type.GetProperties(Declared).Where(HasInjectAttribute).Select(p => (p.Name, p.PropertyType)));
            foreach (var (name, memberType) in injectedMembers)
            {
                var dependency = Unwrap(memberType);
                if (dependency != null && !dependency.IsInterface && known.Contains(Definition(dependency)) && DoesWork(Definition(dependency)))
                    findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"injected {name} is the concrete class {dependency.Name}: depend on the interface of the capability it needs"));
            }
        }

        // A method that takes a class that does work depends on it as much as a constructor does.
        private static void CheckMethodParameters(Type type, HashSet<Type> known, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            bool Exposes(Type member, out Type dependency)
            {
                dependency = Unwrap(member);
                if (dependency == null || dependency.IsInterface) return false;
                var definition = Definition(dependency);
                if (definition == Definition(type) || definition == Definition(type.DeclaringType) || !known.Contains(definition)) return false;
                return !IsCoreAssembly(definition, options.RootNamespace) && DoesWork(definition);
            }

            foreach (var method in type.GetMethods(Declared).Where(m => !m.IsPrivate && !m.IsSpecialName && !HasInjectAttribute(m) && IsOwnMethod(m)))
            {
                foreach (var parameter in method.GetParameters())
                {
                    if (Exposes(parameter.ParameterType, out var dependency))
                        findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"{method.Name}'s parameter {parameter.Name} is the concrete class {dependency.Name}: take the interface of the capability it needs"));
                }

                if (Exposes(method.ReturnType, out var returned))
                    findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"{method.Name} returns the concrete class {returned.Name}: return the interface of the capability"));
            }

            foreach (var property in type.GetProperties(Declared))
            {
                var isVisible = property.GetMethod != null && !property.GetMethod.IsPrivate;
                if (isVisible && !HasInjectAttribute(property) && Exposes(property.PropertyType, out var exposed))
                    findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"property {property.Name} is the concrete class {exposed.Name}: expose the interface of the capability"));
            }
        }

        // A class may own a small helper it creates itself, and anyone may own Core's building blocks, such as a pool.
        // Everything else travels through contracts, within a domain as well as between domains.
        private static void CheckFields(Type type, HashSet<Type> known, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            foreach (var field in type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
            {
                if (HasInjectAttribute(field)) continue;
                if (field.IsDefined(typeof(CompilerGeneratedAttribute), false) && !field.Name.Contains("k__BackingField")) continue;
                var dependency = Unwrap(field.FieldType);
                if (dependency == null || dependency.IsInterface) continue;
                var definition = Definition(dependency);
                if (!known.Contains(definition) || IsCoreAssembly(definition, options.RootNamespace) || !DoesWork(definition)) continue;
                if (definition.Assembly != type.Assembly)
                    findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"field {field.Name} is {dependency.Name} from {definition.Assembly.GetName().Name}: another assembly's concrete class"));
                else if (!IsOwnedHelper(definition, type, known))
                    findings.Add(new ArchitectureFinding("concrete-dependency", type.FullName, $"field {field.Name} is the concrete class {dependency.Name}: depend on the interface of the capability it needs"));
            }
        }

        private static void CheckContract(Type type, HashSet<Type> known, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            if (type.IsAbstract || !DoesWork(type) || IsCoreAssembly(type, options.RootNamespace) || IsFrameworkShaped(type)) return;
            var implements = type.GetInterfaces().Where(i => known.Contains(Definition(i))).ToList();
            var hasAContract = type.GetInterfaces().Any(i => i != typeof(IDisposable) && !i.Name.StartsWith("IEquatable", StringComparison.Ordinal) && !i.Name.StartsWith("IComparable", StringComparison.Ordinal));
            var isService = type.IsPublic || typeof(MonoBehaviour).IsAssignableFrom(type) || HasProjectDependencies(type, known);
            if (!hasAContract && isService && HasPublicBehavior(type))
                findings.Add(new ArchitectureFinding("no-contract", type.FullName, "a class with behavior and no interface: others can only depend on its concrete type"));
            if (type.IsPublic && implements.Any(i => i.IsPublic) && !typeof(UnityEngine.Object).IsAssignableFrom(type))
                findings.Add(new ArchitectureFinding("public-implementation", type.FullName, "implements a public interface and is public itself: implementations are internal"));
        }

        private static void CheckSize(Type type, ArchitectureAuditOptions options, List<ArchitectureFinding> findings)
        {
            var methods = type.GetMethods(Declared).Count(IsOwnMethod);
            if (methods > options.MaxMethods)
                findings.Add(new ArchitectureFinding(Size(methods, options.MaxMethods, "large-class"), type.FullName, $"{methods} methods (limit {options.MaxMethods}): more than one responsibility"));
            var fields = type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly).Length;
            if (fields > options.MaxFields && DoesWork(type))
                findings.Add(new ArchitectureFinding(Size(fields, options.MaxFields, "large-class"), type.FullName, $"{fields} fields (limit {options.MaxFields}): more than one responsibility"));
        }

        private static List<string> Stats(List<Type> audited)
        {
            var stats = new List<string>();
            foreach (var group in audited.GroupBy(t => t.Assembly.GetName().Name).OrderBy(g => g.Key))
            {
                var interfaces = group.Count(t => t.IsInterface);
                var classes = group.Count(t => t.IsClass && !IsStatic(t) && !IsDelegate(t) && !IsCompositionRoot(t) && DoesWork(t));
                stats.Add($"{group.Key}: {interfaces} interfaces, {classes} classes with behavior");
            }

            return stats;
        }

        private static ArchitectureReport Filter(List<ArchitectureFinding> findings, List<ArchitectureFinding> signals, List<string> stats, ArchitectureAuditOptions options)
        {
            var open = new List<ArchitectureFinding>();
            var excepted = new List<ArchitectureFinding>();
            var used = new HashSet<(string, string)>();
            foreach (var finding in findings.Distinct())
            {
                if (options.Exceptions.TryGetValue((finding.Rule, finding.Subject), out var reason))
                {
                    excepted.Add(new ArchitectureFinding(finding.Rule, finding.Subject, $"{finding.Detail} [accepted: {reason}]"));
                    used.Add((finding.Rule, finding.Subject));
                }
                else
                {
                    open.Add(finding);
                }
            }

            if (options.Exceptions.Count > options.MaxExceptions)
                open.Add(new ArchitectureFinding("too-many-exceptions", options.RootNamespace, $"{options.Exceptions.Count} exceptions (limit {options.MaxExceptions}): this is a different architecture, which is the user's decision"));

            var unused = options.Exceptions.Where(e => !used.Contains(e.Key))
                .Select(e => new ArchitectureFinding(e.Key.Rule, e.Key.Subject, $"nothing matches this exception any more: {e.Value}")).ToList();
            return new ArchitectureReport(open, excepted, unused, signals, stats);
        }

        // Reflection fails on a type whose members name a type from an assembly that isn't loaded.
        private static bool IsUnreadable(Type type)
        {
            try
            {
                type.GetFields(Declared);
                type.GetMethods(Declared);
                type.GetConstructors(Declared);
                _ = typeof(UnityEngine.Object).IsAssignableFrom(type);
                return false;
            }
            catch (Exception exception) when (exception is TypeLoadException || exception is FileNotFoundException)
            {
                return true;
            }
        }

        private static bool IsAudited(string assembly, string root)
        {
            if (assembly != root && !assembly.StartsWith(root + ".", StringComparison.Ordinal)) return false;
            return !assembly.EndsWith(".Tests", StringComparison.Ordinal) && !assembly.EndsWith("Tests", StringComparison.Ordinal) &&
                   !assembly.EndsWith(".Editor", StringComparison.Ordinal) && !assembly.Contains(".Editor.");
        }

        private static bool IsCoreAssembly(Type type, string root)
        {
            var name = type.Assembly.GetName().Name;
            return name == root + ".Core" || name.StartsWith(root + ".Core.", StringComparison.Ordinal);
        }

        private static IEnumerable<Type> LoadableTypes(Assembly assembly)
        {
            try
            {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException exception)
            {
                return exception.Types.Where(t => t != null);
            }
        }

        // A class that does work, as opposed to data: it has methods of its own beyond accessors and object overrides.
        private static bool DoesWork(Type type)
        {
            if (!type.IsClass || IsDelegate(type) || typeof(ScriptableObject).IsAssignableFrom(type)) return false;
            return type.GetMethods(Declared).Any(IsOwnMethod) || (type.IsAbstract && type.GetInterfaces().Length > 0);
        }

        private static bool IsOwnMethod(MethodInfo method) =>
            !method.IsSpecialName && !method.IsDefined(typeof(CompilerGeneratedAttribute), false) && !method.Name.Contains("<") && !ObjectMethods.Contains(method.Name);

        // A helper its owner can create and replace freely: small, needing nothing from the project, holding no other class
        // that does work, and with no Unity lifetime. A tree of classes creating each other is no helper.
        private static bool IsOwnedHelper(Type helper, Type owner, HashSet<Type> known)
        {
            if (Definition(helper.DeclaringType) == Definition(owner)) return true;
            if (typeof(UnityEngine.Object).IsAssignableFrom(helper) || HasProjectDependencies(helper, known)) return false;
            if (helper.GetMethods(Declared).Count(IsOwnMethod) > MaxHelperMethods) return false;
            return !helper.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)
                .Select(f => Unwrap(f.FieldType))
                .Any(f => f != null && !f.IsInterface && known.Contains(Definition(f)) && DoesWork(Definition(f)));
        }

        private static bool HasProjectDependencies(Type type, HashSet<Type> known)
        {
            var constructors = type.GetConstructors(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly);
            return constructors.Cast<MethodBase>().Concat(type.GetMethods(Declared).Where(HasInjectAttribute))
                .SelectMany(m => m.GetParameters())
                .Any(p => IsProjectDependency(p.ParameterType, known));
        }

        private static bool IsProjectDependency(Type parameter, HashSet<Type> known)
        {
            var unwrapped = parameter.IsInterface ? parameter : Unwrap(parameter);
            if (unwrapped == null) return false;
            var definition = Definition(unwrapped);
            return known.Contains(definition) && (definition.IsInterface || DoesWork(definition));
        }

        private static bool HasPublicBehavior(Type type) => type.GetMethods(Declared).Any(m => m.IsPublic && !m.IsStatic && IsOwnMethod(m));

        // Types whose shape a framework dictates: they can't sit behind a project interface in any useful way.
        private static bool IsFrameworkShaped(Type type) =>
            typeof(Exception).IsAssignableFrom(type) || typeof(Attribute).IsAssignableFrom(type);

        private static bool IsCompositionRoot(Type type)
        {
            for (var current = type.BaseType; current != null; current = current.BaseType)
                if (CompositionRoots.Contains(current.Name)) return true;
            return false;
        }

        private static bool HasInjectAttribute(MemberInfo member) => member.GetCustomAttributes(false).Any(a => a.GetType().Name == "InjectAttribute");

        private static bool IsStatic(Type type) => type.IsAbstract && type.IsSealed;

        private static bool IsDelegate(Type type) => typeof(Delegate).IsAssignableFrom(type);

        private static bool IsCompilerGenerated(Type type)
        {
            for (var current = type; current != null; current = current.DeclaringType)
                if (current.IsDefined(typeof(CompilerGeneratedAttribute), false) || current.Name.Contains("<")) return true;
            return false;
        }

        private static Type Definition(Type type) => type != null && type.IsGenericType ? type.GetGenericTypeDefinition() : type;

        // The element type of arrays, lists and factories, so IReadOnlyList<Enemy> and Func<Enemy> count as Enemy.
        private static Type Unwrap(Type type)
        {
            if (type.IsByRef || type.IsArray) return Unwrap(type.GetElementType());
            if (type.IsGenericParameter) return null;
            if (type.IsGenericType && type.Namespace != null && type.Namespace.StartsWith("System", StringComparison.Ordinal))
            {
                var arguments = type.GetGenericArguments();
                return arguments.Length == 0 ? null : Unwrap(arguments[arguments.Length - 1]);
            }

            return type.IsClass || type.IsInterface ? type : null;
        }
    }
}
