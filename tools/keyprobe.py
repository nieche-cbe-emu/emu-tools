
"""
tools/keyprobe.py <module.cbe> [--frames 6] [--bits 16]

按键的位掩码由模块自己定义（`MF_KEY_*` 在模块头文件里，固件 DWARF 里没有），
所以只能试。这里离线逐位试探：对每一位分别按下若干帧，比较画面是否变化，
报告哪些位是"有反应"的，以及变化幅度（改变的像素数）。
"""
import sys, os, io, contextlib, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

def snapshot(rt):
    return bytes(rt.mach.uc.mem_read(rt.fb.buf, rt.fb.bytes))

def diff(a, b):
    return sum(1 for i in range(0, len(a), 2) if a[i:i + 2] != b[i:i + 2])

def run(path, nframes, bits, warm=6):
    m = cbelib.load(path)
    results = []
    for b in range(bits):
        rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False)
        rt.mach.BUDGET = 40_000_000
        with contextlib.redirect_stdout(io.StringIO()):
            rt.boot(); rt.app_start()
            for _ in range(warm):
                rt.frame()
            base = snapshot(rt)
            rt.press(1 << b)
            for _ in range(nframes):
                rt.frame()
            rt.release()
            for _ in range(nframes):
                rt.frame()
            after = snapshot(rt)
        results.append((b, diff(base, after)))
    return m, results

if __name__ == "__main__":
    path = sys.argv[1]
    nf = int(sys.argv[sys.argv.index("--frames") + 1]) if "--frames" in sys.argv else 6
    nb = int(sys.argv[sys.argv.index("--bits") + 1]) if "--bits" in sys.argv else 16
    m, res = run(path, nf, nb)

    noise = min(d for _, d in res) if res else 0
    print(f"{m.name}：逐位试探（噪声基线 {noise} 像素）")
    hits = [(b, d) for b, d in res if d > max(noise * 2, 200)]
    for b, d in sorted(hits, key=lambda x: -x[1]):
        print(f"   bit{b:<2d}  掩码 {1 << b:#06x}   变化 {d} 像素")
    if not hits:
        print("   没有明显反应的位——可能这个画面本来就不吃按键")
