#!/bin/bash
# =============================================================================
# jvm_diag.sh v2.0 — JVM + Linux 现场证据一键采集（自包含诊断包）
#
# 用法:
#   ./jvm_diag.sh <java_pid> [--dump] [--live-histo] [--out <dir>]
#
# 选项:
#   --dump         追加 full heap dump（.hprof，含全部对象；抓取期间 JVM 长停顿，
#                  完成后自动 gzip -1 压缩）
#   --live-histo   直方图改用 jmap -histo:live（先触发一次 Full GC，只算存活对象）；
#                  默认不带 :live（零停顿、含不可达对象）——OOM 分析保持默认
#   --out <dir>    输出根目录（默认当前目录）
#
# 产物:
#   <out>/jvm_diag_<pid>_<ts>.tar.gz
#   包内 manifest.txt 逐项标注采集状态，判读前先看它:
#     [OK]    成功有数据
#     [EMPTY] 命令成功但无输出（也可能是真实结论，如"无 D 状态线程"）
#     [MISS]  工具不存在（如 sysstat 未装）——不要误读成"没有数据"
#     [ERR]   执行报错，同名 .err 文件保留原始报错
#     [SKIP]  主动跳过（如磁盘不足放弃 dump、未开 -Xloggc）
#
# 设计要点（改脚本前先读）:
#   1. JVM 工具从目标进程自身的 JDK 目录解析——多 JDK 混装的服务器上，
#      PATH 里高版本 jstack/jmap attach 低版本进程会失败。
#   2. 每项采集 stderr 独立落 .err，绝不 2>/dev/null 吞错；空输出必须可区分。
#   3. 取证顺序: 线程栈最先（时效最强），直方图次之，full dump 最后；
#      全部采集完成之前不要重启进程。
# =============================================================================

SCRIPT_VERSION="2.0"

usage() { sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; }

PID=""
DO_DUMP=0
LIVE_HISTO=0
OUT_ROOT="."

while [ $# -gt 0 ]; do
  case "$1" in
    --dump)       DO_DUMP=1 ;;
    --live-histo) LIVE_HISTO=1 ;;
    --out)        OUT_ROOT="$2"; shift ;;
    -h|--help)    usage; exit 0 ;;
    *) if [ -z "$PID" ]; then PID="$1"; else echo "未知参数: $1" >&2; usage; exit 1; fi ;;
  esac
  shift
done

if [ -z "$PID" ]; then
  usage
  exit 1
fi

PID_CMD=$(ps -p "$PID" -o cmd= 2>/dev/null)
if [ -z "$PID_CMD" ]; then
  echo "错误: 进程 $PID 不存在（或无权限查看）" >&2
  exit 1
fi
echo "$PID_CMD" | grep -q java || \
  echo "警告: $PID 的命令行不含 java，确认目标无误: $PID_CMD"

# ---------------------------------------------------------------------------
# 定位目标进程自己的 JDK（java 命令路径 → -Djava.home → PATH）
# ---------------------------------------------------------------------------
JAVA_BIN_DIR=""
for t in $PID_CMD; do
  case "$t" in
    */java|java) [ -x "$t" ] && JAVA_BIN_DIR=$(dirname "$t") && break ;;
  esac
done
if [ -z "$JAVA_BIN_DIR" ]; then
  JH=$(echo "$PID_CMD" | grep -oE '\-Djava\.home=[^ ]+' | head -1 | cut -d= -f2)
  [ -n "$JH" ] && [ -x "$JH/bin/java" ] && JAVA_BIN_DIR="$JH/bin"
fi
if [ -z "$JAVA_BIN_DIR" ] && command -v java >/dev/null 2>&1; then
  JAVA_BIN_DIR=$(dirname "$(command -v java)")
fi

tool_of() {
  local name="$1"
  if [ -n "$JAVA_BIN_DIR" ] && [ -x "$JAVA_BIN_DIR/$name" ]; then
    echo "$JAVA_BIN_DIR/$name"
  elif command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
  else
    echo ""
  fi
}
JSTACK=$(tool_of jstack)
JMAP=$(tool_of jmap)
JSTAT=$(tool_of jstat)
JCMD=$(tool_of jcmd)

