
"""tools/baseline.py gen|verify|diff —— 差分测试的基准

Rust 侧要一份"标准答案"才能验证自己搬对了。这个工具用 Python 引擎
生成它：固定输入、逐帧记两个指纹，落成语言无关的文本文件。

    gen [帧数]       生成 spec/baseline/*.txt
    verify [帧数]    重新跑一遍，和存档比对（自证可复现）
    diff A.txt B.txt 找出两份基准第一次分叉的帧

**为什么记两个指纹**

    fb    帧缓冲的 CRC32。抓的是"画错了"。
    call  这一帧宿主接口**调用名序列**的 CRC32。抓的是"走错了"，
          而且分叉点直接指向某个接口，不用从像素反推。

调用指纹**只哈希名字，不哈希参数**：堆地址在两套实现里本来就可能不同，
把参数算进去只会制造假分叉。参数错了会经由帧缓冲暴露出来。

**为什么用 CRC32**

    两边都有原生实现（Python 的 zlib.crc32、Rust 的 crc32fast），
    多项式是同一个 IEEE 标准，逐字节可复现。用 FNV 之类要自己写循环，
    在 Python 里跑 240x400 的缓冲慢到不可用。

**为什么直接驱动 Runtime 而不是 Session**

    Session 那层的按键连发是按真实时钟算的（0.40 秒起始、0.12 秒间隔），
    本身就不确定。差分契约覆盖的是 Runtime；Session 的输入整形
    属于前端手感，各端自己保证。

**输入脚本 default-v1**（Rust 侧要照着实现）

    第 i 帧（从 0 起）：
        i % 37 == 0  ->  press(1 << ((i / 37) % 12))
        i % 37 == 4  ->  release(全部)
    不注入触摸——触摸坐标的语义各模块不同，放进基准只会制造噪声。
"""
import collections
import contextlib
import glob
import io
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

OUT = "spec/baseline"
FRAMES = 300
INPUT = "default-v1"

def apply_input(rt, i):

    if i % 37 == 0:
        rt.press(1 << ((i // 37) % 12))
    elif i % 37 == 4:
        rt.release()

def run(path, frames):
    m = cbelib.load(path)
    rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False, audio=False)
    rows = []
    with contextlib.redirect_stdout(io.StringIO()):
        rt.boot()
        rt.app_start()
        rt.mach.log_calls = True

        rt.mach.call_log = collections.deque(maxlen=1 << 20)
        for i in range(frames):
            rt.mach.call_log.clear()
            apply_input(rt, i)
            rt.frame()
            names = "\n".join(c[0] for c in rt.mach.call_log)
            rows.append((i,
                         zlib.crc32(rt.fb.raw565()) & 0xFFFFFFFF,
                         zlib.crc32(names.encode()) & 0xFFFFFFFF,
                         len(rt.mach.call_log)))
    return m, rt, rows

def render(m, rt, rows):
    out = ["# nieche-baseline 1",
           f"module {m.name}",
           f"endian {m.endian}",
           f"screen {rt.screen_w} {rt.screen_h}",
           f"input {INPUT}",
           f"frames {len(rows)}",
           "# idx fb call ncalls"]
    for i, fb, cl, n in rows:
        out.append(f"{i} {fb:08x} {cl:08x} {n}")
    return "\n".join(out) + "\n"

def paths():
    return sorted(glob.glob("assets/cbe/*.CBE") + glob.glob("assets/cbe/*.cbe"))

def basename_for(path):

    stem = os.path.splitext(os.path.basename(path))[0]
    return f"{stem}.txt"

def gen(frames):
    os.makedirs(OUT, exist_ok=True)
    for p in paths():
        try:
            m, rt, rows = run(p, frames)
        except Exception as e:
            print(f"   ✗ {os.path.basename(p)}: {type(e).__name__}: {e}")
            continue
        f = os.path.join(OUT, basename_for(p))
        with open(f, "w") as fh:
            fh.write(render(m, rt, rows))
        live = sum(1 for _, _, _, n in rows if n)
        print(f"   {m.name:12s} {len(rows)} 帧   有调用的 {live} 帧   -> {f}")
    return 0

def verify(frames):
    bad = []
    for p in paths():
        try:
            m, rt, rows = run(p, frames)
        except Exception as e:
            bad.append((os.path.basename(p), f"{type(e).__name__}: {e}"))
            continue
        f = os.path.join(OUT, basename_for(p))
        if not os.path.exists(f):
            bad.append((m.name, "没有存档基准"))
            continue
        if open(f).read() != render(m, rt, rows):
            bad.append((m.name, "和存档不一致"))
    print(f"   比对 {len(paths())} 个模块，不一致 {len(bad)} 个")
    for n, why in bad:
        print(f"   ✗ {n}: {why}")
    return 1 if bad else 0

def load_rows(f):
    head, rows = {}, []
    for line in open(f):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0].isdigit() and len(parts) == 4:
            rows.append((int(parts[0]), parts[1], parts[2], int(parts[3])))
        else:
            head[parts[0]] = " ".join(parts[1:])
    return head, rows

def diff(a, b):
    ha, ra = load_rows(a)
    hb, rb = load_rows(b)
    for k in ("module", "screen", "input"):
        if ha.get(k) != hb.get(k):
            print(f"   头部就不一样：{k}  {ha.get(k)!r} vs {hb.get(k)!r}")
            return 1
    for i in range(min(len(ra), len(rb))):
        if ra[i][2] != rb[i][2]:
            print(f"   第 {i} 帧**调用序列**先分叉（调用数 {ra[i][3]} vs {rb[i][3]}）")
            print(f"   -> 用 tools/engine.py 在这一帧开 trace，对比两边的调用名")
            return 1
        if ra[i][1] != rb[i][1]:
            print(f"   第 {i} 帧**画面**分叉，但调用序列一致")
            print("   -> 走对了流程、画错了内容：某个接口的参数解读或算法不同")
            return 1
    if len(ra) != len(rb):
        print(f"   前 {min(len(ra), len(rb))} 帧一致，但帧数不同：{len(ra)} vs {len(rb)}")
        return 1
    print(f"   {len(ra)} 帧完全一致")
    return 0

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "gen":
        return gen(int(sys.argv[2]) if len(sys.argv) > 2 else FRAMES)
    if cmd == "verify":
        return verify(int(sys.argv[2]) if len(sys.argv) > 2 else FRAMES)
    if cmd == "diff":
        return diff(sys.argv[2], sys.argv[3])
    print(__doc__)
    return 2

if __name__ == "__main__":
    sys.exit(main())
