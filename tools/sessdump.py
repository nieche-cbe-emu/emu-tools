
"""tools/sessdump.py <module.cbe> [帧数] [--native] —— 逐帧指纹。

默认走 `emu.host.Session`（Python 参照实现）；给 `--native` 就改走
`nieche.NiecheSession`（ctypes 接 Rust 核心）。同一段驱动代码开两边，
所以两次输出该逐字节相同——差一点就是 ctypes 那层绑错了。

**这是 Session 这一层的参照实现。** spec/baseline 是直驱 Runtime 生成的，
不含 Session 的输入整形（锁存、触摸排队、按键事件、长按连发），
所以走 Session 的一侧不能拿它当基准——那是两回事。

输入脚本 sess-v1，两侧必须逐条一致，见 tools/ffidiff.sh。
时钟喂虚拟值（每帧 40ms），否则长按连发按真实时钟算，跑两次结果都不一样。
"""
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emu.host import Session

FPS_DT = 0.04

def script(sess, i, w, h):

    if i % 37 == 0:
        sess.set_keys(1 << ((i // 37) % 12))
    elif i % 37 == 4:
        sess.set_keys(0)
    if i % 53 == 7:
        sess.set_touch(w // 2, h // 2, "down")
    elif i % 53 == 9:
        sess.set_touch(w // 2, h // 2, "up")

def main():
    if len(sys.argv) < 2:
        print("用法: sessdump.py <module.cbe> [帧数] [--native]", file=sys.stderr)
        return 2
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[1]) if len(args) > 1 else 60
    native = "--native" in sys.argv
    if native:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rust", "python"))
        from nieche import NiecheSession
        s = NiecheSession(args[0], audio=False)
    else:
        s = Session(args[0], audio=False)
    s.boot()
    rows = []
    for i in range(n):
        w, h = s.size
        script(s, i, w, h)

        px = s.step() if native else s.step(now=i * FPS_DT)
        rows.append(f"{i} {zlib.crc32(px) & 0xFFFFFFFF:08x}")

    w, h = s.size
    print(f"screen {w} {h}")
    print(f"screens {s.screens}")
    print(f"nonblank {s.nonblank}")
    for r in rows:
        print(r)
    s.stop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
