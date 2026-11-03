namespace ProjectName.Core.Algorithms
{
    public interface IWalkableGrid
    {
        int Width { get; }
        int Height { get; }
        bool IsWalkable(int x, int y);
    }
}
