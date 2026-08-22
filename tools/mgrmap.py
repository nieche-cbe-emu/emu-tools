
"""
tools/mgrmap.py <module.cbe> [--global 0x35xx]

还原 CoolBar manager 接口: 扫描
    ldr rA,[pc,#k] ; add rA,sb ; ldr rB,[rA{,#0}] ; ... ; ldr rC,[rB,#off] ; blx rC
统计每个 sb 全局(manager 指针)上被调用的方法偏移, 并列出调用点附近引用到的字符串,
用于给方法命名。
"""
import sys, os, struct, collections, string
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from capstone import *
from capstone.arm import *

PRINT = set(bytes(string.printable[:-5], 'ascii'))

def cstr_at(ro, off, maxlen=72):
    if off < 0 or off >= len(ro):
        return None
    end = ro.find(b"\x00", off)
    if end < 0 or end - off < 3 or end - off > maxlen:
        return None
    s = ro[off:end]
    return s.decode('latin1') if all(c in PRINT for c in s) else None

def analyse(m):
    mode = CS_MODE_THUMB | (CS_MODE_BIG_ENDIAN if m.endian == 'BE' else CS_MODE_LITTLE_ENDIAN)
    md = Cs(CS_ARCH_ARM, mode); md.detail = True; md.skipdata = True
    ro, base = m.ro, m.load_base
    rd = (lambda o: struct.unpack_from('>I' if m.endian == 'BE' else '<I', ro, o)[0])

    lit = {}
    sbg = {}
    mgr = {}
    meth = {}
    strs = collections.deque(maxlen=6)
    calls = collections.defaultdict(collections.Counter)
    sites = collections.defaultdict(list)

    def kill(r):
        for d in (lit, sbg, mgr, meth):
            d.pop(r, None)

    for i in md.disasm(ro, base):
        if i.id == 0:
            lit.clear(); sbg.clear(); mgr.clear(); meth.clear(); continue
        ops = i.operands
        if i.id in (ARM_INS_LDR, ARM_INS_ADR) and ops and ops[0].type == ARM_OP_REG:
            dst = ops[0].reg
            if i.id == ARM_INS_ADR:
                tgt = ops[1].imm - base
                s = cstr_at(ro, tgt)
                if s: strs.append((i.address, s))
                kill(dst); continue
            mem = ops[1].mem if ops[1].type == ARM_OP_MEM else None
            if mem and mem.base == ARM_REG_PC:
                off = ((i.address + 4) & ~3) + mem.disp - base
                v = rd(off) if 0 <= off + 4 <= len(ro) else 0
                kill(dst); lit[dst] = v
                s = cstr_at(ro, (off + 4 + v) if v < 0x80000000 else 0)
                continue
            if mem and mem.base in sbg and mem.disp == 0:
                g = sbg[mem.base]; kill(dst); mgr[dst] = g; continue
            if mem and mem.base in mgr:
                g = mgr[mem.base]; kill(dst); meth[dst] = (g, mem.disp); continue
            kill(dst); continue
        if i.id == ARM_INS_ADD and len(ops) == 2 and ops[1].type == ARM_OP_REG:
            dst = ops[0].reg
            if ops[1].reg == ARM_REG_SB and dst in lit:
                v = lit[dst]; kill(dst); sbg[dst] = v; continue
            if ops[1].reg == ARM_REG_PC and dst in lit:
                tgt = i.address + 4 + lit[dst] - base
                s = cstr_at(ro, tgt)
                if s: strs.append((i.address, s))
            kill(dst); continue
        if i.id in (ARM_INS_BLX, ARM_INS_BX) and ops and ops[0].type == ARM_OP_REG:
            r = ops[0].reg
            if r in meth:
                g, off = meth[r]
                calls[g][off] += 1
                near = [s for a, s in strs if i.address - a < 0x60]
                sites[(g, off)].append((i.address, near[-1] if near else None))
            continue
        for op in ops:
            if op.type == ARM_OP_REG and op.access & CS_AC_WRITE:
                kill(op.reg)
    return calls, sites

if __name__ == '__main__':
    m = cbelib.load(sys.argv[1])
    only = int(sys.argv[sys.argv.index('--global') + 1], 0) if '--global' in sys.argv else None
    calls, sites = analyse(m)
    tot = {g: sum(c.values()) for g, c in calls.items()}
    for g in sorted(tot, key=lambda x: -tot[x]):
        if only is not None and g != only:
            continue
        zone = '.data' if g < len(m.rw) else '.bss'
        print(f"\n=== manager @ sb+{g:#07x} ({zone})   共 {tot[g]} 次调用, "
              f"{len(calls[g])} 个方法, vtable >= {max(calls[g]) + 4:#x} 字节")
        for off in sorted(calls[g]):
            hints = [s for _, s in sites[(g, off)] if s]
            h = ('  // ' + ' | '.join(dict.fromkeys(hints))[:110]) if hints else ''
            print(f"   +{off:#05x}  x{calls[g][off]:<4d}{h}")
