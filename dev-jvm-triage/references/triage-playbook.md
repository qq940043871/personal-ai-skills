# JVM 排障判读手册

从两次实战沉淀的判读规则。实战 A = 2026-01-21 mid-s 服务（Tomcat7 + JDK7.0_80，Xmx1g + ParallelGC）健康基线采集（jvm_diag_81939_20260121_194114）；实战 B = 2026-10-27 W_2007_iface OOM（4.5GB hprof 流式分析定案）。

## 1. 采集包判读顺序

拿到 `jvm_diag_<pid>_<ts>.tar.gz` 后按此顺序读：

1. `manifest.txt` —— 先看状态标记再读数据。`[MISS]` 的文件代表"没采到"，不能参与判读；`[EMPTY]` 可能是真实结论；`[ERR]` 看同名 `.err` 定位原因（常见：权限、JDK 版本不匹配）。
2. `jstat_gcutil.txt` + `jstat_gccause.txt` —— GC 健康度
3. `jstack.txt` —— 线程状态分布与业务线程
4. `histo.txt` —— 堆内对象概况（轻量，先看趋势再决定要不要 full dump）
5. `fd_summary.txt` / `ss_pid_states.txt` / `dmesg_tail.txt` —— 系统侧三件套

## 2. GC 数字判读（jstat -gcutil）

列含义：S0/S1 幸存区、E(Eden)、O(老年代)、P(Perm，JDK7)/无(JDK8+)、YGC/FGC 次数、YGCT/FGC/T 累计耗时。

| 读数 | 判读 |
|---|---|
| FGC=0 或个位数，O 平稳 | 健康（实战 A：FGC 0，O 47.89%） |
| O 持续 >80~90% 且 FGC 频繁、FGCT 占比高 | 老年代吃紧，准备 full dump 抓现行 |
| P（JDK7 Perm）>80% | 黄旗：动态类生成（CGLIB/脚本引擎）或类加载器泄漏 → 加采 `jmap -permstat` 看哪个 loader 涨（实战 A：P 82.51%，脚本 v2 已自动补采） |
| YGC 次数×单次耗时换算出 GC 占比 >5% | 吞吐受损；>10% 明显异常 |
| `jstat -gccause` 末次 GC 原因 | `System.gc()` 频现 = 代码/堆外组件显式触发；`Allocation Failure` 常态 = 正常；`Promotion Failed`/`Concurrent Mode Failure` = 老年代碎片/容量问题 |

## 3. 线程栈判读（jstack）

- **状态分布**：WAITING/TIMED_WAITING 的池子（Tomcat exec、Jedis、c3p0 PoolThread）属正常常态；大量 BLOCKED 要顺着 `waiting to lock <0x...>` 找锁持有者；RUNNABLE 里找业务包名热点帧。
- **业务线程名直接定位模块**：实战 A 的"SubscribeThread 检测线程"一帧定位到 `com.ylsoft.mid.service.subscribe`；实战 B 的 498 线程里 `com.ylsoft.t9serv.Thread.Job*` 家族即后台任务面。
- **nid 互转**：jstack 的 `nid=0x14040` 是十六进制 TID，`top -H`/`ps -L` 的 TID 是十进制（`printf '%x' <tid>` 互转），高 CPU 线程用 top -H 找到 TID 再回 jstack 对帧。
- **挂死进程**：普通 jstack 报错/空输出时用 `jstack -F`（脚本已自动降级），注意 -F 模式下 JVM 停顿更久。
- **kill -3 的产物在哪**：打在 JVM stdout（Tomcat 即 `catalina.out`），脚本 v2 已自动收集尾部 300 行——v1 的坑是采了 kill -3 却没收输出文件。

## 4. 堆直方图判读信号表（HprofHistogram）

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

判读要点：**数量列跨版本可比，字节列只在本工具同版本内可比**（v2 起对象数组按 idSize 计，v1 按 4B 低估）；直方图含不可达对象（unreachableMarks 计数在输出里），OOM 分析这正是要的口径。

## 5. 固定容量缓冲区指纹 → 字节码反查（HprofArrays + scan_bytecode)

当直方图出现"几百万个 short[]/int[]，长度分布 99% 集中在同一个长度"：

