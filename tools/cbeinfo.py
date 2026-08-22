
"""tools/cbeinfo.py [files...] — 打印 CBE 模块结构信息（不带参数则扫描 CBE/ 目录）"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib

def show(p):
    m = cbelib.load(p)
    print(f"{os.path.basename(p)}")
    print(f"  模块名     : {m.name}")
    print(f"  架构       : ARMv5TE {m.endian} (Thumb 为主, 少量 ARM), RWPI/r9 静态基址")
    print(f"  加载基址   : {m.load_base:#010x} {'(位置无关)' if not m.load_base else '(固定)'}")
    print(f"  RO 段      : 文件 {m.ro_off:#08x}  大小 {len(m.ro):#08x}  校验 {m.ro_chk:#010x}")
    print(f"  RW 段      : 文件 {m.rw_off:#08x}  .data {len(m.rw):#07x}  .bss {m.bss_size:#07x}  (r9 区共 {m.rw_size:#x})")
    if m.icons:
        print(f"  内建资源包 : {m.icons.count} 项  {m.icons.names()[:4]}")
    if m.res:
        n = m.res
        print(f"  主资源包   : {n.count} 项  数据 {n.data_size:#x} 字节")
        print(f"               {n.names()[:6]} …")
    else:
        print("  主资源包   : (无 / 非标准容器)")

if __name__ == '__main__':
    args = sys.argv[1:] or sorted(glob.glob('CBE/*.CBE') + glob.glob('CBE/*.cbe'))
    for p in args:
        try:
            show(p); print()
        except Exception as e:
            print(f"{p}: {type(e).__name__}: {e}\n")
