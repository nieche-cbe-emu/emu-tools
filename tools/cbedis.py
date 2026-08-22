
"""tools/dis.py <module.cbe> <vaddr|0xADDR> [count] — 按虚拟地址反汇编 RO 段"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from capstone import *

def make(m, thumb=True):
    mode = (CS_MODE_THUMB if thumb else CS_MODE_ARM)
    mode |= CS_MODE_BIG_ENDIAN if m.endian == 'BE' else CS_MODE_LITTLE_ENDIAN
    md = Cs(CS_ARCH_ARM, mode); md.detail = True; md.skipdata = True
    return md

def dis(m, va, n=40, thumb=True):
    md = make(m, thumb)
    off = va - m.load_base
    out = []
    for i in md.disasm(m.ro[off:off + n * 4 + 16], va):
        out.append(i)
        if len(out) >= n: break
    return out

if __name__ == '__main__':
    m = cbelib.load(sys.argv[1])
    va = int(sys.argv[2], 0)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    thumb = (len(sys.argv) <= 4) or sys.argv[4] != 'arm'
    for i in dis(m, va, n, thumb):
        print(f"{i.address:08x}: {i.bytes.hex():<9s} {i.mnemonic:<8s} {i.op_str}")
