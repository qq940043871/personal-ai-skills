# cookie 获取排错

采集层靠「微信读书已登录 cookie」读文章。cookie 失效的症状是接口返回
`errCode=-2012`（登录超时）。本文件把各条获取路线的取舍与坑讲清楚。

## 三条路线（按推荐顺序）

### 路线 1：CDP 直读（推荐）

`get_cookie.py` 默认会尝试：启动带调试端口的浏览器 → 让浏览器自己把 cookie 吐出来。

```bash
python scripts/get_cookie.py --browser edge
```

**为什么走它**：Edge/Chrome 127+ 对**默认 user-data-dir** 的 cookie 用
v20 App-Bound 加密，密文绑定 Windows 账户 + 浏览器安装路径，**第三方离线解不开**；
复制到别的 profile 目录会被浏览器当损坏数据清空。而浏览器的调试端口是官方接口，
让它自己交 cookie，既不用管理员权限、也不用关浏览器。

**注意**：Chrome/Edge 136+ 在**默认 user-data-dir** 下直接拒绝
`--remote-debugging-port`。所以脚本用的是**独立的非默认 profile**
（`%TEMP%\cdp_edge_profile`），它用普通 v10 加密，既可调试又可读。
代价是这个 profile 需要**在该窗口里登录过一次**微信读书：

```bash
python scripts/get_cookie.py --browser edge --explicit-profile
# 在弹出的窗口里扫码登录 weread.qq.com，然后重跑
```

### 路线 2：browser-cookie3 直读

```bash
pip install browser-cookie3
```

装了才能用。但新版浏览器给 cookie 库加了独占锁，读文件常报
`共享冲突 (err 32)` —— 所以它只是 CDP 失败后的备选。

### 路线 3：手动粘贴（保底，永远可行）

```bash
python scripts/get_cookie.py --manual
```

1. 浏览器打开 `https://weread.qq.com`，确认已登录；
2. F12 → Network → 刷新页面 → 随便点一个请求 → 复制请求头里的 **Cookie 整行**；
3. 粘到 `config.yaml` 的 `source.weread.cookie`，并把 `cookie_from` 改成 `manual`。

## 死路（别再浪费时间）

| 尝试 | 结果 |
|---|---|
| 直接读默认 profile 的 Cookies 文件 | v20 加密，解不开 |
| 把 Cookies 复制到别的 profile 再读 | 浏览器当损坏数据清空 |
| 卷影副本(VSS) 硬拷 Cookies 文件 | 能绕过独占锁，但对 v20 无用 |
| Firefox 路径 | 多数机器没登录过，profile 是空壳 |

## 写回配置

拿到 cookie 串后，改 `config.yaml`：

```yaml
source:
  weread:
    cookie_from: manual
    cookie: "wr_rt=...; wr_skey=...; ..."
```

改完重跑 `run_pipeline.py`。若仍报 `-2012`，说明 cookie 本身没带上 `wr_skey`，
回到路线 3 手动复制一次。

## 定时任务里的注意点

- cookie 有效期不固定，可能几小时到几天。**建议在每次流水线运行前先检查**，
  失败再用 `get_cookie.py` 刷新（配合自动化里的条件分支）。
- 刷新 cookie 前先备份 `config.yaml`，避免写坏。
