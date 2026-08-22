
"""
tools/axf.py — MStar MSW8533 固件 AXF(ELF+DWARF2) 索引器

    python3 tools/axf.py sections
    python3 tools/axf.py sym <正则>          按名字查符号（地址/大小/类型）
    python3 tools/axf.py pub <正则>          在 .debug_pubnames 里查 DIE，给出 CU 偏移
    python3 tools/axf.py cu <偏移>           用 llvm-dwarfdump 展开某个 CU
    python3 tools/axf.py struct <名字>       直接把某个结构体的字段表打印出来
    python3 tools/axf.py read <地址> <长度>  按虚拟地址读取镜像内容
"""
import sys, os, re, struct, subprocess

AXF = os.environ.get("AXF") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets/firmware/I9/extracted/I9智能版V017版本0419",
    "SW_7835E_V017[PATCH3]_M10_NIECHE/调试信息/8533n_7835.axf")
DWARFDUMP = "/Library/Developer/CommandLineTools/usr/bin/llvm-dwarfdump"

class Elf:
    def __init__(self, path):
        self.f = open(path, "rb")
        d = self.f.read(52)
        (self.e_shoff,) = struct.unpack_from("<I", d, 0x20)
        self.e_shentsize, self.e_shnum, self.e_shstrndx = struct.unpack_from("<HHH", d, 0x2E)
        self.f.seek(self.e_shoff)
        raw = self.f.read(self.e_shentsize * self.e_shnum)
        hdrs = []
        for i in range(self.e_shnum):
            name, typ, flags, addr, off, size, link, info, align, entsz =                struct.unpack_from("<10I", raw, i * self.e_shentsize)
            hdrs.append(dict(name=name, type=typ, addr=addr, off=off, size=size,
                             link=link, entsize=entsz))
        sh = hdrs[self.e_shstrndx]
        self.f.seek(sh["off"]); strtab = self.f.read(sh["size"])
        for h in hdrs:
            e = strtab.find(b"\0", h["name"])
            h["sname"] = strtab[h["name"]:e].decode()
        self.sections = hdrs
        self.by_name = {h["sname"]: h for h in hdrs}

    def data(self, name):
        h = self.by_name[name]
        self.f.seek(h["off"]); return self.f.read(h["size"])

    def read_va(self, va, n):
        for h in self.sections:
            if h["addr"] and h["addr"] <= va < h["addr"] + h["size"] and h["type"] == 1:
                self.f.seek(h["off"] + va - h["addr"]); return self.f.read(n)
        return None

    def symbols(self):
        sym = self.by_name[".symtab"]; strd = self.data(".strtab")
        self.f.seek(sym["off"]); raw = self.f.read(sym["size"])
        out = []
        for o in range(0, len(raw), 16):
            nm, val, size, info, other, shndx = struct.unpack_from("<IIIBBH", raw, o)
            e = strd.find(b"\0", nm)
            out.append((strd[nm:e].decode("latin1"), val, size, info & 0xF))
        return out

def pubnames(elf):
    d = elf.data(".debug_pubnames"); o = 0; out = []
    while o + 14 <= len(d):
        ulen, ver, cu_off, cu_len = struct.unpack_from("<IHII", d, o)
        end = o + 4 + ulen; p = o + 14
        while p < end:
            (die,) = struct.unpack_from("<I", d, p); p += 4
            if die == 0: break
            e = d.find(b"\0", p)
            out.append((d[p:e].decode("latin1"), cu_off, cu_off + die))
            p = e + 1
        o = end
    return out

def dump_cu(off, maxlines=100000):
    r = subprocess.run([DWARFDUMP, f"--debug-info=0x{off:x}", "--show-children", AXF],
                       capture_output=True, text=True, errors="replace")
    return r.stdout

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sections"
    elf = Elf(AXF)
    if cmd == "sections":
        for h in elf.sections:
            if h["size"]:
                print(f"{h['sname']:26s} addr={h['addr']:#010x} off={h['off']:#010x} size={h['size']:#x}")
    elif cmd == "sym":
        pat = re.compile(sys.argv[2])
        for nm, val, size, typ in elf.symbols():
            if pat.search(nm):
                print(f"{nm:52s} {val:#010x} size={size:<6d} type={typ}")
    elif cmd == "pub":
        pat = re.compile(sys.argv[2])
        for nm, cu, die in pubnames(elf):
            if pat.search(nm):
                print(f"{nm:52s} cu={cu:#x} die={die:#x}")
    elif cmd == "cu":
        print(dump_cu(int(sys.argv[2], 0)))
    elif cmd == "read":
        va, n = int(sys.argv[2], 0), int(sys.argv[3], 0)
        b = elf.read_va(va, n)
        for i in range(0, len(b), 16):
            c = b[i:i + 16]
            print(f"{va + i:08x}: {c.hex(' ', 1):<48s} {''.join(chr(x) if 32 <= x < 127 else '.' for x in c)}")
