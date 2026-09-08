#!/bin/bash

cd "$(dirname "$0")/.."
BIN="${CARGO_TARGET_DIR:-$HOME/.cache/nieche-rust}/release/framecmp"
f="$1"; fr="$2"
h=$(mktemp -d); NIECHE_HOME=$h python3 tools/tracecalls.py "$f" "$fr" > /tmp/rstrace_py.txt 2>&1; rm -rf "$h"
h=$(mktemp -d); NIECHE_HOME=$h TRACE=$fr "$BIN" "$f" $((fr+1)) 2>/tmp/rstrace_rs.txt >/dev/null; rm -rf "$h"
echo "第 $fr 帧: Python $(wc -l < /tmp/rstrace_py.txt) / Rust $(wc -l < /tmp/rstrace_rs.txt)"
n=$(diff /tmp/rstrace_py.txt /tmp/rstrace_rs.txt | head -1 | grep -oE '^[0-9]+')
if [ -n "$n" ]; then
  a=$((n>3?n-3:1)); b=$((n+2))
  echo "--- Python ${a}-${b} ---"; sed -n "${a},${b}p" /tmp/rstrace_py.txt
  echo "--- Rust ---"; sed -n "${a},${b}p" /tmp/rstrace_rs.txt
else
  echo "完全一致"
fi
