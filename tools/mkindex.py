
"""tools/mkindex.py [游戏目录] [-o index.json] [--base URL] —— 生成镜像源目录

app 里「镜像源」拉的就是这份 index.json。用法：把 .cbe 传到自己的
GitHub 仓库，在仓库根目录跑一次这个脚本，把 index.json 一起提交，
然后在 app 里填 `用户名/仓库` 就能看到列表。

    python3 tools/mkindex.py assets/cbe -o index.json

默认不写 base：app 会按 index.json 自身的位置解析相对路径，
所以 index.json 和游戏文件放同一层最省事。游戏在子目录时用
`--base https://raw.githubusercontent.com/用户名/仓库/main/games/`。

sha256 会一并写进去，app 下载后校验；不想校验就加 --no-hash。
"""
import argparse
import hashlib
import json
import os
import sys

def scan(d, want_hash=True):
    out = []
    for name in sorted(os.listdir(d)):
        if not name.lower().endswith(".cbe"):
            continue
        p = os.path.join(d, name)
        if not os.path.isfile(p):
            continue
        e = {
            "title": os.path.splitext(name)[0],
            "file": name,
            "size": os.path.getsize(p),
        }
        if want_hash:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            e["sha256"] = h.hexdigest()
        out.append(e)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default="assets/cbe", help="放 .cbe 的目录")
    ap.add_argument("-o", "--out", default="index.json")
    ap.add_argument("--base", default=None, help="游戏文件的基地址；不给则按 index.json 位置解析")
    ap.add_argument("--name", default="尼彩 CBE 游戏镜像")
    ap.add_argument("--no-hash", action="store_true", help="不算 sha256（大目录会快很多）")
    a = ap.parse_args()

    if not os.path.isdir(a.dir):
        sys.exit(f"目录不存在：{a.dir}")
    games = scan(a.dir, want_hash=not a.no_hash)
    doc = {"name": a.name, "games": games}
    if a.base:
        doc["base"] = a.base if a.base.endswith("/") else a.base + "/"
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    total = sum(g["size"] for g in games)
    print(f"{a.out}：{len(games)} 个游戏，合计 {total/1048576:.1f} MB")
    if not a.base:
        print("（没写 base —— 把 index.json 和 .cbe 放同一层目录即可）")

if __name__ == "__main__":
    main()
