---
name: prod-triage
display_name: 生产问题链路定界与快速定位
display_name_en: Production Incident Triage (Client-Mids-DS-Backend-3rd)
description: "按「客户端 → Mids → DS → 后端 → 第三方」分层链路快速定位生产问题：CPU 飙高、接口响应慢、超时（连接超时/读超时/写超时）、Socket 长连接读取超时、服务端说没收到报文、偶发丢包断连、线程池打满、慢 SQL。输出可直接复制的 SSH 命令行诊断路径 + 分层定界结论 + HTML 排障报告。当用户提到「生产问题」「线上故障」「CPU 高」「接口慢」「超时」「读取超时」「长连接断开」「没收到报文」「报文丢失」「Socket 报错」「Mids」「DS」「定位一下」「排查一下线上」时使用。另含 JVM 离线取证分支：OOM / 内存溢出 / OutOfMemory / heap dump / hprof / jstack / jmap / jstat / Full GC 频繁 / 线程堆积 / 服务假死 / 固定容量缓冲区 —— 不需要 SSH，拿到诊断包或 dump 即可流式分析（含 JDK9+ Compact Strings 的 byte[] 关键词取证）。"
description_zh: 面向多语言微服务（Java / C / C++ / Go）生产环境的分层定界排障方法论：先用同一 traceId/流水号确定故障发生在哪一跳，再用语言专属工具下钻根因（jstack/arthas/perf/gdb/pprof/tcpdump），产出带证据的 HTML 排障报告。
description_en: Layer-by-layer production incident triage across Client → Mids → DS → Backend → Third-party, with SSH command playbooks per symptom (high CPU, slow API, timeouts, socket read timeout, missing packets) and an HTML triage report.
category: Operations
version: 1.1.0
author: hasWhere
tags: ["生产排障", "链路定界", "CPU飙高", "接口慢", "超时", "Socket长连接", "TCP", "tcpdump", "jstack", "arthas", "pprof", "多语言微服务", "OOM", "heap dump", "hprof", "内存分析", "GC"]
permissions:
  - file_read
  - file_write
  - shell_exec
metadata:
  last_created: "2026-09-30"
  last_updated: "2026-10-31"
  merged_from: "dev-jvm-triage@1.0.0"
  agent_created: true
---

# 生产问题链路定界与快速定位

生产排障最贵的错误不是查不出根因，而是**在错误的层里查根因**。客户端报超时你就去后端翻日志，后端说没收到你就去抓包——两天后才发现是 LB 空闲回收了长连接。本 Skill 强制先做**分层定界**，再下钻。

## 链路模型（四层五跳 + 每跳之间的 LB 链）

```
L0  客户端         APP / 小程序 / Web（含客户侧机房）
     │ ①   ← LB①：客户侧硬件 F5 / A10 / 深信服，或 DNS · 专线 · SD-WAN
L1  Mids 集群      接入层（N 实例）：鉴权、限流、协议转换、长连接接入、会话保持
     │ ②   ← LB②：Nginx / HAProxy / 云 SLB（四层转发 or 七层代理）
L2  DS 集群        分发层（N 实例）：路由编排、聚合、缓存、报文转发
     │ ③   ← LB③：内部负载（LVS / K8s Service / sidecar / 服务发现）
L3  后端集群       领域服务（Java 为主）+ DB / Redis / MQ
     │ ④   ← LB④：出口 NAT / 专线网关 / 第三方前置机
L4  第三方         银行 / 交易所 / 支付 / 短信 / 外部行情
```

**LB 不是可选装饰，是头号嫌疑犯。** 每一跳之间可能有 0~3 级负载均衡：客户的硬件 F5、自家的 Nginx、云 SLB、K8s Service，串成一条 **LB 链**。三个必须记住的事实：

1. **idle timeout 取的是整条链上的最小值**，不是你在某一层配的那个。你在 Nginx 上把 `keepalive_timeout` 调到 3600s，客户 F5 上的 300s 照样把连接掐了。
2. **Mids / DS 是集群**，故障可能只落在其中 1 台实例上——表现为"部分请求失败"。定界必须**按实例分组统计**，看聚合数会把单实例故障稀释成"偶发抖动"。
3. **LB 会改写 IP 与连接**：SNAT 之后服务端看到的源 IP 全是 LB 的；七层代理会拆成两段 TCP 连接（客户端↔LB、LB↔后端），`ss` 双向比对时**两侧的连接不是同一条**。

层名（Mids / DS / 后端）在不同项目里叫法不同，**首次使用时用 `references/00-link-model.md` 的 LB 链清单 + 层名映射表把真实拓扑填进来**，不要死记缩写。

## 两种工作模式：在线定界 / 离线取证

