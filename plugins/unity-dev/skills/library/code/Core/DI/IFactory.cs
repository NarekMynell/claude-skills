namespace Company.Product.Core.DI
{
    // Create hands what it returns to the caller, who destroys or disposes it.
    public interface IFactory<out T>
    {
        T Create();
    }
}
