# 03 · Socket 长连接专题（读超时 / 半开连接 / 服务端没收到报文）

长连接问题的共同特征：**客户端和服务端对同一件事的描述互相矛盾**。一个说"发了我等不到"，另一个说"我压根没见着"。这种时候不要争论，**用 seq 号和连接表说话**。

## 0. 先把"收到"定义清楚（不然永远扯皮）

| 层级 | 判定依据 | 谁负责 |
|---|---|---|
| ① 内核收到了 | 服务端 `tcpdump` 能看到该报文的 seq | 网络 |
| ② 应用读到了 | 应用日志有该流水号 / 解码后打印 | 接入层（Mids/DS） |
| ③ 业务受理了 | 落库 / 有回执 / 有下游调用记录 | 后端 |

**"服务端说没收到" 必须问清是哪一层。** ② 有 ③ 没有，通常是报文校验失败或幂等去重；① 有 ② 没有，是应用层解析/线程/队列问题；① 都没有，才是真的在路上丢了。

---

## 1. 现象 A：客户端 read timeout，服务端说没这条连接 —— 半开连接（最常见）

**机制**：LB / 防火墙 / NAT 网关有 **idle timeout**（常见 60s、90s、350s、900s）。连接空闲超过该值，中间设备**静默删除会话表项**，且**不通知两端**。于是：
- 客户端仍认为连接 ESTABLISHED，`write()` 成功（数据进了内核发送缓冲区，甚至被中间设备丢弃）；
- 服务端对应的 socket 早就不存在了，或者中间设备直接丢包 / 回 RST；
- 客户端 `read()` 永久阻塞 → **Read timed out**；
- 服务端日志干净——它真的没收到。

**TCP keepalive 救不了你**：Linux 默认 `tcp_keepalive_time=7200s`（2 小时），远大于 LB 的 idle timeout。连接早死了，keepalive 还没开始探。

### LB 链：idle timeout 取**最小值**（改一处没用）

一条长连接通常要穿过好几级设备：

```
客户端 ──① 客户硬件 F5/A10 ──② 云 SLB/CLB ──③ 自家 Nginx ──④ Mids 实例
```

**每一级都有自己的空闲计时器，且各自独立计时。** 谁先到点谁先删会话表项，所以实际生效的 idle timeout = **链上的最小值**。你在 Nginx 上把 `keepalive_timeout` 从 75s 调到 3600s，客户 F5 上的 300s 照样掐掉你——这就是"明明改了配置没效果"的标准答案。

对齐规则（逐级递增，且不靠猜、靠实测）：

```
客户端心跳周期  <  Nginx keepalive_timeout  <  云 LB idle  <  客户硬件 LB idle
   60s                    120s                   600s              900s（示例）
```

| 级 | 参数在哪里看 | 拿不到怎么办 |
|---|---|---|
| 客户端 | SDK 心跳配置 | 抓包看心跳报文间隔（最直接） |
| 客户硬件 F5/A10 | 客户网络组；TCP Profile 的 idle timeout | **实测**：静默探测二分法（见 `01` §C.4） |
| 云 SLB/CLB | 控制台监听器/连接空闲超时 | 云厂商文档默认值 + 实测 |
| 自家 Nginx | `nginx -T \| grep keepalive_timeout` | — |

**七层代理会把一条连接拆成两条**：客户端↔LB 是连接 A，LB↔后端是连接 B（upstream keepalive 池）。这意味着：
- `ss` 双向比对时，你在服务端看到的连接**不是客户端那条**，不要因为"服务端有连接"就排除半开；
- 后端连接 B 可能被 LB 复用给别的客户端（如 F5 OneConnect），出现"会话串了"的诡异现象；
- 上游必须配 `proxy_http_version 1.1` + `proxy_set_header Connection ""`，否则后端连接每次请求重建，长连接名存实亡。

**粘性（sticky）是长连接的命门**：会话保持没开或开了但按源 IP 哈希，而客户端 IP 经 SNAT 后是同一个 → 所有连接都被哈希到同一台实例（负载倾斜 + 该实例一挂全挂）。开了 cookie 粘性但对长连接（非 HTTP）无效 → 请求落到没有会话状态的实例上，表现为"服务端说没这个会话"。

### 判据（按这个顺序取证）

```bash
# 1) 客户端侧：连接还在吗？
ss -tnpi '( dport = :<PORT> )' | grep <PEER_IP>
#    ESTAB 且 retrans 高、或 lastrcv 是很久以前 → 高度可疑

# 2) 服务端侧：同一条四元组在不在？（这是决定性证据）
ss -tnp | grep <CLIENT_IP>
#    客户端有 ESTAB，服务端查无此连接 → 半开连接，实锤

# 3) 两端同时抓包（30~60 秒，覆盖一次复现）
tcpdump -i any -nn -s0 -C 50 -W 3 -w /tmp/incident/cli.pcap host <SERVER_IP> and port <PORT>   # 客户端
tcpdump -i any -nn -s0 -C 50 -W 3 -w /tmp/incident/srv.pcap host <CLIENT_IP> and port <PORT>   # 服务端
#   客户端 pcap 里有 [P.] 推送、服务端 pcap 里完全没有对应 seq → 中间丢了

# 4) 看有没有 RST / FIN
tshark -r cli.pcap -Y 'tcp.flags.reset==1 || tcp.flags.fin==1'
#   客户端收到 RST → 中间设备或服务端主动拒绝；什么都没有 → 纯静默丢弃
```

