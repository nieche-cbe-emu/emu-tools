
"""tools/stability.py [帧数] —— 核心固化验收

回归脚本回答"跑不跑得起来"，体检脚本回答"离通用还差多少"，
这个回答的是**"能不能定下来"**：

    长跑        全语料连续跑，看有没有异常、宿主报错、内存是否稳住
    确定性      同一模块跑两遍，逐检查点比对帧缓冲哈希——不一致就不能冻结
    反复启停    boot/stop 循环，看句柄和内存有没有攒
    脏输入      截断/损坏的文件必须干净报错，不能把进程带走
    契约        Session 的对外方法集必须和冻结清单一致

任何一项不过，核心就不算固化。
"""
import gc
import glob
import hashlib
import io
import contextlib
import os
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.host import Session
from emu.runtime import Runtime

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 600

CONTRACT = {
    "boot", "stop", "step", "set_keys", "set_touch", "soft_key",
    "take_events", "take_events_json", "name", "screens", "nonblank", "size",
}

def paths():
    return sorted(glob.glob("assets/cbe/*.CBE") + glob.glob("assets/cbe/*.cbe"))

def _run(path, frames, seed_input=False):

    marks = []
    try:
        m = cbelib.load(path)
        rt = Runtime(m, trace=False, quiet_log=True, trace_fs=False, audio=False)
        with contextlib.redirect_stdout(io.StringIO()):
            rt.boot()
            rt.app_start()
            for i in range(frames):
                if seed_input and i % 37 == 0:
                    rt.press(1 << (i // 37 % 12))
                rt.frame()
                if i % max(1, frames // 8) == 0:
                    marks.append(hashlib.md5(rt.fb.raw565()).hexdigest()[:12])
        return marks, None, sum(rt.host_errors.values())
    except Exception as e:
        return marks, f"{type(e).__name__}: {e}", 0

def long_run():
    print(f"── 长跑：{len(paths())} 个模块 × {FRAMES} 帧")
    tracemalloc.start()
    base = tracemalloc.take_snapshot()
    bad, errs = [], 0
    t0 = time.time()
    for p in paths():
        _, exc, he = _run(p, FRAMES)
        errs += he
        if exc:
            bad.append((os.path.basename(p), exc))
        gc.collect()
    cur = tracemalloc.take_snapshot()
    grow = sum(s.size_diff for s in cur.compare_to(base, "filename")) / 1048576
    tracemalloc.stop()
    print(f"   用时 {time.time()-t0:.0f}s   异常 {len(bad)}   宿主报错 {errs}   "
          f"常驻增长 {grow:+.1f} MB")
    for n, e in bad:
        print(f"   ✗ {n}: {e}")
    return not bad and errs == 0

def determinism():
    print("── 确定性：同一模块跑两遍，逐检查点比对")
    bad = []
    for p in paths():
        a, e1, _ = _run(p, 200, seed_input=True)
        b, e2, _ = _run(p, 200, seed_input=True)
        if a != b or e1 != e2:
            bad.append(os.path.basename(p))
    print(f"   不一致 {len(bad)} 个" + (f": {bad}" if bad else ""))
    return not bad

def churn(rounds=40):
    print(f"── 反复启停：{rounds} 轮 boot/stop")
    tracemalloc.start()
    base = tracemalloc.take_snapshot()
    picks = paths()[:6]
    try:
        for i in range(rounds):
            p = picks[i % len(picks)]
            with contextlib.redirect_stdout(io.StringIO()):
                s = Session(p, audio=False).boot()
                for _ in range(12):
                    s.step()
                s.stop()
            del s
            gc.collect()
    except Exception as e:
        tracemalloc.stop()
        print(f"   ✗ 第 {i} 轮炸了: {type(e).__name__}: {e}")
        return False
    cur = tracemalloc.take_snapshot()
    grow = sum(s.size_diff for s in cur.compare_to(base, "filename")) / 1048576
    tracemalloc.stop()
    print(f"   完成，常驻增长 {grow:+.1f} MB")
    return grow < 60

def dirty():
    print("── 脏输入：截断/损坏的文件必须干净报错")
    src = open(paths()[0], "rb").read()
    cases = {
        "空文件": b"",
        "只有头": src[:64],
        "截一半": src[: len(src) // 2],
        "尾巴被砍": src[:-16],
        "头部乱码": b"\xff" * 256 + src[256:],
        "纯噪声": os.urandom(4096),
    }
    ok = True
    for name, blob in cases.items():
        f = "/tmp/_dirty.cbe"
        open(f, "wb").write(blob)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = cbelib.load(f)
                rt = Runtime(m, trace=False, quiet_log=True, audio=False)
                rt.boot(); rt.app_start()
                for _ in range(5):
                    rt.frame()
            print(f"   {name}: 居然跑起来了（可接受，只要不炸）")
        except Exception as e:
            kind = type(e).__name__
            if kind in ("RecursionError", "MemoryError", "SystemError"):
                print(f"   ✗ {name}: {kind} —— 这种不算干净报错")
                ok = False
            else:
                print(f"   {name}: {kind} ✓")
    os.path.exists("/tmp/_dirty.cbe") and os.remove("/tmp/_dirty.cbe")
    return ok

def contract():
    print("── 契约：Session 对外方法集")

    have = set()
    for n in dir(Session):
        if n.startswith("_"):
            continue
        a = getattr(Session, n, None)
        if callable(a) or isinstance(a, property):
            have.add(n)
    miss, extra = CONTRACT - have, have - CONTRACT
    if miss:
        print(f"   ✗ 少了: {sorted(miss)}")
    if extra:
        print(f"   ! 多出来: {sorted(extra)}（新增不算破坏，但要记进清单）")
    return not miss

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    checks = [("契约", contract), ("脏输入", dirty), ("反复启停", churn),
              ("确定性", determinism), ("长跑", long_run)]
    res = {}
    for name, fn in checks:
        res[name] = fn()
        print()
    print("═" * 46)
    for name, ok in res.items():
        print(f"   {name:8s} {'通过' if ok else '未通过'}")
    print("═" * 46)
    print("核心可以固化" if all(res.values()) else "还不能固化")
    return 0 if all(res.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
