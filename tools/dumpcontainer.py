
"""tools/dumpcontainer.py <file.cbe> —— 容器解析结果的语言无关转储

和 Rust 侧的 cbedump 输出**逐行相同**，这是阶段 02 的验收手段。
条目数据不打出来，打它的 CRC32：既能发现一个字节的偏差，
又不会让比对文件涨到几百兆。
"""
import os
import sys
import struct
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from cbelib import imgcodec, lz

def dump_archive(tag, a):
    print(f"{tag} count={a.count} data_off={a.data_off:#x} "
          f"data_size={a.data_size:#x} base={a.base:#x} size={a.size:#x}")
    for i, e in enumerate(a.entries):

        un = ""
        if e.data and e.data[0] == 2:
            try:
                v = lz.unpack_entry(e.data)
            except Exception:
                v = None
            if v is not None:
                un = f" lz={zlib.crc32(v) & 0xFFFFFFFF:08x}:{len(v)}"

        img = ""
        try:
            im = imgcodec.decode(e.data) if e.data else None
        except Exception:
            im = None
        if im:
            px = b"".join(struct.pack("<H", v & 0xFFFF) for v in im["rgb565"])
            tr = im.get("transparent")
            a = im.get("alpha")
            img = (f" img={im['width']}x{im['height']}:"
                   f"{zlib.crc32(px) & 0xFFFFFFFF:08x}:"
                   f"tr{tr if tr is not None else '-'}:"
                   f"a{zlib.crc32(bytes(a)) & 0xFFFFFFFF:08x}" if a else
                   f" img={im['width']}x{im['height']}:"
                   f"{zlib.crc32(px) & 0xFFFFFFFF:08x}:"
                   f"tr{tr if tr is not None else '-'}:a-")
        print(f"E {i} {e.name} {e.off:#x} {e.size:#x} "
              f"{zlib.crc32(e.data) & 0xFFFFFFFF:08x}{un}{img}")

def main():
    if len(sys.argv) < 2:
        print("用法: dumpcontainer.py <file.cbe>", file=sys.stderr)
        return 2
    try:
        m = cbelib.load(sys.argv[1])
    except Exception as e:
        print(f"ERROR {e}")
        return 1
    print(f"module {m.name}")
    print(f"endian {m.endian}")
    print(f"load_base {m.load_base:#x}")
    print(f"image_size {m.image_size:#x}")
    print(f"image_end {m.image_end:#x}")
    print(f"rw_size {m.rw_size:#x}")
    print(f"ro off={m.ro_off:#x} size={len(m.ro):#x} chk={m.ro_chk:#x} "
          f"crc={zlib.crc32(m.ro) & 0xFFFFFFFF:08x}")
    print(f"rw off={m.rw_off:#x} size={len(m.rw):#x} chk={m.rw_chk:#x} "
          f"crc={zlib.crc32(m.rw) & 0xFFFFFFFF:08x}")
    if m.icons:
        dump_archive("icons", m.icons)
    else:
        print("icons none")
    if m.res:
        dump_archive("res", m.res)
    else:
        print("res none")
    print(f"packages {len(m.packages)}")
    for nm, a in m.packages.items():
        dump_archive(f"pkg[{nm}]", a)
    return 0

if __name__ == "__main__":
    sys.exit(main())
