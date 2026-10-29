# -*- coding: utf-8 -*-
"""
实时性测量骨架：写操作回执延迟（WS）+ 他人可见延迟（轮询）——单点适配版

用法（适配 place_bid() 后）：
  python realtime_measure.py --ws-url ws://host/wspayback --accounts accounts.csv \
      --rounds 2 --pollers 30 --poll-url https://host/api --out-dir runs/rt_xxx

结构（来自实战：29 路 WS + 30 路轮询 + 58 笔真实出价）：
  1) 每个出价账号：登录（适配 login()）→ 建 WS → 发登录鉴权帧（适配 AUTH_FRAME）→ 收帧线程
  2) N 路匿名轮询观察者：1s 档拉关键字段快照（适配 fetch_snapshot()）
  3) 逐账号出价（适配 place_bid()，价格跟随实时底价）→ 记 T0/T1
  4) 指标：M5a' 回执延迟 = T0→该连接收到业务帧；M5c' 可见延迟 = T0→轮询者见基线变化
输出：bids.jsonl / receipts.csv / polls.csv / summary.md
依赖：websocket-client、requests。
"""
import argparse
import csv
import json
import os
import sys
import threading
import time
from datetime import datetime

try:
    import websocket
    import requests
except ImportError:
    sys.exit("请先: pip install websocket-client requests")

# ===================== 适配区（按目标系统修改这三处 + 常量）=====================
HEARTBEAT_FRAME = "[0000...固定心跳帧全文...]"      # 无心跳协议则置空
HEARTBEAT_INTERVAL = 25.0
BUSINESS_TYPES_EXCLUDE = ("heartbeat", "0000")     # 不算业务帧的类型


def login(account, password):
    """返回 dict(sess=requests.Session, token=str, ws_auth_frame=str)；失败返回 None。
    ws_auth_frame = 该账号的 WS 登录鉴权帧全文（token/FIRMID 拼帧）。"""
    raise NotImplementedError("适配目标系统的登录与拼帧")


def place_bid(sess, ordno, price_hint=None):
    """发起一笔写操作。返回 dict(t0_ms, t1_ms, price, ok, msg)。
    价格规则通常是跟随实时底价（无报价=起拍+1，有报价=当前允许价）。"""
    raise NotImplementedError("适配目标系统的写接口")


def fetch_snapshot():
    """轮询观察者拉一份关键字段快照。返回 dict(t_ms, recv_ms, value=float)。
    value = 用于判定可见性的字段（如 BESTPRICE）。"""
    raise NotImplementedError("适配目标系统的行情/状态查询")
# ==============================================================================


def pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    i = max(0, min(len(v) - 1, int(q / 100.0 * len(v) + 0.999) - 1))
    return v[i]


def ws_observer(acc, auth_frame, stop_evt, receipts, lock):
    ws = websocket.create_connection(WS_URL, timeout=10)
    try:
        ws.send(auth_frame)
        last_hb = time.time()
        while not stop_evt.is_set():
            if HEARTBEAT_FRAME and time.time() - last_hb >= HEARTBEAT_INTERVAL:
                ws.send(HEARTBEAT_FRAME)
                last_hb = time.time()
            ws.settimeout(1.0)
            try:
                frame = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if frame == "":
                break
            ftype = frame[1:5] if frame.startswith("[") and len(frame) >= 5 else "?"
            if ftype in BUSINESS_TYPES_EXCLUDE:
                continue
            with lock:
                receipts.append({"account": acc, "t_ms": time.time() * 1000,
                                 "type": ftype, "payload": frame[:400]})
    except Exception as e:
        with lock:
            receipts.append({"account": acc, "event": "error", "msg": type(e).__name__})
    finally:
        try:
            ws.close()
        except Exception:
            pass


def poll_observer(stop_evt, polls, lock):
    while not stop_evt.is_set():
        try:
            rec = fetch_snapshot()
        except Exception as e:
            rec = {"t_ms": time.time() * 1000, "recv_ms": time.time() * 1000,
                   "error": type(e).__name__}
        with lock:
            polls.append(rec)
        time.sleep(1.0)


