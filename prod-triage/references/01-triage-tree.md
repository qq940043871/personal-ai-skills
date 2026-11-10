# 01 · 开场十问与症状决策树

## 0. 开场十一问（先问，别猜）

用户一句"接口慢"就开始敲命令，是排障界的行为艺术。先拿到这十项：

1. **现象**：慢 / 超时 / 报错 / 无响应 / 数据不对？具体报错原文是什么（错误码 + 文案 + 堆栈首行）？
2. **影响面**：全部用户还是部分？全部接口还是某个？比例多少？QPS 掉了多少？
3. **起始时间**：精确到分钟。是发布/配置变更/流量高峰之后出现的吗？
4. **持续性**：一直慢、间歇慢、还是越来越慢（后者指向泄漏/堆积）？
5. **是否有规律**：固定时间点？固定某几台机器？固定某个客户/机构/地域？
6. **请求标识**：有 traceId / 订单号 / 报文流水号吗？有几个失败样本？
7. **拓扑**：客户端到服务端经过几跳？**每一跳之间有没有 LB（客户硬件 F5 / 自家 Nginx / 云 SLB / K8s Service）**？谁是四层谁是七层？长连接还是短连接？
8. **集群与分布**：Mids / DS / 后端各几个实例？失败是**均匀分布**还是**集中在某些实例 / 某些客户端 IP / 某些地域**？（这一问直接区分"集群单实例故障"和"某条客户链路故障"）
9. **最近变更**：发布、配置、证书、网络策略、**LB 配置与健康检查**、第三方版本、DNS、扩容缩容。
10. **已做过什么**：重启过吗？重启后好了还是照旧？（好了但不持久 → 容量/泄漏；照旧 → 配置/依赖）
11. **能否复现**：预发/灰度能复现吗？能复现就可以随便下钻，不能就得靠现场证据。

拿到 1~5 项就能开始定界，6~10 项边查边补。

---

## §A CPU 飙高

### A.0 先看 CPU 时间分布（30 秒定方向）

```bash
top -b -n1 | head -20          # 看 us sy ni id wa hi si st
mpstat -P ALL 1 5              # 每核是否均衡（单核打满 = 单线程瓶颈/锁）
vmstat 1 10                    # r 列=运行队列，cs 列=上下文切换，b 列=IO阻塞
pidstat -u -p <PID> 1 5        # 确认是进程级还是系统级
```

| 分布 | 含义 | 下一步 |
|---|---|---|
| **us 高** | 业务代码在算 | 抓线程栈 / CPU profile（A.1） |
| **sy 高** | 系统调用、锁竞争、上下文切换频繁 | 看 cs 是否 > 5万/s、`pidstat -w`、锁分析 |
| **wa 高** | 等 IO（磁盘 / 网络） | 看磁盘 `iostat -x 1`、慢 SQL、网络重传 |
| **si/hi 高** | 软中断：网络包量过大 | `cat /proc/softirqs`、`sar -n DEV 1`、是否被打/包风暴 |
| **us 不高但 load 高** | 大量线程在等锁 / D 状态 | `ps -eLo pid,tid,stat` 看 D 状态线程 |

### A.1 JVM（Java 服务）

```bash
top -H -p <PID>                                  # 找占 CPU 的线程 TID
printf '%x\n' <TID>                              # 转 16 进制，得到 nid
jstack -l <PID> > /tmp/incident/jstack-1.txt     # 间隔 5 秒打 3 次
sleep 5; jstack -l <PID> > /tmp/incident/jstack-2.txt
sleep 5; jstack -l <PID> > /tmp/incident/jstack-3.txt
grep -n 'nid=0x<hex>' -A 25 /tmp/incident/jstack-1.txt
```

- 三次栈里**停在同一方法且处于 RUNNABLE** → 热方法/死循环/正则回溯。
- 大量线程 `BLOCKED` 在同一把锁 → 锁竞争（结合 `jstack -l` 的 locked/waiting to lock 链）。
- GC 线程占满 → `jstat -gcutil <PID> 1000 10`，看 FGC 频率与 O 区是否下不来。
- 有 arthas（推荐）：`dashboard` → `thread -n 5` → `thread -b`（找死锁）→ `profiler start/stop`（火焰图）。

