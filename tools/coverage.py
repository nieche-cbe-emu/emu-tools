
"""tools/coverage.py [帧数] —— 通用性体检

回归脚本 batch.py 回答的是"跑不跑得起来"，这个回答的是"离通用还差多少"：

    未实现的宿主 API   还有哪些接口是空的，被谁调、调多少次
    宿主实现内部报错   实现里抛了异常——参数解读多半不对
    空指针调用         模块调了一个没填的函数指针，通常是宿主漏给了什么
    非默认屏幕尺寸     哪些模块不是 240x400

判断标准不是"某个游戏能玩"，而是这四项在全语料上收敛。
"""
import collections
import contextlib
import glob
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.runtime import Runtime

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 60

def main():
    miss = collections.Counter()
    who = collections.defaultdict(set)
    errs = collections.Counter()
    nulls = collections.Counter()
    screens = {}
    broken = []
    paths = sorted(glob.glob("assets/cbe/*.CBE") + glob.glob("assets/cbe/*.cbe"))
    for p in paths:
        try:
            m = cbelib.load(p)
            rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False, audio=False)
            with contextlib.redirect_stdout(io.StringIO()):
                rt.boot()
                rt.app_start()
                for _ in range(FRAMES):
                    rt.frame()
        except Exception as e:
            broken.append((os.path.basename(p), f"{type(e).__name__}: {e}"))
            continue
        for (tag, off, nm), n in rt.unimpl.items():
            k = f"{tag}+{off:#05x} {nm}"
            miss[k] += n
            who[k].add(m.name)
        for k, n in rt.host_errors.items():
            errs[f"{k[0]} / {k[1]}"] += n
        for lr, n in getattr(rt.mach, "null_calls", {}).items():
            nulls[(m.name, rt.mach.where(lr))] += n
        if (rt.screen_w, rt.screen_h) != (240, 400):
            screens[m.name] = (rt.screen_w, rt.screen_h)

    print(f"语料 {len(paths)} 个模块，每个跑 {FRAMES} 帧\n")
    print(f"未实现的宿主 API：{len(miss)} 个，合计 {sum(miss.values())} 次调用")
    for k, n in miss.most_common(20):
        print(f"   {k:46s} x{n:<6d} {sorted(who[k])[:3]}")
    print(f"\n宿主实现内部报错：{sum(errs.values())} 次")
    for k, n in errs.most_common(10):
        print(f"   {k:46s} x{n}")
    print(f"\n空指针调用：{sum(nulls.values())} 次")
    for (mod, site), n in nulls.most_common(10):
        print(f"   {mod:14s} {site:30s} x{n}")
    print(f"\n非 240x400 的模块：{screens or '无'}")
    if broken:
        print(f"\n引导就失败的：")
        for name, e in broken:
            print(f"   {name}: {e}")

if __name__ == "__main__":
    main()
