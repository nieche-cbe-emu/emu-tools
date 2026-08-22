
"""
tools/engine.py <module.cbe> [--fps 30]

无界面引擎进程：stdin 收命令（每行一个 JSON），stdout 吐二进制帧。
给 SwiftUI 外壳用——比 HTTP 轮询省掉每帧一次往返。

stdout 分组，小端：
    "FRM0" u32 帧号 u16 宽 u16 高 u32 长度  + 长度字节的 RGB565 原始帧缓冲
    "LOG0" u32 长度 + UTF-8 文本
stdin 每行一个 JSON：
    {"keys": 掩码}                     当前按住的位
    {"touch": [x, y, "down|move|up"]}
    {"fps": 30}
    {"quit": true}
stdout 还有一路音频事件：
    "AUD0" u32 长度 + UTF-8 的 JSON，{"op":"play","path":…,"loop":…} / {"op":"stop"}
    ——MIDI 得靠系统合成器，Python 侧播不了，所以转给原生外壳去发声。
"""
import sys, os, json, struct, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cbelib
from emu.host import Session

out = sys.stdout.buffer
out_lock = threading.Lock()

class ClientGone(Exception):

def emit(tag, payload, *extra):
    with out_lock:
        try:
            out.write(tag)
            for v in extra:
                out.write(v)
            out.write(struct.pack("<I", len(payload)))
            out.write(payload)
            out.flush()
        except (BrokenPipeError, ValueError):

            raise ClientGone

class Engine:

    def __init__(self, path, fps):
        self.sess = Session(path, audio="--no-audio" not in sys.argv)
        if "--no-audio" not in sys.argv:
            self.sess.rt.audio.on_event = lambda e: emit(
                b"AUD0", json.dumps(e, ensure_ascii=False).encode())
        self.mod = self.sess.mod
        self.rt = self.sess.rt
        self.fps = fps
        self.running = True
        self.lock = threading.Lock()

    def boot(self):
        self.sess.boot()

    def shutdown(self):
        self.sess.stop()

    def reader(self):
        for line in sys.stdin:
            try:
                d = json.loads(line)
            except Exception:
                continue
            with self.lock:
                if "keys" in d:
                    self.sess.set_keys(int(d["keys"]))
                if "touch" in d:
                    x, y, st = d["touch"]
                    self.sess.set_touch(int(x), int(y), st)
                if "fps" in d:
                    self.fps = max(1, min(int(d["fps"]), 240))
                if d.get("quit"):
                    self.running = False
                    return

    def loop(self):
        fb = self.rt.fb
        while self.running:
            t = time.time()
            with self.lock:
                px = self.sess.step()
            for e in self.sess.take_events():
                kind = e.get("kind")
                if kind == "audio":
                    emit(b"AUD0", json.dumps(e, ensure_ascii=False).encode())
                elif kind == "exit":
                    emit(b"EXT0", b"module")
                    self.running = False
                elif kind == "log":
                    emit(b"LOG0", e.get("text", "").encode("utf-8", "replace"))
            emit(b"FRM0", px,
                 struct.pack("<I", self.sess.frame_no), struct.pack("<HH", fb.w, fb.h))
            time.sleep(max(0, 1.0 / self.fps - (time.time() - t)))

if __name__ == "__main__":
    fps = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30
    eng = Engine(sys.argv[1], fps)
    eng.boot()
    emit(b"LOG0", f"{eng.mod.name} 已引导，screens={len(eng.rt.screens)}".encode())
    threading.Thread(target=eng.reader, daemon=True).start()
    try:
        eng.loop()
    except ClientGone:
        pass
    eng.shutdown()