```bash
# 无 arthas 时的原生火焰图
# 需要 perf + perf-map-agent，或直接用 async-profiler
./profiler.sh -d 30 -e cpu -f /tmp/incident/flame.html <PID>
```

**常见根因清单**：死循环 / 正则灾难性回溯 / 大对象 JSON 序列化（含大 LIST 导出）/ HashMap 并发成环 / 频繁 TLS 握手 / 同步打日志（尤其是大报文打印）/ XPath 或 OGNL 解析 / 不合理的轮询空转 / 序列化反序列化风暴 / 加密解密（RSA 私钥解密）/ 压缩解压大报文。

### A.2 C / C++ 服务（交易网关、CS 中间件）

```bash
perf top -p <PID> -g                                   # 实时热点函数
perf record -F 99 -g -p <PID> -- sleep 30 && perf report
strace -c -p <PID> -f -o /tmp/incident/strace.stat     # 系统调用占比（谨慎：有开销）
gdb -p <PID> -ex 'thread apply all bt' -ex detach -batch > /tmp/incident/gdb-bt.txt
cat /proc/<PID>/status | egrep 'Threads|VmRSS'
```

- 无符号表时 `perf report` 全是地址 → 需要 `-fno-omit-frame-pointer` 编译或加载符号。
- 怀疑死循环：`gdb -p <PID>` → `info threads` → 多次 `bt` 对比停在哪个帧。
- **注意**：gdb attach 会暂停进程（STW），生产慎用、时间要短，且必须先跟业务确认可停。

### A.3 Go 服务

```bash
curl -s 'http://127.0.0.1:6060/debug/pprof/profile?seconds=30' -o /tmp/incident/cpu.pprof
go tool pprof -top /tmp/incident/cpu.pprof
go tool pprof -http=:0 /tmp/incident/cpu.pprof       # 火焰图
curl -s 'http://127.0.0.1:6060/debug/pprof/goroutine?debug=2' > /tmp/incident/goroutine.txt
curl -s 'http://127.0.0.1:6060/debug/pprof/heap' -o /tmp/incident/heap.pprof
```

- goroutine 数暴涨 → 看 `goroutine?debug=2` 里最多的那个栈，通常是**下游慢导致协程堆积**或**忘记关闭 body/连接**。
- 前提：服务里 import `_ "net/http/pprof"` 并开了端口；没开就只能靠 perf（Go 1.20+ 需 `-buildmode` 保留符号）。

### A.4 CPU 高但进程找不到（系统级）

```bash
sar -n DEV 1 5            # 网卡包量是否异常（小包风暴）
nstat -az | egrep -i 'retrans|rst|syn'   # 重传 / SYN 洪水
cat /proc/softirqs        # NET_RX 是否集中在某一个 CPU（网卡队列绑定问题）
```

---

## §B 接口响应慢

### B.0 先把耗时分段（客户端视角）

```bash
curl -o /dev/null -s -w 'dns=%{time_namelookup} conn=%{time_connect} tls=%{time_appconnect} pre=%{time_pretransfer} ttfb=%{time_starttransfer} total=%{time_total}\n' https://host/api
```

| 段 | 大则说明 |
|---|---|
| `dns` | DNS 慢：本地 resolver / 域名解析链路 |
| `conn` | 建连慢：网络链路 / backlog / 跨地域 |
| `tls` | TLS 握手慢：证书链、RSA 密钥、会话复用没开 |
| `pre` − `tls` | 请求发出慢（大 body 上传） |
| `ttfb` − `pre` | **服务端处理慢** ← 绝大多数慢的接口卡在这 |
| `total` − `ttfb` | 响应下载慢（大报文 / 带宽 / Nagle） |

### B.1 服务端侧再分三段

