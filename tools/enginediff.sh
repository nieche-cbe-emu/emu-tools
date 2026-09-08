#!/bin/bash

cd "$(dirname "$0")/.."
BIN="${CARGO_TARGET_DIR:-$HOME/.cache/nieche-rust}/release/engine"
N="${1:-40}"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
ok=0; tot=0
for f in assets/cbe/*.CBE assets/cbe/*.cbe; do
  [ -e "$f" ] || continue
  stem=$(basename "${f%.*}")
  tot=$((tot+1))
  h=$(mktemp -d); NIECHE_HOME="$h" timeout 300 python3 tools/enginedrive.py \
      "python3 tools/engine.py" "$f" "$N" > "$TMP/py.txt" 2>/dev/null; rm -rf "$h"
  h=$(mktemp -d); NIECHE_HOME="$h" timeout 300 python3 tools/enginedrive.py \
      "$BIN" "$f" "$N" > "$TMP/rs.txt" 2>/dev/null; rm -rf "$h"
  if [ ! -s "$TMP/py.txt" ] || [ ! -s "$TMP/rs.txt" ]; then
    printf "   %-22s 没跑出输出\n" "$stem"; continue
  fi
  if diff -q "$TMP/py.txt" "$TMP/rs.txt" >/dev/null; then
    ok=$((ok+1)); printf "   %-22s 协议输出一致\n" "$stem"
  else
    printf "   %-22s 有 %s 行不同\n" "$stem" "$(diff "$TMP/py.txt" "$TMP/rs.txt" | grep -c '^<')"
  fi
done
echo "──────────"
echo "两个 engine 协议输出一致: $ok / $tot"
