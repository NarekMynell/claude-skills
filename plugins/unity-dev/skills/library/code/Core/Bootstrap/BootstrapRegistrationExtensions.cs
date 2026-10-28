using Company.Product.Core.Providers;
using VContainer;
using VContainer.Unity;

namespace Company.Product.Core.Bootstrap
{
    public static class BootstrapRegistrationExtensions
    {
        // Registers the flow and its progress. Register the steps separately, in the order they run:
        // builder.Register<IBootstrapStep, FrameRateStep>(Lifetime.Singleton);
        public static void RegisterBootstrapFlow(this IContainerBuilder builder)
        {
            builder.RegisterProvider(new BootstrapProgress(BootstrapStatus.NotStarted, 0f));
            builder.RegisterEntryPoint<BootstrapFlow>();
        }
    }
}
