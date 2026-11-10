# 离线 JVM 取证与分析

> 本文件是 dev-prod-triage 的**离线分支**：不连生产、不要 SSH，只处理一个已经拿到手的
> 诊断包或 heap dump。适用于"企业不允许外部工具连生产"的场景——这也是它比在线定界
> 更容易落地商用的原因。
>
> 在线命令（jstack/jmap/jstat 现场怎么跑）见 `02-command-handbook.md` §Java。
> 本文件与 `scripts/jvm/` 是 JVM 取证的**唯一权威版本**（原 `dev-jvm-triage` 技能已整体并入）。

沉淀自两次实战：
- **实战 A** = 2026-01-21 mid-s 服务（Tomcat7 + JDK7.0_80，Xmx1g + ParallelGC）健康基线采集
  `jvm_diag_81939_20260121_194114`
- **实战 B** = 2026-10-27 W_2007_iface OOM（4.5GB hprof 流式分析定案：openGauss SQLWarning
  风暴 + 异步队列积压 + `short[32]×531.85万` 缓冲区指纹）

## 0. 两条路，先分清

| 手上有什麼 | 走哪条 |
|---|---|
| 还在跑的故障进程，且有 SSH | 走在线定界（SKILL.md 五步流程）+ `scripts/collect.sh` 保全 |
| 已有 `.hprof` 或 `jvm_diag_*.tar.gz` | **走本文件**，纯离线 |
| 只有现象的投诉，没有现场 | 先教用户按 `scripts/jvm/jvm_diag.sh` 采一份，再回来 |

`.hprof` 体积决定工具：≤1GB 可用 MAT/VisualVM；**>1GB 用本技能的流式工具**——
MAT 分析大 dump 时要约等量内存，"分析 OOM 的工具自己 OOM"是常态（实测 4.5GB dump
在 8MB 缓冲下流式解析完毕）。

**六条取证铁律**（违反任何一条，结论都不可信）：

1. **分级取证，轻→重**：jstack（秒级）→ jstat/jmap -histo（秒~分钟）→ full dump（分钟级 + 长停顿）→
   **全部完成才允许重启**。重启之前永远先取证。
2. **dump 前先 df**：磁盘余量 ≥ 堆 ×1.2，不够先清理或 `--out` 换目录（脚本已内置检查，不足自动 SKIP 不硬抓）。
3. **JVM 工具用目标进程自己的 JDK**：多 JDK 混装机器上，PATH 里的高版本 jstack attach 低版本进程会失败；
   脚本从进程命令行自动解析 JDK 路径，回退 PATH 时 manifest 会 NOTE 提醒。
4. **吞错是取证的天敌**：工具缺失、空输出、报错必须可区分，判读以 `manifest.txt` 为准（见 §1）。
5. **基线 + 事故双采集**：平时业务闲时用同一脚本采一份基线，告警时再采一份，做差才有结论（见 §9）。
6. **OOM 按"全部对象"口径**：`jmap -histo` 不加 `:live`（`:live` 触发 Full GC 且丢失已死对象——
   不可达对象的历史峰值正是线索）。full dump 同理不加 live。

## 1. 采集包判读顺序

拿到 `jvm_diag_<pid>_<ts>.tar.gz` 后，**先读 `manifest.txt` 的状态标记，再读数据**：

- `[MISS]` = 工具没装 / 采不到，该文件不能参与判读
- `[EMPTY]` = 命令成功但无输出，**可能是真实结论**（如确实没有 D 状态线程）
- `[ERR]` = 看同名 `.err`（常见原因：权限不足、JDK 版本不匹配）

**把 MISS 读成"没有异常"是这类排障最常见的冤案。**

然后按序读：`manifest.txt` → `jstat_gcutil` / `jstat_gccause` → `jstack` → `histo` →
`fd_summary` / `ss_pid_states` / `dmesg_tail`。

## 2. GC 数字判读（jstat -gcutil）

