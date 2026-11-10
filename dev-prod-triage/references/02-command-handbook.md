# 02 · 命令速查手册（SSH 到服务器上直接抄）

> 前提：生产服务器 Linux。命令默认以 root 或 sudo 运行。`$PID` `$PORT` `$PEER` 自行替换。
> 标记 ⚠️ 的命令有副作用（暂停进程 / 触发 STW / 高 IO），高峰慎跑，跑前知会业务方。

## 一、系统级 60 秒体检

```bash
uptime; top -b -n1 | head -20
mpstat -P ALL 1 3; vmstat 1 5; iostat -x 1 3
free -m; df -h; df -i
dmesg -T | tail -30                      # OOM / 网卡 down / 磁盘错误
sar -n DEV 1 5                           # 网卡流量与包量
pidstat -u -p <PID> 1 5                  # 进程 CPU
pidstat -d -p <PID> 1 5                  # 进程 IO
pidstat -w -p <PID> 1 5                  # 上下文切换（sy 高时看）
cat /proc/<PID>/status | egrep 'Threads|VmRSS|VmSwap'
ls /proc/<PID>/fd | wc -l                # 句柄数
cat /proc/<PID>/limits | grep 'open files'
```

## 二、网络与连接

```bash
ss -s                                     # 连接总数概览
ss -lnt                                   # 监听端口与 Recv-Q/Send-Q（Send-Q 满=backlog 打满）
ss -tnp | grep <PORT>                     # 某端口所有连接
ss -tn state established | wc -l
ss -tnpi '( dport = :<PORT> or sport = :<PORT> )'   # rto / retrans / cwnd / lastrcv（重点）
ss -tnp | awk '{print $1}' | sort | uniq -c         # 状态分布
netstat -s | egrep -i 'retrans|listen|overflow|pruned|reset|bad'
nstat -az | egrep -i 'retrans|zero|window|rst|syn'
conntrack -L | wc -l                      # 有 NAT/防火墙时看连接跟踪表
cat /proc/sys/net/ipv4/ip_local_port_range
cat /proc/sys/net/core/somaxconn
cat /proc/sys/net/ipv4/tcp_keepalive_time   # 默认 7200s，长连接必改
```

**抓包**（一定要带过滤 + 分片，别抓全量）

```bash
tcpdump -i any -nn -s0 -C 100 -W 5 -w /tmp/incident/cap.pcap host <PEER> and port <PORT>
tcpdump -i any -nn 'tcp[tcpflags] & (tcp-rst|tcp-fin) != 0' and host <PEER>      # 只看断连
tcpdump -i any -nn -A -s0 host <PEER> and port <PORT>                            # 看明文报文内容
# 离线分析
tcpdump -nn -r cap.pcap | head -50
tshark -r cap.pcap -q -z io,stat,1                                              # 每秒包量
tshark -r cap.pcap -Y 'tcp.analysis.retransmission || tcp.analysis.flags'        # 重传/异常
```

**连通性与路径**

```bash
nc -zv -w 2 <HOST> <PORT>
curl -o /dev/null -s -w 'dns=%{time_namelookup} conn=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://<HOST>/<PATH>
traceroute -T -p <PORT> <HOST>            # 四层路径
mtr --tcp --port <PORT> <HOST>
ping -s 1472 -M do <PEER>                 # MTU 探测（不通说明 DF 被丢，调小继续试）
openssl s_client -connect <HOST>:<PORT> -servername <HOST> </dev/null 2>/dev/null | openssl x509 -noout -dates   # 证书过期检查
dig <DOMAIN> +short; nslookup <DOMAIN>
```

### 2.5 Nginx / 负载均衡（LB 链每一级都要查）

```bash
# 实际生效的完整配置（含所有 include，-T 比 grep 配置文件可靠）
nginx -T | grep -E 'proxy_(connect|send|read)_timeout|keepalive_timeout|keepalive_requests|proxy_http_version|max_fails|fail_timeout|proxy_set_header|upstream|server .*:'
nginx -T | grep -A8 -E '^\s*upstream'
# 连接与请求速率
curl -s http://127.0.0.1/nginx_status      # stub_status：Active/Reading/Writing/Waiting
ss -tn '( sport = :80 or sport = :443 )' | wc -l
# 错误日志（LB 层的关键证据都在这）
grep -E 'upstream timed out|upstream prematurely closed|no live upstreams|Connection refused|connect\(\) failed|no live upstream' /var/log/nginx/error.log | tail -40
grep -E 'upstream timed out' /var/log/nginx/error.log | grep -oP 'upstream: "\S+"' | sort | uniq -c | sort -nr   # 超时集中在哪台后端
# HAProxy
echo 'show stat' | socat stdio /var/run/haproxy.sock | awk -F, '{print $1,$2,$18,$37,$38}'   # 含 check 状态与会话数
```

