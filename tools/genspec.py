
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

OLD_GAME_LIB = {
    0x004: "DrawImageWithClip", 0x008: "DrawImageClipAndAlpha", 0x00c: "DrawFullScreen",
    0x010: "DrawNumber", 0x014: "DrawUI", 0x018: "DrawUIFourXRepeat",
    0x01c: "DrawUISingleRepeat", 0x020: "DrawUIHorizontal", 0x024: "DrawString",
    0x038: "SetClip", 0x03c: "IMG_GetHeight", 0x040: "IMG_GetWidth", 0x044: "ToRGB",
    0x048: "DrawVLine", 0x04c: "DrawHLine", 0x050: "DrawLine", 0x054: "DrawRect",
    0x058: "FillRect", 0x060: "GetClip", 0x064: "OldLib_064", 0x068: "CheckClip",
    0x06c: "DrawLineEx", 0x070: "GetFontWidth", 0x074: "GetFontWidth_char",
    0x078: "GetFontHeight", 0x07c: "GetFontHeight_char", 0x080: "DrawImageWithClipEx",
    0x084: "DrawImageClipAndAlphaEx", 0x088: "DrawImageNumberEx", 0x08c: "OldLib_08c",
    0x090: "DrawStringEx", 0x0b8: "RefresScreen", 0x0bc: "NumToZhiFei", 0x0c0: "GetLCDBuffer",
    0x0c4: "CdRect", 0x0cc: "CdRect2", 0x0d0: "CdRectPoint2", 0x0d4: "Abs", 0x0d8: "Max",
    0x0dc: "Min", 0x0e0: "Random", 0x0ec: "InitSprite", 0x11c: "InitTextBox",
    0x120: "initDFMap", 0x124: "initDFMapRenderBuffer", 0x128: "initDFMapVScollBuffer",
    0x12c: "initDFPictureLibrary", 0x130: "initDFRecord", 0x134: "initDFScene",
    0x138: "initDFSpriteLibrary", 0x13c: "initDFWindows", 0x1b4: "initDFActor",
    0x1bc: "XS_Init", 0x1c0: "XS_ShutDown", 0x1c4: "XS_LoadScript", 0x1c8: "XS_RunScripts",
    0x1cc: "XS_ResetScript", 0x1d0: "XS_CallScriptFunc", 0x1d4: "XS_InvokeScriptFunc",
    0x1d8: "XS_RegisterHostAPIFunc", 0x1dc: "XS_StartScript", 0x1e0: "XS_StopScript",
    0x1e4: "XS_PauseScript", 0x1e8: "XS_UnpauseScript", 0x1ec: "XS_GetReturnValueAsInt",
    0x1f0: "XS_GetReturnValueAsFloat", 0x1f4: "XS_GetReturnValueAsString",
    0x1f8: "XS_ReturnFromHost", 0x1fc: "XS_ReturnIntFromHost", 0x200: "XS_ReturnFloatFromHost",
    0x204: "XS_ReturnStringFromHost", 0x208: "XS_GetParamAsInt", 0x20c: "XS_GetParamAsFloat",
    0x210: "XS_GetParamAsString",
}

for _o in (0x094, 0x098, 0x09c, 0x0a0, 0x0a4, 0x0a8, 0x0ac, 0x0b0, 0x0b4):
    OLD_GAME_LIB.setdefault(_o, f"OldLib_{_o:03x}")
for _o in OLD_GAME_LIB:
    assert _o not in slots, f"老游戏库槽位 {_o:#x} 与固件填表冲突"
structs["GameManagerOldTag"] = {
    "name": "GameManagerOldTag", "size": 636,
    "members": sorted([{"off": o, "name": _resolve(slots[o]), "type": ""} for o in slots]
                      + [{"off": o, "name": n, "type": ""} for o, n in OLD_GAME_LIB.items()],
                      key=lambda m: m["off"]),
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