列含义：S0/S1 幸存区、E(Eden)、O(老年代)、P(Perm，JDK7)/无(JDK8+)、YGC/FGC 次数、YGCT/FGCT 累计耗时。

| 读数 | 判读 |
|---|---|
| FGC=0 或个位数，O 平稳 | 健康（实战 A：FGC 0，O 47.89%） |
| O 持续 >80~90% 且 FGC 频繁、FGCT 占比高 | 老年代吃紧，准备抓 full dump 抓现行 |
| P（JDK7 Perm）>80% | 黄旗：动态类生成（CGLIB/脚本引擎）或类加载器泄漏 → 加采 `jmap -permstat` 看哪个 loader 涨（实战 A：P 82.51%，脚本已自动补采） |
| YGC 次数×单次耗时 换算出 GC 占比 >5% | 吞吐受损；>10% 明显异常（实战 A：YGC 133 次 / 3.1s） |
| `-gccause` 末次原因 | `System.gc()` 频现 = 代码/堆外组件显式触发；`Allocation Failure` 常态 = 正常；`Promotion Failed`/`Concurrent Mode Failure` = 老年代碎片/容量 |

## 3. 线程栈判读（jstack）

- **状态分布**：WAITING/TIMED_WAITING 的池子（Tomcat exec、Jedis、c3p0 PoolThread）属正常常态；
  大量 BLOCKED 要顺 `waiting to lock <0x...>` 找锁持有者；RUNNABLE 里找**业务包名**热点帧。
- **业务线程名直接定位模块**：实战 A 的"SubscribeThread 检测线程"一帧定位到
  `com.ylsoft.mid.service.subscribe`；实战 B 的 498 线程里 `com.ylsoft.t9serv.Thread.Job*` 家族
  即后台任务面。业务线程名往往是免费的模块地图。
- **nid 互转**：jstack 的 `nid=0x14040` 是十六进制 TID，`top -H`/`ps -L` 的 TID 是十进制
  （`printf '%x' <tid>` 互转）；高 CPU 线程用 `top -H` 找 TID 再回 jstack 对帧。
- **挂死进程**：普通 jstack 报错/空输出时用 `jstack -F`（脚本已自动降级），注意 `-F` 模式 JVM 停顿更久。
- **kill -3 的产物在哪**：打在 JVM stdout（Tomcat 即 `catalina.out`），别采了却不收输出
  （脚本 v2 已自动收集尾部 300 行）。
- **必须打 3 次**，间隔 3~5 秒，`-l` 带锁信息；只看长时间停在同一行的 RUNNABLE 线程。

## 4. 堆直方图信号表（`HprofHistogram`）

| 堆里的信号 | 判读 | 实战 B 数字 |
|---|---|---|
| `java/lang/StackTraceElement` 百万级 + `Throwable` 十万级 | **异常风暴**：某处在循环/高频路径反复 throw（异常构造要抓全栈） | 1078 万 + 13.7 万 |
| `java.util.concurrent.LinkedBlockingQueue$Node` 十万级 | **异步队列积压**：生产快于消费，查队列任务为什么处理不动 | 65.5 万 |
| `org/apache/log4j/spi/LoggingEvent`（或 logback 等价类）十万级 | **日志风暴**：高频错误日志自身成为内存压力源，与异常风暴常伴生 | 13.6 万 |
| 驱动专有类海量（如 `org.opengauss.util.PSQLWarning` / `ServerErrorMessage`） | **定位到组件与故障模式**：驱动在反复产生告警/错误对象 | 各 75 万 → openGauss SQLWarning 风暴 |
| `char[]` 海量 | 常与异常/日志/SQL 文本伴生，下一步用关键词扫描定性 | 821 万个 / 743MB |
| 同长度海量基本类型数组 | **固定容量缓冲区指纹**（见 §5） | short[32]×531.85 万、int[32]×266.7 万 |
| `HeapCharBuffer`/NIO 缓冲类多 | 编解码缓冲，查网络层与 charset 转换 | 13.9 万（次要） |
| `ClassLoader`/`Class`/`Method` 持续增长（对比多份直方图） | 类加载器泄漏（JDK7 看 Perm，JDK8+ 看 Metaspace） | 实战 A 用 permstat 盯 |

