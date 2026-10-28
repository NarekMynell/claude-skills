namespace Company.Product.Core.DI
{
    public interface IFactory<out T>
    {
        T Create();
    }
}
