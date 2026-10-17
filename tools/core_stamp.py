
"""tools/core_stamp.py [--hash] —— 模拟核心源码的指纹

安卓的 libnieche.so 不进 git，要靠 tools/build-android.sh 现编。
v0.3.8 就是忘了重编：打包进去的还是 09-15 的旧核心，10-01 以后核心侧的
修复一个都没带上，安卓上一点声音都没有。

所以编 .so 时把源码指纹写进 app 的 assets/core.stamp，Gradle 每次构建前
（app/build.gradle 的 checkCoreFresh）再算一遍，对不上就不让构建。

    指纹 = rust/ 下三个 crate 的 .rs 与各级 Cargo.toml、Cargo.lock 的内容哈希。
    **按内容算，不按修改时间**：git checkout / 拷贝都会改 mtime，按时间比会误报。

输出：
    默认      "<指纹12位> <git 短哈希>[+]"，+ 表示 rust/ 有未提交的改动
    --hash    只输出指纹
"""
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUST = os.path.join(ROOT, "rust")
CRATES = ("cbelib", "emucore", "emuffi")

def files():
    out = [os.path.join(RUST, f) for f in ("Cargo.toml", "Cargo.lock")]
    for c in CRATES:
        base = os.path.join(RUST, c)
        out.append(os.path.join(base, "Cargo.toml"))
        for d, _, fs in os.walk(os.path.join(base, "src")):
            out += [os.path.join(d, f) for f in fs if f.endswith(".rs")]
    return sorted(p for p in out if os.path.isfile(p))

def digest():
    h = hashlib.sha256()
    for p in files():

        h.update(os.path.relpath(p, RUST).replace(os.sep, "/").encode())
        h.update(b"\0")
        with open(p, "rb") as f:
            h.update(f.read())
        h.update(b"\0")
    return h.hexdigest()[:12]

def git_short():
    try:
        rev = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "rust"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return rev + ("+" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"

if __name__ == "__main__":
    if "--hash" in sys.argv:
        print(digest())
    else:
        print(f"{digest()} {git_short()}")