判读要点：**数量列跨版本可比，字节列只在本工具同版本内可比**（v2 起对象数组按 idSize 计，v1 按 4B 低估）；
直方图含不可达对象（`unreachableMarks` 计数在输出里），OOM 分析正是要这个口径——不要加 `:live`。

## 5. 固定容量缓冲区指纹 → 字节码反查

直方图出现"几百万个 short[]/int[]，长度分布 99% 集中在同一个值"时：

```bash
# 1) 看长度分布与内容（近零内容 = 分配后未用/异常路径）
java -Dfile.encoding=UTF-8 scripts/jvm/HprofArrays.java heap.hprof

# 2) 回代码找分配点
python scripts/jvm/scan_bytecode.py <解包jar根> --sizes 32 --types short,int
```

实战 B 的指纹读法：

```
short length top: 32->5318540   （总数 5318582，即 99.999% 都是 len=32）
int   length top: 32->2666570
short zero(first32)=18          （前 32 元素非零 → 有真实数据）
```

`scan_bytecode.py` 匹配 `iconst/bipush/sipush <N>` + `newarray <atype>` 指令序列（编码见脚本 docstring）。

**输出是候选不是定论**：实战 B 命中 8 个全是库类（tomcat HPACK 与 dump 字节里的 HTTP/2 连接前导
`PRI * HTTP/2.0` 呼应、xmlbeans、BarcodePDF417、UnixCrypt），必须结合 jstack 业务线程与堆中数组
所在对象上下文互证。若 "no candidate"，说明数组来自 `Arrays.copyOf` 或运行期定长，转查驱动源码。

## 6. 关键词取证：必须扫 byte[]，否则 JDK9+ 全是假阴性

JDK9 的 Compact Strings（JEP 254）把 `String` 内部存储从 `char[]` 改为
`byte[] value + byte coder`（coder=0 Latin-1 / coder=1 UTF-16）。
**只扫 char[] 在 JDK11/17/21 上会静默返回 0 命中**——字符串明明在堆里，工具说没有。
静默空结果比报错危险得多，会让整个归因走偏。

`HprofArrays` 对每个 `byte[]` 解三种视图匹配（同数组内同词只计一次）：
Latin-1（coder=0 西文）/ UTF-16LE（coder=1，**含中文必走这条**，HotSpot 用 native byte order，
x86/ARM 皆小端）/ UTF-16BE（兜底，兼容其他工具链写出的堆快照）。输出会标注命中通道，并在结尾给出判读提示：

```
提示：命中 2922987 条全部来自 byte[]（char[] 贡献 0）—— 目标 JVM 为 JDK9+ Compact Strings，符合预期。
```

用法要点：

- 第二个参数是 `keywords.txt` **文件路径**（不是关键词本身），一行一词，`#` 开头为注释，UTF-8 保存
- 省略则用内置默认清单（源自实战 B 的 openGauss SQLWarning 风暴）——**务必按业务替换**：
  驱动异常类名、业务表名、协议词、订单号前缀等
- 中英文关键词都可以，中文在 JDK9+ 堆上经 UTF-16 通道命中
- Windows 控制台默认 GBK，输出中文加 `-Dfile.encoding=UTF-8`（或先 `chcp 65001`）
- 只取每数组前 512 字节匹配，超大缓冲区不会被拖慢；实测 289MB dump 含 76 万数组全扫 1.2 秒
- 工具自带防呆：找不到 heap-dump 记录直接 `exit 2`，不会让你误以为"堆里很干净"
- 实战 B 用 `SQLWarning/openGauss/SQLException` 命中 4922+ 处，直接锁定组件

## 7. 系统侧三件套

