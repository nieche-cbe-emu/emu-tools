# emu-tools

CoolBar `.cbe` 逆向与验证工具集，以及从固件 DWARF 导出的宿主接口规格。
配合 [emu-core-py](https://github.com/nieche-cbe-emu/emu-core-py) 与
[emu-core-rs](https://github.com/nieche-cbe-emu/emu-core-rs) 使用。

## 特性

- 固件侧：AXF（ELF + DWARF2）符号索引、结构体还原、宿主 manager 槽位表生成
- 模块侧：`.cbe` 解包、按虚拟地址反汇编、资源导出、键位试探
- 验证侧：全语料回归，以及 Python 与 Rust 两份实现的四层逐帧差分
- 交叉编译：安卓 `libnieche.so` 的构建脚本

## 环境要求

- Python 3.9 及以上
- 差分需要两份核心都可用：`pip install unicorn capstone`，以及构建好的 `emu-core-rs`
- 安卓交叉编译需要 Android NDK 与对应的 Rust target

## 逆向工具

```bash
tools/cbex.py <module.cbe> [outdir]              # 解包，导出资源
tools/cbeinfo.py [files...]                      # 容器概览
tools/cbedis.py <module.cbe> <vaddr> [count]     # 按虚拟地址反汇编 RO 段
tools/axf.py                                     # 固件符号索引
tools/dwarfstruct.py <cu_die_offset> [名字正则]   # DWARF 结构体还原为带偏移的 C 声明
tools/genspec.py                                 # 从固件生成 manager 槽位表
tools/genspec_rs.py                              # 把上表转成 Rust 侧的表
tools/fatx.py <FatImage.fat> [输出目录] [--list]  # 导出真机 FAT 分区
```

## 运行与调试

```bash
tools/play.py <module.cbe> [帧数]                 # 跑若干帧并出图
tools/demo.py <module.cbe> [帧数] [--key 0x20] [--every 6]
tools/run_web.py <module.cbe> [--port 8777] [--fps 20] [--rotate 270]
tools/engine.py <module.cbe> [--fps 30] [--vclock]
tools/keyprobe.py <module.cbe> [--frames 6] [--bits 16]
tools/tracecalls.py <file.cbe> <帧号>             # 逐条列出宿主调用
```

## 回归与差分

```bash
tools/batch.py [帧数]        # 全语料回归：每个模块走到了哪一步
tools/ci.sh [帧数]           # 全部验收项，一条命令
```

`ci.sh` 依次执行：

| 检查 | 比对内容 |
|---|---|
| `cargo build` / `cargo test` | Rust 构建与单元测试 |
| `tools/batch.py` | Python 参照实现回归 |
| `dumpcontainer.py` vs `cbedump` | 容器 / LZ / 图片解码 |
| `dumplayout.py` vs `layout` | 段落摆放 |
| `dumpboot.py` vs `bootcmp` | 引导 |
| `tools/rsdiff.sh` | 画面 + 宿主调用序列 + 调用次数 |
| `tools/ffidiff.sh` | C ABI 与 `emu.host.Session` 逐帧一致 |
| `sessdump.py --native` | ctypes 绑定与 Python 实现一致 |
| `tools/enginediff.sh` | 两个 `engine` 进程的协议输出一致 |

差分基准需与被测层对应：经 `Session` 的一侧应对 `tools/sessdump.py`，
而非直驱 `Runtime` 生成的 `spec/baseline`——后者不含输入整形，两者不可比。
比对时两侧均需使用虚拟时钟（`Session.step(now=)`、`nieche_step_at`、
`engine --vclock`），否则长按连发按真实时钟计时，结果不可复现。

## 交叉编译

```bash
tools/build-android.sh      # 出 arm64-v8a 与 armeabi-v7a 的 libnieche.so
```

脚本读取 `DEVENV`（默认 `/Volumes/MX500/DevEnv`）并 source 其中的 `env.sh`，
后者需提供 `ANDROID_NDK_HOME` 与 `CARGO_TARGET_DIR`。构建结束会校验
`__clear_cache` 已被解析——该符号未定义时编译与链接均可通过，但在设备上
`dlopen` 会失败。

## 规格

```
spec/vm_managers.json    从固件 DWARF 导出的宿主接口规格
```

## 说明

多数工具需要手机固件或游戏数据才能发挥作用，两者均不在本仓库，也不提供。
