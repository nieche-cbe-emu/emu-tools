
"""tools/dumpboot.py <file.cbe> —— 跑模块入口，打印可与 Rust 侧 bootcmp 比对的结果

cb0/cb1 是模块自己写回来的函数地址：入口约定判错、宿主上下文摆错、
内存落位错，任何一样都会让它们对不上。
"""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

def main():
    if len(sys.argv) < 2:
        print("用法: dumpboot.py <file.cbe>", file=sys.stderr)
        return 2
    try:
        m = cbelib.load(sys.argv[1])
    except Exception as e:
        print(f"ERROR load {e}")
        return 1
    rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False, audio=False)
    print(f"module {m.name}")
    with contextlib.redirect_stdout(io.StringIO()):
        rt.boot()
    print(f"style {rt.style}")
    print(f"cb0 {(rt.mod_cb0 or 0):#x}")
    print(f"cb1 {(rt.mod_cb1 or 0):#x}")
    print(f"managers {len(rt.managers)}")
    print(f"exit {rt.mach.exit_reason or '-'}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
