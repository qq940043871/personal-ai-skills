# 离线 JVM 取证与分析

> 本文件是 prod-triage 的**离线分支**：不连生产、不要 SSH，只处理一个已经拿到手的
> 诊断包或 heap dump。适用于"企业不允许外部工具连生产"的场景——这也是它比在线定界
> 更容易落地商用的原因。
>
> 在线命令（jstack/jmap/jstat 现场怎么跑）见 `02-command-handbook.md` §Java。

## 0. 两条路，先分清

| 手上有什麼 | 走哪条 |
|---|---|
| 还在跑的故障进程，且有 SSH | 走在线定界（SKILL.md 五步流程）+ `scripts/collect.sh` 保全 |
| 已有 `.hprof` 或 `jvm_diag_*.tar.gz` | **走本文件**，纯离线 |
| 只有现象的投诉，没有现场 | 先教用户按 `scripts/jvm/jvm_diag.sh` 采一份，再回来 |

`.hprof` 体积决定工具：≤1GB 可用 MAT/VisualVM；**>1GB 用本技能的流式工具**——
MAT 分析大 dump 时要约等量内存，"分析 OOM 的工具自己 OOM"是常态。

## 1. 采集包判读顺序

拿到 `jvm_diag_<pid>_<ts>.tar.gz` 后，**先读 `manifest.txt` 的状态标记，再读数据**：

- `[MISS]` = 工具没装 / 采不到，该文件不能参与判读
- `[EMPTY]` = 命令成功但无输出，**可能是真实结论**（如确实没有 D 状态线程）
- `[ERR]` = 看同名 `.err`（常见原因：权限不足、JDK 版本不匹配）

**把 MISS 读成"没有异常"是这类排障最常见的冤案。**

然后按序读：`jstat_gcutil` / `jstat_gccause` → `jstack` → `histo` → `fd_summary` / `ss_pid_states` / `dmesg_tail`。

## 2. GC 数字判读

| 读数 | 判读 |
|---|---|
| FGC 个位数、O 平稳 | 健康 |
| O 持续 >80~90% 且 FGC 频繁、FGCT 占比高 | 老年代吃紧，准备抓 full dump |
| Perm（JDK7）>80% | 黄旗：动态类生成或类加载器泄漏 → 加采 `jmap -permstat` |
| YGC 次数×单次耗时 换算 GC 占比 >5% | 吞吐受损；>10% 明显异常 |
| `-gccause` 末次原因 | `System.gc()` 频现 = 代码显式触发；`Promotion Failed`/`Concurrent Mode Failure` = 老年代碎片/容量 |

## 3. 线程栈判读

- 大量 BLOCKED → 顺 `waiting to lock <0x...>` 找锁持有者
- RUNNABLE 里找**业务包名**热点帧；业务线程名往往直接定位模块
- `nid=0x14040`（十六进制）↔ `top -H` 的 TID（十进制）：`printf '%x' <tid>` 互转
- 挂死进程普通 jstack 空输出 → `jstack -F`（停顿更久，慎用）
- `kill -3` 的产物打在 JVM stdout（Tomcat 是 `catalina.out`），别采了却不收输出

## 4. 堆直方图信号表（`HprofHistogram`）

| 堆里的信号 | 判读 |
|---|---|
| `StackTraceElement` 百万级 + `Throwable` 十万级 | **异常风暴**：循环/高频路径反复 throw |
| `LinkedBlockingQueue$Node` 十万级 | **异步队列积压**：生产快于消费 |
| `LoggingEvent`（log4j/logback 等价类）十万级 | **日志风暴**：错误日志自己成了内存压力源 |
| 驱动专有类海量（如 `PSQLWarning`） | **定位到组件与故障模式** |
| 同长度海量基本类型数组 | **固定容量缓冲区指纹**（见 §5） |
| `HeapCharBuffer`/NIO 缓冲类多 | 编解码缓冲，查网络层与 charset |
| `ClassLoader`/`Class` 持续增长（对比多份直方图） | 类加载器泄漏（JDK7 看 Perm，8+ 看 Metaspace） |