```
access log 耗时（网关记录）
  = 排队时间（线程队列 / 连接池等待）
  + 应用内部处理（方法级）
  + 下游等待（DB / Redis / MQ / 第三方）
```

- access log 慢、应用内部快 → **排队**（线程池打满、连接池等不到连接）。
- access log 慢、应用内部也慢 → 方法级剖析（arthas `trace`/`profiler`）。
- 应用内部慢集中在一次 DB 调用 → 慢 SQL（见 `02` §DB）。

### B.2 快接口突然变慢 / 慢接口更慢

```bash
# 网关 access log 取耗时列算分位（假设耗时在最后一列，单位秒）
awk '{print $NF}' access.log | sort -n | awk '{a[NR]=$1} END{print "P50="a[int(NR*0.5)], "P95="a[int(NR*0.95)], "P99="a[int(NR*0.99)], "MAX="a[NR]}'
# 按接口维度聚合
awk '{print $7, $NF}' access.log | sort | awk '{c[$1]++; s[$1]+=$2; if($2>m[$1])m[$1]=$2} END{for(i in c) printf "%s n=%d avg=%.3f max=%.3f\n", i, c[i], s[i]/c[i], m[i]}' | sort -k4 -nr | head
```

### B.3 连锁反应：慢会往上传染

下游慢 → 本层线程被占满 → 上游排队 → 上游超时 → 客户端重试 → 流量翻倍 → 雪崩。

**排查顺序必须从最慢的那一跳开始，而不是从报错的那一跳开始。** 报错的往往是受害者。

```bash
# 快速看线程池/连接池是否打满
jstack <PID> | grep -c 'http-nio-.*-exec'                     # 业务线程数
jstack <PID> | grep -A2 'waiting on condition' | grep -c 'Druid'  # 等 DB 连接
grep -c 'Timeout waiting for idle object' app.log              # 连接池耗尽典型报错
```

### B.4 部分慢 / 部分失败 —— 先按实例分组（集群场景必做）

集群里"偶发失败"八成是固定某几台实例。聚合成功率会把它稀释掉，必须拆开看。

```bash
# Nginx 日志按 upstream 实例看成功率（需 $upstream_addr；假设是第 13 列，按实际改）
awk '{print $13, $9}' access.log | sort | awk '{c[$1"|"$2]++} END{for(i in c) print i, c[i]}' | sort -k3 -nr | head -30
# 只看 5xx 落在哪台实例
awk '$9 ~ /^5/ {print $13}' access.log | sort | uniq -c | sort -nr
# 只看慢请求（$upstream_response_time 假设第 15 列）
awk '$15+0 > 1 {print $13, $15}' access.log | sort | uniq -c | sort -nr | head
# 错误是否集中在某些客户端 IP（判断是不是某条客户链路的问题）
awk '$9 ~ /^5/ {print $1}' access.log | sort | uniq -c | sort -nr | head
# K8s：endpoints 与实际 Pod 是否一致（滚动发布期间的经典不一致）
kubectl get endpoints <svc> -o wide; kubectl get pod -l app=<app> -o wide
```

| 分布形态 | 结论 |
|---|---|
| 集中在 1~2 个实例 | **单实例故障**：查版本是否一致、磁盘/inode、GC、线程数、是否被 LB 摘除却还在收流量、本地缓存是否为空 |
| 均匀分布在所有实例 | 依赖或容量问题（下游慢 / 连接池 / GC / 限流），不是单点 |
| 集中在少数客户端 IP / 机构 / 地域 | **客户侧链路问题**：专线、客户硬件 LB、地域 DNS、客户端版本 |
| 与具体接口或参数相关 | 数据倾斜或特定慢路径（大客户大查询、某字段触发全表扫） |
| 随实例重启消失、运行一段时间复发 | 泄漏（连接 / 内存 / 句柄 / 线程） |

---

## §C 超时（必须分清是哪一种）

### C.1 connect timeout（连不上）

判据：报错是 `connect timed out` / `Connection refused` / `No route to host` / `SYN_SENT 堆积`。

