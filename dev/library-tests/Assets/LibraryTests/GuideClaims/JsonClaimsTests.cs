using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;

namespace LibraryTests.GuideClaims
{
    // What the serialization reference claims about moving from JsonUtility to Newtonsoft. A failure after a package
    // upgrade means the guide is out of date: fix the guide, not the test.
    public sealed class JsonClaimsTests
    {
        [Serializable]
        private sealed class Stats
        {
            public int PublicField = 1;
            [SerializeField] private int _serializeField = 2;
            [JsonProperty] private int _jsonProperty = 3;

            public int Sum => _serializeField + _jsonProperty;
        }

        private sealed class Scores
        {
            public Dictionary<string, int> ByLevel = new Dictionary<string, int> { { "first", 7 } };
        }

        [Test]
        public void APrivateSerializeField_IsLeftOut_AndJsonPropertyIsWritten()
        {
            var json = JObject.Parse(JsonConvert.SerializeObject(new Stats()));

            Assert.That(new Stats().Sum, Is.EqualTo(5));
            Assert.That(json.ContainsKey("PublicField"), Is.True);
            Assert.That(json.ContainsKey("_serializeField"), Is.False);
            Assert.That(json.ContainsKey("_jsonProperty"), Is.True);
        }

        [Test]
        public void AVector3_FailsOnItsOwnProperties()
        {
            var failure = Assert.Throws<JsonSerializationException>(() => JsonConvert.SerializeObject(Vector3.one));

            Assert.That(failure.Message, Does.Contain("normalized"));
        }

        [Test]
        public void ADictionary_SurvivesNewtonsoft_AndJsonUtilityDropsIt()
        {
            var scores = new Scores();

            var viaNewtonsoft = JsonConvert.DeserializeObject<Scores>(JsonConvert.SerializeObject(scores));

            Assert.That(viaNewtonsoft.ByLevel["first"], Is.EqualTo(7));
            Assert.That(JsonUtility.ToJson(scores), Is.EqualTo("{}"));
        }
    }
}
