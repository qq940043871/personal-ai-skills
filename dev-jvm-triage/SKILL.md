---
name: dev-jvm-triage
description: Java/JVM 服务故障现场取证与内存分析——现场一键采集（jstack/GC/堆直方图/Perm/句柄/连接/系统指标自包含诊断包，兼容 JDK7 目标进程）+ 大体积 heap dump 零依赖流式分析（类直方图、基本类型数组长度指纹、堆内字符串关键词取证（char[]+byte[] 双通道，兼容 JDK9+ Compact Strings）、字节码反查分配点）+ 判读手册（异常风暴/异步队列积压/日志风暴/固定容量缓冲区指纹/Perm 满/CLOSE_WAIT 堆积/基线对比）。当用户提到 OOM、内存溢出、OutOfMemory、heap dump、hprof、jstack、jmap、jstat、Full GC 频繁、GC 停顿、线程堆积、服务假死卡顿、CPU 飙高排查、句柄/连接泄漏，或压测/探顶把服务打挂后要取证归因时使用；用户说"帮我分析这个 heap dump/hprof""服务又内存溢出了""采一份 JVM 诊断"也应触发。
---

# JVM 故障现场取证与内存分析

两段式工作流：**现场采集**（客户服务器，只依赖目标 JDK 自带工具与常用 Linux 命令）→ **离线分析**（把诊断包拿回本地，零依赖工具啃大体积 dump）。沉淀自两次实战：2026-01-21 mid-s 服务（Tomcat7 + JDK7）健康基线采集；2026-10-27 W_2007_iface OOM（4.5GB hprof，openGauss SQLWarning 风暴 + short[32]×531 万缓冲区指纹定案）。

## 开工先问：现场采了吗？dump 有多大？

- **还在运行的故障进程** → 先跑 `scripts/jvm_diag.sh`（见下），采完才允许重启。
- **已有 .hprof 文件** → 看体积：≤1GB 可直接 MAT/VisualVM；**>1GB 用本 skill 的流式工具**（MAT 要约等量内存，分析 OOM 的工具自己 OOM 是常态，实测 4.5GB dump 在 8MB 缓冲下流式解析完毕）。
- **只有 tar.gz 诊断包** → 先解包读 `manifest.txt` 确认每项采集状态，再进判读。

## 铁律

1. **分级取证，轻→重**：jstack（秒级）→ jstat/jmap -histo（秒~分钟）→ full dump（分钟级 + 长停顿）→ **全部完成才允许重启**。重启之前永远先取证。
2. **dump 前先 df**：磁盘余量 ≥ 堆 ×1.2，不够先清理或 `--out` 换目录（脚本已内置检查，磁盘不足自动 SKIP 不硬抓）。
3. **JVM 工具用目标进程自己的 JDK**：多 JDK 混装服务器上，PATH 高版本 jstack attach 低版本进程会失败；脚本从进程命令行自动解析 JDK 路径，回退 PATH 时 manifest 会 NOTE 提醒。
4. **吞错是取证的天敌**：工具缺失、空输出、报错必须可区分。判读以 `manifest.txt` 为准——`[MISS]`=工具没装，`[EMPTY]`=命令成功无输出（可能是真实结论，如无 D 状态线程），`[ERR]`=看同名 .err。**不要把 MISS 读成"没有异常"**。
5. **基线 + 事故双采集**：平时业务闲时用同一脚本采一份基线，告警时再采一份，做差才有结论（同 dev-web-stress-test 的双口径哲学；1 月那份 81939 采集就是健康基线样板）。
6. **OOM 分析按"全部对象"口径**：`jmap -histo` 不加 `:live`（`:live` 触发 Full GC 且丢失已死对象；OOM 案例里不可达对象的历史峰值就是线索）。full dump 同理不加 live。

## 现场采集（scripts/jvm_diag.sh）

```bash
./jvm_diag.sh <pid>                      # 常规采集（~40s，无停顿）
./jvm_diag.sh <pid> --dump               # 追加 full dump（长停顿，自动 gzip）
./jvm_diag.sh <pid> --live-histo         # 直方图改 :live 口径（默认不要）
./jvm_diag.sh <pid> --out /data/tmp      # 大 dump 换输出盘
```

采集项按"轻→重"排序：线程栈最先（jstack 失败自动降级 `jstack -F` 兜底挂死进程）→ JVM 版本/flags/gcutil/gccause → PermGen 或类加载器统计（按 JDK 版本自动选 `-permstat`/`-clstats`）→ 堆直方图 → 可选 dump → 系统基线（load/vmstat/mpstat/iostat/top/df）→ 进程线程（fd 数对 limits、D 状态线程、top -H）→ 日志（gc.log 尾部、catalina.out 尾部、dmesg）→ 网络（ss + 目标进程连接状态分布）。产物为单个 tar.gz，包内 `manifest.txt` 是判读入口。

## 离线分析（scripts/ 三个工具，零依赖，javac/python3 即用）

