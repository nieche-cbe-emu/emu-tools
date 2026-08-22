
"""
tools/fontfind.py <文件> [stride...]

找定长点阵字库，两级：
  1) 64KB 窗口位密度粗筛。点阵字库 12%~42%，压缩/随机数据稳定在 50% 附近。
  2) 残差投票定对齐：真字库里"字形首行为空"的比例极高，且只在正确的
     base mod stride 上成立。对每个残差统计一次即可，O(n)。
"""
import sys

POP = bytes(bin(i).count("1") for i in range(256))
WIN = 1 << 16

def regions(buf, lo=0.12, hi=0.42, minlen=WIN):
    out = []
    for i in range(0, len(buf) - WIN, WIN):
        d = sum(buf[i:i + WIN].translate(POP)) / (WIN * 8)
        if lo <= d <= hi:
            if out and i == out[-1][1] + WIN:
                out[-1][1] = i
            else:
                out.append([i, i])
    return [(a, b + WIN) for a, b in out if b - a >= minlen]

def best_align(buf, a, b, stride, bpr):

    best = (None, 0, 0)
    for r in range(stride):
        blank = total = 0
        for p in range(a + r, b - stride, stride):
            gl = buf[p:p + bpr]
            tail = buf[p + stride - bpr:p + stride]
            if any(buf[p:p + stride]):
                total += 1
                if not any(gl) and not any(tail):
                    blank += 1
        if total > 500 and blank / total > best[1]:
            best = (r, blank / total, total)
    return best

def render(buf, off, w, rows_n):
    bpr = (w + 7) // 8
    return ["".join("█" if int.from_bytes(buf[off + r * bpr:off + (r + 1) * bpr], "big")
                    & (1 << (w - 1 - c)) else "·" for c in range(w))
            for r in range(rows_n)]

if __name__ == "__main__":
    buf = open(sys.argv[1], "rb").read()
    strides = [int(x) for x in sys.argv[2:]] or [32, 24]
    regs = regions(buf)
    print(f"候选区域 {len(regs)} 个: " + ", ".join(f"{a:#x}-{b:#x}" for a, b in regs[:8]))
    for stride in strides:
        w = 16 if stride == 32 else 12
        bpr = (w + 7) // 8
        rows_n = stride // bpr
        print(f"\n=== stride={stride} ({w}x{rows_n}) ===")
        for a, b in regs:
            r, frac, n = best_align(buf, a, b, stride, bpr)
            if r is None or frac < 0.6:
                print(f"  {a:#x}-{b:#x}: 最佳留白率仅 {frac:.0%}，不像字库")
                continue
            base = a + r
            print(f"  {a:#x}-{b:#x}: 残差 {r} 留白率 {frac:.0%}（{n} 个字形）→ base {base:#x}")
            for g0 in (0, 1000):
                lines = [render(buf, base + (g0 + k) * stride, w, rows_n) for k in range(4)]
                for row in zip(*lines):
                    print("      " + "  ".join(row))
                print()