**access log 必须有的字段**（没有 `$upstream_addr` 就没法做实例级定界，先补日志格式）：

```
log_format main '$remote_addr | $http_x_forwarded_for | $request | $status | $request_time | '
                '$upstream_addr | $upstream_response_time | $upstream_status | $request_id';
```
- `$request_time` vs `$upstream_response_time` 的差值 = **Nginx 自身排队/握手开销**，差值大说明 upstream 连接池不够或建连慢。
- `$upstream_addr` 出现多个地址（逗号分隔）= 发生了重试/故障转移；出现 `-` = 根本没转发到后端。

**硬件 LB（F5/A10）拿不到配置时的替代取证**

```bash
# 抓包看 TTL 判断是否经过七层代理（代理会重新发包，TTL 被重置）
tcpdump -i any -nn -v host <PEER> | grep -oP 'ttl \d+' | sort | uniq -c
# 看 RST 是谁发的（对比 MAC 或 TTL 可区分是 LB 还是真实服务端）
tcpdump -i any -nn -e 'tcp[tcpflags] & tcp-rst != 0'
# 源 IP 是否被 SNAT：服务端日志里的客户端 IP 是否全是同一个内网段
awk '{print $1}' access.log | sort -u | head
```

**K8s / 服务网格**

```bash
kubectl get endpoints <svc> -o wide; kubectl describe svc <svc>
kubectl get pod -l app=<app> -o wide --show-labels     # 看版本标签是否一致（发布残留）
kubectl top pod -l app=<app>                           # 单实例 CPU/内存异常
kubectl logs <pod> --since=10m --timestamps
istioctl proxy-config cluster <pod> -o json | grep -i timeout    # sidecar 超时
```

## 三、Java（JVM）

```bash
jps -lv                                    # 找 PID
jstack -l <PID> > /tmp/incident/jstack-$(date +%H%M%S).txt        # 打 3 次，间隔 5s
jstat -gcutil <PID> 1000 10                # GC 概览（O 区下不来 + FGC 频繁 = 泄漏/容量）
jstat -gccapacity <PID>                    # 各区容量
jmap -histo <PID> | head -30               # 轻量对象分布
jmap -histo:live <PID> | head -30          # ⚠️ 会触发一次 Full GC
jmap -dump:live,format=b,file=/tmp/incident/heap.hprof <PID>      # ⚠️ STW，大堆停几十秒
jinfo -flags <PID>                         # 实际生效的 JVM 参数
jcmd <PID> VM.native_memory summary        # NMT，看堆外内存（直接内存泄漏）
jcmd <PID> Thread.print > /tmp/incident/tp.txt
jcmd <PID> GC.heap_info
```

**arthas（有就优先用，attach 一次全都有）**

```bash
java -jar arthas-boot.jar
dashboard                      # 总览：线程/内存/GC/TPS
thread -n 5                    # CPU Top5 线程 + 栈
thread -b                      # 找阻塞其他线程的"元凶锁"
thread --state BLOCKED         # 所有阻塞线程
trace <class> <method> '#cost>200' -n 5        # 方法级耗时（>200ms 才输出）
watch <class> <method> '{params, returnObj}' -x 3
profiler start / profiler stop --format html   # 火焰图
heapdump /tmp/incident/heap.hprof              # ⚠️ STW
```

**常见报错 → 根因速查**

| 日志关键字 | 含义 |
|---|---|
| `java.net.SocketTimeoutException: Read timed out` | 已连上，等响应超时 → 看服务端处理或半开连接 |
| `java.net.ConnectException: Connection refused` | 端口没人监听 / 进程挂了 |
| `java.net.SocketException: Connection reset` | 对端发 RST：进程重启、LB 摘除、连接被中间设备清 |
| `java.net.SocketException: Broken pipe` | 往已关闭的连接写 |
| `Timeout waiting for idle object` | 连接池耗尽（DB/HTTP），不是 DB 慢就是池太小或漏关闭 |
| `Too many open files` | 句柄泄漏，查 fd 数与连接关闭逻辑 |
| `OutOfMemoryError: unable to create new native thread` | 线程数打爆，查线程栈与 ulimit |
| `OutOfMemoryError: Direct buffer memory` | 堆外/直接内存泄漏（Netty 常见），配 `-XX:MaxDirectMemorySize` |

## 四、C / C++（交易网关、CS 中间件）

```bash
perf top -p <PID> -g
perf record -F 99 -g -p <PID> -- sleep 30; perf report
gdb -p <PID> -ex 'thread apply all bt' -ex 'detach' -batch > /tmp/incident/gdb-bt.txt   # ⚠️ 会暂停进程
strace -tt -T -p <PID> -f -o /tmp/incident/strace.log      # ⚠️ 开销大，短跑
pstack <PID>                                                # 轻量线程栈
pmap -x <PID> | tail -5                                     # 内存映射与总量
cat /proc/<PID>/smaps_rollup                                # 内存汇总
valgrind --tool=memcheck ...                                # 只在测试环境，生产别跑
```

