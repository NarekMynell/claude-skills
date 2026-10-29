namespace Company.Product.Persistence
{
    // CRC-32 (IEEE 802.3, the zlib and PNG checksum), used to tell an intact save from a damaged one.
    internal static class Crc32
    {
        private const uint Polynomial = 0xEDB88320u;

        private static readonly uint[] Table = CreateTable();

        public static uint Compute(byte[] data, int offset, int count)
        {
            var crc = 0xFFFFFFFFu;
            var end = offset + count;
            for (var i = offset; i < end; i++) crc = Table[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
            return ~crc;
        }

        private static uint[] CreateTable()
        {
            var table = new uint[256];
            for (uint i = 0; i < table.Length; i++)
            {
                var value = i;
                for (var bit = 0; bit < 8; bit++) value = (value & 1) != 0 ? Polynomial ^ (value >> 1) : value >> 1;
                table[i] = value;
            }

            return table;
        }
    }
}
