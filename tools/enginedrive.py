
"""tools/enginedrive.py <引擎命令> <module.cbe> [帧数]

驱动一个 engine 子进程，按固定脚本喂输入，把收到的 FRM0 逐帧打指纹。
两个引擎（Python 的和 Rust 的）说同一套协议，所以同一个驱动能开两边。

**不比对音频与日志分组**：Python 侧的日志文本是它自己的措辞，
两边一字不差没有意义，也不是协议的一部分。协议本身要对上的是帧。
"""
import os
import shlex
import struct
import subprocess
import sys
import zlib

def main():
    if len(sys.argv) < 3:
        print("用法: enginedrive.py <引擎命令> <module.cbe> [帧数]", file=sys.stderr)
        return 2
    cmd = shlex.split(sys.argv[1]) + [sys.argv[2], "--fps", "240", "--no-audio", "--vclock"]
    want = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    buf = b""
    seen = 0
    out = []
    try:
        while seen < want:
            chunk = p.stdout.read(65536)
            if not chunk:
                break
            buf += chunk
            while len(buf) >= 8:
                tag = buf[:4]
                if tag == b"FRM0":
                    if len(buf) < 12:
                        break
                    no, w, h, ln = struct.unpack("<IHHI", buf[4:16]) if len(buf) >= 16 else (0, 0, 0, 0)
                    if len(buf) < 16 + ln:
                        break
                    px = buf[16:16 + ln]
                    buf = buf[16 + ln:]
                    out.append(f"{no} {w}x{h} {zlib.crc32(px) & 0xFFFFFFFF:08x}")
                    seen += 1

                    if seen % 11 == 0:
                        p.stdin.write(b'{"keys": %d}\n' % (1 << ((seen // 11) % 12)))
                        p.stdin.flush()
                    elif seen % 11 == 3:
                        p.stdin.write(b'{"keys": 0}\n')
                        p.stdin.flush()
                    if seen % 17 == 5:
                        p.stdin.write(b'{"touch": [%d, %d, "down"]}\n' % (w // 2, h // 2))
                        p.stdin.flush()
                    elif seen % 17 == 7:
                        p.stdin.write(b'{"touch": [%d, %d, "up"]}\n' % (w // 2, h // 2))
                        p.stdin.flush()
                elif tag in (b"LOG0", b"AUD0", b"EXT0"):
                    ln = struct.unpack("<I", buf[4:8])[0]
                    if len(buf) < 8 + ln:
                        break
                    buf = buf[8 + ln:]
                else:

                    print(f"未知分组 {tag!r}", file=sys.stderr)
                    return 1
    finally:
        try:
            p.stdin.write(b'{"quit": true}\n')
            p.stdin.flush()
            p.stdin.close()
        except Exception:
            pass
        try:
            p.wait(timeout=20)
        except Exception:
            p.kill()
    print("\n".join(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
