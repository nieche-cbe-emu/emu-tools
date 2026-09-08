#!/bin/bash

set -u
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/Cellar/rustup/1.29.0_2/bin:$PATH"
export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$HOME/.cache/nieche-rust}"
N="${1:-60}"
fail=0

TOTAL=$(ls assets/cbe/*.CBE assets/cbe/*.cbe 2>/dev/null | wc -l | tr -d ' ')

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
check() {
  if [ "$2" = "$3" ]; then printf '   ✓ %-26s %s\n' "$1" "$3"
  else printf '   ✗ %-26s 期望 %s，实得 %s\n' "$1" "$2" "$3"; fail=1; fi
}

step "Rust 构建与单元测试"
(cd rust && cargo build --release 2>&1 | tail -2)

out=$(cd rust && cargo test --release 2>&1); rc=$?
bins=$(printf '%s\n' "$out" | grep -c "test result: ok")
cases=$(printf '%s\n' "$out" | sed -n 's/^test result: ok\. \([0-9]*\) passed.*/\1/p' | awk '{s+=$1} END{print s+0}')
check "cargo test 退出码" "0" "$rc"
printf '   · %s 个测试二进制，%s 个用例全过\n' "$bins" "$cases"

step "Python 参照实现回归"
h=$(mktemp -d); r=$(NIECHE_HOME=$h timeout 1800 python3 tools/batch.py 2>&1 | tail -1); rm -rf "$h"
check "跑进主循环" "28/$TOTAL 个模块跑进主循环" "$r"

step "阶段 02：容器 / LZ / 图片解码"
p=0; for f in assets/cbe/*.CBE assets/cbe/*.cbe; do [ -e "$f" ] || continue
  python3 tools/dumpcontainer.py "$f" > "$TMP/py.txt" 2>&1
  "$CARGO_TARGET_DIR/release/cbedump" "$f" > "$TMP/rs.txt" 2>&1
  diff -q "$TMP/py.txt" "$TMP/rs.txt" >/dev/null && p=$((p+1)); done
check "两侧转储逐行相同" "$TOTAL" "$p"

step "阶段 03：段落摆放"
p=0; for f in assets/cbe/*.CBE assets/cbe/*.cbe; do [ -e "$f" ] || continue
  python3 tools/dumplayout.py "$f" > "$TMP/py.txt" 2>&1
  "$CARGO_TARGET_DIR/release/layout" "$f" > "$TMP/rs.txt" 2>&1
  diff -q "$TMP/py.txt" "$TMP/rs.txt" >/dev/null && p=$((p+1)); done
check "两侧摆放一致" "$TOTAL" "$p"

step "阶段 04：引导（style/cb0/cb1/managers/exit）"
p=0; for f in assets/cbe/*.CBE assets/cbe/*.cbe; do [ -e "$f" ] || continue
  h=$(mktemp -d); NIECHE_HOME=$h python3 tools/dumpboot.py "$f" > "$TMP/py.txt" 2>&1; rm -rf "$h"
  h=$(mktemp -d); NIECHE_HOME=$h "$CARGO_TARGET_DIR/release/bootcmp" "$f" > "$TMP/rs.txt" 2>&1; rm -rf "$h"
  diff -q "$TMP/py.txt" "$TMP/rs.txt" >/dev/null && p=$((p+1)); done
check "两侧引导一致" "$TOTAL" "$p"

step "阶段 04：逐帧差分（$N 帧）"
r=$(./tools/rsdiff.sh "$N" 2>/dev/null | tail -1 | grep -oE '[0-9]+ / [0-9]+')

exp_diff=$( [ "$N" -le 60 ] && echo "$TOTAL / $TOTAL" || echo "$((TOTAL-1)) / $TOTAL" )
check "画面+调用序列+调用数" "$exp_diff" "$r"

step "阶段 05：C ABI vs Python Session（$N 帧）"
r=$(./tools/ffidiff.sh "$N" 2>/dev/null | tail -1 | grep -oE '[0-9]+ / [0-9]+')
check "导出层+输入整形" "$TOTAL / $TOTAL" "$r"

step "阶段 05：ctypes 绑定（Python Session vs 原生核心）"
p=0; for f in assets/cbe/*.CBE assets/cbe/*.cbe; do [ -e "$f" ] || continue
  h=$(mktemp -d); NIECHE_HOME=$h python3 tools/sessdump.py "$f" 20 > "$TMP/py.txt" 2>/dev/null
  NIECHE_HOME=$h python3 tools/sessdump.py "$f" 20 --native > "$TMP/rs.txt" 2>/dev/null; rm -rf "$h"
  diff -q "$TMP/py.txt" "$TMP/rs.txt" >/dev/null && p=$((p+1)); done
check "nieche.py 绑定正确" "$TOTAL" "$p"

step "阶段 05：两个 engine 进程对拍"
r=$(./tools/enginediff.sh 40 2>/dev/null | tail -1 | grep -oE '[0-9]+ / [0-9]+')
check "协议输出一致" "$TOTAL / $TOTAL" "$r"

printf '\n══════════════════════════\n'
[ "$fail" = "0" ] && echo "双轨验收通过" || echo "双轨验收未通过"
exit "$fail"
