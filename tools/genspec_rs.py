
"""tools/genspec_rs.py —— 把 emu/vmspec.py 转成 rust/emucore/src/vmspec.rs

**为什么从 vmspec.py 转，而不是直接读固件**

    genspec.py 要 assets/firmware 里那份 197MB 的 axf，那是私有资产，
    公开仓库和 CI 都拿不到。而 vmspec.py 本身是入库的生成物——
    以它为单一真源，两边就不可能漂移。改固件规格时的顺序是：
    先跑 genspec.py，再跑这个。
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import emu.vmspec as V

OUT = os.path.join(HERE, "rust/emucore/src/vmspec.rs")

def rs_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def main():
    tags = sorted(V.MGR)
    idx = {t: i for i, t in enumerate(tags)}
    out = []
    out.append("//! 自动生成 —— 请勿手改。")
    out.append("//! 来源: emu/vmspec.py（它自己来自固件 8533n_7835.axf 的 DWARF）。")
    out.append("//! 生成命令: python3 tools/genspec_rs.py")
    out.append("")
    out.append("/// manager 结构体里的一格：偏移、方法名、签名。")
    out.append("pub struct Field {")
    out.append("    pub off: u32,")
    out.append("    pub name: &'static str,")
    out.append("    pub sig: &'static str,")
    out.append("}")
    out.append("")
    out.append("/// 一张 manager 表：类型名、字节大小、字段表（按偏移升序）。")
    out.append("pub struct Mgr {")
    out.append("    pub tag: &'static str,")
    out.append("    pub size: u32,")
    out.append("    pub fields: &'static [Field],")
    out.append("}")
    out.append("")
    out.append("/// VmManager 里的取值器：sys 表偏移 -> (取值器名, manager 类型名)。")
    out.append("pub static SYS: &[(u32, &str, Option<&str>)] = &[")
    for off in sorted(V.SYS):
        g, tag = V.SYS[off]
        t = f"Some({rs_str(tag)})" if tag else "None"
        out.append(f"    ({off:#06x}, {rs_str(g)}, {t}),")
    out.append("];")
    out.append("")
    for t in tags:
        fields = V.MGR[t]
        out.append(f"static F_{idx[t]}: &[Field] = &[")
        for off in sorted(fields):
            nm, sig = fields[off]
            out.append(
                f"    Field {{ off: {off:#06x}, name: {rs_str(nm)}, sig: {rs_str(sig)} }},")
        out.append("];")
    out.append("")
    out.append("pub static MGR: &[Mgr] = &[")
    for t in tags:
        out.append(
            f"    Mgr {{ tag: {rs_str(t)}, size: {V.SIZE.get(t, 0)}, fields: F_{idx[t]} }},")
    out.append("];")
    out.append("")
    out.append("/// 按类型名找 manager 表。表只有二十来张，线性扫足够——")
    out.append("/// 这个查找只在建表时走一次，不在热路径上。")
    out.append("pub fn mgr(tag: &str) -> Option<&'static Mgr> {")
    out.append("    MGR.iter().find(|m| m.tag == tag)")
    out.append("}")
    out.append("")
    out.append("/// 某张表在某个偏移上的字段。字段表按偏移升序，二分。")
    out.append("pub fn field(tag: &str, off: u32) -> Option<&'static Field> {")
    out.append("    let m = mgr(tag)?;")
    out.append("    m.fields")
    out.append("        .binary_search_by_key(&off, |f| f.off)")
    out.append("        .ok()")
    out.append("        .map(|i| &m.fields[i])")
    out.append("}")
    out.append("")
    with open(OUT, "w") as f:
        f.write("\n".join(out))
    nf = sum(len(v) for v in V.MGR.values())
    print(f"   写出 {OUT}")
    print(f"   SYS {len(V.SYS)} 项   MGR {len(tags)} 张表   字段 {nf} 个")
    return 0

if __name__ == "__main__":
    sys.exit(main())
