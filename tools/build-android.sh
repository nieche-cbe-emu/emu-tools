#!/bin/bash

set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)

DEV=${DEVENV:-/Volumes/MX500/DevEnv}
[ -f "$DEV/env.sh" ] || { echo "找不到 $DEV/env.sh —— 交叉编译环境没装？"; exit 1; }
source "$DEV/env.sh"
TC="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/bin"
STUB="$DEV/android/stub-libs"
RTLIB="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64/lib/clang/17/lib/linux"
export PATH="/opt/homebrew/Cellar/rustup/1.29.0_2/bin:/opt/homebrew/bin:$TC:$PATH"
export ANDROID_NDK_ROOT="$ANDROID_NDK_HOME" ANDROID_NDK="$ANDROID_NDK_HOME"

rm -rf "$STUB"; mkdir -p "$STUB/armv7"
cp "$RTLIB/libclang_rt.builtins-aarch64-android.a" "$STUB/libpthread.a"
cp "$RTLIB/libclang_rt.builtins-aarch64-android.a" "$STUB/librt.a"
cp "$RTLIB/libclang_rt.builtins-arm-android.a"     "$STUB/armv7/libpthread.a"
cp "$RTLIB/libclang_rt.builtins-arm-android.a"     "$STUB/armv7/librt.a"

build() {
  local t=$1 abi=$2 stub=$3 cc=$4
  echo "== $abi =="

  local u=${t//-/_}
  export "CC_$u=$TC/$cc" "AR_$u=$TC/llvm-ar" "CFLAGS_$u=-L$stub"
  RUSTFLAGS="-L native=$stub" cargo build --release -p emuffi --lib --target "$t"
  local so="$CARGO_TARGET_DIR/$t/release/libnieche.so"
  local dst="$ROOT/emu-android/app/src/main/jniLibs/$abi/libnieche.so"
  mkdir -p "$(dirname "$dst")"
  "$TC/llvm-strip" -o "$dst" "$so"
  echo "   $dst  $(ls -lh "$dst" | awk '{print $5}')"
}

cd rust
build aarch64-linux-android   arm64-v8a   "$STUB"       aarch64-linux-android24-clang
build armv7-linux-androideabi armeabi-v7a "$STUB/armv7" armv7a-linux-androideabi24-clang
cd ..

echo

echo "检查 __clear_cache 是否仍未定义（未定义 = 装到机器上会 dlopen 失败）："
bad=0
for a in arm64-v8a armeabi-v7a; do
  n=$("$TC/llvm-nm" -D --undefined-only "$ROOT/emu-android/app/src/main/jniLibs/$a/libnieche.so" \
        2>/dev/null | grep -cw __clear_cache || true)
  if [ "$n" = "0" ]; then printf "   %-14s 已解决\n" "$a"
  else printf "   %-14s 仍未定义 —— 装上去会 dlopen 失败\n" "$a"; bad=1; fi
done
exit $bad
