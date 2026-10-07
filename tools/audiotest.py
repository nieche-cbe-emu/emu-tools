
"""tools/audiotest.py —— 音频时长的自检

和 Rust 侧 `audio.rs` 的 `mp3_duration_ms_cases` / `wav_duration_ms_cases`
是同一组用例：两份实现必须报同一个数，差一条就是差分测试里的假一致。

为什么要测它：时长决定 `vMAduioGetState` 什么时候答"停了"。估长了，
轮询等音效放完的游戏就干等；估短了，游戏以为放完了又重放一遍。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emu.audio import mp3_duration_ms, wav_duration_ms

def mp3(b1, b2, total):

    return bytes([0xFF, b1, b2, 0x00]) + b"\x00" * (total - 4)

def id3(size, inner):

    n = size
    syncsafe = bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])
    return b"ID3\x03\x00\x00" + syncsafe + b"\x00" * n + inner

def wav(byte_rate, data_len):
    import struct
    fmt = struct.pack("<HHIIHH", 1, 1, 8000, byte_rate, 1, 8)
    return (b"RIFF" + struct.pack("<I", 36 + data_len) + b"WAVE"
            + b"fmt " + struct.pack("<I", 16) + fmt
            + b"data" + struct.pack("<I", data_len) + b"\x00" * data_len)

CASES = [
    ("MPEG1 层3 128k 29227B", mp3(0xFB, 0x90, 29227), 29227 * 8 // 128),
    ("MPEG2 层3 8k 35428B",   mp3(0xF3, 0x10, 35428), 35428 * 8 // 8),
    ("MPEG1 层3 32k 91869B",  mp3(0xFB, 0x10, 91869), 91869 * 8 // 32),
    ("MPEG1 层3 48k 91869B",  mp3(0xFB, 0x30, 91869), 91869 * 8 // 48),
    ("带 ID3 头",             id3(1024, mp3(0xFB, 0x90, 4096)), 4096 * 8 // 128),
    ("太短、不足一帧",         b"\xff", max(500, 1 * 8 // 32)),
    ("认不出帧头",             b"\x11" * 8000, max(500, 8000 * 8 // 32)),
]

WAVS = [
    ("每秒 32000 字节、data 64000", wav(32000, 64000), 2000),
    ("没有 fmt/data", b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 64, max(500, 76 // 8)),
]

def main():
    bad = 0
    for note, data, want in CASES:
        got = mp3_duration_ms(data)
        if got != want:
            print(f"   ✗ mp3 {note}: {got} != {want}")
            bad += 1
    for note, data, want in WAVS:
        got = wav_duration_ms(data)
        if got != want:
            print(f"   ✗ wav {note}: {got} != {want}")
            bad += 1
    print("ok" if bad == 0 else f"{bad} 条不符")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