TOOLS_FROM_PATH=0
for t in "$JSTACK" "$JMAP" "$JSTAT" "$JCMD"; do
  case "$t" in
    "$JAVA_BIN_DIR"/*|"") ;;
    *) TOOLS_FROM_PATH=1 ;;
  esac
done

# ---------------------------------------------------------------------------
# 采集框架：step(简单命令) / stepsh(管道)，状态落 manifest，stderr 落 .err
# ---------------------------------------------------------------------------
mkdir -p "$OUT_ROOT"
DIR="$OUT_ROOT/jvm_diag_${PID}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DIR"
MANIFEST="$DIR/manifest.txt"

log() { echo "$(date '+%F %T')  $*" >> "$MANIFEST"; }
note() { echo "  * $*"; log "NOTE: $*"; }

finish() { # finish <file> <desc> <rc>
  local out="$1" desc="$2" rc="$3"
  if [ "$rc" = 127 ]; then
    log "[MISS]  $out -- $desc（命令不存在）"
  elif [ "$rc" != 0 ]; then
    log "[ERR]   $out -- $desc（exit=$rc，见 $out.err）"
  elif [ -s "$DIR/$out" ]; then
    log "[OK]    $out -- $desc"
  else
    log "[EMPTY] $out -- $desc（命令成功但无输出）"
  fi
  [ -s "$DIR/$out.err" ] || rm -f "$DIR/$out.err"
}
step() { # step <file> <desc> <cmd...>
  local out="$1" desc="$2"; shift 2
  "$@" > "$DIR/$out" 2> "$DIR/$out.err"
  finish "$out" "$desc" $?
}
stepsh() { # stepsh <file> <desc> <shell-string>
  local out="$1" desc="$2" sh="$3"
  bash -c "$sh" > "$DIR/$out" 2> "$DIR/$out.err"
  finish "$out" "$desc" $?
}

{
  echo "# jvm_diag manifest v$SCRIPT_VERSION"
  echo "host: $(hostname 2>/dev/null)"
  echo "date: $(date '+%F %T')"
  echo "user: $(id -un 2>/dev/null)"
  echo "pid: $PID"
  echo "pid_cmd: $PID_CMD"
  echo "java_bin_dir: ${JAVA_BIN_DIR:-<未找到，JVM 工具回退 PATH>}"
  echo "args: dump=$DO_DUMP live_histo=$LIVE_HISTO out=$OUT_ROOT"
  echo
} > "$MANIFEST"

[ "$TOOLS_FROM_PATH" = 1 ] && \
  note "部分 JVM 工具来自 PATH 而非目标 JDK（$JAVA_BIN_DIR），attach 可能失败，见对应 .err"

echo "==== JVM + Linux Diagnostic Collection v$SCRIPT_VERSION ===="
echo "PID: $PID    Output: $DIR"

# ---------------------------------------------------------------------------
# [1/8] 线程栈（最先采，时效最强）
# ---------------------------------------------------------------------------
echo "[1] 线程栈..."
if [ -n "$JSTACK" ]; then
  step jstack.txt "线程栈（jstack）" "$JSTACK" "$PID"
  if [ ! -s "$DIR/jstack.txt" ]; then
    step jstack_force.txt "线程栈（jstack -F 强制模式，进程疑似挂死时兜底）" "$JSTACK" -F "$PID"
  fi
else
  log "[MISS]  jstack.txt -- jstack 不可用（目标 JDK 目录与 PATH 都没有）"
fi

# ---------------------------------------------------------------------------
# [2/8] JVM 基本信息 + GC
# ---------------------------------------------------------------------------
echo "[2] JVM 基本信息 / GC..."
if [ -n "$JCMD" ]; then
  step jvm_version.txt "JVM 版本" "$JCMD" "$PID" VM.version
  step jvm_flags.txt "JVM 启动参数（生效值）" "$JCMD" "$PID" VM.flags
else
  log "[MISS]  jvm_version.txt / jvm_flags.txt -- jcmd 不可用"
fi

if [ -n "$JSTAT" ]; then
  step jstat_gcutil.txt "GC 占用率 1s x5（O/P 百分比、YGC/FGC 次数与耗时）" \
    "$JSTAT" -gcutil "$PID" 1 5
  step jstat_gccause.txt "GC 原因 1s x5（末次与当前 GC 成因）" \
    "$JSTAT" -gccause "$PID" 1 5
else
  log "[MISS]  jstat_gcutil.txt / jstat_gccause.txt -- jstat 不可用"
fi

# JDK major 判定：JDK7 走 -permstat，JDK8+ 走 -clstats
JDK_MAJOR=$(grep -oE 'JDK [0-9]+(\.[0-9]+)?' "$DIR/jvm_version.txt" 2>/dev/null \
  | head -1 | awk '{print $2}')
case "$JDK_MAJOR" in 1.*) JDK_MAJOR="${JDK_MAJOR#1.}" ;; esac

if [ -n "$JMAP" ]; then
  if [ -n "$JDK_MAJOR" ] && [ "$JDK_MAJOR" -ge 8 ] 2>/dev/null; then
    step classloader_stats.txt "类加载器统计（jmap -clstats）" "$JMAP" -clstats "$PID"
  else
    step permgen_stats.txt "PermGen 类加载器统计（jmap -permstat，大 Perm 可能耗时数分钟）" \
      "$JMAP" -permstat "$PID"
  fi
else
  log "[MISS]  permgen_stats.txt -- jmap 不可用"
fi

# ---------------------------------------------------------------------------
# [3/8] 堆直方图 + 可选 full dump（重证据，放轻证据之后）
# ---------------------------------------------------------------------------
echo "[3] 堆直方图 / dump..."
if [ -n "$JMAP" ]; then
  if [ "$LIVE_HISTO" = 1 ]; then
    step histo.txt "堆直方图（-histo:live，触发过 Full GC，仅存活对象）" "$JMAP" -histo:live "$PID"
  else
    step histo.txt "堆直方图（-histo，含不可达对象）" "$JMAP" -histo "$PID"
  fi
else
  log "[MISS]  histo.txt -- jmap 不可用"
fi

if [ "$DO_DUMP" = 1 ]; then
  if [ -z "$JMAP" ]; then
    log "[SKIP]  heap.hprof.gz -- jmap 不可用"
  else
    HEAP_BYTES=""
    if [ -s "$DIR/jvm_flags.txt" ]; then
      HEAP_BYTES=$(grep -oE 'MaxHeapSize=[0-9]+' "$DIR/jvm_flags.txt" | head -1 | cut -d= -f2)
    fi
    if [ -z "$HEAP_BYTES" ]; then
      XMX=$(echo "$PID_CMD" | grep -oE 'Xmx[0-9]+[kKmMgG]?' | head -1 | sed 's/^Xmx//')
      [ -n "$XMX" ] && HEAP_BYTES=$(echo "$XMX" | awk '{
        u=tolower(substr($0,length($0),1)); n=substr($0,1,length($0)-1);
        if(u=="g") print n*1073741824; else if(u=="m") print n*1048576;
        else if(u=="k") print n*1024; else print n }')
    fi
    AVAIL=$(df -Pk "$OUT_ROOT" 2>/dev/null | awk 'NR==2{print $4*1024}')
    NEED=0
    [ -n "$HEAP_BYTES" ] && NEED=$((HEAP_BYTES * 12 / 10))
    if [ "$NEED" -gt 0 ] 2>/dev/null && [ -n "$AVAIL" ] && [ "$AVAIL" -lt "$NEED" ]; then
      log "[SKIP]  heap.hprof.gz -- 磁盘不足: 需≈$((NEED/1048576))MB，可用 $((AVAIL/1048576))MB（清理磁盘或 --out 换目录）"
    else
      note "开始 full dump（进程会长停顿），完成后自动 gzip -1"
      stepsh heap_dump.txt "jmap full dump（含全部对象，供离线流式分析）" \
        "\"$JMAP\" -dump:format=b,file=\"$DIR/heap.hprof\" $PID"
      if [ -s "$DIR/heap.hprof" ]; then
        DUMPSZ=$(du -h "$DIR/heap.hprof" | awk '{print $1}')
        if gzip -1 -f "$DIR/heap.hprof" 2>>"$DIR/heap_dump.txt.err"; then
          log "[OK]    heap.hprof.gz -- dump 完成（原始 $DUMPSZ → $(du -h "$DIR/heap.hprof.gz" | awk '{print $1}')）"
        else
          log "[ERR]   heap.hprof.gz -- gzip 失败，保留原始文件"
        fi
      else
        log "[ERR]   heap.hprof.gz -- dump 未产出文件，见 heap_dump.txt / .err"
      fi
      [ -s "$DIR/heap_dump.txt.err" ] || rm -f "$DIR/heap_dump.txt.err"
    fi
  fi
else
  log "[SKIP]  heap.hprof.gz -- 未加 --dump（大堆 OOM 分析建议加上，注意停顿窗口）"
fi

# ---------------------------------------------------------------------------
# [4/8] 系统与资源基线
# ---------------------------------------------------------------------------
echo "[4] 系统基线..."
step uptime.txt    "负载与开机时长" uptime
step uname.txt     "内核版本"       uname -a
stepsh os-release.txt "OS 版本"        "cat /etc/os-release 2>/dev/null"
step lscpu.txt     "CPU 信息"       lscpu
step free.txt      "内存（Swap=0 主机注意 free 值）" free -h
step vmstat.txt    "CPU/内存/IO 概览 1s x5" vmstat 1 5
step mpstat.txt    "分核 CPU 1s x3" mpstat -P ALL 1 3
step iostat.txt    "磁盘 IO 1s x3"  iostat -x 1 3
step top.txt       "全系统 top 快照" top -b -n 1
step df.txt        "磁盘空间（dump 前置检查依据）" df -h
step mount.txt     "挂载点"         mount

# ---------------------------------------------------------------------------
# [5/8] 进程与线程细节
# ---------------------------------------------------------------------------
echo "[5] 进程 / 线程..."
step ps_pid.txt "目标进程概览" ps -p "$PID" -o pid,ppid,stat,%cpu,%mem,cmd
stepsh ps_pid_threads_top.txt \
  "目标进程线程按 CPU 排序（ps %CPU 是进程生命周期平均，与 top -H 瞬时值排名可能不同）" \
  "ps -Lo pid,tid,stat,pcpu,comm -p $PID --sort=-pcpu 2>/dev/null | head -50"
stepsh d_state_threads.txt \
  "D 状态线程（系统级；EMPTY=当前无 D 状态线程，属正常结论）" \
  "ps -eLo pid,tid,stat,comm 2>/dev/null | awk '\$3 ~ /D/'"
stepsh fd_list.txt "打开的句柄列表（fd 总数见 fd_summary.txt）" \
  "ls -l /proc/$PID/fd 2>/dev/null"
step limits.txt "进程 rlimits（Max open files 对比 fd 数）" cat "/proc/$PID/limits"

FD_COUNT=$(ls "/proc/$PID/fd" 2>/dev/null | wc -l)
FD_LIMIT=$(grep 'Max open files' "$DIR/limits.txt" 2>/dev/null | awk '{print $4}')
{
  echo "fd_count=$FD_COUNT"
  echo "fd_limit=${FD_LIMIT:-unknown}"
} > "$DIR/fd_summary.txt"
log "[OK]    fd_summary.txt -- fd_count=$FD_COUNT / limit=${FD_LIMIT:-unknown}"

step top_threads.txt "目标进程线程实时 CPU（top -H，瞬时值）" top -H -b -n 1 -p "$PID"

# ---------------------------------------------------------------------------
# [6/8] 日志与内核
# ---------------------------------------------------------------------------
echo "[6] 日志 / 内核..."
GCLOG=$(tr '\0' '\n' < "/proc/$PID/cmdline" 2>/dev/null \
  | grep -oE 'Xloggc:[^ ]+' | head -1 | sed 's/^Xloggc://')
if [ -n "$GCLOG" ] && [ -f "$GCLOG" ]; then
  step gc_log_tail.txt "GC 日志尾部 300 行（$GCLOG）" tail -300 "$GCLOG"
else
  log "[SKIP]  gc_log_tail.txt -- 未开启 -Xloggc（建议启动参数补 -Xloggc:<path> -XX:+PrintGCDetails）"
fi

CATBASE=$(echo "$PID_CMD" | grep -oE 'catalina\.base=[^ ]+' | head -1 | cut -d= -f2)
if [ -n "$CATBASE" ] && [ -f "$CATBASE/logs/catalina.out" ]; then
  step catalina_out_tail.txt \
    "catalina.out 尾部 300 行（kill -3 的线程栈与 OOM 报告都打到这里）" \
    tail -300 "$CATBASE/logs/catalina.out"
else
  log "[SKIP]  catalina_out_tail.txt -- 非 Tomcat 或未找到 catalina.out"
fi

stepsh dmesg_tail.txt \
  "内核日志尾部 200 行（OOM killer 搜: Out of memory / Killed process）" \
  "dmesg -T 2>/dev/null | tail -200"

# ---------------------------------------------------------------------------
# [7/8] 网络
# ---------------------------------------------------------------------------
echo "[7] 网络..."
step ss_summary.txt "socket 汇总" ss -s
step ss_antp.txt    "全部 TCP 连接（含进程归属）" ss -antp

if [ -s "$DIR/ss_antp.txt" ]; then
  grep "pid=$PID," "$DIR/ss_antp.txt" 2>/dev/null \
    | awk '{print $1}' | sort | uniq -c > "$DIR/ss_pid_states.txt"
  if [ -s "$DIR/ss_pid_states.txt" ]; then
    log "[OK]    ss_pid_states.txt -- 目标进程连接状态分布（CLOSE_WAIT 持续增长=连接泄漏）"
  else
    log "[EMPTY] ss_pid_states.txt -- 该进程无 TCP 连接"
  fi
fi

# ---------------------------------------------------------------------------
# [8/8] 收尾打包
# ---------------------------------------------------------------------------
log "[DONE] 采集完成"
tar czf "${DIR}.tar.gz" -C "$OUT_ROOT" "$(basename "$DIR")" \
  && log "[OK]    <tar> ${DIR}.tar.gz ($(du -h "${DIR}.tar.gz" | awk '{print $1}'))" \
  || log "[ERR]   tar 打包失败，原始目录保留: $DIR"

echo "============================================================"
echo "Collection completed: ${DIR}.tar.gz"
echo "判读顺序: 先 manifest.txt（确认 MISS/ERR/EMPTY/SKIP），再"
echo "jstat_gcutil → jstack → histo → fd_summary → ss_pid_states"
echo "============================================================"
