#!/usr/bin/env bash
# =============================================================================
# dev-prod-triage · 现场保全一键采集脚本
# 用途：生产故障发生、尚未重启/回滚之前，先跑这个把第一现场抓下来。
# 用法（上传到服务器后）：
#   chmod +x collect.sh
#   ./collect.sh                                   # 自动探测（推荐先跑这个）
#   ./collect.sh --pid 12345 --lang java           # 指定进程与语言
#   ./collect.sh --port 9000 --peer 10.0.0.8 --pcap   # 顺带抓包（谨慎）
#   ./collect.sh --aggressive                      # 包含 jmap dump / gdb（会 STW，需摘流量）
#
# 安全边界：
#   - 默认不执行任何会暂停业务的操作（jmap -dump / gdb attach 属 --aggressive）
#   - 抓包必须显式 --pcap，且带 host/port 过滤与分片，默认最多 60 秒
#   - 所有采集项失败不影响其它项继续
# 输出：/tmp/incident/<YYYYmmdd-HHMMSS>/  +  同名 .tar.gz
# =============================================================================

set -u
# 注意：故意不使用 set -e —— 采集脚本要容忍单项失败

PID=""
LANG_HINT=""          # java | go | cpp | auto
PORT=""
PEER=""
DO_PCAP=0
PCAP_SEC=60
AGGRESSIVE=0
TOP_N=20

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pid)        PID="$2"; shift 2;;
    --lang)       LANG_HINT="$2"; shift 2;;
    --port)       PORT="$2"; shift 2;;
    --peer)       PEER="$2"; shift 2;;
    --pcap)       DO_PCAP=1; shift;;
    --pcap-sec)   PCAP_SEC="$2"; shift 2;;
    --aggressive) AGGRESSIVE=1; shift;;
    -h|--help)    sed -n '2,22p' "$0"; exit 0;;
    *)            echo "unknown arg: $1" >&2; exit 1;;
  esac
done

TS=$(date +%Y%m%d-%H%M%S)
OUT="/tmp/incident/${TS}"
mkdir -p "$OUT"
LOG="$OUT/00-collect.log"

have() { command -v "$1" >/dev/null 2>&1; }
run() {   # run <outfile> <label> <cmd...>
  local out="$1"; shift
  local label="$1"; shift
  echo "----- [$(date '+%F %T')] $label -----" >> "$LOG"
  { echo "### $label  @ $(date '+%F %T')"; "$@" 2>&1; echo; } >> "$out" 2>&1 \
    && echo "  [ok]   $label" || echo "  [fail] $label"
}

echo "采集目录: $OUT"
echo "开始时间: $(date '+%F %T %Z')" | tee -a "$LOG"

# ---------------------------------------------------------------- 1. 系统概览
run "$OUT/01-system.txt" "hostname/date/uptime"      bash -c 'hostname; date "+%F %T %Z"; uptime'
run "$OUT/01-system.txt" "top snapshot"              bash -c 'top -b -n1 | head -30'
run "$OUT/01-system.txt" "cpu per-core (mpstat)"     bash -c 'mpstat -P ALL 1 3'
run "$OUT/01-system.txt" "vmstat"                    bash -c 'vmstat 1 5'
run "$OUT/01-system.txt" "iostat"                    bash -c 'iostat -x 1 3'
run "$OUT/01-system.txt" "memory"                    bash -c 'free -m; echo; cat /proc/meminfo | egrep "Slab|Buffers|Cached|Swap"'
run "$OUT/01-system.txt" "disk"                      bash -c 'df -h; echo; df -i'
run "$OUT/01-system.txt" "dmesg tail"                bash -c 'dmesg -T 2>/dev/null | tail -40'
run "$OUT/01-system.txt" "loadavg / interrupts"      bash -c 'cat /proc/loadavg; echo; cat /proc/softirqs'

# ---------------------------------------------------------------- 2. 进程定位
if [[ -z "$PID" ]]; then
  if have jps; then
    echo "未指定 --pid，检测到 Java 进程列表：" | tee -a "$LOG"
    jps -lv | tee "$OUT/02-jps.txt"
  fi
  echo "Top 内存/CPU 进程：" | tee -a "$LOG"
  ps -eo pid,ppid,user,stat,%cpu,%mem,etime,cmd --sort=-%cpu | head -"$TOP_N" | tee "$OUT/02-ps.txt"
