
"""
tools/dwarfstruct.py <cu_die_offset> [结构体名正则]

用 llvm-dwarfdump 展开固件 AXF 里某个 CU，把其中的 DW_TAG_structure_type
还原成带字段偏移的 C 声明。这是把宿主 manager 接口搬进模拟器的桥梁。
"""
import sys, os, re, subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AXF = os.environ.get("AXF") or os.path.join(
    HERE, "assets/firmware/I9/extracted/I9智能版V017版本0419",
    "SW_7835E_V017[PATCH3]_M10_NIECHE/调试信息/8533n_7835.axf")
DWARFDUMP = "/Library/Developer/CommandLineTools/usr/bin/llvm-dwarfdump"

TAG = re.compile(r'^0x([0-9a-f]+):(\s+)(DW_TAG_\w+|NULL)')
ATTR = re.compile(r'^\s+(DW_AT_\w+)\s+\((.*)\)\s*$')

def dump(cu_off):
    r = subprocess.run([DWARFDUMP, f"--debug-info=0x{cu_off:x}", "--show-children", AXF],
                       capture_output=True, text=True, errors="replace")
    return r.stdout.splitlines()

def parse(lines):

    out, cur, last_tag = [], None, None
    depth_of_struct = None
    for ln in lines:
        m = TAG.match(ln)
        if m:
            off, indent, tag = int(m.group(1), 16), len(m.group(2)), m.group(3)
            if tag == "DW_TAG_structure_type":
                cur = dict(name=None, size=0, members=[], indent=indent)
                out.append(cur); depth_of_struct = indent
            elif tag == "DW_TAG_member" and cur is not None:
                cur["members"].append(dict(name=None, type=None, off=None))
            elif tag == "NULL" and depth_of_struct is not None and indent <= depth_of_struct:
                cur = None; depth_of_struct = None
            last_tag = tag
            continue
        m = ATTR.match(ln)
        if not m or cur is None:
            continue
        k, v = m.group(1), m.group(2)
        if last_tag == "DW_TAG_structure_type":
            if k == "DW_AT_name":
                cur["name"] = v.strip('"')
            elif k == "DW_AT_byte_size":
                cur["size"] = int(v, 0)
        elif last_tag == "DW_TAG_member" and cur["members"]:
            mem = cur["members"][-1]
            if k == "DW_AT_name":
                mem["name"] = v.strip('"')
            elif k == "DW_AT_type":
                mm = re.search(r'"(.*)"', v)
                mem["type"] = mm.group(1) if mm else v
            elif k == "DW_AT_data_member_location":
                mm = re.search(r'0x([0-9a-f]+)', v)
                mem["off"] = int(mm.group(1), 16) if mm else 0
    return [s for s in out if s["name"] and s["members"]]

def emit(s):
    print(f"/* {s['name']}  ({s['size']} = {s['size']:#x} bytes) */")
    print(f"typedef struct {s['name']} {{")
    for m in s["members"]:
        t = m["type"] or "?"

        if "(*)" in t:
            decl = t.replace("(*)", f"(*{m['name']})", 1)
        elif t.endswith("*"):
            decl = f"{t}{m['name']}"
        else:
            decl = f"{t} {m['name']}"
        print(f"    /* +{m['off']:#05x} */  {decl};")
    print(f"}} {s['name']};\n")

def structs(cu_off):
    return parse(dump(cu_off))

if __name__ == "__main__":
    cu = int(sys.argv[1], 0)
    args = sys.argv[2:]
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    pat = re.compile(args[0]) if args else None
    got = [s for s in structs(cu) if pat is None or pat.search(s["name"])]
    if as_json:
        import json
        print(json.dumps(got, indent=1, ensure_ascii=False))
    else:
        for s in got:
            emit(s)
