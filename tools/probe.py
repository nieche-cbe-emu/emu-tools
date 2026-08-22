
"""tools/probe.py <module.cbe> — boot + app_start，然后扫描内存里被模块登记的回调指针"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

m = cbelib.load(sys.argv[1])
rt = Runtime(m, trace=False, quiet_log=False)
mach = rt.mach
rt.boot()
print(f"entry ok; app_start={rt.mod_cb0:#x} app_stop={rt.mod_cb1:#x}")
mach.call(rt.mod_cb0)
print(f"app_start done, exit={mach.exit_reason}")

ro_lo, ro_hi = mach.ro_base, mach.ro_base + len(m.ro)

def blk(a):
    best = None
    for p, (n, tag) in mach.data.blocks.items():
        if p <= a < p + n:
            best = f"{tag}+{a - p:#x}"
    return best or ""

def scan(name, base, size):
    buf = bytes(mach.uc.mem_read(base, size))
    hits = []
    for o in range(0, size - 4, 4):
        v = struct.unpack_from('<I', buf, o)[0]
        if v & 1 and ro_lo <= (v & ~1) < ro_hi and (v & ~1) > 0x100:
            hits.append((base + o, v))
    if hits:
        print(f"\n{name}: {len(hits)} 个疑似模块回调指针")
        for a, v in hits[:80]:
            print(f"   [{mach.where(a)}] {blk(a):22s} -> RO+{v & ~1:#x}")

scan("RW(.data/.bss)", mach.RW_BASE, m.rw_size)
scan("HEAP", mach.HEAP_BASE, mach.heap.cur - mach.HEAP_BASE)
scan("DATA(宿主结构)", mach.DATA_BASE, mach.data.cur - mach.DATA_BASE)
rt.report_unimpl()