同一套排障思维，两条落地路径。**先问用户有哪个，别默认要 SSH 权限。**

| 模式 | 前提 | 能回答什么 | 走哪份 |
|---|---|---|---|
| **在线定界** | 能登上服务器、能跑命令 | 故障在哪一跳、哪台实例、哪个线程/接口 | 本文件五步流程 + `scripts/collect.sh` |
| **离线取证** | 只有一个 `.hprof` 或 `jvm_diag_*.tar.gz` | 谁在分配、分配了多少、堆里有没有异常风暴/队列积压/缓冲区泄漏 | `references/04-jvm-offline.md` |

**为什么要有离线这条路**：企业普遍不允许外部工具连生产，在线定界经常卡在"给我个 SSH"。
而 heap dump 可以脱敏带出来分析——**信任门槛低一个数量级，是这套方法论最容易落地收费的形态**。

两条路的结论要互相印证：离线看到的"short[32]×531万"，必须能对上在线 jstack 里的业务线程，
单边结论只能标"疑似"。

## 三条铁律

1. **先止血，后破案。** 影响面还在扩大时，不许沉浸在 jstack 里。止血手段优先级：回滚 > 扩容 > 降级/开关 > 限流 > 重启（重启永远最后，且必须先保全现场）。
2. **先定界，后下钻。** 没拿到"最后一次出现该请求的层"之前，不做任何语言级剖析。定界用**同一个 traceId / requestId / 报文流水号**，找到它最后一次出现的地方——故障就发生在那之后的那一跳。
3. **先保全，后操作。** 任何可能丢失现场的动作（重启、回滚、切流）之前，先跑 `scripts/collect.sh` 抓一份快照。

## 五步流程

| 步 | 动作 | 产出 |
|---|---|---|
| 1 | 问清**现象 + 影响面 + 起始时间 + 是否持续**（见 `references/01-triage-tree.md` 的开场十问） | 一句话故障陈述 |
| 2 | 拿 traceId/流水号在四层做**进出计数比对**，定界到某一跳 | 定界结论 |
| 3 | 按症状走决策树，跑语言专属命令下钻（`references/02-command-handbook.md`） | 根因 + 证据 |
| 4 | 止血 + 验证 | 恢复确认 |
| 5 | 用 `assets/report-template.html` 出报告 | HTML 报告 |

## 症状路由表

| 症状 | 优先怀疑的层 | 走哪份 reference |
|---|---|---|
| CPU 飙高 | L1/L3（本机），L4 不会让你 CPU 高 | `01` §A + `02` §Java/C-C++/Go |
| 接口响应慢（全部慢/部分慢） | 全慢看 L1/L3 容量与 GC；**部分慢先按实例分组** | `01` §B |
| 连接超时 connect timeout | LB 后端健康检查摘除 / L1 backlog 满 / 连接池耗尽 / ACL | `01` §C.1 |
| 读超时 read timeout（已连上） | L3 处理慢 / GC / 死锁 / **Nginx proxy_read_timeout(默认60s)** | `01` §C.2 |
| 写超时 / 发送阻塞 | 对端不读 → zero window，看 L2/L3 消费端 | `01` §C.3 |
| **Socket 长连接读取超时** | **LB 链上 idle timeout 最小的那一级**（客户 F5 / Nginx / 云 SLB 逐个问） | `03-long-conn.md` §1 |
| **服务端说没收到报文** | 报文出没出网卡 / 被中间设备丢 / **LB 路由到别的实例** / 粘包 / 幂等去重 | `03-long-conn.md` §2 |
| **只有部分请求失败 / 时好时坏** | **集群里某 1~N 台实例异常**（发布残留、磁盘满、GC、线程打满） | `00` §3 + `01` §B.4 |
| 502 / 504 / 499 | 502=连不上 upstream，504=upstream 超时，499=客户端先撤 | `01` §C.5 |
| 偶发时快时慢、夜间抖 | GC、定时任务、网络重传、邻居节点、LB 探活 | `01` §D |
| 大量 5xx/线程池打满 | 下游慢导致连锁，先查最慢的那一跳 | `01` §B.3 |
| OOM / 内存溢出 / 反复 Full GC | L3 JVM 堆；先看 `jstat` 老年代曲线，再决定是否 dump | `04` §1–§2 |
| 有 heap dump 但不知从哪看 | 直方图第一刀 → 数组指纹 → 关键词 | `04` §4–§6 |
| 服务假死 / 线程堆积 / 响应卡顿 | 线程栈：BLOCKED 找锁持有者，RUNNABLE 找业务热点帧 | `04` §3 |

## 各跳的"层界证据"（缺一个就补一个，这是长期资产）

