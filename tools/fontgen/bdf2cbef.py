
"""tools/fontgen/bdf2cbef.py <旧 font12.cbef> <输出.cbef> [--unifont unifont.hex] <字体.bdf>...

把 12px 点阵字体（BDF）转成模拟器的 CBEF 字库。

mkfont.swift 是拿 CoreText 把矢量字体硬缩到 12 像素再二值化，笔画粘连、
横竖粗细不一；专门按 12px 设计的点阵字体每一笔都落在像素格上，原生分辨率下
清楚得多。格式、索引、度量和旧字库完全一致（ASCII 6x12、汉字 12x12、
GB2312 94x94 槽位），只换字形。

可以给多个 BDF，按顺序取第一个有这个字的（同一字体的简中、繁中、日文版
各自覆盖的符号不一样）。BDF 里都没有的字依次找：symbols12.py 手绘的全角数学符号、
Unifont 压到 12px 的字形（hex2cell.py）。**再没有才沿用旧字库的字形**，不留空白——
空白在游戏里看起来像"字没画出来"，比字形风格不统一更糟。
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hex2cell
import symbols12

AW, AH, HW, HH = 6, 12, 12, 12

def parse_bdf(path):
    glyphs = {}
    ascent = None
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = iter(f.read().splitlines())
    for line in lines:
        if line.startswith("FONT_ASCENT"):
            ascent = int(line.split()[1])
        elif line.startswith("STARTCHAR"):
            enc, bbx, rows = None, None, []
            for l in lines:
                if l.startswith("ENCODING"):
                    enc = int(l.split()[1])
                elif l.startswith("BBX"):
                    bbx = tuple(int(v) for v in l.split()[1:5])
                elif l == "BITMAP":
                    for b in lines:
                        if b == "ENDCHAR":
                            break
                        rows.append(int(b, 16) if b else 0)
                    break
            if enc is not None and enc >= 0 and bbx:
                glyphs[enc] = (bbx, rows)
    return glyphs, ascent

def cell(glyph, ascent, w, h):

    (bw, bh, xo, yo), rows = glyph
    out = [0] * h
    top = ascent - (bh + yo)
    nbits = ((bw + 7) // 8) * 8
    for r, bits in enumerate(rows[:bh]):
        y = top + r
        if not 0 <= y < h:
            continue
        for c in range(bw):
            if bits >> (nbits - 1 - c) & 1:
                x = xo + c
                if 0 <= x < w:
                    out[y] |= 1 << (w - 1 - x)
    return out

def pack(rows, w):
    bpr = (w + 7) // 8
    out = bytearray()
    for v in rows:
        v <<= bpr * 8 - w
        out += v.to_bytes(bpr, "big")
    return bytes(out)

def main():
    if len(sys.argv) < 4:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    args = sys.argv[3:]
    uni_path = None
    if "--unifont" in args:
        k = args.index("--unifont")
        uni_path = args[k + 1]
        del args[k:k + 2]
    glyphs, ascent = {}, None
    for bdf in reversed(args):
        g, ascent = parse_bdf(bdf)
        glyphs.update(g)
    old = open(sys.argv[1], "rb").read()
    assert old[:4] == b"CBEF" and tuple(old[6:10]) == (AW, AH, HW, HH)
    n_ascii, n_hanzi = struct.unpack_from("<II", old, 10)
    abpr, hbpr = (AW + 7) // 8, (HW + 7) // 8
    a_len, h_len = abpr * AH, hbpr * HH
    old_ascii = old[18:18 + n_ascii * a_len]
    old_hanzi = old[18 + n_ascii * a_len:]

    ascii_out = bytearray()
    miss_a = 0
    for c in range(n_ascii):
        g = glyphs.get(c) if c >= 0x20 else None
        if g:
            ascii_out += pack(cell(g, ascent, AW, AH), AW)
        else:
            miss_a += c >= 0x20
            ascii_out += old_ascii[c * a_len:(c + 1) * a_len]

    hanzi_out = bytearray()
    miss_h, total = [], 0
    extra = {}
    if uni_path:
        want = set()
        for i in range(n_hanzi):
            hi, lo = divmod(i, 94)
            try:
                want.add(ord(bytes([hi + 0xA1, lo + 0xA1]).decode("gb2312")))
            except UnicodeDecodeError:
                pass
        uni = hex2cell.load_hex(uni_path, want - set(glyphs))
        extra = {cp: hex2cell.hanzi_cell(*g) for cp, g in uni.items()}
    n_sym = n_uni = 0
    for i in range(n_hanzi):
        hi, lo = divmod(i, 94)
        try:
            ch = bytes([hi + 0xA1, lo + 0xA1]).decode("gb2312")
        except UnicodeDecodeError:
            hanzi_out += old_hanzi[i * h_len:(i + 1) * h_len]
            continue
        total += 1
        g = glyphs.get(ord(ch))
        if g:
            hanzi_out += pack(cell(g, ascent, HW, HH), HW)
        elif ch in symbols12.GLYPHS:
            n_sym += 1
            hanzi_out += pack(symbols12.cell(ch), HW)
        elif ord(ch) in extra:
            n_uni += 1
            hanzi_out += pack(extra[ord(ch)], HW)
        else:
            miss_h.append(ch)
            hanzi_out += old_hanzi[i * h_len:(i + 1) * h_len]

    with open(sys.argv[2], "wb") as f:
        f.write(old[:18] + ascii_out + hanzi_out)
    print(f"ASCII 缺 {miss_a}；GB2312 {total} 字，手绘符号 {n_sym}，Unifont 补 {n_uni}，"
          f"仍缺 {len(miss_h)} {''.join(miss_h[:40])}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
