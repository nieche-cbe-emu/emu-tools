
"""tools/batch.py [帧数] — 把 assets/cbe 下所有模块跑一遍，汇总走到哪一步"""
import sys, os, io, glob, contextlib, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib, emu.api as A
from emu.runtime import Runtime

NF = int(sys.argv[1]) if len(sys.argv) > 1 else 3
rows = []
for p in sorted(glob.glob("assets/cbe/*.CBE") + glob.glob("assets/cbe/*.cbe")):
    name = os.path.basename(p)
    texts = []
    orig_rect = A.API[(A.LCD, "VMDrawStringRect")]
    orig_dt = A._draw_text

    def prect(mc, rt, _o=orig_rect):
        texts.append((mc.cstr(mc.arg(0)) or b"").decode("gb18030", "replace")); _o(mc, rt)

    def pdt(rt, mc, s, x, y, c, _o=orig_dt):
        texts.append(s.decode("gb18030", "replace")); _o(rt, mc, s, x, y, c)

    A.API[(A.LCD, "VMDrawStringRect")] = prect
    A._draw_text = pdt
    try:
        m = cbelib.load(p)
        rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False)
        rt.mach.BUDGET = 40_000_000
        with contextlib.redirect_stdout(io.StringIO()):
            rt.boot()
            boot_err = rt.mach.exit_reason
            rt.app_start()
            start_err = rt.mach.exit_reason
            for _ in range(NF):
                rt.frame()
        px = rt.fb.nonblank()
        os.makedirs(f"out/{m.name}", exist_ok=True)
        rt.fb.write_png(f"out/{m.name}/last.png")
        top = list(dict.fromkeys(t for t in texts if t.strip()))[:2]
        rows.append((name, m.name, m.endian, boot_err, start_err, len(rt.screens),
                     px, len(rt.unimpl), top))
    except Exception as e:
        rows.append((name, "-", "-", f"EXC {type(e).__name__}: {e}", "", 0, 0, 0, []))
    finally:
        A.API[(A.LCD, "VMDrawStringRect")] = orig_rect
        A._draw_text = orig_dt

print(f"{'文件':26s} {'模块':13s} {'端':3s} {'screen':6s} {'像素':7s} {'缺API':5s} 状态")
ok = 0
for name, mod, en, be, se, ns, px, nu, top in rows:
    st = be or se or "OK"
    if st == "OK" and ns:
        ok += 1
    txt = (" | ".join(top))[:34]
    print(f"{name:26s} {mod:13s} {en:3s} {ns:^6d} {px:7d} {nu:^5d} {st[:34]:34s} {txt}")
print(f"\n{ok}/{len(rows)} 个模块跑进主循环")
