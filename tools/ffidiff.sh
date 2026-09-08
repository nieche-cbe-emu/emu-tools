#!/bin/bash

cd "$(dirname "$0")/.."
BIN="${CARGO_TARGET_DIR:-$HOME/.cache/nieche-rust}/release/ffitest"
N="${1:-60}"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
ok=0; tot=0
for f in assets/cbe/*.CBE assets/cbe/*.cbe; do
  [ -e "$f" ] || continue
  stem=$(basename "${f%.*}")
  tot=$((tot+1))

  h=$(mktemp -d); NIECHE_HOME="$h" timeout 300 "$BIN" "$f" "$N" > "$TMP/rs.txt" 2>/dev/null; rm -rf "$h"
  h=$(mktemp -d); NIECHE_HOME="$h" timeout 600 python3 tools/sessdump.py "$f" "$N" > "$TMP/py.txt" 2>/dev/null; rm -rf "$h"
  if [ ! -s "$TMP/rs.txt" ] || [ ! -s "$TMP/py.txt" ]; then
    printf "   %-22s 没跑出输出\n" "$stem"; continue
  fi
  bad=$(diff "$TMP/py.txt" "$TMP/rs.txt" | grep -c '^<')
  if [ "$bad" = "0" ]; then ok=$((ok+1)); printf "   %-22s 完全一致\n" "$stem"
  else printf "   %-22s 有 %s 行不同\n" "$stem" "$bad"; fi
done
echo "──────────"
echo "经 C ABI 与 Python Session 一致: $ok / $tot"
