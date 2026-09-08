
"""tools/dumplayout.py <file.cbe> —— 打印一个模块的段落摆放

和 Rust 侧的 `layout` 逐行比对，这是阶段 03 的第一道验收：
地址算错的话，后面所有涉及指针的差分都会假分叉，而且极难定位。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.machine import Machine, align_up

def main():
    if len(sys.argv) < 2:
        print("用法: dumplayout.py <file.cbe>", file=sys.stderr)
        return 2
    try:
        m = cbelib.load(sys.argv[1])
    except Exception as e:
        print(f"ERROR {e}")
        return 1
    ro_base = m.load_base or Machine.RO_DEFAULT
    ro_size = align_up(max(m.image_size, len(m.ro)))
    rw_size = align_up(max(m.rw_size, len(m.rw)) + 0x10000)
    rw_base = Machine.rw_place(m) if m.load_base else Machine.RW_BASE
    print(f"module {m.name}")
    print(f"endian {m.endian}")
    print(f"ro_base {ro_base:#x}")
    print(f"ro_size {ro_size:#x}")
    print(f"rw_base {rw_base:#x}")
    print(f"rw_size {rw_size:#x}")
    print(f"ro_len {len(m.ro):#x}")
    print(f"rw_len {len(m.rw):#x}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
