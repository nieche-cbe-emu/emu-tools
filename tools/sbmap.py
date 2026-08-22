
"""扫描 Thumb 代码里的 `ldr rX,[pc,#k]; add rX,sb` 组合，统计 r9(sb) 相对全局变量的使用情况，
并进一步解析紧随其后的 `ldr rY,[rX,#imm]` 链，用于还原宿主 API 表结构。"""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from capstone import *
from capstone.arm import *

def scan(m):
    mode = CS_MODE_THUMB | (CS_MODE_BIG_ENDIAN if m.endian == 'BE' else CS_MODE_LITTLE_ENDIAN)
    md = Cs(CS_ARCH_ARM, mode); md.detail = True; md.skipdata = True
    ro = m.ro; base = m.load_base
    rd = (lambda o: struct.unpack_from('>I', ro, o)[0]) if m.endian == 'BE' else         (lambda o: struct.unpack_from('<I', ro, o)[0])

    lit = {}
    sb_uses = collections.Counter()
    chains = collections.Counter()
    cur = {}
    for i in md.disasm(ro, base):
        if i.id == 0:
            lit.clear(); cur.clear(); continue
        if i.id == ARM_INS_LDR and len(i.operands) == 2 and           i.operands[1].type == ARM_OP_MEM and i.operands[1].mem.base == ARM_REG_PC:
            pcv = (i.address + 4) & ~3
            off = pcv + i.operands[1].mem.disp - base
            if 0 <= off + 4 <= len(ro):
                lit[i.operands[0].reg] = rd(off)
            cur.pop(i.operands[0].reg, None)
        elif i.id == ARM_INS_ADD and len(i.operands) == 2 and             i.operands[1].type == ARM_OP_REG and i.operands[1].reg == ARM_REG_SB:
            r = i.operands[0].reg
            if r in lit:
                sb_uses[lit[r]] += 1
                cur[r] = lit[r]
            lit.pop(r, None)
        elif i.id == ARM_INS_LDR and len(i.operands) == 2 and             i.operands[1].type == ARM_OP_MEM and i.operands[1].mem.base in cur:
            sbo = cur[i.operands[1].mem.base]
            chains[(sbo, i.operands[1].mem.disp)] += 1
            cur.pop(i.operands[0].reg, None)
            cur.pop(i.operands[1].mem.base, None)
        else:
            for op in i.operands:
                if op.type == ARM_OP_REG and op.access & CS_AC_WRITE:
                    cur.pop(op.reg, None); lit.pop(op.reg, None)
    return sb_uses, chains

if __name__ == '__main__':
    m = cbelib.load(sys.argv[1])
    sb, ch = scan(m)
    print(f"# {m.name}  rw(.data)={len(m.rw):#x}  rw_total={m.rw_size:#x}")
    print(f"# 共 {len(sb)} 个不同的 sb 偏移, 总引用 {sum(sb.values())} 次")
    print("\n## 最常引用的 sb 全局 (offset, 引用次数, 区域)")
    for off, cnt in sb.most_common(25):
        zone = '.data' if off < len(m.rw) else '.bss '
        print(f"  sb+{off:#07x}  x{cnt:<5d} {zone}")
    print("\n## sb 全局 + 字段偏移 组合 (top 30)")
    for (sbo, disp), cnt in ch.most_common(30):
        print(f"  [sb+{sbo:#07x}] + {disp:#05x}   x{cnt}")
