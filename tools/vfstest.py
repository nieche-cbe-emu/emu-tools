
"""tools/vfstest.py —— 虚拟文件系统的路径规范化自检

和 Rust 侧 `vfs.rs` 的 `norm_clamps_parent_dir` / `write_stays_inside_sandbox`
是同一组用例：两份实现必须逐条一致，差一条就是差分测试里的假一致。

重点是 `..` 不能把模块带出沙盒——镜像源可以下载任意 .cbe，
路径逃逸等于让陌生模块往用户主目录里写文件。
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emu.vfs import Vfs

CASES = [
    ("a/b.dat", "a/b.dat"),
    ("..\\..\\escape.txt", "escape.txt"),
    ("C:\\x\\y", "x/y"),
    ("/abs/p", "abs/p"),
    ("a/./b", "a/b"),
    ("a/../b", "b"),
    ("a/b/../../../../c", "c"),
    ("", ""),
    ("..", ""),
    (".system/MB_MSTAR_WQVGA\\AppStore.CBE", ".system/MB_MSTAR_WQVGA/AppStore.CBE"),
]

def main():
    bad = 0
    for raw, want in CASES:
        got = Vfs._norm(raw)
        if got != want:
            print(f"   ✗ _norm({raw!r}) = {got!r}，期望 {want!r}")
            bad += 1

    tmp = tempfile.mkdtemp(prefix="nieche-vfs-")
    try:
        root = os.path.join(tmp, "fs", "mod")
        v = Vfs(root)
        h = v.open(2, "..\\..\\escaped.txt", "w+")
        if h == Vfs.OPEN_FAIL:
            print("   ✗ 打开失败，测不到落点")
            bad += 1
        else:

            v.handles[h].write(b"x")
            v.close(h)
            if not os.path.exists(os.path.join(root, "escaped.txt")):
                print("   ✗ 没落在沙盒里")
                bad += 1
            if os.path.exists(os.path.join(tmp, "escaped.txt")):
                print("   ✗ 落到沙盒外面了")
                bad += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("ok" if bad == 0 else f"{bad} 条不符")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
