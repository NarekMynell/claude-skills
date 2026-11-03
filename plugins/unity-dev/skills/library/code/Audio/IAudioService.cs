using UnityEngine;

namespace ProjectName.Audio
{
    public interface IAudioService
    {
        AudioHandle Play(AudioCue cue);
        AudioHandle PlayAt(AudioCue cue, Vector3 position);
        bool IsPlaying(AudioHandle handle);
        void Stop(AudioHandle handle);
        void StopAll();
    }
}