- **`fd_summary.txt`**：`fd_count` 对 `limits.txt` 的 Max open files。实战 A：104/4096 健康；
  爬到 limit 附近 = 句柄泄漏（配合 `fd_list.txt` 看 socket/文件分布）。
- **`ss_pid_states.txt`**：目标进程连接状态分布。`CLOSE_WAIT` 持续增长 = 应用不 close 对端已断的连接；
  `SYN_RECV` 堆积 = 半连接攻击/背压；`TIME_WAIT` 大量属正常。
- **`dmesg_tail.txt`**：搜 `Out of memory`、`Killed process`——内核 OOM killer 杀进程。
  常见于无 swap 主机（实战 A：Swap=0）：堆外内存失控时 JVM 不抛 OOM 而是被内核直接杀掉，
  **heap dump 里什么都看不到**，这时只能靠 dmesg 定案。
- **`free.txt` 的读法**：Swap=0 主机上 available 低 = OOM killer 前夜；buff/cache 高不算压力。

## 8. 分析顺序（固定）

**直方图 → 找可疑类与数组 → 数组长度分布 → 关键词扫描 → 字节码反查 → jstack 交叉验证。**

三个工具各管一刀（零依赖，`javac`/`python3` 即用）：

| 工具 | 场景 | 用法 |
|---|---|---|
| `HprofHistogram.java` | 任何 >1GB hprof 的第一刀：类直方图 + 全量 CSV | `javac -encoding UTF-8 HprofHistogram.java && java -Xmx1g HprofHistogram heap.hprof out.csv` |
| `HprofArrays.java` | 直方图发现海量基本类型数组后的第二刀：长度分布指纹 + 堆内字符串关键词（char[]+byte[] 双通道） | `java -Dfile.encoding=UTF-8 HprofArrays heap.hprof [keywords.txt]` |
| `scan_bytecode.py` | 拿到数组长度指纹后回代码定位分配点 | `python3 scan_bytecode.py <解包jar根> --sizes 32 --types short,int` |

单边结论只能标"疑似"：离线看到的 `short[32]×531万`，必须能对上在线 jstack 里的业务线程。

## 9. 基线 vs 事故对比法

同一服务、同一脚本、两个时刻做差：

| 维度 | 基线读法（实战 A 数字） | 事故时关注 |
|---|---|---|
| load / CPU | 0.01 / id 98%+ | 飙升档位与饱和维度（us 高=计算，wa 高=IO，sy 高=系统调用/锁） |
| YGC/FGC | 133 次 / 3.1s，FGC 0 | FGC 次数与 FGCT 增速 |
| 线程数 | 80（23 RUNNABLE） | 线程数暴涨 = 线程池泄漏/突发并发 |
| 连接 | estab 58，无 CLOSE_WAIT | CLOSE_WAIT/ESTAB 比例 |
| fd | 104/4096 | fd 增速 |
| Perm/Old | P 82.5%（黄旗盯防）/ O 47.9% | 是否逼近上限 |

实战 A 与实战 B 是**不同服务**，上表数字只是各自快照；对比法必须同服务自己和自己比。

## 10. 采集脚本（`scripts/jvm/jvm_diag.sh`）

```bash
./jvm_diag.sh <pid>                    # 常规采集（~40s，无停顿）
./jvm_diag.sh <pid> --dump             # 追加 full dump（长停顿，自动 gzip）
./jvm_diag.sh <pid> --live-histo       # 直方图改 :live 口径（默认不要）
./jvm_diag.sh <pid> --out /data/tmp    # 大 dump 换输出盘
```

采集项按"轻→重"排序：线程栈最先（jstack 失败自动降级 `jstack -F` 兜底挂死进程）→ JVM 版本/flags/
gcutil/gccause → PermGen 或类加载器统计（按 JDK 版本自动选 `-permstat`/`-clstats`）→ 堆直方图 →
可选 dump → 系统基线（load/vmstat/mpstat/iostat/top/df）→ 进程线程（fd 数对 limits、D 状态线程、
top -H）→ 日志（gc.log 尾部、catalina.out 尾部、dmesg）→ 网络（ss + 目标进程连接状态分布）。
产物为单个 tar.gz，包内 `manifest.txt` 是判读入口。