每一层（**每一个实例**）必须能回答四个数：**入向请求数 / 出向请求数 / 耗时分位(P50/P99) / 错误码分布**，外加 LB 侧两个数：**分发到哪台实例 + 该实例是否被摘除**。

- 某层 **in 有、out 无** → 报文在这层被丢弃（限流、鉴权、报文校验失败、队列溢出）。
- 某层 **in 有、out 慢** → 耗时吃在这一层（看它的下游耗时 vs 自身处理耗时之差）。
- 某层 **in 无、上游 out 有** → 报文在链路上丢了（网络 / LB / 半开连接）。
- **聚合值正常、某实例值异常** → 单实例故障，集群聚合会把它稀释成"偶发"，必须按 `$upstream_addr` 分组看。

## 交付要求

- 默认输出**一份 HTML 排障报告**（单文件、内联 CSS、暗色），模板在 `assets/report-template.html`，占位符见文件顶部注释。
- 报告必须写清：**定界结论（哪一跳）+ 根因 + 证据命令与输出 + 止血动作 + 后续加固项**。没有证据链的根因只能标"疑似"，不许写成结论。
- 命令一律给出**可直接复制的完整命令**，并在危险命令（jmap -dump、gdb attach、kill、重启）前标注风险与前置条件。

## 文件导航

- `references/00-link-model.md` —— **LB 链清单** + 链路分层、层名映射表、集群形态、层界证据、缺口自查
- `references/01-triage-tree.md` —— 开场十问 + 五大症状决策树（CPU / 慢 / 超时 / 抖动 / 打满）+ Nginx 状态码
- `references/02-command-handbook.md` —— 命令速查：OS、网络、**Nginx/LB**、Java、C/C++、Go、DB/MQ/Redis
- `references/03-long-conn.md` —— 长连接专题：LB 链 idle 取最小值、半开连接、粘性路由、抓包比对
- `references/04-jvm-offline.md` —— **离线 JVM 取证**：诊断包判读顺序、GC/线程栈判读、堆直方图信号表、缓冲区指纹、byte[] 关键词取证
- `scripts/collect.sh` —— 一键现场保全（上传服务器执行，输出打包目录）
- `scripts/jvm/jvm_diag.sh` —— JVM 诊断包采集（Linux，轻→重分级，内含 df 检查）
- `scripts/jvm/HprofHistogram.java` —— 大 dump 类直方图（零依赖，流式，>1GB 可用）
- `scripts/jvm/HprofArrays.java` —— 数组长度指纹 + 堆内字符串关键词（char[]/byte[] 双通道）
- `scripts/jvm/scan_bytecode.py` —— 由数组长度反查字节码分配点
- `assets/report-template.html` —— 排障报告模板

## 坑（血泪版）

- **别一上来就 jstack**。CPU 高先看 `top` 的 us/sy/wa/si 分布，sy 高是锁与上下文切换，wa 高是 IO，方向完全不同。
- **jstack 只打一次等于没打**。必须间隔 3~5 秒打 3 次，`-l` 带锁信息；只看 RUNNABLE 且长时间停在同一行的线程。
- **`jmap -dump` 会 STW**，大堆能停几十秒，业务高峰别干。先 `jmap -histo` 看个大概。
- **arthas 只覆盖 JVM**。C/C++ 交易网关和 Go 行情服务得用 perf / gdb / pprof，别拿 arthas 去查非 Java 进程还纳闷没数据。
- **读超时 ≠ 服务端慢**。半开连接下客户端 write 成功、read 永久超时，服务端连 socket 都没有——先 `ss` 双向比对连接是否存在。
- **"服务端没收到" 要先定义"收到"**：是内核收到了（tcpdump 有包）、还是应用收到了（日志有）、还是业务受理了（落库/回执有）。三层结论完全不同。
- **tcpdump 别在业务高峰无过滤抓全量**，`-s0 -w` 几分钟能吃满磁盘。一定带 host/port 过滤和 `-C` 分片。
- **集群里"偶发失败"八成是固定某几台实例**。看聚合成功率会把它稀释掉；按实例分组一比对，往往是某台没发布完、磁盘满了、或者根本没注册上。
- **Nginx 默认 `proxy_read_timeout` 是 60s**，很多"莫名其妙的 504"就是它。改之前先确认后端真的需要那么久，别把超时堆成定时炸弹。
- **LB 之后源 IP 会变**。没配 `X-Forwarded-For` / `proxy_protocol` / TOA 模块的话，服务端日志里全是 LB 的 IP，按客户端 IP 定界直接失效。
- **改 keepalive 只改一处没用**。LB 链的 idle timeout 取最小值：客户端心跳 < Nginx keepalive < 云 SLB idle < 客户 F5 idle，逐级对齐才有效。
