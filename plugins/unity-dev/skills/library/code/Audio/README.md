# Audio

Plays `AudioCue` assets on pooled AudioSources.

- **Destination:** `Audio/` (its own domain)
- **Depends on:** Pooling, DI, Extensions, Logging; VContainer.

```csharp
// Root scope
builder.RegisterInstance(_audioServiceSettings);
builder.RegisterEntryPoint<AudioService>();   // also resolvable as IAudioService

var handle = _audio.PlayAt(_impactCue, hit.point);
_audio.Stop(handle);
```

- `AudioCue` (ScriptableObject): clip variants (never the same one twice in a row), mixer group, volume and pitch with random variation, spatial blend, loop, and a maximum number of instances: playing it again beyond the limit stops its oldest instance.
- `AudioService` keeps its voices under a `DontDestroyOnLoad` object and returns finished voices to the pool in `Tick`, so register it as an entry point in the root scope. While `AudioListener.pause` is on, paused voices are kept, not recycled.
- `Play` doesn't allocate once the pool is warm. Remembering each cue's last clip uses weak references, so played cues can still unload.
- `AudioVolume.ToDecibels` / `ToLinear` convert a 0–1 slider to an exposed mixer parameter and back.
- Mixer snapshots (`AudioMixerSnapshot.TransitionTo`) and ducking are set up in the project's mixer.