内存泄漏定位：`pmap` 定时采样对比增长区域；有 jemalloc/tcmalloc 时用其 heap profiler：

```bash
# jemalloc
MALLOC_CONF=prof:true,prof_prefix:/tmp/incident/jeprof <cmd>
jeprof --show_bytes <binary> /tmp/incident/jeprof.*
```

## 五、Go

```bash
curl -s 'http://127.0.0.1:6060/debug/pprof/profile?seconds=30' -o /tmp/incident/cpu.pprof
curl -s 'http://127.0.0.1:6060/debug/pprof/heap' -o /tmp/incident/heap.pprof
curl -s 'http://127.0.0.1:6060/debug/pprof/goroutine?debug=2' > /tmp/incident/goroutine.txt
curl -s 'http://127.0.0.1:6060/debug/pprof/block' -o /tmp/incident/block.pprof
curl -s 'http://127.0.0.1:6060/debug/pprof/mutex' -o /tmp/incident/mutex.pprof
go tool pprof -top /tmp/incident/cpu.pprof
go tool pprof -http=:8080 /tmp/incident/cpu.pprof
go tool pprof -base=old.pprof new.pprof     # 对比两次采样
GODEBUG=gctrace=1 <cmd>                     # 临时开 GC 日志（需重启）
```

## 六、DB / Redis / MQ

```bash
# MySQL
mysql -e "SHOW FULL PROCESSLIST" | egrep -v 'Sleep' | head -40
mysql -e "SELECT * FROM information_schema.INNODB_TRX\G"          # 长事务/锁等待
mysql -e "SELECT * FROM sys.innodb_lock_waits\G" 2>/dev/null
mysql -e "SHOW ENGINE INNODB STATUS\G" | sed -n '/LATEST DETECTED DEADLOCK/,/------------/p'
mysql -e "SHOW GLOBAL STATUS LIKE 'Threads_%'; SHOW GLOBAL STATUS LIKE 'Max_used_connections';"
# 慢日志分析
mysqldumpslow -s t -t 20 /var/log/mysql/slow.log
pt-query-digest /var/log/mysql/slow.log > /tmp/incident/slow-digest.txt

# Redis
redis-cli info clients | egrep 'connected_clients|blocked_clients'
redis-cli info stats | egrep 'instantaneous_ops_per_sec|rejected_connections|keyspace'
redis-cli --latency-history -i 5
redis-cli slowlog get 20
redis-cli info commandstats | sort -t= -k2 -nr | head
redis-cli --bigkeys                                              # ⚠️ 大 key 扫描有开销

# Kafka
kafka-consumer-groups.sh --bootstrap-server <bs> --describe --group <g>    # LAG 是关键
kafka-topics.sh --bootstrap-server <bs> --describe --topic <t>
```

**慢 SQL 三板斧**：`EXPLAIN` 看有没有走索引 / `rows` 是否爆炸 / `Extra` 有没有 `Using filesort; Using temporary`。

## 七、日志检索（没有 APM 时的主力）

```bash
# 按 traceId 串全链路（各层日志路径替换）
grep -rn '<TRACE_ID>' /data/logs/mids/ /data/logs/ds/ /data/logs/app/ | sort
# 时间窗内的错误分布
awk '$0 >= "2026-09-30 14:00" && $0 <= "2026-09-30 14:30"' app.log | grep -oP 'ERROR|TIMEOUT|SocketTimeout' | sort | uniq -c
# 耗时 Top（假设日志里有 cost=xxx）
grep -oP 'cost=\d+' app.log | sort -t= -k2 -nr | head -20
# 某分钟各接口的错误数
grep '2026-09-30 14:05' access.log | awk '{print $7, $9}' | sort | uniq -c | sort -nr | head
# 长连接断连统计
grep -c 'Connection reset by peer' app.log
grep -oP 'clientId=\S+' app.log | sort | uniq -c | sort -nr | head      # 是否集中在少数客户端
```

## 八、危险命令清单（跑前必须确认）

| 命令 | 风险 | 前置条件 |
|---|---|---|
| `jmap -dump:live` | STW，大堆停几十秒 | 已摘流量或业务低峰 |
| `jmap -histo:live` | 触发 Full GC | 同上 |
| `gdb -p` | 暂停进程 | 已摘流量，attach 时间 < 10s |
| `strace -p` | 性能下降 10 倍+ | 只跑几秒 |
| `tcpdump -s0` 无过滤 | 磁盘打满 | 必须带 host/port + `-C` 分片 |
| `kill -9` | 现场全丢 | 先 `jstack`/`pstack` 保全 |
| 重启 / 回滚 | 现场全丢 | 先跑 `scripts/collect.sh` |
| `redis-cli --bigkeys` / `KEYS *` | Redis 卡顿 | 低峰或改用 SCAN |
