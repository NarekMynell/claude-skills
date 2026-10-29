# Audio

Plays `AudioCue` assets on pooled AudioSources.

- **Destination:** `Audio/` (its own domain)
- **Depends on:** Pooling, DI, Extensions, Logging; VContainer.

```csharp
// Root scope
builder.RegisterAudio(_audioServiceSettings);   // IAudioService, ticked and disposed by the container

var handle = _audio.PlayAt(_impactCue, hit.point);
_audio.Stop(handle);
```

- `AudioCue` (ScriptableObject): clip variants (never the same one twice in a row), mixer group, volume and pitch with random variation, spatial blend, loop, and a maximum number of instances: playing it again beyond the limit stops its oldest instance.
- The service keeps its voices under a `DontDestroyOnLoad` object and returns finished voices to the pool in `Tick`, so register it in the root scope. While `AudioListener.pause` is on, paused voices are kept, not recycled.
- **`AudioCue` overlaps Unity's Audio Random Container** (clip variants without repeats, random volume and pitch). Compare them for the project before copying the module: keep `AudioCue` when the game needs what the service adds on top, a limit on simultaneous instances per cue that replaces the oldest instance and no repeat across all of a cue's voices; otherwise give the pooled sources an Audio Random Container (`AudioSource.resource`) and drop the cue's own variation.
- `Play` doesn't allocate once the pool is warm. Remembering each cue's last clip uses weak references, so played cues can still unload.
- `AudioVolume.ToDecibels` / `ToLinear` convert a 0–1 slider to an exposed mixer parameter and back.
- Mixer snapshots (`AudioMixerSnapshot.TransitionTo`) and ducking are set up in the project's mixer.