def main():
    global WS_URL
    ap = argparse.ArgumentParser()
    ap.add_argument("--ws-url", required=True)
    ap.add_argument("--accounts", required=True, help="csv: account,password")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--pollers", type=int, default=30)
    ap.add_argument("--bid-interval", type=float, default=3.0)
    ap.add_argument("--receipt-wait", type=float, default=15.0)
    ap.add_argument("--out-dir", default="runs/rt_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    args = ap.parse_args()
    WS_URL = args.ws_url
    os.makedirs(args.out_dir, exist_ok=True)

    accounts = []
    with open(args.accounts, encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if row and row[0].strip() and not row[0].startswith(("#", "账号", "account")):
                accounts.append((row[0].strip(), row[1].strip() if len(row) > 1 else ""))

    lock, stop_evt = threading.Lock(), threading.Event()
    receipts, polls, bids = [], [], []

    pollers = [threading.Thread(target=poll_observer, args=(stop_evt, polls, lock), daemon=True)
               for _ in range(args.pollers)]
    for t in pollers:
        t.start()

    sessions = []
    for acc, pwd in accounts:
        try:
            info = login(acc, pwd)
        except NotImplementedError:
            raise
        except Exception:
            info = None
        if not info:
            print("[skip] %s login failed" % acc, flush=True)
            continue
        t = threading.Thread(target=ws_observer,
                             args=(acc, info["ws_auth_frame"], stop_evt, receipts, lock), daemon=True)
        t.start()
        sessions.append((acc, info, t))
        print("[ready] %s" % acc, flush=True)
    time.sleep(5)

    for rnd in range(args.rounds):
        for acc, info, _t in sessions:
            try:
                rec = place_bid(info["sess"])
            except Exception as e:
                rec = {"ok": False, "msg": type(e).__name__}
            rec["acc"], rec["round"] = acc, rnd
            bids.append(rec)
            print("[bid r%d] %s %s" % (rnd, acc, rec), flush=True)
            time.sleep(args.bid_interval)

    time.sleep(8)
    stop_evt.set()
    for t in pollers + [s[2] for s in sessions]:
        t.join(timeout=5)

    ok_bids = [b for b in bids if b.get("ok")]
    lat_receipt, vis = [], []
    for b in ok_bids:
        cands = [r for r in receipts if r.get("account") == b["acc"] and r.get("t_ms", 0) >= b.get("t0_ms", 0)
                 and r["t_ms"] - b["t0_ms"] <= args.receipt_wait * 1000]
        if cands:
            b["receipt_latency_ms"] = round(min(cands, key=lambda r: r["t_ms"])["t_ms"] - b["t0_ms"], 1)
            lat_receipt.append(b["receipt_latency_ms"])
        # 可见延迟：T0 前基线变化
        pre = [p for p in polls if p.get("t_ms", 0) < b["t0_ms"] and "value" in p]
        base = pre[-1]["value"] if pre else None
        if base is not None:
            after = [p for p in polls if p.get("recv_ms", 0) >= b["t0_ms"]
                     and p.get("value") is not None and p["value"] != base]
            if after:
                d = round(min(after, key=lambda p: p["recv_ms"])["recv_ms"] - b["t0_ms"], 1)
                b["visibility_ms"] = d
                vis.append(d)

    with open(os.path.join(args.out_dir, "bids.jsonl"), "w", encoding="utf-8") as f:
        for b in bids:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    for name, rows, fields in (("receipts.csv", receipts, ["account", "t_ms", "type", "payload", "event", "msg"]),
                               ("polls.csv", polls, ["t_ms", "recv_ms", "value", "error"])):
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    lines = ["# 实时性测量汇总", "",
             "M5a' 回执延迟（%d 样本）: P50=%s P95=%s P99=%s max=%s" % (
                 len(lat_receipt), pct(lat_receipt, 50), pct(lat_receipt, 95),
                 pct(lat_receipt, 99), max(lat_receipt) if lat_receipt else None),
             "M5b' 到达率: %d/%d" % (len(lat_receipt), len(ok_bids)),
             "M5c' 可见延迟（%d 样本）: P50=%s P95=%s max=%s" % (
                 len(vis), pct(vis, 50), pct(vis, 95), max(vis) if vis else None)]
    summary = "\n".join(lines)
    open(os.path.join(args.out_dir, "summary.md"), "w", encoding="utf-8").write(summary + "\n")
    print(summary, flush=True)


if __name__ == "__main__":
    main()
