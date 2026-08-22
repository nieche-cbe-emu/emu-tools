
"""
tools/fontscan.py <文件> [--stride 32] [--step 1]

在二进制里定位 GB2312 点阵字库。判据：按 index=(hi-0xA1)*94+(lo-0xA1) 布局时，
汉字「一」(GB2312 D2BB) 的字形极有特征——只有中间一两行是实心横条，其余全空；
再用「十」(CAAE，一横一竖) 和全角空格「　」(A1A1，全空) 交叉验证。
"""
import sys, os

def idx(gb):
    hi, lo = gb >> 8, gb & 0xFF
    return (hi - 0xA1) * 94 + (lo - 0xA1)

YI, SHI, SP, KOU = 0xD2BB, 0xCAAE, 0xA1A1, 0xBFDA

def rows(buf, off, stride, w):
    bpr = (w + 7) // 8
    return [int.from_bytes(buf[off + r * bpr:off + (r + 1) * bpr], "big")
            for r in range(stride // bpr)]

def looks_like_yi(rw, w):
    full = (1 << w) - 1
    solid = [i for i, v in enumerate(rw) if bin(v).count("1") >= w - 3]
    empty = [i for i, v in enumerate(rw) if v == 0]
    return 1 <= len(solid) <= 3 and len(empty) >= len(rw) - 4 and        len(rw) // 4 <= (solid[0] if solid else 0) <= len(rw) * 3 // 4

def scan(path, stride, w, step=1, limit=None):
    buf = open(path, "rb").read()
    n = len(buf)
    hits = []
    iy, ish, isp = idx(YI), idx(SHI), idx(SP)
    need = max(iy, ish, isp) * stride + stride
    for base in range(0, n - need, step):
        oy = base + iy * stride
        rw = rows(buf, oy, stride, w)
        if not looks_like_yi(rw, w):
            continue

        if any(buf[base + isp * stride: base + isp * stride + stride]):
            continue

        rs = rows(buf, base + ish * stride, stride, w)
        solid = sum(1 for v in rs if bin(v).count("1") >= w - 3)
        inked = sum(1 for v in rs if v)
        if solid < 1 or inked < len(rs) // 2:
            continue
        hits.append(base)
        if limit and len(hits) >= limit:
            break
    return buf, hits

def show(buf, base, stride, w, gb):
    bpr = (w + 7) // 8
    off = base + idx(gb) * stride
    for r in range(stride // bpr):
        v = int.from_bytes(buf[off + r * bpr:off + (r + 1) * bpr], "big")
        print("   " + "".join("█" if v & (1 << (w - 1 - c)) else "·" for c in range(w)))

if __name__ == "__main__":
    path = sys.argv[1]
    strides = [(32, 16), (24, 12)] if "--stride" not in sys.argv else        [(int(sys.argv[sys.argv.index("--stride") + 1]),
          int(sys.argv[sys.argv.index("--width") + 1]))]
    step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 1
    for stride, w in strides:
        buf, hits = scan(path, stride, w, step, limit=4)
        print(f"stride={stride} ({w}x{stride // ((w + 7) // 8)}): 命中 {len(hits)} 处 "
              f"{[hex(h) for h in hits]}")
        for h in hits[:2]:
            for gb, name in ((YI, "一"), (SHI, "十"), (KOU, "口")):
                print(f"  base={h:#x}  {name}:")
                show(buf, h, stride, w, gb)
