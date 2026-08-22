
"""
tools/genspec.py — 把固件 DWARF 里的 manager 结构体转成模拟器可直接消费的规格

输出 emu/vmspec.py：
    SYS  = {sys表偏移: (getter名, manager结构体名)}
    MGR  = {manager结构体名: {方法偏移: (方法名, 签名)}}
    SIZE = {manager结构体名: 字节大小}
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "spec/vm_managers.json")
OUT = os.path.join(HERE, "emu/vmspec.py")

structs = {s["name"]: s for s in json.load(open(SRC))}
vmmgr = structs["VmManagerTag"]

ret_re = re.compile(r'^([A-Za-z_]\w*)\s*\*\(\*\)\(')
sys_map = {}
for m in vmmgr["members"]:
    t = m["type"] or ""
    mm = ret_re.match(t)
    if not mm:
        continue
    ret = mm.group(1)
    tag = ret + "Tag" if ret + "Tag" in structs else (ret if ret in structs else None)
    sys_map[m["off"]] = (m["name"], tag)

sys.path.insert(0, os.path.join(HERE, "tools"))
import io, contextlib, bisect
import vtinit
from axf import Elf, AXF
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    slots = vtinit.main("vMInitGameManagerOldIn")
_elf = Elf(AXF)
_tbl = sorted({(v & ~1, nm) for nm, v, sz, t in _elf.symbols() if t in (1, 2) and v})
_keys = [a for a, _ in _tbl]
def _resolve(a):
    i = bisect.bisect_right(_keys, a & ~1) - 1
    if i < 0: return f"sub_{a:x}"
    b, nm = _tbl[i]
    return nm if b == (a & ~1) else f"{nm}+{(a & ~1) - b:#x}"
structs["GameManagerOldTag"] = {
    "name": "GameManagerOldTag", "size": 636,
    "members": [{"off": o, "name": _resolve(slots[o]), "type": ""} for o in sorted(slots)],
}
sys_map[0x84] = ("VMGetGameManagerOld", "GameManagerOldTag")

with open(OUT, "w") as f:
    f.write('"""自动生成 —— 请勿手改。来源: 固件 8533n_7835.axf 的 DWARF 调试信息。\n'
            '生成命令: python3 tools/genspec.py\n"""\n\n')
    f.write("SYS = {\n")
    for off in sorted(sys_map):
        g, tag = sys_map[off]
        f.write(f"    {off:#05x}: ({g!r}, {tag!r}),\n")
    f.write("}\n\nSIZE = {\n")
    for n, s in sorted(structs.items()):
        f.write(f"    {n!r}: {s['size']},\n")
    f.write("}\n\nMGR = {\n")
    for n, s in sorted(structs.items()):
        f.write(f"    {n!r}: {{\n")
        for m in s["members"]:
            sig = (m["type"] or "").replace("(*)", "", 1)
            f.write(f"        {m['off']:#05x}: ({m['name']!r}, {sig!r}),\n")
        f.write("    },\n")
    f.write("}\n")
print(f"wrote {OUT}: {len(sys_map)} sys 槽位, {len(structs)} 个 manager")
