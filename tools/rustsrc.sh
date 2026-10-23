#!/bin/bash

set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
case "$ROOT" in
  *" "*) ;;
  *) echo "$ROOT/rust"; exit 0 ;;
esac
DST="${DEVENV:-/Volumes/MX500/DevEnv}/scratch/nieche-rust-src"
mkdir -p "$DST"

rsync -a --delete --exclude /target "$ROOT/rust/" "$DST/"
echo "$DST"
