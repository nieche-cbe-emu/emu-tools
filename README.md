# emu-tools

尼彩 CBE 逆向过程中用到的工具与规格。

```
tools/axf.py           固件 AXF(ELF+DWARF2) 索引器：查符号、展开 CU、导出结构体
tools/dwarfstruct.py   把 DWARF 里的结构体还原成带偏移的 C 声明
tools/genspec.py       从固件生成宿主 manager 的槽位表
tools/genspec_rs.py    把上面那份规格转成 Rust 侧的表
tools/cbex.py          解包 .cbe，导出资源
tools/cbedis.py        按虚拟地址反汇编模块 RO 段
tools/batch.py         全语料回归：跑一遍所有模块，汇总走到哪一步
tools/play.py          单模块跑若干帧并出图
tools/engine.py        无界面引擎进程（stdin 收命令，stdout 吐二进制帧）
tools/run_web.py       本地网页前端
tools/keyprobe.py      对单个模块逐位试探键位
tools/mkindex.py       生成镜像源目录 index.json
tools/fontgen/         点阵字库生成
spec/vm_managers.json  从固件 DWARF 导出的宿主接口规格
```

## 双轨差分

[emu-core-py](https://github.com/nieche-cbe-emu/emu-core-py) 是参照实现，
[emu-core-rs](https://github.com/nieche-cbe-emu/emu-core-rs) 是发布产物，
后者必须逐帧对上前者。四层比对，配合 `tools/ci.sh` 一条命令跑完：

```
tools/rsdiff.sh      画面 + 宿主调用序列 + 调用次数
tools/ffidiff.sh     C ABI + 输入整形，对 Python 的 Session
tools/enginediff.sh  两个 engine 进程的协议输出
tools/ci.sh          以上全部，加构建与单元测试
```

差分基准要选对：走 `Session` 的一侧**不能**拿直驱 Runtime 生成的基准来比，
那里面没有输入整形（锁存、触摸排队、按键事件、长按连发），比出来的分叉是假的。

## 构建

```
tools/build-android.sh   把 Rust 核心交叉编译成安卓的 libnieche.so
```

## 说明

这些工具需要手机固件和游戏数据才能发挥作用，两者都不在本仓库，也不会提供。