else
  run "$OUT/02-ps.txt" "target process"  bash -c "ps -o pid,ppid,user,stat,%cpu,%mem,etime,cmd -p $PID"
  run "$OUT/02-ps.txt" "proc status"     bash -c "cat /proc/$PID/status"
  run "$OUT/02-ps.txt" "proc limits"     bash -c "cat /proc/$PID/limits"
  run "$OUT/02-ps.txt" "fd count"        bash -c "ls /proc/$PID/fd 2>/dev/null | wc -l"
  run "$OUT/02-ps.txt" "cmdline"         bash -c "tr '\0' ' ' < /proc/$PID/cmdline; echo"
  run "$OUT/02-ps.txt" "cpu per-thread"  bash -c "top -b -n1 -H -p $PID | head -30"
  run "$OUT/02-ps.txt" "pidstat cpu"     bash -c "pidstat -u -p $PID 1 5"
  run "$OUT/02-ps.txt" "pidstat ctx"     bash -c "pidstat -w -p $PID 1 5"
fi

# 语言自动识别
if [[ -z "$LANG_HINT" || "$LANG_HINT" == "auto" ]]; then
  if [[ -n "$PID" ]] && tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null | grep -qi 'java'; then
    LANG_HINT="java"
  elif [[ -n "$PID" ]] && have go && ls /proc/$PID/exe >/dev/null 2>&1; then
    LANG_HINT="cpp"
  else
    LANG_HINT="unknown"
  fi
fi
echo "识别语言: $LANG_HINT" | tee -a "$LOG"

# ---------------------------------------------------------------- 3. 网络
run "$OUT/03-network.txt" "ss summary"        bash -c 'ss -s'
run "$OUT/03-network.txt" "listen queues"     bash -c 'ss -lnt'
run "$OUT/03-network.txt" "conn state dist"   bash -c 'ss -tan | awk "{print \$1}" | sort | uniq -c'
if [[ -n "$PORT" ]]; then
  run "$OUT/03-network.txt" "port detail"     bash -c "ss -tnpi '( dport = :$PORT or sport = :$PORT )' | head -100"
  run "$OUT/03-network.txt" "port conn count" bash -c "ss -tn '( dport = :$PORT or sport = :$PORT )' | wc -l"
fi
run "$OUT/03-network.txt" "netstat -s"        bash -c 'netstat -s | egrep -i "retrans|listen|overflow|pruned|reset|bad|drop"'
run "$OUT/03-network.txt" "nstat"             bash -c 'nstat -az | egrep -i "retrans|zero|window|rst|syn"'
run "$OUT/03-network.txt" "netdev"            bash -c 'sar -n DEV 1 5'
run "$OUT/03-network.txt" "sysctl tcp"        bash -c 'sysctl -a 2>/dev/null | egrep "tcp_keepalive|somaxconn|syn_backlog|tw_reuse|tcp_mem|tcp_rmem|tcp_wmem|ip_local_port"'
run "$OUT/03-network.txt" "conntrack count"   bash -c 'cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null; cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null'
run "$OUT/03-network.txt" "ntp/clock"         bash -c 'date "+%F %T %Z"; ntpq -p 2>/dev/null || chronyc sources 2>/dev/null'