### 解法（按优先级）

1. **应用层心跳周期 < LB idle timeout / 2**（idle=350s 则心跳 ≤ 120s，推荐 60s）。这是唯一根治手段。
2. **开启并调小 TCP keepalive**（双保险，不能替代心跳）：
   ```bash
   sysctl -w net.ipv4.tcp_keepalive_time=60
   sysctl -w net.ipv4.tcp_keepalive_intvl=15
   sysctl -w net.ipv4.tcp_keepalive_probes=3
   # 应用层也要设 SO_KEEPALIVE（Java: new Socket() 后 setKeepAlive(true) 或 Netty 的 ChildOption）
   ```
3. **写超时 + 失败重连**：客户端不能只设 read timeout，必须有 `soTimeout` + 发送失败即触发重建连接 + 业务层重试幂等。
4. **空闲连接主动回收**：客户端或服务端在空闲超过阈值时主动 FIN 关闭并重建，别等中间设备下手。
5. **调大中间设备 idle timeout**（能改的话），并让 LB idle > 服务端 idle > 客户端心跳 × 2。

---

## 2. 现象 B：客户端 write 成功，服务端坚称没收到

### B.1 先破一个错觉

`write()` 返回正数 **只代表数据进了本机内核发送缓冲区**，不代表对端收到，甚至不代表数据出了网卡。所以"我发送成功了"不是证据。

### B.2 两端抓包对账（唯一硬证据）

```bash
# 两端对齐时间后同时抓
tcpdump -i any -nn -s0 -w /tmp/incident/cli.pcap host <PEER> and port <PORT>
tshark -r cli.pcap -T fields -e frame.number -e frame.time_epoch -e ip.src -e tcp.seq -e tcp.len -e tcp.flags
```

| 客户端 pcap | 服务端 pcap | 结论 |
|---|---|---|
| 有报文（含正确 seq） | 有同样 seq | **到了**，问题在应用层（解析/线程/队列/幂等），转 §B.4 |
| 有报文 | 无 | **链路上丢了** → 中间设备（LB/防火墙/DPI/NAT）、MTU/DF 丢大包、路由不对称 |
| 无报文 | 无 | **客户端根本没发出去** → 应用层 bug：send buffer 满、阻塞在非阻塞写、序列化异常被吞、发到了错误的连接/错误的后端实例 |
| 有 SYN 无 SYN-ACK | 无 | 建连就被拦 → 安全组/ACL/对端 backlog 满 |

### B.3 链路丢包的常见物理原因

- **报文过大 + DF 置位**：`ping -s 1472 -M do <PEER>` 不通 → MTU 有问题，调小 MSS（`iptables --clamp-mss-to-pmtu` 或调网卡 MTU）。
- **中间设备 DPI/IPS 丢包**：报文内容命中特征（如明文敏感字段、超大报文、非标准端口跑 HTTP），被静默丢。
- **NAT 会话表满 / conntrack 满**：`conntrack -L | wc -l`、`dmesg | grep 'conntrack table full'`。
- **集群里路由到了别的实例**：长连接的会话状态在实例 A 上，但这一跳被 LB 分发到了实例 B → A 说没收到，B 收到了但不认这个会话。**必须按实例维度查，不能只 grep 一台机器的日志。**
- **粘性（sticky）失效**：HTTP 用 cookie 粘性、四层用源 IP 哈希。客户端经 SNAT 后 IP 相同 → 全被哈希到同一台（倾斜 + 单点）；长连接非 HTTP 场景 cookie 粘性根本不生效。
- **LB 连接复用（F5 OneConnect / upstream keepalive）**：多个客户端连接复用同一条后端连接，报文能到但会话上下文串了，表现为偶发的"收到了但不认识"。查法：对比报文中携带的会话号与后端实例上的会话归属。
- **双网卡 / 策略路由**：回程走了另一条路，服务端回的包客户端收不到。

### B.4 到了但应用层"当没收到"

```bash
# 网关/接入层的丢弃往往有日志，只是没打到业务日志里
grep -n 'decode\|invalid\|length\|checksum\|reject\|drop' /data/logs/mids/mids.log | tail -50
# 限流与鉴权
grep -c 'rate limit\|forbidden\|token expired' /data/logs/mids/mids.log
```

- **粘包/拆包**：长连接流式传输必须自己定界（长度字段 / 分隔符）。没处理好会表现为"部分报文丢失"或"解析失败被丢弃"。
- **长度字段与编码**：长度字段按字节算还是按字符算？GBK 与 UTF-8 下中文长度差 1.5 倍——经典事故源。
- **字符集**：报文头用 ISO-8859-1、报文体用 GBK，服务端按 UTF-8 解 → 解码异常被 catch 掉，日志只留一行 warn。
- **幂等去重误杀**：客户端重试时复用了同一流水号，服务端判定重复直接丢弃且**不回执** → 表现为"服务端没收到"。查去重表/去重缓存：
  ```sql
  SELECT * FROM msg_dedup WHERE msg_id='<流水号>';   -- 有记录 = 收过但被去重
  ```
