
"""tools/fwtriage.py <刷机包目录 | .axf 路径> —— 一份固件能不能解老 SDK

现在卡住的是**老 SDK 那一代的 manager 布局**：
    模块从 SYS+0x090 取 GameManagerOld，而手上这份 I9 固件那里是 GSensor；
    GameManagerOldTag 的 0x0 / 0x3c / 0x40 / 0x12c 四格对不上或压根没有名字。

所以一份候选固件有没有价值，只看三件事，不用猜机型：

    1. 包里有没有**带符号表的 ELF**（.axf）。绝大多数刷机包只有烧录镜像，
       没有调试信息，那就直接没用——I9 这份能用纯属它带了「调试信息」文件夹。
    2. 它有没有 vMGetGSensorManager 这类**晚期特性**的符号。
       有 = 和 I9 同代，白搭；没有 = 更早的一代，正是要找的。
    3. 它的 vMInitGameManagerOldIn 第 0 格填的是不是别的函数。
       手上这份填的是 IMG_CreateImageFormRes，而老 SDK 的模块往那一格
       传的是 GB2312 字符串——两者必然不同。

三条都对，老 SDK 就能收工。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

LATE = [
    "vMGetGSensorManager", "VmGetDlWPayManager", "VmGetVideoManager",
    "vMGetDlLoadManager", "vMGetDlRsManager", "vMGetDlImageManager",
    "vMGetVmImManager",
]

WANT = [0x0, 0x3c, 0x40, 0x12c]

def find_elfs(root):
    if os.path.isfile(root):
        return [root]
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            try:
                with open(p, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        out.append(p)
            except OSError:
                pass
    return out

def triage(path):
    os.environ["AXF"] = path
    for m in ("axf", "vtinit"):
        sys.modules.pop(m, None)
    sys.path.insert(0, HERE)
    import axf as A
    elf = A.Elf(path)
    try:
        syms = elf.symbols()
    except Exception as e:
        print(f"   读符号表失败：{type(e).__name__}: {e}")
        return False
    names = {n for n, *_ in syms if n}
    print(f"   符号 {len(names)} 个")
    if len(names) < 100:
        print("   ✗ 没有像样的符号表 —— 这份用不了")
        return False

    late = [n for n in LATE if n in names]
    print(f"   晚期特性符号：{len(late)}/{len(LATE)}" + (f"  {late[:4]}" if late else "  （一个都没有）"))

    init = "vMInitGameManagerOldIn"
    if init not in names:
        alt = sorted(n for n in names if "GameManagerOld" in n)
        print(f"   ✗ 找不到 {init}" + (f"，相近的有 {alt[:3]}" if alt else ""))
        return False

    import vtinit
    import bisect
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        slots = vtinit.main(init)
    tbl = dict(slots) if not isinstance(slots, dict) else slots

    pairs = sorted({(v & ~1, n) for n, v, sz, t in syms if t in (1, 2) and v})
    keys = [a for a, _ in pairs]

    def resolve(a):
        i = bisect.bisect_right(keys, a & ~1) - 1
        if i < 0:
            return f"sub_{a:x}"
        b, nm = pairs[i]
        return nm if b == (a & ~1) else f"{nm}+{(a & ~1) - b:#x}"

    named = {o: resolve(v) for o, v in tbl.items()}
    print(f"   GameManagerOld 还原出 {len(named)} 格：")
    for o in WANT:
        print(f"      +{o:#05x}  {named.get(o, '（空）')}")
    tbl = named

    old_gen = not late
    differs = tbl.get(0x0) not in (None, "IMG_CreateImageFormRes")
    if old_gen and differs:
        print("   ★ 就是这一代 —— 能解老 SDK")
    elif old_gen:
        print("   ~ 像更早的一代，但第 0 格没变，价值存疑")
    else:
        print("   ✗ 和 I9 同代，解不了老 SDK")
    return old_gen and differs

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = sys.argv[1]
    elfs = find_elfs(root)
    if not elfs:
        print(f"{root}：没找到 ELF —— 刷机包里没有调试信息，用不了")
        return 1
    hit = False
    for p in elfs:
        print(f"\n{p}  ({os.path.getsize(p) / 1048576:.0f} MB)")
        try:
            hit |= bool(triage(p))
        except Exception as e:
            print(f"   分析出错：{type(e).__name__}: {e}")
    return 0 if hit else 1

if __name__ == "__main__":
    sys.exit(main())