```bash
ss -lnt                                   # 看 Recv-Q / Send-Q，Send-Q 满 = backlog 打满
netstat -s | egrep -i 'listen|overflow|drop|SYNs'   # "times the listen queue of a socket overflowed" 是关键
ss -s                                     # 总连接数，是否接近 ulimit / 端口上限
telnet <host> <port>                      # 通不通
nc -zv -w 2 <host> <port>
cat /proc/sys/net/ipv4/ip_local_port_range   # 客户端侧端口是否耗尽
```

根因候选：backlog 太小（`somaxconn` / `tcp_max_syn_backlog`）、服务没起来、LB 后端健康检查失败摘除、防火墙/安全组、连接池配置过小、DNS 解析到错 IP、端口耗尽（短连接高频场景）。

### C.2 read timeout（连上了，等不到响应）

判据：连接成功，等了 N 秒后超时；服务端可能处理很慢，也可能根本没收到。

```bash
ss -tnpi '( dport = :<port> )'            # 看 rto / retrans / cwnd / lastrcv
netstat -s | egrep -i 'retransmit'
tcpdump -i any -nn -s0 host <peer> and port <port> -w /tmp/incident/rt.pcap
```

- **服务端日志里根本没有这条请求** → 不是慢，是**没到**：转 `03-long-conn.md`（半开连接 / 中间设备丢包）。
- 服务端有日志但耗时长 → 走 §B。
- 服务端很快返回但客户端仍超时 → 响应在回程丢了 / 报文太大被中间设备丢 / 客户端读 buffer 逻辑 bug。

### C.3 write timeout / 发送阻塞

判据：写不进去、socket 缓冲区满、或对端不读。

```bash
ss -tnpi                                   # 看 snd_wnd / rcv_space，rcv_space=0 即对端零窗口
nstat -az | egrep -i 'ZeroWindow|zero window'
ss -tnp | grep <peer>                      # 看 Send-Q 是否持续堆积
```

根因：对端消费线程卡死/GC、对端 backlog 应用缓冲区满、Nagle + 延迟 ACK 组合放大延迟、报文过大被分片丢包（MTU/DF）。

### C.4 LB 层检查清单（每一跳之间都要过一遍，别只查自家 Nginx）

```bash
# ① 后端实例有没有被健康检查摘除
grep -E 'no live upstreams|upstream timed out|Connection refused|connect\(\) failed' /var/log/nginx/error.log | tail -30
kubectl get endpoints <svc> -o wide          # endpoints 是否少了某台
curl -s http://LB/status                      # Nginx stub_status / HAProxy stats

# ② 源 IP 有没有被改写（SNAT / XFF）
#    服务端日志里如果源 IP 全是同一个内网地址 → 就是 LB，按客户端 IP 定界直接失效
awk '{print $1}' access.log | sort | uniq -c | sort -nr | head
grep -o 'X-Forwarded-For: [^,]*' access.log | head

# ③ Nginx 超时实际配置（默认值最容易坑人：proxy_read_timeout 默认 60s）
nginx -T | grep -E 'proxy_(connect|send|read)_timeout|keepalive_timeout|keepalive_requests|proxy_http_version|max_fails|fail_timeout'
```

**实测 idle timeout（比查文档可靠）**：文档写的值经常和实际生效的不一致（尤其跨了客户的硬件 LB）。做法：建一条长连接，静默 N 秒后发一个字节，二分法找断连点。

```bash
# 简易探测：连接后静默 N 秒再发数据，看是否超时（N 从 60 起，每次翻倍）
python3 - <<'PY'
import socket, time, sys
host, port, idle = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
s = socket.create_connection((host, port), 5)
s.settimeout(30)
time.sleep(idle)
try:
    s.sendall(b'\x00')          # 换成真实心跳报文
    print(f'idle={idle}s -> 仍可写，等待响应...')
    print('收到:', s.recv(1024) or b'(空，连接已被对端关闭)')
except Exception as e:
    print(f'idle={idle}s -> 失败: {type(e).__name__}: {e}')
PY
```

