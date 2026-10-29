# JMeter + WebSocket Samplers 实战手册

## 1. 环境

- JMeter 5.6.3 + Java 17；WS 插件 `net/luminis/jmeter/jmeter-websocket-samplers`（Maven Central，最新 1.3.2）放 `lib/ext/`。
- 采样器类名（写 JMX 时 XML 标签 = 全限定类名）：
  `eu.luminis.jmeter.wssampler.OpenWebSocketSampler / SingleWriteWebSocketSampler / SingleReadWebSocketSampler / RequestResponseWebSocketSampler / CloseWebSocketSampler`。
- 关键属性名：`server/port/path/connectTimeout/readTimeout`（Open）、`createNewConnection/requestData/payloadType(Text|Binary)`（Write）、`dataType(Text|Binary|Any)/optional`（Read，optional=true 表示读超时不算错）。

## 2. 计划结构（对应 assets/jmeter-plan-template.jmx）

```
TestPlan
 ├─ User Defined Variables：HOST/PORT/业务参数/协议常量（鉴权帧、心跳帧全文）——全部 ${__P(name,default)} 可 -J 覆盖
 ├─ TG 首页（-Jhome_threads，模型 = HTML+资源+首页接口，思考时间挂首个采样器）
 ├─ TG 详情首屏（HTML+快照接口）
 ├─ TG 轮询-快照（1s 档）   TG 轮询-时钟（10s 档）
 ├─ TG WS 观察者：OnceOnly(建连→发鉴权帧→读鉴权应答+断言→初始化心跳时钟)
 │                + 循环(If 心跳到期→发心跳帧；可选读 1s；JSR223 记录业务推送)
 └─ TG 洪峰（SyncTimer 集合点 + 首屏 + 建连；单独跑！）
```

**双口径**：复制一份计划、把静态资源采样器 `enabled=false` 即"缓存模型"；判定指标用缓存模型，无缓存版看静态容量。

## 3. JMX 高频坑（全部实战踩过）

1. **集合点的类是 `SyncTimer`**（`org.apache.jmeter.timers.SyncTimer`，TestBean，属性 `groupSize`/`timeoutInMs`），不是 SynchronizingTimer——写错类名整个计划解析失败。`groupSize=0` = 全测试线程汇合 → **洪峰组必须单独跑**。
2. **ConstantTimer 的作用域**：挂在控制器下 = 组内**每个采样器前**都延迟一次；要"每轮一次思考时间"必须挂到**首个采样器的子树里**（6 采样器 × 5s 思考会变成 30s/轮，直接把阶段拖超时）。
3. **jtl 是追加写**：重复运行前删旧文件或每轮新文件名，否则两轮数据混在一起。
4. **404 状态码但内容正常**（SPA 路由很常见）：页面请求挂 ResponseAssertion 且勾 `Assertion.assume_success=true`（忽略状态码）+ 内容断言（如 `id="app"`），以内容判成功。
5. 断言字符串含引号/冒号没问题，`Asserion.test_strings`（注意官方就是这个拼写）作 collectionProp 名。
6. 大文件下载设足 response timeout；10s 超时口径要在报告注明（"撞 10s 超时"就是它）。
7. 静态资源动态发现：RegexExtractor 从 HTML 提取 `/assets/*`，别写死 bundle 文件名（站点重部署就换名）。
8. 分布式未启用时单机 300 路 WS + 轮询没问题；再大考虑 `-R` 分布式。**单机 QPS 上限 ~4k**，探顶超过就要分片并行。
9. 同一计划内多个 JSONPostProcessor 会让**后续采样器被跳过**（5.6.3 实测）——字段提取统一用正则（响应为紧凑 JSON 时等价且稳定）。

## 4. 执行器模式（run_round.py 的设计，建议照搬）

- 阶段表驱动：每阶段 = (名称, -J 参数串, 预估秒数)；`--stage` 过滤器支持单跑。
- 每阶段独立进程（jtl/HTML 报告/jmeter.log 各一份），超时兜底 = 预估×3。
- **每阶段结束立即落 results_summary.md/json**（中止也有数据）；中止阶段的 jtl 事后补录并标"部分数据（中止）"。
- 汇总按采样器名给 n/err/P50/P95/P99/max，**外加每采样器 TPS + 阶段稳态 TPS 列**——没有 TPS 列画不出并发-吞吐-RT 曲线，容量探顶无从谈起。
- 汇总末尾自动生成"能力曲线"表（并发-稳态TPS-增益-P95-失败率，增益 <5% 标吞吐平台期/拐点候选）；探顶/容量评估整体方法论见 `capacity-probe.md`。
- **实现指针（skill 未随附这些脚本，照搬去样例工程取）**：阶段执行器/TPS 汇总/能力曲线 = `D:\ai_work\p002_stress_test_k206\autotest\perf\run_round.py`；会话守护续期（capacity-probe §7）= 同目录 `ensure_sessions.py`；熔断护栏（近 200 次滚动错误率 >5% 自动停压）= 同目录 `portal_stress.py`（`deque(maxlen=200)` 模式，可移植进任何自研加压器）；标的/场次数据面（capacity-probe §6）= 同目录 `prepare_symbols.py`/`refresh_symbols.py`。

## 5. 实时性测量（WS 回执 + 轮询可见性）

- 观察者 WS 用 F408（登录帧）还是游客帧，由协议侦察的受众实验决定；鉴权帧若是固定常量直接放 UDV。
- 回执延迟 = 写操作发起 T0 → 该连接收到业务帧 T1；可见延迟 = T0 → 轮询者首次看到关键字段**变化**（基线取 T0 前最后一次快照，别用"≥目标值"——出价价可能等于旧值提前命中）。
- 推送落盘列：`recv_ts, observer, type, payload`；出价落盘列：`t0, t1, price, ok`；分析脚本 `scripts/push_latency.py`。
- 写操作触发的定价跟随实时底价（见 protocol-discovery §5）。

## 6. 健康窗口复测（环境噪声剔除）

若某轮所有接口 RT 同步抬升且与并发无关（空载也慢）：记为"环境劣化时段"，在正常窗口用同参数复测关键档位（2~3 分钟一档），**判定用复测值**，劣化另立条目归因（实战归因：同时升级程序）。压测机自身也要对照（负载中用 curl 打一发看基线）。
