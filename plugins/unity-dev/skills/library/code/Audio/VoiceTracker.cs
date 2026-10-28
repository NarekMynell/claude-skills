using System.Collections.Generic;
using UnityEngine;

namespace Company.Product.Audio
{
    // Bookkeeping of playing voices, separate from AudioSource playback so the limits are testable.
    internal sealed class VoiceTracker
    {
        private readonly List<Voice> _voices = new List<Voice>(32);

        public int Count => _voices.Count;

        public Voice this[int index] => _voices[index];

        public void Add(int id, AudioCue cue, AudioSource source) => _voices.Add(new Voice(id, cue, source));

        public int CountOf(AudioCue cue)
        {
            var count = 0;
            for (var i = 0; i < _voices.Count; i++)
                if (_voices[i].Cue == cue) count++;

            return count;
        }

        // Voices are kept in start order, so the first match is the oldest.
        public int IndexOfOldest(AudioCue cue)
        {
            for (var i = 0; i < _voices.Count; i++)
                if (_voices[i].Cue == cue) return i;

            return -1;
        }

        public int IndexOf(int id)
        {
            for (var i = 0; i < _voices.Count; i++)
                if (_voices[i].Id == id) return i;

            return -1;
        }

        public void RemoveAt(int index) => _voices.RemoveAt(index);

        internal readonly struct Voice
        {
            public readonly int Id;
            public readonly AudioCue Cue;
            public readonly AudioSource Source;

            public Voice(int id, AudioCue cue, AudioSource source)
            {
                Id = id;
                Cue = cue;
                Source = source;
            }
        }
    }
}
