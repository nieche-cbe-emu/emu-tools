
"""
tools/demo.py <module.cbe> [帧数] [--key 0x20] [--every 6]

跑模块并周期性按键，把每帧输出成 PNG + 可读 SVG。
按键是位掩码（固件 SCREEN_IsKeyDown 就是按掩码判定的），
默认 0x20 —— 用 tools/demo.py --probe 可以逐位试出各键的掩码。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1], 0)        if name in sys.argv and isinstance(default, int) else default

path = sys.argv[1]
nframes = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 20
key = int(sys.argv[sys.argv.index("--key") + 1], 0) if "--key" in sys.argv else 0x20
every = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 6

m = cbelib.load(path)
rt = Runtime(m, trace=False, quiet_log=False, trace_fs=False,
             audio="--audio" in sys.argv)
rt.mach.BUDGET = 40_000_000
out = f"out/{m.name}/demo"
os.makedirs(out, exist_ok=True)
print(f"== {m.name} ==")
rt.boot()
rt.app_start()
for n in range(nframes):
    if every and n % every == every - 1:
        rt.press(key)
    rt.frame()
    if every and n % every == every - 1:
        rt.release()
    rt.fb.write_png(f"{out}/f{n:03d}.png")
    rt.write_svg(f"{out}/f{n:03d}.svg", scale=2)
    txt = " / ".join(t[3] for t in rt.text_layer[:2])
    print(f"  f{n:03d} px={rt.fb.nonblank():6d} {'[key]' if every and n % every == every-1 else '     '} {txt[:44]}")
rt.report_unimpl(10)
