---
name: audio-design
description: Sound design and audio production for Unity games. Covers the sound list per event, emotional intent, sources (generation tools, procedural synthesis, licensed libraries), escalating reward sounds, variation against fatigue, AudioMixer groups and snapshots, ducking, and the audio service. Use when a game or feature needs sounds or music, or when audio feels flat, repetitive or unbalanced.
---

# Audio design

Claude designs and produces every sound unless the user provides them. The official `unity:optimize-audio` and `unity:audio-setup-mixers` skills cover import settings, memory and mixer routing mechanics.

## Design

- A **sound list** per game event, each with its emotional intent ("satisfying, weighty", "light, playful"), layers and variations. Keep it in `docs/audio.md`.
- **Feel:** reward sounds escalate (pitch rises along a combo); UI sounds are crisp; impacts are satisfying.
- **No fatigue:** frequent sounds have several variants plus random pitch and volume variation.

## Sources

1. Generation tools where available, such as Unity's AI generators.
2. Procedural synthesis in code for UI and simple sounds.
3. Libraries under CC0 or a commercial-use license, recorded in `docs/`.

Never unlicensed audio. The user approves the key sounds: the main theme and the core feedback sounds. Generated and synthesized sounds still need a listening check by the user.

## Mix

- AudioMixer groups: Music, SFX, UI, Ambience, Voice.
- Snapshots for states such as pause and menus.
- Music ducks under important sounds. Loudness is consistent across sounds.

## Implementation

- An audio service in DI (library Audio module): pooled AudioSources, a limit on simultaneous instances of the same sound, variation built in.
- Sound playback is triggered by game events, never by polling.
