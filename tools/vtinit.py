
"""
tools/vtinit.py <init函数名>

反汇编固件里的 vMInitXxxManager 函数，还原它往结构体里填的函数指针表。
需要跟踪 `movs rX,r0` / `adds rX,#imm` 造出来的移动基址，
因为 RVCT 对大结构体会用 `base += 0xc0` 再 `str [base,#0x24]` 这种写法。
"""
import sys, os, struct, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from axf import Elf, AXF
from capstone import *
from capstone.arm import *

def load(elf):
    syms = elf.symbols()
    byname = {}
    for nm, val, size, typ in syms:
        if nm and nm not in byname:
            byname[nm] = (val, size, typ)
    tbl = sorted({(v & ~1, nm) for nm, v, s, t in syms if t in (1, 2) and v})
    return byname, tbl

def main(fname, base_reg_is_r0=True):
    elf = Elf(AXF)
    byname, tbl = load(elf)
    keys = [a for a, _ in tbl]

    def resolve(a):
        i = bisect.bisect_right(keys, a & ~1) - 1
        if i < 0:
            return f"{a:#x}"
        b, nm = tbl[i]
        return nm if b == (a & ~1) else f"{nm}+{(a & ~1) - b:#x}"

    va, size, _ = byname[fname]
    code = elf.read_va(va & ~1, size)
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    md.detail = True; md.skipdata = True

    lit = {}
    base = {ARM_REG_R0: 0}
    slots = {}
    for i in md.disasm(code, va & ~1):
        if i.id == 0:
            continue
        ops = i.operands
        if i.id == ARM_INS_LDR and len(ops) == 2 and ops[1].type == ARM_OP_MEM           and ops[1].mem.base == ARM_REG_PC:
            p = ((i.address + 4) & ~3) + ops[1].mem.disp
            b = elf.read_va(p, 4)
            d = ops[0].reg
            lit[d] = struct.unpack("<I", b)[0] if b else 0
            base.pop(d, None)
            continue
        if i.id == ARM_INS_STR and len(ops) == 2 and ops[1].type == ARM_OP_MEM           and ops[1].mem.base in base and ops[0].reg in lit:
            slots[base[ops[1].mem.base] + ops[1].mem.disp] = lit[ops[0].reg]
            continue
        if i.mnemonic.startswith('mov') and len(ops) == 2           and ops[1].type == ARM_OP_REG:
            d, s = ops[0].reg, ops[1].reg
            lit.pop(d, None); base.pop(d, None)
            if s in base:
                base[d] = base[s]
            elif s in lit:
                lit[d] = lit[s]
            continue
        if i.mnemonic.startswith('add') and ops and ops[0].type == ARM_OP_REG:
            d = ops[0].reg
            if len(ops) == 2 and ops[1].type == ARM_OP_IMM and d in base:
                base[d] += ops[1].imm
                lit.pop(d, None)
                continue
            if len(ops) == 3 and ops[1].type == ARM_OP_REG and ops[2].type == ARM_OP_IMM               and ops[1].reg in base:
                base[d] = base[ops[1].reg] + ops[2].imm
                lit.pop(d, None)
                continue
            lit.pop(d, None); base.pop(d, None)
            continue
        for op in ops:
            if op.type == ARM_OP_REG and op.access & CS_AC_WRITE:
                lit.pop(op.reg, None)
                if op.reg != ARM_REG_R0:
                    base.pop(op.reg, None)

    print(f"/* {fname} @ {va:#x}  —  {len(slots)} 个槽位, 表长 >= {max(slots) + 4:#x} */")
    for off in sorted(slots):
        print(f"    /* +{off:#05x} */  {resolve(slots[off])}")
    return slots

if __name__ == "__main__":
    main(sys.argv[1])
