# -*- coding: utf-8 -*-
"""
推送扇出延迟分析（仅适用于广播架构）：JMeter push.csv × 出价 bids.jsonl

  python push_latency.py --push push.csv --bids bids.jsonl --out push_latency.csv

适用范围：对照实验确认"推送为广播"的架构才可用（M5a=扇出延迟、M5b=到达率）；
个人回执架构（只有当事人收到回执）不适用，改用 realtime_measure.py，且匹配
条件必须用"T0 前基线变化"——"载荷包含价格 P"在出价价等于旧底价时会提前命中。

匹配规则：对每笔成功出价（T0，价格 P），找每位观察者在 [T0, T0+窗口] 内
载荷包含 P 的第一条业务推送，latency = recv_ts - T0（含出价接口 RT，偏保守）。
输出：push_latency.csv（每对一行）+ 控制台 P50/P90/P95/P99/max 与到达率（M5b）。
"""
import argparse
import csv
import json
import sys


def load_bids(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                b = json.loads(line)
                if b.get("ok"):
                    out.append(b)
    out.sort(key=lambda b: b["t_ms"])
    return out


def load_pushes(path):
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            try:
                t_ms = float(row[0])
                observer = int(row[1])
            except ValueError:
                continue   # 表头
            out.append({"t_ms": t_ms, "observer": observer,
                        "type": row[2], "payload": row[3]})
    out.sort(key=lambda p: p["t_ms"])
    return out


def percentile(vals, q):
    if not vals:
        return None
    vals = sorted(vals)
    i = max(0, min(len(vals) - 1, int(q / 100.0 * len(vals) + 0.999) - 1))
    return vals[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", required=True)
    ap.add_argument("--bids", required=True)
    ap.add_argument("--out", default="push_latency.csv")
    ap.add_argument("--window", type=float, default=10000, help="匹配窗口 ms")
    ap.add_argument("--match", default="price", choices=["price", "nearest"])
    args = ap.parse_args()

    bids = load_bids(args.bids)
    pushes = [p for p in load_pushes(args.push)
              if p["type"] not in ("heartbeat", "2458", "securityInfo")]
    rows = []
    for b in bids:
        for p in pushes:
            dt = p["t_ms"] - b["t_ms"]
            if dt < 0:
                continue
            if dt > args.window:
                break
            if args.match == "price":
                price = b.get("price")
                hay = p["payload"] or ""
                if not (str(int(price)) in hay or str(price) in hay):
                    continue
            rows.append({"bid_t_ms": b["t_ms"], "price": b.get("price"),
                         "account": b.get("account"), "observer": p["observer"],
                         "type": p["type"], "latency_ms": round(dt, 1)})

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["bid_t_ms", "price", "account", "observer", "type", "latency_ms"])
        w.writeheader()
        w.writerows(rows)

    lat = [r["latency_ms"] for r in rows]
    per_bid = {}
    for r in rows:
        per_bid.setdefault(r["bid_t_ms"], []).append(r["latency_ms"])
    fanout = [max(v) for v in per_bid.values()]
    observers = {r["observer"] for r in rows}
    print("出价(成功) %d 笔 | 匹配对 %d | 命中出价 %d | 观察者 %d | 明细 %s" % (
        len(bids), len(rows), len(per_bid), len(observers), args.out))
    if lat:
        print("M5a 到达延迟 ms: P50=%.0f P90=%.0f P95=%.0f P99=%.0f max=%.0f" % (
            percentile(lat, 50), percentile(lat, 90), percentile(lat, 95),
            percentile(lat, 99), max(lat)))
        print("单笔广播收齐(全部观察者)延迟 ms: P95=%.0f max=%.0f" % (
            percentile(fanout, 95), max(fanout)))
    if bids:
        print("M5b 到达率(有匹配推送的出价占比): %.1f%%" % (len(per_bid) * 100.0 / len(bids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