### C.5 Nginx / LB 状态码速查

| 状态码 | 含义 | 下一步 |
|---|---|---|
| **499**（Nginx 私有） | **客户端先撤了**（客户端超时比服务端短） | 对齐超时配置；查客户端为什么等不及 |
| **502** Bad Gateway | 连不上 upstream：进程挂了 / 端口不通 / backlog 满 / 全被摘除 | `error.log` 找 `no live upstreams`、`Connection refused` |
| **504** Gateway Timeout | upstream 处理超时 | `error.log` 找 `upstream timed out` → 看是 `proxy_read_timeout`(默认60s) 还是后端真慢 |
| **503** | 无可用 upstream / 主动熔断 / 限流 | 查熔断与限流配置、健康检查结果 |
| **500** | 后端应用异常 | 看应用日志堆栈 |
| **408** | 请求头/请求体读取超时 | `client_header_timeout` / `client_body_timeout` |

```bash
grep -o 'HTTP/1.1" [45][0-9][0-9]' access.log | sort | uniq -c | sort -nr
grep -E 'upstream timed out|upstream prematurely closed|no live upstreams' /var/log/nginx/error.log | wc -l
```

> **499 是最容易被误读的一个**：它不代表服务端有问题，只代表客户端先跑了。看到大量 499，先问"客户端超时设的多少"，而不是去优化后端。

---

## §D 抖动 / 偶发 / 时快时慢

| 特征 | 优先怀疑 |
|---|---|
| 固定时间点（整点、每天 2 点） | 定时任务、日志切割、备份、对账批处理、第三方维护窗口 |
| 周期性几十秒到几分钟一次 | GC（Full GC）、缓存集中过期、连接池重建、心跳批量重连 |
| 只有个别机器慢 | 单机问题：磁盘、网卡、CPU steal（云主机超卖）、该机上有大查询 |
| 只有个别客户/机构慢 | 该租户数据量倾斜、专线、限流规则、证书 |
| 发布后偶发 | 连接池/线程池参数变了、新代码有概率性慢路径、灰度比例 |
| 客户端侧慢但服务端快 | 弱网、DNS、TLS、客户端线程池、移动端休眠掐断心跳 |

```bash
# GC 相关性
jstat -gcutil <PID> 1000 60 | awk '{print $1, $8, $9, $10}'    # FGC/YGC 与 O 区
grep -c 'Full GC\|GC pause' gc.log
# 云主机超卖
top   # 看 %st（steal time）
# 磁盘
iostat -x 1 5        # await / %util
```

---

## §E 打满类（线程池 / 连接池 / 队列 / 磁盘 / inode）

```bash
# 文件句柄
ls /proc/<PID>/fd | wc -l; cat /proc/<PID>/limits | grep 'open files'
# 磁盘
df -h; df -i                                # 空间与 inode 都要看
# 内存与 OOM
dmesg -T | tail -50                         # "Out of memory: Kill process" 铁证
free -m; cat /proc/meminfo | egrep 'Slab|Buffers|Cached'
# JVM
jmap -histo <PID> | head -30                # 对象数量 Top（比 dump 轻量）
jstat -gcutil <PID> 1000 10
# MQ 堆积
# Kafka
kafka-consumer-groups.sh --bootstrap-server x --describe --group g
# RocketMQ：看控制台 Topic 的 diff
```

**判断"堆积 vs 泄漏"**：堆内存/连接数随时间单调上升不回落 → 泄漏；随流量涨落、高峰后回落 → 容量不足。

---

## 收尾：结论怎么写

- **定界结论**：故障发生在 `L1→L2` 这一跳（证据：L1 out 计数 = N，L2 in 计数 = 0，同一 traceId）。
- **根因**：一句话 + 机制解释（为什么这个根因会导致这个现象）。
- **证据**：命令 + 关键输出片段（不要贴全量日志）。
- **未排除项**：写清楚排除了什么、凭什么排除的。
- **加固项**：观测补齐、参数调整、超时对齐、重试与幂等、压测验证。
