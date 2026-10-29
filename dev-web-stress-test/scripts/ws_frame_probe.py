# -*- coding: utf-8 -*-
"""
通用 WS 帧探测器：建连 → 发鉴权帧 → 心跳保活 → 全帧落盘（协议侦察/联调用）

  python ws_frame_probe.py --url ws://host/path --auth-frame "[F409...JSON]" --listen 60
  python ws_frame_probe.py --url ws://host/path --auth-frame-file auth.txt \
      --heartbeat "[0000...]" --hb-interval 25 --out frames.csv

依赖：websocket-client。帧落盘列：recv_epoch_ms, dir, type_guess, frame。
type_guess 按"81 字符协议头"启发（`[` + 4 位类型）；协议不同可加 --no-parse。
"""
import argparse
import csv
import sys
import time

try:
    import websocket
except ImportError:
    sys.exit("请先: pip install websocket-client")


def guess_type(frame):
    if frame.startswith("[") and len(frame) >= 5:
        return frame[1:5]
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--auth-frame", default="", help="建连后立即发送的鉴权帧全文")
    ap.add_argument("--auth-frame-file", help="鉴权帧从文件读（避免命令行转义）")
    ap.add_argument("--heartbeat", default="", help="心跳帧全文")
    ap.add_argument("--hb-interval", type=float, default=25.0, help="心跳间隔秒（0=不发）")
    ap.add_argument("--listen", type=float, default=60.0, help="监听秒数")
    ap.add_argument("--out", default="ws_frames.csv")
    ap.add_argument("--no-parse", action="store_true", help="不做帧类型启发解析")
    args = ap.parse_args()

    auth = args.auth_frame
    if args.auth_frame_file:
        auth = open(args.auth_frame_file, encoding="utf-8").read().strip()

    ws = websocket.create_connection(args.url, timeout=10)
    print("[connect] %s ok, %.0fms" % (args.url, 0), flush=True)
    rows = []

    def log(direction, data):
        t = time.time() * 1000
        kind = "raw" if args.no_parse else guess_type(data)
        rows.append({"recv_epoch_ms": t, "dir": direction, "type_guess": kind, "frame": data[:2000]})
        print("[%s] type=%s len=%d %s" % (direction, kind, len(data), data[:120]), flush=True)

    if auth:
        ws.send(auth)
        log("C->S", auth)
    last_hb = time.time()
    end = time.time() + args.listen
    try:
        while time.time() < end:
            if args.hb_interval and args.heartbeat and time.time() - last_hb >= args.hb_interval:
                ws.send(args.heartbeat)
                log("C->S", args.heartbeat)
                last_hb = time.time()
            ws.settimeout(1.0)
            try:
                frame = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if frame == "":
                print("[close] server closed", flush=True)
                break
            log("S->C", frame if isinstance(frame, str) else repr(frame))
    finally:
        ws.close()
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["recv_epoch_ms", "dir", "type_guess", "frame"])
            w.writeheader()
            w.writerows(rows)
        print("[done] %d frames -> %s" % (len(rows), args.out), flush=True)


if __name__ == "__main__":
    main()
