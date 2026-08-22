
"""
tools/cbex.py <module.cbe> [outdir] — 解包 CBE 内的资源

资源条目按名字导出原始字节。注意：多数游戏的图片资源不是原始 GIF/PNG，
而是打包时转成的平台私有位图格式（首字节 0x01 + 头），需要单独解码器；
本工具只负责按索引正确切分并落盘。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from cbelib.imgcodec import decode as decode_img, ImgError
from emu.lcd import rgb565_to_png

MAGICS = [(b'GIF8', 'gif'), (b'\x89PNG', 'png'), (b'MThd', 'mid'),
          (b'RIFF', 'wav'), (b'BM', 'bmp'), (b'\xff\xd8\xff', 'jpg')]

def kind(b):
    for magic, name in MAGICS:
        if b.startswith(magic):
            return name
    return 'raw'

TYPE_NAME = {0: "raw565", 1: "gif", 2: "script", 3: "png", 5: "text",
             10: "midi", 12: "mp3"}

def dump(arch, outdir, label):

    if not arch:
        return
    os.makedirs(outdir, exist_ok=True)
    pngdir = os.path.join(outdir, "png")
    stat, decoded, failed = {}, 0, 0
    for e in arch.entries:
        t = e.data[0] if e.data else -1
        k = TYPE_NAME.get(t, f"type{t}")
        stat[k] = stat.get(k, 0) + 1
        safe = e.name.replace('/', '_').replace('\\', '_')
        with open(os.path.join(outdir, safe), 'wb') as f:
            f.write(e.data)
        try:
            img = decode_img(e.data)
        except Exception:
            failed += 1
            continue
        if not img:
            continue
        os.makedirs(pngdir, exist_ok=True)
        base = os.path.splitext(safe)[0] + ".png"
        rgb565_to_png(os.path.join(pngdir, base), img["width"], img["height"],
                      img["rgb565"], img.get("transparent"))
        decoded += 1
    print(f"  {label}: {arch.count} 项 -> {outdir}   {stat}")
    print(f"      解码出 {decoded} 张图片 -> {pngdir}" + (f"（{failed} 张失败）" if failed else ""))

if __name__ == '__main__':
    m = cbelib.load(sys.argv[1])
    base = sys.argv[2] if len(sys.argv) > 2 else os.path.join('out', m.name)
    print(f"解包 {m.name}")
    dump(m.icons, os.path.join(base, 'icons'), '内建资源')
    dump(m.res, os.path.join(base, 'res'), '主资源包')
    for tag, blob in (('ro.bin', m.ro), ('rw.bin', m.rw)):
        os.makedirs(base, exist_ok=True)
        open(os.path.join(base, tag), 'wb').write(blob)
    print(f"  段镜像 -> {base}/ro.bin, {base}/rw.bin")
