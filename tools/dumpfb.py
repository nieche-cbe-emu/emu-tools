
"""tools/dumpfb.py <file.cbe> <帧号> <输出路径> —— 把某一帧的帧缓冲原样写出

和 Rust 侧 `FBDUMP=<帧号>:<路径> framecmp` 的输出逐像素对比。
调用序列一致而画面不一致时，只能这么定位。
"""
import contextlib, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

def main():
    m = cbelib.load(sys.argv[1])
    want = int(sys.argv[2])
    rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False, audio=False)
    with contextlib.redirect_stdout(io.StringIO()):
        rt.boot(); rt.app_start()
        for i in range(want + 1):
            if i % 37 == 0:
                rt.press(1 << ((i // 37) % 12))
            elif i % 37 == 4:
                rt.release()
            rt.frame()
    open(sys.argv[3], "wb").write(rt.fb.raw565())
    return 0

if __name__ == "__main__":
    sys.exit(main())
