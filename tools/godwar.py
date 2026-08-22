
"""众神之战的导航脚手架：一路点进黑暗神殿地图，之后交给调用者操作。

菜单和软键**只吃触摸**，按键位一律无效；坐标是实测出来的，写死在这里。
"""
import io, os, sys, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

SKIP     = (220, 385)
ARROW_L  = (48, 338)
SELECT   = (120, 338)
CONFIRM  = (60, 271)

def make(path='assets/cbe/众神之战.CBE', **kw):
    m = cbelib.load(path)
    return Runtime(m, trace=False, quiet_log=True, trace_fs=False, **kw)

def touch(rt, x, y, hold=3, after=8):
    rt.pointer = (x, y)
    rt.touch_down = rt.touch_hold = 1
    rt.touch_up = 0
    for _ in range(hold):
        rt.frame()
    rt.touch_down = rt.touch_hold = 0
    rt.touch_up = 1
    for _ in range(2):
        rt.frame()
    rt.touch_up = 0
    for _ in range(after):
        rt.frame()

def to_map(rt, extra=240):

    with contextlib.redirect_stdout(io.StringIO()):
        rt.boot(); rt.app_start()
        for _ in range(20):
            rt.frame()
        touch(rt, *SKIP)
        for _ in range(2):
            touch(rt, *ARROW_L)
        touch(rt, *SELECT)
        touch(rt, *CONFIRM)
        for _ in range(extra):
            rt.frame()
    return rt

def shot(rt, name):
    os.makedirs("out/GodWar", exist_ok=True)
    p = f"out/GodWar/{name}.png"
    rt.fb.write_png(p)
    return p

def texts(rt, n=6):
    return list(dict.fromkeys(t for _, _, _, t, _ in rt.text_layer))[-n:]

if __name__ == "__main__":
    rt = to_map(make())
    print("像素:", rt.fb.nonblank(), "->", shot(rt, "arrived"))
    print("文字:", texts(rt))
