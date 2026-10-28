using Company.Product.Core.Algorithms;

namespace Company.Product.Core.Tests.Algorithms
{
    // Rows are written top to bottom: '#' is a wall, anything else is walkable.
    internal sealed class TestGrid : IWalkableGrid
    {
        private readonly string[] _rows;

        public TestGrid(params string[] rows) => _rows = rows;

        public int Width => _rows[0].Length;

        public int Height => _rows.Length;

        public bool IsWalkable(int x, int y) => _rows[Height - 1 - y][x] != '#';
    }
}
