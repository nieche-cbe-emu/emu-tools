
"""tools/play.py <module.cbe> [帧数] — 引导 + app_start + 跑主循环，把每帧存成 PNG"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime
from emu.patches import offline_activate

path = sys.argv[1]
nframes = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8
ROT = int(sys.argv[sys.argv.index("--rotate") + 1]) if "--rotate" in sys.argv else 0
m = cbelib.load(path)
if '--online' not in sys.argv:
    offline_activate(m)
rt = Runtime(m, trace=False, quiet_log=False)
outdir = f"out/{m.name}/frames"
os.makedirs(outdir, exist_ok=True)

print(f"== boot {m.name} ==")
rt.boot()
print(f"== app_start ==")
rt.app_start()
print(f"   exit={rt.mach.exit_reason}  screens={len(rt.screens)}")
if not rt.screens:
    print("   没有注册任何 screen，无法进入主循环"); rt.report_unimpl(); sys.exit(1)

for n in range(nframes):
    rt.frame(event=0, data=0)
    p = rt.fb.write_png(f"{outdir}/frame{n:03d}.png", rotate=ROT)
    rt.write_svg(f"{outdir}/frame{n:03d}.svg", scale=2)
    print(f"   frame {n}: 非黑像素 {rt.fb.nonblank()}/{rt.fb.w*rt.fb.h}  exit={rt.mach.exit_reason}  -> {p}")
    rt.mach.exit_reason = None
rt.report_unimpl(30)
rt.report_errors()
