#!/bin/bash

cd "$(dirname "$0")/.."
BIN="${CARGO_TARGET_DIR:-$HOME/.cache/nieche-rust}/release/framecmp"
N="${1:-60}"
ok=0; tot=0
for f in assets/cbe/*.CBE assets/cbe/*.cbe; do
  [ -e "$f" ] || continue
  stem=$(basename "${f%.*}")
  [ -f "spec/baseline/$stem.txt" ] || continue
  tot=$((tot+1))
  home=$(mktemp -d)
  NIECHE_HOME="$home" timeout 300 "$BIN" "$f" "$N" > /tmp/rsdiff.txt 2>&1 || true
  rm -rf "$home"
  r=$(python3 tools/baseline.py diff "spec/baseline/$stem.txt" /tmp/rsdiff.txt 2>&1 | head -1 | sed 's/^ *//')
  case "$r" in *帧完全一致*|前*帧一致，但帧数不同*) ok=$((ok+1));; esac
  printf "   %-22s %s\n" "$stem" "$r"
done
echo "──────────"
echo "前 $N 帧完全一致: $ok / $tot"
