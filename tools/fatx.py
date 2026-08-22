
"""
tools/fatx.py <FatImage.fat> [输出目录] [--list]

MStar 的 FatImage.fat 是一个裸 FAT16 卷，前面有 16 字节 MSTM 头。
这里实现一个只读 FAT12/16/32 解析器，把整个用户分区导出到宿主目录，
用来给模拟器提供真实的 `.system/MB_MSTAR_WQVGA` 平台文件。
"""
import sys, os, struct

MSTM = b"MSTM"

class Fat:
    def __init__(self, path):
        self.f = open(path, "rb")
        head = self.f.read(16)
        self.base = 16 if head.startswith(MSTM) else 0
        self.f.seek(self.base)
        bs = self.f.read(512)
        self.bytes_per_sec = struct.unpack_from("<H", bs, 0x0B)[0]
        self.sec_per_clus = bs[0x0D]
        self.reserved = struct.unpack_from("<H", bs, 0x0E)[0]
        self.n_fats = bs[0x10]
        self.root_entries = struct.unpack_from("<H", bs, 0x11)[0]
        total16 = struct.unpack_from("<H", bs, 0x13)[0]
        self.fat_sz = struct.unpack_from("<H", bs, 0x16)[0]
        total32 = struct.unpack_from("<I", bs, 0x20)[0]
        self.fat_sz32 = struct.unpack_from("<I", bs, 0x24)[0]
        self.root_clus32 = struct.unpack_from("<I", bs, 0x2C)[0]
        self.total = total16 or total32
        self.fatsz = self.fat_sz or self.fat_sz32
        self.root_dir_sectors = (self.root_entries * 32 + self.bytes_per_sec - 1) // self.bytes_per_sec
        self.first_data_sec = self.reserved + self.n_fats * self.fatsz + self.root_dir_sectors
        clusters = (self.total - self.first_data_sec) // self.sec_per_clus
        self.bits = 12 if clusters < 4085 else (16 if clusters < 65525 else 32)
        self.fat = self._read_sectors(self.reserved, self.fatsz)

    def _read_sectors(self, sec, n):
        self.f.seek(self.base + sec * self.bytes_per_sec)
        return self.f.read(n * self.bytes_per_sec)

    def next_clus(self, c):
        if self.bits == 16:
            v = struct.unpack_from("<H", self.fat, c * 2)[0]
            return None if v >= 0xFFF8 else v
        if self.bits == 32:
            v = struct.unpack_from("<I", self.fat, c * 4)[0] & 0x0FFFFFFF
            return None if v >= 0x0FFFFFF8 else v
        o = c + c // 2
        v = struct.unpack_from("<H", self.fat, o)[0]
        v = (v >> 4) if (c & 1) else (v & 0xFFF)
        return None if v >= 0xFF8 else v

    def clus_data(self, c):
        sec = self.first_data_sec + (c - 2) * self.sec_per_clus
        return self._read_sectors(sec, self.sec_per_clus)

    def chain(self, c, limit=None):
        out = bytearray()
        while c and c >= 2:
            out += self.clus_data(c)
            if limit and len(out) >= limit:
                break
            c = self.next_clus(c)
            if c is None:
                break
        return bytes(out[:limit] if limit else out)

    def root(self):
        if self.bits == 32:
            return self.chain(self.root_clus32)
        return self._read_sectors(self.reserved + self.n_fats * self.fatsz,
                                  self.root_dir_sectors)

    def entries(self, data):
        out, lfn = [], []
        for o in range(0, len(data), 32):
            e = data[o:o + 32]
            if not e or e[0] == 0x00:
                break
            if e[0] == 0xE5:
                lfn = []; continue
            attr = e[11]
            if attr == 0x0F:
                seq = e[0] & 0x3F
                part = (e[1:11] + e[14:26] + e[28:32]).decode("utf-16-le", "ignore")
                lfn.append((seq, part.split("￿")[0].split("\x00")[0]))
                continue
            name = "".join(p for _, p in sorted(lfn)) if lfn else None
            lfn = []
            if not name:
                base = e[0:8].decode("latin1").rstrip()
                ext = e[8:11].decode("latin1").rstrip()
                name = base + ("." + ext if ext else "")
            clus = struct.unpack_from("<H", e, 26)[0] | (struct.unpack_from("<H", e, 20)[0] << 16)
            size = struct.unpack_from("<I", e, 28)[0]
            out.append((name, attr, clus, size))
        return out

    def walk(self, data=None, prefix=""):
        for name, attr, clus, size in self.entries(data if data is not None else self.root()):
            if name in (".", ".."):
                continue
            path = prefix + "/" + name if prefix else name
            if attr & 0x10:
                yield path, None, 0
                if clus >= 2:
                    yield from self.walk(self.chain(clus), path)
            else:
                yield path, clus, size

if __name__ == "__main__":
    img = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    fat = Fat(img)
    print(f"FAT{fat.bits}  簇 {fat.sec_per_clus * fat.bytes_per_sec} 字节  "
          f"总扇区 {fat.total}  数据起始扇区 {fat.first_data_sec}")
    n = 0
    for path, clus, size in fat.walk():
        if clus is None:
            print(f"  [DIR ] {path}")
            if outdir:
                os.makedirs(os.path.join(outdir, path), exist_ok=True)
            continue
        n += 1
        print(f"  {size:9d}  {path}")
        if outdir:
            dst = os.path.join(outdir, path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(fat.chain(clus, size) if clus >= 2 else b"")
    print(f"共 {n} 个文件")
