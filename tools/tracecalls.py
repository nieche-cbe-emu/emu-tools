
"""tools/tracecalls.py <file.cbe> <帧号> —— 把某一帧的宿主调用逐条打出来

帧号 -1 表示追 app_start（帧缓冲在那里就可能被画过）。

和 Rust 侧 `TRACE=<帧号> framecmp` 的输出对拍，找出**第一条不同的调用**。
差分基准只能告诉你"第几帧分叉"，这个告诉你"分在哪一条"。

    TRACEARGS=1   连前四个参数一起打
    TRACERET=1    连返回值一起打——名字和参数都对得上、行为还是不同时，
                  差别只可能在返回值里
"""
import collections
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.machine import Machine
from emu.runtime import Runtime

WITH_ARGS = bool(os.environ.get("TRACEARGS"))
WITH_RET = bool(os.environ.get("TRACERET"))

def install_tracer():

    import unicorn.arm_const as AC
    orig = Machine._on_trap

    def traced(self, uc, address, size, user):
        orig(self, uc, address, size, user)
        if self.log_calls and WITH_RET and self.call_log:
            r = uc.reg_read(AC.UC_ARM_REG_R0)
            n, a, lr = self.call_log[-1]
            self.call_log[-1] = (n, a, lr, r)

    Machine._on_trap = traced

def fmt(log):
    out = []
    for rec in log:
        n, a = rec[0], rec[1]
        line = n
        if WITH_ARGS:
            line += " " + " ".join(hex(x) for x in a[:4])
        if WITH_RET and len(rec) > 3:
            line += f" -> {rec[3]:#x}"
        out.append(line)
    return out

def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    want = int(sys.argv[2])
    if WITH_RET:
        install_tracer()
    m = cbelib.load(sys.argv[1])
    rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False, audio=False)
    names = []
    with contextlib.redirect_stdout(io.StringIO()):
        rt.boot()
        rt.mach.log_calls = True
        rt.mach.call_log = collections.deque(maxlen=1 << 20)
        rt.app_start()
        if want < 0:
            names = fmt(rt.mach.call_log)
        for i in range(max(want + 1, 0)):
            rt.mach.call_log.clear()
            if i % 37 == 0:
                rt.press(1 << ((i // 37) % 12))
            elif i % 37 == 4:
                rt.release()
            rt.frame()
            if i == want:
                names = fmt(rt.mach.call_log)
    print("\n".join(names))
    return 0

if __name__ == "__main__":
    sys.exit(main())