1. `HprofArrays` 确认长度分布与内容（近零内容 = 未填充即弃用的缓冲区，指向"分配后未用/异常路径"）：
   ```
   short length top: 32->5318540   （总数 5318582，即 99.999% 都是 len=32）
   int   length top: 32->2666570
   short zero(first32)=18          （前 32 元素非零 → 有真实数据）
   ```
2. 对业务 jar（解包后根目录）跑字节码反查找分配点：
   ```bash
   python3 scan_bytecode.py _jar_root --sizes 32 --types short,int
   ```
   匹配 `iconst/bipush/sipush <N>` + `newarray <atype>` 指令序列（编码见脚本 docstring）。
3. **输出是候选不是定论**：实战 B 命中 8 个全是库类（tomcat HPACK 与 dump 字节里的 HTTP/2 连接前导 `PRI * HTTP/2.0` 呼应、xmlbeans、BarcodePDF417、UnixCrypt），必须结合 jstack 业务线程、堆中数组所在对象上下文互证。若"no candidate"则数组来自 `Arrays.copyOf`/运行期定长，转查驱动源码。
4. 关键词扫描（`HprofArrays` 第二能力）：对 char[] 扫驱动异常类名/业务 SQL 片段，把"匿名海量对象"变成"可指认的驱动文本"——实战 B 用 `SQLWarning/openGauss/SQLException` 命中 4922+ 处直接锁定组件。**关键词清单按业务/驱动定制**（`keywords.txt` 参数），默认清单来自实战 B。

## 6. 系统侧三件套

- **fd_summary.txt**：`fd_count` 对 `limits.txt` 的 Max open files。实战 A：104/4096 健康；爬到 limit 附近 = 句柄泄漏（配合 `fd_list.txt` 看 socket/文件分布）。
- **ss_pid_states.txt**：目标进程连接状态分布。`CLOSE_WAIT` 持续增长 = 应用不 close 对端已断的连接；`SYN_RECV` 堆积 = 半连接攻击/背压；`TIME_WAIT` 大量属正常。
- **dmesg_tail.txt**：搜 `Out of memory`、`Killed process`——内核 OOM killer 杀进程（常见于无 swap 主机：实战 A 的机器 Swap=0，堆外内存失控时 JVM 不抛 OOM 而是直接被内核杀，heap dump 里什么都看不到）。
- **free.txt 的读法**：Swap=0 的主机上 available 低 = 直接触发 OOM killer 的前夜；buff/cache 高不算压力。

## 7. 基线 vs 事故对比法

同一服务、同一脚本、两个时刻，做差：

| 维度 | 基线读法（实战 A 数字） | 事故时关注 |
|---|---|---|
| load / CPU | 0.01 / id 98%+ | 飙升档位与饱和维度（us 高=计算，wa 高=IO，sy 高=系统调用/锁） |
| YGC/FGC | 133 次/3.1s，FGC 0 | FGC 次数与 FGCT 增速 |
| 线程数 | 80（23 RUNNABLE） | 线程数暴涨 = 线程池泄漏/突发并发 |
| 连接 | estab 58，无 CLOSE_WAIT | CLOSE_WAIT/ESTAB 比例 |
| fd | 104/4096 | fd 增速 |
| Perm/Old | P 82.5%（黄旗盯防）/ O 47.9% | 是否逼近上限 |

注意实战 A 与实战 B 是**不同服务**，上表数字只是各自快照，对比法必须同服务自己和自己比。

## 8. 工具边界（引用前先读）

- HprofHistogram/HprofArrays：支持 HPROF 1.0.2（分段 0x1C，jmap/JDK7-8 attach 写出）与 1.0.1（单记录 0x0C，进程内 HotSpotDiagnosticMXBean 写出）两种格式、idSize=8（64 位 JVM）；未知子记录 fail-fast；全程未见堆记录时拒绝输出空结果（exit 2）。大小为近似值（16B 头 + 实际大小）。
- HprofArrays 采样上限：char[] 前 8192 字符参与关键词扫描、short/int 前 32 元素采样、byte[] 前 256 字节采样、长度分布截断在 100 万——长度恰在边界的极端 case 需人工复核。
- scan_bytecode.py：仅匹配立即数定长分配（size ≤ 32767）；更大长度走 ldc/wide 未覆盖。
- jvm_diag.sh：JDK9+ 的统一日志（`-Xlog:gc`）未覆盖 gc.log 发现逻辑（当前只识别 `-Xloggc:`）；目标是 JDK6~8 的存量服务器（客户现场主力）。