口径提醒：**数量列跨版本可比，字节列只在同一工具版本内可比**；直方图含不可达对象，
OOM 分析正需要这个口径（不要加 `:live`）。

## 5. 固定容量缓冲区指纹 → 字节码反查

直方图出现"几百万个 short[]/int[]，长度 99% 集中在一个值"时：

```bash
# 1) 看长度分布与内容（近零内容 = 分配后未用/异常路径）
java -Dfile.encoding=UTF-8 scripts/jvm/HprofArrays.java heap.hprof

# 2) 回代码找分配点
python scripts/jvm/scan_bytecode.py <解包jar根> --sizes 32 --types short,int
```

**输出是候选不是定论**：库类（Tomcat HPACK、xmlbeans、条码库）也会命中，必须结合
jstack 业务线程与堆中宿主对象互证。若 "no candidate"，说明数组来自
`Arrays.copyOf` 或运行期定长，转查驱动源码。

## 6. 关键词取证：必须扫 byte[]，否则 JDK9+ 全是假阴性

JDK9 的 Compact Strings（JEP 254）把 `String` 内部存储从 `char[]` 改为
`byte[] value + byte coder`。**只扫 char[] 在 JDK11/17/21 上会静默返回 0 命中**——
字符串明明在堆里，工具说没有。静默空结果比报错危险得多。

`HprofArrays` 对每个 `byte[]` 解三种视图匹配（同数组内同词只计一次）：
Latin-1（coder=0 西文）/ UTF-16LE（coder=1，**含中文必走这条**）/ UTF-16BE（兜底）。
输出会标注命中通道。

用法要点：

- 第二个参数是 `keywords.txt` **文件路径**（不是关键词本身），一行一词，`#` 为注释，UTF-8 保存
- 省略则用内置默认清单（源自 openGauss SQLWarning 风暴实战）——**务必按业务替换**
- Windows 控制台默认 GBK，输出中文加 `-Dfile.encoding=UTF-8`
- 只取每数组前 512 字节匹配，实测 289MB dump 含 76 万数组全扫 1.2 秒
- 工具自带防呆：找不到 heap-dump 记录直接 `exit 2`，不会让你误以为"堆里很干净"

## 7. 已知边界（别拿它当万能锤）

- 支持 HPROF 1.0.2（0x1C 分段）与 1.0.1（0x0C 单记录）、idSize=8（64 位 JVM）；
  遇到未知子记录**故意 fail-fast**——宁可报错，不可静默算错
- 字节码反查是候选，不是定论
- 大小口径为近似值（16B 对象头 + 字段/元素实际大小）；对象数组 v2 起按 idSize 计，
  v1 按 compressed oops 4B 估算会低估 → **跨版本只比数量，不比字节**
- 只能回答"谁在分配、分配了多少"，**不给引用链**（谁持有这些对象）；
  根因仍需结合代码或 MAT 的 dominator tree 确认

## 8. 现场采集脚本（`scripts/jvm/jvm_diag.sh`）

```bash
./jvm_diag.sh <pid>                    # 常规采集（~40s，无停顿）
./jvm_diag.sh <pid> --dump             # 追加 full dump（长停顿，自动 gzip）
./jvm_diag.sh <pid> --live-histo       # 直方图改 :live 口径（默认不要）
./jvm_diag.sh <pid> --out /data/tmp    # 大 dump 换输出盘
```

- **面向 Linux 服务器**。Windows Git Bash 下会因进程语义不同直接失败（报"进程不存在"），
  这是设计边界不是 bug；Windows 上请手工跑 `jstack`/`jmap -histo`/`jstat -gcutil`。
- **dump 前先 df**：磁盘余量 ≥ 堆 ×1.2，脚本内置检查，不足自动 SKIP 不硬抓。
- **用目标进程自己的 JDK**：多 JDK 混装机器上，PATH 里的高版本 jstack attach 低版本进程会失败。
- 基线 + 事故双采集：平时采一份基线，告警时采一份，**做差才有结论**。
