
"""
tools/run_web.py <module.cbe> [--port 8777] [--fps 20] [--rotate 270] [--scale 2]

把模拟器跑起来并开一个本地 Web 前端（默认 http://127.0.0.1:8777）。
浏览器负责显示和输入：方向键 / Z / X / 回车 / 退格，以及画面上的触摸。
按键是位掩码，键位由模块自己定义——页面上有 bit0-15 的按钮可以逐位试。
"""
import sys, os, webbrowser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime
from emu.web import serve

def opt(name, default, cast=int):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

path = sys.argv[1]
m = cbelib.load(path)
rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False,
             audio="--no-audio" not in sys.argv)
rt.mach.BUDGET = 40_000_000
print(f"引导 {m.name} …")
rt.boot()
rt.app_start()
print(f"  app_start 完成，screens={len(rt.screens)}  exit={rt.mach.exit_reason}")

port = opt("--port", 8777)
sess, srv = serve(rt, port=port, fps=opt("--fps", 20),
                  rotate=opt("--rotate", 0), scale=opt("--scale", 2))
url = f"http://127.0.0.1:{port}/"
print(f"打开 {url}  （Ctrl-C 退出）")
if "--no-open" not in sys.argv:
    try:
        webbrowser.open(url)
    except Exception:
        pass
try:
    srv.serve_forever()
except KeyboardInterrupt:
    sess.running = False
    print("\n已停止")