| 工具 | 场景 | 用法 |
|---|---|---|
| `HprofHistogram.java` | 任何 >1GB hprof 的第一刀：类直方图 + 全量 CSV | `javac -encoding UTF-8 HprofHistogram.java && java -Xmx1g HprofHistogram heap.hprof out.csv` |
| `HprofArrays.java` | 直方图发现海量基本类型数组后的第二刀：长度分布指纹 + **堆内字符串关键词取证（char[] + byte[] 双通道）** | `java -Dfile.encoding=UTF-8 HprofArrays heap.hprof [keywords.txt]` |
| `scan_bytecode.py` | 拿到数组长度指纹后回代码定位分配点 | `python3 scan_bytecode.py <解包jar根> --sizes 32 --types short,int` |

分析顺序固定：**直方图 → 找可疑类与数组 → 数组长度分布 → 关键词扫描 → 字节码反查 → jstack 交叉验证**。判读信号表见 `references/triage-playbook.md`（异常风暴、队列积压、日志风暴、固定容量缓冲区指纹、驱动类定位等，全部带实战数字）。

### 关键词取证：必须扫 byte[]，否则 JDK9+ 上全是假阴性

**JDK9 引入 Compact Strings（JEP 254）后，`String` 内部存储从 `char[]` 改成了 `byte[] value + byte coder`**
（coder=0 Latin-1 / coder=1 UTF-16）。只扫 `char[]` 在 JDK11/17/21 的堆上会**静默返回 0 命中**——
字符串明明就在堆里，工具却说没有。静默空结果比报错危险得多，会让整个归因走偏。

`HprofArrays` 因此对每个 `byte[]` 解出三种视图再做匹配（同一数组内同词只计一次）：
- **Latin-1**：coder=0，纯 ASCII/西文字符串走这条
- **UTF-16LE**：coder=1，HotSpot 用 native byte order（x86/ARM 皆小端），**含中文的字符串必走这条**
- **UTF-16BE**：兜底，兼容其他工具链写出的堆快照

输出会标注每条命中来自哪个通道，并在结尾给出判读提示：

```
提示：命中 2922987 条全部来自 byte[]（char[] 贡献 0）—— 目标 JVM 为 JDK9+ Compact Strings，符合预期。
```

**用法要点**：
- 第二个参数是 `keywords.txt` **文件路径**（不是关键词本身），一行一个词，`#` 开头为注释；文件存 UTF-8。
- 省略该参数则用内置默认清单（源自 openGauss SQLWarning 风暴实战），**务必按业务替换**：
  驱动异常类名、业务表名、协议词、订单号前缀等。
- 中英文关键词都可以，中文在 JDK9+ 堆上经 UTF-16 通道命中。
- **Windows 控制台默认 GBK，输出中文会乱码** → 加 `-Dfile.encoding=UTF-8`（或先 `chcp 65001`）。
- 只取每个数组前 512 字节做匹配，超大缓冲区不会被拖慢；实测 289MB dump 含 76 万数组，全扫 1.2 秒。
- 工具自带防呆：没找到 heap-dump 记录会直接 `exit 2` 并拒绝输出空结果，不会让你误以为"堆里很干净"。

## 实战样例（复用前确认路径仍存在）

- **健康基线样板**：`D:\ai_person\personal-ai-engineering\ai_study_py\50_tools\ops\jvm_diag_81939_20260121_194114\`——Tomcat7+JDK7 中间服务全项正常读数（load 0.01、FGC 0、Perm 82.5% 黄旗、fd 104/4096、estab 58）。
- **OOM 完整实战**：`D:\郑大信息\K206河南国龙\iface内存溢出\`——4.5GB hprof 的直方图/数组指纹/关键词/字节码反查全套产物与结论（openGauss SQLWarning 风暴 + 异步队列积压 + short[32]×531 万）。
- **故障演练场**：`D:\郑大信息\K206河南国龙\iface内存溢出\jvm-fault-lab\`——Spring Boot(2.7.18+Java8+log4j 1.2.17) 复现程序，9 个场景一键触发全部指纹（异常风暴/队列积压/short[32] 缓冲区/char[] 文本/日志风暴/线程/CPU/类加载器/连接泄漏）+ iface-oom 预设组合拳；带 Web 控制台、进程内取证包（与 jvm_diag.sh 同构）和内置分析器。练手/回归验证工具链时用它，README 有场景↔指纹↔工具对照表。
- 本 skill `scripts/` 为工具权威版本；personal-ai-engineering 仓库 `ai_study_py/50_tools/ops/` 是 jvm_diag.sh 出生地，iface 项目内是工具的 v1 原型（对象数组字节估算口径不同，勿跨版本比对字节数）。

## 已知边界

- 流式工具支持 HPROF 1.0.2（分段 0x1C）与 1.0.1（单记录 0x0C）两种 HotSpot 写出格式、idSize=8（64 位 JVM）；遇到未知子记录**故意 fail-fast**（新 JVM 新记录需扩 switch 表，宁可报错不可静默算错）；若全程没见到堆记录会拒绝输出空直方图（exit 2）——2026-10-28 曾靠这个场景发现"0x0C 没被解析"的真实缺陷。
- 字节码反查输出是**候选不是定论**（库类也会命中），必须与 jstack/业务上下文互证。
- 工具大小口径为近似值（16B 对象头 + 实际字段/元素大小）；v2 起对象数组按 idSize 计，v1 按 compressed oops 4B 估算会低估——跨版本比对看"数量列"，别比对"字节列"。