- **报文校验失败静默丢**：签名、MAC、证书序列号、时间戳窗口（服务端时间漂移导致报文"过期"被丢）。**先看两端机器时间是否一致**：`date; ntpq -p`。

---

## 3. 现象 C：偶发断连（RST / FIN）

```bash
tcpdump -i any -nn 'tcp[tcpflags] & (tcp-rst|tcp-fin) != 0' and host <PEER>
tshark -r cap.pcap -Y 'tcp.flags.reset==1' -T fields -e frame.time -e ip.src -e tcp.seq
```

| 谁发的 | 含义 | 查什么 |
|---|---|---|
| 服务端发 RST | 进程崩溃/重启、收到不属于自己的连接、缓冲区里有未读数据就 close | `dmesg`、进程 uptime、OOM |
| 客户端发 RST | 客户端读超时后强关、SDK 主动断 | 客户端日志 |
| LB 发 RST | 健康检查失败摘除、idle 回收 | LB 日志与健康检查配置 |
| 正常 FIN | 谁先关？关的时机是否符合预期 | 应用层关闭逻辑 |

```bash
dmesg -T | egrep -i 'oom|kill|segfault'        # 进程被杀的铁证
ps -o lstart,etime,cmd -p <PID>                # 进程启动时间（判断是否刚重启）
grep -c 'Connection reset by peer' app.log
```

---

## 4. 现象 D：连接数暴涨 / 泄漏

```bash
ss -tn state established '( sport = :<PORT> )' | wc -l
ss -tnp | awk '{print $NF}' | sort | uniq -c | sort -nr | head     # 按进程统计
ss -tan | awk '{print $1}' | sort | uniq -c                        # 状态分布（TIME_WAIT/CLOSE_WAIT）
```

- **大量 CLOSE_WAIT** → 服务端（被动关闭方）没调 close，应用 bug，句柄迟早耗尽。
- **大量 TIME_WAIT** → 短连接高频，考虑长连接化或 `tcp_tw_reuse`（注意与 NAT 环境的兼容性）。
- 连接数随时间单调增长 → 客户端重连风暴（所有客户端同时重连会打爆服务端）：**重连必须有随机退避（jitter）**。

---

## 5. 长连接健康检查清单（贴到运维 wiki）

| 项 | 推荐值 / 要求 | 现状 |
|---|---|---|
| **LB 链 idle timeout 实测值** | **每级实测并记录（客户端/客户F5/云LB/Nginx 四行）** | |
| 客户端心跳周期 | ≤ **链上最小 idle** / 2（最小 300s → 心跳 ≤ 120s） | |
| 服务端 idle 检测 | 心跳周期 × 3 未收到则主动关闭 | |
| TCP keepalive（内核） | time=60 intvl=15 probes=3 | |
| SO_KEEPALIVE（应用层） | 必须显式开启 | |
| **粘性路由（sticky）** | **长连接必须开启且验证有效**（四层看源 IP 哈希是否被 SNAT 破坏） | |
| **七层 upstream keepalive** | `proxy_http_version 1.1` + `Connection ""` + `keepalive N` | |
| **源 IP 透传** | X-Forwarded-For / proxy_protocol / TOA，保证日志里是真实客户端 IP | |
| read timeout（soTimeout） | 明确设置，**不允许无限等待** | |
| connect timeout | 与 read timeout 分开配置（如 3s / 30s） | |
| 重连策略 | 指数退避 + 随机 jitter，禁止全量同时重连 | |
| 重试幂等 | 重试保留原流水号，服务端去重且**必须回执** | |
| LB / 防火墙 idle timeout | 明确记录数值，大于服务端 idle 检测 | |
| 粘性路由（sticky） | 长连接必须保证同一连接路由到同一后端 | |
| 两端机器时间 | NTP 同步，偏移 < 1s | |
| 连接数指标 | 连接数、重连次数、心跳成功率、半开连接数 有面板有告警 | |

## 6. 排查 SOP（一页纸，照着走）

1. 拿**失败样本的流水号 + 精确时间戳**（至少 3 个样本，看有没有规律）。
2. 客户端 `ss -tnpi` 看连接是否还在、retrans 多少、lastrcv 多久以前。
3. 服务端 `ss -tnp` 查同一四元组在不在 → **不在 = 半开连接**。
4. 两端同时抓包，按 seq 对账（§B.2 的四格表）。
5. 出了网卡 → 找中间设备（LB/防火墙/NAT）；没出网卡 → 客户端应用层。
6. 到了内核 → 看接入层解码/限流/去重日志，确认是"丢了"还是"应用当没收到"。
7. 确认应用层处理了 → 看为什么没回执 / 回执在回程丢了。
8. 写结论时**必须写清是①内核 / ②应用 / ③业务哪一层**。
