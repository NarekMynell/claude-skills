using System;
using VContainer;
using VContainer.Unity;

namespace Company.Product.Audio
{
    // Registers the module's internal implementation under its public interface.
    public static class AudioRegistrationExtensions
    {
        // The audio service, as an entry point of the root scope: its voices live under a DontDestroyOnLoad object,
        // and its Tick returns finished voices to the pool.
        public static RegistrationBuilder RegisterAudio(this IContainerBuilder builder, AudioServiceSettings settings)
        {
            if (settings == null) throw new ArgumentNullException(nameof(settings));

            builder.RegisterInstance(settings);
            return builder.RegisterEntryPoint<AudioService>();
        }
    }
}
