
"""tools/cheattest.py <module.cbe> [--native] —— 修改器对拍

默认走 `emu.host.Session`（Python 参照实现）；给 `--native` 就改走
`nieche.NiecheSession`（ctypes 接 Rust 核心）。两边跑同一段脚本：

    40 帧 → 搜 4 字节的 1 → 20 帧 → 再搜 1（筛） → 改写第一个候选、锁定第二个
    → 20 帧（逐帧指纹） → 列候选

全程不给输入（没有按键就没有长按连发，原生一侧没有时钟注入口也照样可比）。
两次输出该逐字节相同。
"""
import os
import sys
import zlib

if not os.environ.get("NIECHE_HOME"):
    import tempfile
    os.environ["NIECHE_HOME"] = tempfile.mkdtemp(prefix="nieche-tool-")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

class PyAdapter:
    def __init__(self, path):
        from emu.host import Session
        self.s = Session(path, audio=False)

    def boot(self):
        self.s.boot()

    def step(self, i):
        return self.s.step(now=i * 0.04)

    def search(self, w, v):
        return self.s.cheat.search(w, v)

    def results(self):
        return self.s.cheat.results()

    def write(self, a, w, v):
        return self.s.cheat.write(a, w, v)

    def lock(self, a, w, v):
        self.s.cheat.lock(a, w, v)

class NativeAdapter:
    def __init__(self, path):
        sys.path.insert(0, os.path.join(ROOT, "rust", "python"))
        from nieche import NiecheSession
        self.s = NiecheSession(path, audio=False)

    def boot(self):
        self.s.boot()

    def step(self, i):
        return self.s.step()

    def search(self, w, v):
        return self.s.cheat_search(w, v)

    def results(self):
        return self.s.cheat_results()

    def write(self, a, w, v):
        return self.s.cheat_write(a, w, v)

    def lock(self, a, w, v):
        self.s.cheat_lock(a, w, v)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("用法: cheattest.py <module.cbe> [--native]", file=sys.stderr)
        return 2
    s = (NativeAdapter if "--native" in sys.argv else PyAdapter)(args[0])
    s.boot()
    out = []
    i = 0

    def run(n):
        nonlocal i
        for _ in range(n):
            px = s.step(i)
            out.append(f"frame {i} {zlib.crc32(px) & 0xFFFFFFFF:08x}")
            i += 1

    run(40)
    out.append(f"search1 {s.search(4, 1)}")
    run(20)
    out.append(f"search2 {s.search(4, 1)}")
    res = s.results()
    out.append("results " + " ".join(f"{a:08x}={v}" for a, v in res[:50]))
    if res:
        out.append(f"write {s.write(res[0][0], 4, 7)}")
    if len(res) > 1:
        s.lock(res[1][0], 4, 9)
    run(20)
    out.append("after " + " ".join(f"{a:08x}={v}" for a, v in s.results()[:50]))
    print("\n".join(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