- **面向 Linux 服务器**。Windows Git Bash 下会因进程语义不同直接失败（报"进程不存在"），
  这是设计边界不是 bug；Windows 上请手工跑 `jstack`/`jmap -histo`/`jstat -gcutil`。
- **用目标进程自己的 JDK** + **dump 前先 df**：见 §0 铁律 2、3。
- **基线 + 事故双采集**：平时采一份基线，告警时再采一份，做差才有结论（见 §9）。

## 11. 已知边界（别拿它当万能锤）

- `HprofHistogram` / `HprofArrays`：支持 HPROF 1.0.2（分段 0x1C，jmap/JDK7-8 attach 写出）与
  1.0.1（单记录 0x0C，进程内 HotSpotDiagnosticMXBean 写出）两种格式、idSize=8（64 位 JVM）；
  遇到未知子记录**故意 fail-fast**（新 JVM 新记录需扩 switch 表，宁可报错不可静默算错）；
  全程没见到堆记录会拒绝输出空直方图（`exit 2`）——2026-10-28 曾靠这个场景发现"0x0C 没被解析"的真实缺陷。
- `HprofArrays` 采样上限：`char[]` 前 8192 字符参与关键词扫描、`short[]`/`int[]` 前 32 元素采样、
  `byte[]` 前 512 字节采样、长度分布截断在 100 万——长度恰在边界的极端 case 需人工复核。
- `scan_bytecode.py`：仅匹配立即数定长分配（size ≤ 32767）；更大长度走 `ldc`/`wide` 未覆盖。
- `jvm_diag.sh`：未覆盖 JDK9+ 统一日志（`-Xlog:gc`）的 gc.log 发现逻辑（当前只识别 `-Xloggc:`）；
  目标是 JDK6~8 的存量服务器（客户现场主力）。
- 字节码反查是**候选不是定论**；大小口径为近似值（16B 对象头 + 字段/元素实际大小），
  对象数组 v2 起按 idSize 计，v1 按 compressed oops 4B 估算会低估 → **跨版本只比数量，不比字节**。
- 只能回答"谁在分配、分配了多少"，**不给引用链**（谁持有这些对象）；根因仍需结合代码或
  MAT 的 dominator tree 确认。

## 12. 实战样例（复用前确认路径仍存在）

- **健康基线样板**：`D:\ai_person\personal-ai-engineering\ai_study_py\50_tools\ops\jvm_diag_81939_20260121_194114\`
  ——Tomcat7+JDK7 中间服务全项正常读数（load 0.01、FGC 0、Perm 82.5% 黄旗、fd 104/4096、estab 58）。
- **OOM 完整实战**：`D:\郑大信息\K206河南国龙\iface内存溢出\`——4.5GB hprof 的直方图/数组指纹/
  关键词/字节码反查全套产物与结论。
- **故障演练场**：`D:\郑大信息\K206河南国龙\iface内存溢出\jvm-fault-lab\`——Spring Boot(2.7.18+Java8+
  log4j 1.2.17) 复现程序，9 个场景一键触发全部指纹（异常风暴/队列积压/short[32] 缓冲区/char[] 文本/
  日志风暴/线程/CPU/类加载器/连接泄漏）+ iface-oom 预设组合拳；带 Web 控制台、进程内取证包
  （与 jvm_diag.sh 同构）和内置分析器。练手/回归验证工具链时用它，README 有场景↔指纹↔工具对照表。
- `scripts/jvm/` 为工具**权威版本**；personal-ai-engineering 仓库 `ai_study_py/50_tools/ops/` 是
  jvm_diag.sh 出生地，iface 项目内是工具的 v1 原型（对象数组字节估算口径不同，勿跨版本比对字节数）。