# ---------------------------------------------------------------- 4. 语言级
case "$LANG_HINT" in
  java)
    if [[ -n "$PID" ]]; then
      for i in 1 2 3; do
        run "$OUT/04-jvm.txt" "jstack #$i" bash -c "jstack -l $PID"
        [[ $i -lt 3 ]] && sleep 5
      done
      run "$OUT/04-jvm.txt" "jstat gcutil"   bash -c "jstat -gcutil $PID 1000 10"
      run "$OUT/04-jvm.txt" "jstat gccap"    bash -c "jstat -gccapacity $PID"
      run "$OUT/04-jvm.txt" "jmap histo"     bash -c "jmap -histo $PID | head -40"
      run "$OUT/04-jvm.txt" "jinfo flags"    bash -c "jinfo -flags $PID"
      run "$OUT/04-jvm.txt" "jcmd nmt"       bash -c "jcmd $PID VM.native_memory summary"
      run "$OUT/04-jvm.txt" "jcmd thread"    bash -c "jcmd $PID Thread.print"
      if [[ "$AGGRESSIVE" -eq 1 ]]; then
        echo "  [warn] --aggressive: jmap -dump 会触发 STW，确保已摘流量！"
        run "$OUT/04-jvm.txt" "jmap dump(STW)" bash -c "jmap -dump:live,format=b,file=$OUT/heap.hprof $PID"
      fi
    else
      echo "  [skip] 未指定 --pid，跳过 JVM 采集（Java 场景强烈建议指定）"
    fi
    ;;
  go)
    if [[ -n "$PORT" ]]; then
      PP="127.0.0.1:6060"
      run "$OUT/05-go.txt" "goroutine dump" bash -c "curl -s --max-time 20 http://$PP/debug/pprof/goroutine?debug=2"
      curl -s --max-time 40 "http://$PP/debug/pprof/profile?seconds=30" -o "$OUT/go-cpu.pprof" 2>>"$LOG" \
        && echo "  [ok]   go cpu profile" || echo "  [fail] go cpu profile (pprof 端口可能不是 6060)"
      curl -s --max-time 20 "http://$PP/debug/pprof/heap" -o "$OUT/go-heap.pprof" 2>>"$LOG" \
        && echo "  [ok]   go heap profile" || echo "  [fail] go heap profile"
    else
      echo "  [skip] Go 采集需要 pprof 端口，用 --port 指定或手工执行 references/02 中的 curl 命令"
    fi
    ;;
  cpp)
    if [[ -n "$PID" ]]; then
      run "$OUT/06-cpp.txt" "pstack" bash -c "pstack $PID"
      run "$OUT/06-cpp.txt" "pmap"   bash -c "pmap -x $PID | tail -20"
      if have perf; then
        run "$OUT/06-cpp.txt" "perf top (5s)" bash -c "timeout 10 perf top -p $PID -g -n --stdio"
      fi
      if [[ "$AGGRESSIVE" -eq 1 ]] && have gdb; then
        echo "  [warn] --aggressive: gdb attach 会暂停进程！"
        run "$OUT/06-cpp.txt" "gdb bt" bash -c "gdb -p $PID -ex 'thread apply all bt' -ex detach -batch"
      fi
    fi
    ;;
  *)
    echo "  [skip] 语言未识别（$LANG_HINT），可用 --lang java|go|cpp 显式指定后重跑"
    ;;
esac

# ---------------------------------------------------------------- 5. 抓包（默认关）
if [[ "$DO_PCAP" -eq 1 ]]; then
  if ! have tcpdump; then
    echo "  [fail] 无 tcpdump"
  else
    FILTER=""
    [[ -n "$PEER" ]] && FILTER="host $PEER"
    [[ -n "$PORT" ]] && FILTER="${FILTER:+${FILTER} and }port $PORT"
    FILTER=${FILTER:-"tcp"}
    echo "  抓包 ${PCAP_SEC}s，过滤: $FILTER"
    timeout "$PCAP_SEC" tcpdump -i any -nn -s0 -C 50 -W 3 -w "$OUT/cap.pcap" $FILTER >>"$LOG" 2>&1 \
      && echo "  [ok]   pcap -> $OUT/cap*.pcap" || echo "  [fail] pcap"
  fi
fi

# ---------------------------------------------------------------- 6. 打包
echo "结束时间: $(date '+%F %T %Z')" | tee -a "$LOG"
cd /tmp/incident && tar czf "/tmp/incident/${TS}.tar.gz" "$TS" 2>/dev/null \
  && echo "已打包: /tmp/incident/${TS}.tar.gz" || echo "打包失败，原始目录: $OUT"

echo
echo "采集完成。目录: $OUT"
echo "下一步：把 tar.gz 拉回本地，按 references/01 的决策树逐项分析。"
echo "提醒：重启/回滚前务必确认这份快照已保存。"
