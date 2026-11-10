<#
.SYNOPSIS
  Godot 4.x Android 导出最小工具链一键安装（免管理员、幂等、国内网络友好）。
.DESCRIPTION
  安装内容（约 600MB，全部在用户目录，不需要管理员权限）：
    %USERPROFILE%\godot-android\jdk\           Temurin JDK 17（Godot 4.x 安卓导出要求）
    %USERPROFILE%\godot-android\android-sdk\   cmdline-tools + platform-tools + build-tools(34)
                                                （仅签名/调试所需，不装 Android Studio、不装 platforms）
    %APPDATA%\Godot\export_templates\<版本>\
                                                仅 android_debug.apk + android_release.apk + version.txt
                                                （从官方 TPZ 范围抽取，免下载 1.2GB 全量包）
                                                Godot 4.7+ 读版本目录根层，同时写 templates\ 子层兼容老版本
    %APPDATA%\Godot\keystores\debug.keystore   调试签名（若缺）
  同时把 java/android sdk 路径写入 Godot 的 editor_settings-<大版本.小版本>.tres。

  下载源（按国内可达性选择，均支持 HTTP Range 断点续传）：
    JDK        清华 TUNA Adoptium 镜像（失败回退 Adoptium API → GitHub）
    Android    dl.google.com（国内可达）
    导出模板    downloads.godotengine.org 官方重定向（Hetzner 对象存储；失败回退 GitHub）

  重复运行安全：已存在的组件自动跳过，只补缺失部分。
.EXAMPLE
  pwsh -File setup_android.ps1
  pwsh -File setup_android.ps1 -GodotExe "C:\Program Files\Godot\...\Godot_v4.7.2-stable_win64_console.exe"
#>
[CmdletBinding()]
param(
    [string]$ToolchainDir = "$env:USERPROFILE\godot-android",
    [string]$GodotExe = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TraeGodotSetup/1.0"

# ---------- 工具函数 ----------

function Write-Step([string]$msg)  { Write-Host "`n[setup] $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)    { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg) { Write-Host "  [!!] $msg" -ForegroundColor Yellow }

function Find-Godot {
    if ($GodotExe -and (Test-Path $GodotExe)) { return (Resolve-Path $GodotExe).Path }
    $hit = Get-Command godot -ErrorAction SilentlyContinue
    if ($hit) { return $hit.Source }
    $roots = @("C:\Program Files\Godot", "$env:LOCALAPPDATA\Programs\Godot")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        # 嵌套怪癖：真实 exe 在名为 Godot_vX.Y.Z-stable_win64.exe 的文件夹里
        $c = Get-ChildItem $root -Recurse -Filter "Godot_v*_win64_console.exe" -ErrorAction SilentlyContinue |
             Sort-Object FullName -Descending | Select-Object -First 1
        if ($c) { return $c.FullName }
        $c = Get-ChildItem $root -Recurse -Filter "Godot_v*_win64.exe" -ErrorAction SilentlyContinue |
             Where-Object { -not $_.PSIsContainer } | Sort-Object FullName -Descending | Select-Object -First 1
        if ($c) { return $c.FullName }
    }
    return $null
}

function New-RangeRequest([string]$url, [long]$start, [long]$end) {
    $req = [System.Net.HttpWebRequest]::Create($url)
    if ($start -ge 0) { $req.AddRange($start, $end) }
    $req.UserAgent = $UA
    $req.Timeout = 30000
    $req.ReadWriteTimeout = 60000
    return $req
}

## 断点续传的范围下载（带重试与进度）
function Save-RangeFile([string]$url, [long]$start, [long]$length, [string]$outFile, [string]$tag) {
    $dir = Split-Path $outFile -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $fs = [System.IO.File]::Open($outFile, [System.IO.FileMode]::Create)
    $fs.SetLength($length)
    try {
        $pos = [long]0
        $attempt = 0
        $lastPct = -1
        while ($pos -lt $length) {
            try {
                $resp = (New-RangeRequest $url ($start + $pos) ($start + $length - 1)).GetResponse()
            } catch {
                $attempt++
                if ($attempt -gt 8) { throw }
                Write-Warn2 "$tag 连接中断（$attempt/8），3 秒后续传于 $([math]::Round($pos/1MB,1))MB…"
                Start-Sleep -Seconds 3
                continue
            }
            try {
                $stream = $resp.GetResponseStream()
                $buf = New-Object byte[] (1MB)
                while ($pos -lt $length) {
                    # ReadAsync + 强制等待超时：schannel 流上 ReadWriteTimeout 可能不生效，会无限挂起
                    $rt = $stream.ReadAsync($buf, 0, [int][Math]::Min($buf.Length, $length - $pos))
                    if (-not $rt.Wait(90000)) { throw "读取停滞 90s" }
                    $n = $rt.Result
                    if ($n -le 0) { break }
                    $fs.Write($buf, 0, $n)
                    $pos += $n
                    $attempt = 0
                    $pct = [int]($pos * 100 / $length)
                    if ($pct -ge $lastPct + 5) {
                        $lastPct = $pct
                        Write-Host ("`r  $tag ${pct}%  ($([math]::Round($pos/1MB,0))/$([math]::Round($length/1MB,0))MB)").PadRight(72) -NoNewline
                    }
                }
            } catch {
                Write-Host ""   # 读取停滞/中断：落到下方统一 attempt++ 重连续传
            } finally { $resp.Close() }
            if ($pos -lt $length) { $attempt++; if ($attempt -gt 8) { throw "$tag 多次中断，放弃（重跑脚本可续传）" } }
        }
    } finally {
        $fs.Close()
        Write-Host ("`r  $tag 100%").PadRight(72)
    }
}

## 完整文件下载（缓存到 cache/，已存在则跳过）
function Save-WholeFile([string]$url, [string]$outFile, [string]$tag) {
    if (Test-Path $outFile) { Write-Ok "$tag 已缓存 $(Split-Path $outFile -Leaf)"; return $true }
    try {
        $req = [System.Net.HttpWebRequest]::Create($url)
        $req.UserAgent = $UA; $req.Timeout = 30000; $req.ReadWriteTimeout = 120000
        $resp = $req.GetResponse()
        try {
            $total = $resp.ContentLength
            $dir = Split-Path $outFile -Parent
            if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            $fs = [System.IO.File]::Create($outFile)
            try { $resp.GetResponseStream().CopyTo($fs) } finally { $fs.Close() }
        } finally { $resp.Close() }
        Write-Ok "$tag 下载完成 $(Split-Path $outFile -Leaf)"
        return $true
    } catch {
        Write-Warn2 "$tag 下载失败：$($_.Exception.Message)"
        if (Test-Path $outFile) { Remove-Item $outFile -Force }
        return $false
    }
}

# ---------- 1. 探测 Godot ----------

Write-Step "探测 Godot…"
$godot = Find-Godot
if (-not $godot) {
    Write-Host "未找到 Godot。请用 -GodotExe 指定，或先安装 Godot 4.4+。" -ForegroundColor Red
    exit 1
}
$verOut = & $godot --version 2>&1 | Select-Object -First 1
$versionFull = ($verOut -split "\." | Select-Object -First 4) -join "."        # 4.7.2.stable
$versionShort = ($verOut -split "\." | Select-Object -First 3) -join "."       # 4.7.2
$majMin = ($verOut -split "\." | Select-Object -First 2) -join "."             # 4.7
Write-Ok "Godot $versionFull -> $godot"

# ---------- 2. JDK 17 ----------

Write-Step "JDK 17（Temurin）…"
$jdkDir = Join-Path $ToolchainDir "jdk"
$javaExe = Join-Path $jdkDir "bin\java.exe"
if (Test-Path $javaExe) {
    Write-Ok "已安装：$javaExe"
} else {
    $cacheDir = Join-Path $ToolchainDir "cache"
    $jdkZip = Join-Path $cacheDir "temurin17.zip"
    $done = $false
    # 源1：清华 TUNA Adoptium 镜像（国内快；文件名随小版本更新，先解析目录）
    try {
        $listing = Invoke-WebRequest -Uri "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/17/jdk/x64/windows/" `
            -TimeoutSec 20 -UseBasicParsing -UserAgent $UA
        $zipName = ([regex]::Matches($listing.Content, 'OpenJDK17U-jdk_x64_windows_hotspot_[0-9._]+\.zip') |
                    ForEach-Object { $_.Value } | Sort-Object -Unique | Select-Object -Last 1)
        if ($zipName) {
            $tunaUrl = "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/17/jdk/x64/windows/$zipName"
            $done = Save-WholeFile $tunaUrl $jdkZip "TUNA"
        }
    } catch { Write-Warn2 "TUNA 不可达：$($_.Exception.Message)" }
    # 源2：Adoptium 官方 API（海外网络快，重定向到 GitHub）
    if (-not $done) {
        $done = Save-WholeFile "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse" $jdkZip "Adoptium"
    }
    if (-not $done) {
        Write-Host "JDK 下载失败。请手动下载 Temurin JDK17 zip 解压到：$jdkDir" -ForegroundColor Red
        exit 1
    }
    Write-Host "  解压 JDK…"
    $tmp = Join-Path $ToolchainDir "tmp-jdk"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive -Path $jdkZip -DestinationPath $tmp -Force
    $inner = Get-ChildItem $tmp | Where-Object PSIsContainer | Select-Object -First 1
    if (Test-Path $jdkDir) { Remove-Item $jdkDir -Recurse -Force }
    Move-Item $inner.FullName $jdkDir
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Ok "JDK -> $jdkDir"
}
$env:JAVA_HOME = $jdkDir
$javaVer = & $javaExe -version 2>&1 | Select-Object -First 1
Write-Ok "java: $javaVer"

# ---------- 3. Android SDK（仅 cmdline-tools + platform-tools + build-tools） ----------

Write-Step "Android SDK 最小组件…"
$sdkDir = Join-Path $ToolchainDir "android-sdk"
$sdkmgr = Join-Path $sdkDir "cmdline-tools\latest\bin\sdkmanager.bat"
if (Test-Path $sdkmgr) {
    Write-Ok "已安装：$sdkmgr"
} else {
    $cmdtoolsZip = Join-Path $ToolchainDir "cache\commandlinetools.zip"
    $ok = Save-WholeFile "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip" $cmdtoolsZip "cmdline-tools"
    if (-not $ok) {
        Write-Host "cmdline-tools 下载失败，请检查网络后重跑。" -ForegroundColor Red
        exit 1
    }
    $tmp = Join-Path $ToolchainDir "tmp-sdk"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Expand-Archive -Path $cmdtoolsZip -DestinationPath $tmp -Force
    # zip 内是 cmdline-tools\，规范布局要求改名为 cmdline-tools\latest
    $ctDir = Join-Path $sdkDir "cmdline-tools"
    if (-not (Test-Path $ctDir)) { New-Item -ItemType Directory -Path $ctDir -Force | Out-Null }
    $dst = Join-Path $ctDir "latest"
    if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
    Move-Item (Join-Path $tmp "cmdline-tools") $dst
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Write-Ok "cmdline-tools -> $dst"
}

$needPkgs = $false
if (-not (Test-Path (Join-Path $sdkDir "platform-tools\adb.exe"))) { $needPkgs = $true }
if (-not (Get-ChildItem (Join-Path $sdkDir "build-tools") -Filter "apksigner.bat" -Recurse -ErrorAction SilentlyContinue)) { $needPkgs = $true }
if ($needPkgs) {
    Write-Host "  sdkmanager 安装 platform-tools + build-tools;34.0.0（约 60MB）…"
    $env:JAVA_HOME = $jdkDir
    $yes = "y`n" * 20
    $yes | & $sdkmgr --sdk_root=$sdkDir --licenses 2>&1 | Out-Null
    $yes | & $sdkmgr --sdk_root=$sdkDir "platform-tools" "build-tools;34.0.0" 2>&1 | ForEach-Object {
        $line = "$_"
        if ($line -match '\[\s*\d+%') { Write-Host "  sdkmgr: $line" }
    }
    if (-not (Test-Path (Join-Path $sdkDir "platform-tools\adb.exe"))) {
        Write-Host "sdkmanager 安装失败，请检查网络后重跑。" -ForegroundColor Red; exit 1
    }
    Write-Ok "platform-tools + build-tools 就绪"
} else {
    Write-Ok "platform-tools + build-tools 已存在"
}
$apksigner = (Get-ChildItem (Join-Path $sdkDir "build-tools") -Filter "apksigner.bat" -Recurse | Sort-Object FullName -Descending | Select-Object -First 1).FullName
Write-Ok "apksigner: $apksigner"

# ---------- 4. Godot 安卓导出模板（仅范围抽取 android_*.apk，免下全量 TPZ） ----------

Write-Step "Godot 安卓导出模板 $versionFull …"
# Godot 4.7+ 在版本目录根层查找模板（老版本为 <版本>\templates\ 子层；两层都写，新老通吃）
$tplDir = Join-Path $env:APPDATA "Godot\export_templates\$versionFull"
$tplDirLegacy = Join-Path $tplDir "templates"
$relApk = Join-Path $tplDir "android_release.apk"
$dbgApk = Join-Path $tplDir "android_debug.apk"
$verTxt = Join-Path $tplDir "version.txt"
if ((Test-Path $relApk) -and (Test-Path $dbgApk)) {
    Write-Ok "已安装：$tplDir"
} else {
    if (-not (Test-Path $tplDir)) { New-Item -ItemType Directory -Path $tplDir -Force | Out-Null }
    # 候选源：官方重定向（Hetzner）优先，GitHub 兜底
    $tpzCandidates = @(
        "https://downloads.godotengine.org/?version=$versionShort&flavor=stable&slug=export_templates.tpz&platform=templates",
        "https://github.com/godotengine/godot/releases/download/$versionShort-stable/Godot_v$versionShort-stable_export_templates.tpz"
    )
    $tpzUrl = $null; $tpzSize = [long]0
    foreach ($u in $tpzCandidates) {
        try {
            $req = [System.Net.HttpWebRequest]::Create($u)
            $req.UserAgent = $UA; $req.Timeout = 20000
            $resp = $req.GetResponse()   # 自动跟随重定向
            $tpzSize = $resp.ContentLength
            $tpzUrl = $resp.ResponseUri.AbsoluteUri
            $resp.Close()
            if ($tpzSize -gt 1MB) { break }
        } catch { Write-Warn2 "源不可达：$u" }
    }
    if (-not $tpzUrl) { Write-Host "TPZ 源均不可达，请检查网络后重跑。" -ForegroundColor Red; exit 1 }
    Write-Ok "TPZ 源：$([System.Uri]$tpzUrl | Select-Object -ExpandProperty Host)（$([math]::Round($tpzSize/1GB,2))GB）"

    # 4a. 拉中央目录
    $tailLen = [Math]::Min(65536, $tpzSize)
    $resp = (New-RangeRequest $tpzUrl ($tpzSize - $tailLen) ($tpzSize - 1)).GetResponse()
    $ms = New-Object System.IO.MemoryStream; $resp.GetResponseStream().CopyTo($ms); $resp.Close()
    $tail = $ms.ToArray()
    $eocd = -1
    for ($i = $tail.Length - 22; $i -ge 0; $i--) {
        if ($tail[$i] -eq 0x50 -and $tail[$i+1] -eq 0x4B -and $tail[$i+2] -eq 0x05 -and $tail[$i+3] -eq 0x06) { $eocd = $i; break }
    }
    if ($eocd -lt 0) { Write-Host "TPZ 损坏（无 EOCD）。" -ForegroundColor Red; exit 1 }
    $cdSize = [BitConverter]::ToUInt32($tail, $eocd + 12)
    $cdOff  = [BitConverter]::ToUInt32($tail, $eocd + 16)
    $resp = (New-RangeRequest $tpzUrl $cdOff ($cdOff + $cdSize - 1)).GetResponse()
    $ms = New-Object System.IO.MemoryStream; $resp.GetResponseStream().CopyTo($ms); $resp.Close()
    $cd = $ms.ToArray()
    # 4b. 解析中央目录条目
    $entries = @{}
    $p = 0
    while ($p + 46 -le $cd.Length -and $cd[$p] -eq 0x50 -and $cd[$p+1] -eq 0x4B -and $cd[$p+2] -eq 0x01 -and $cd[$p+3] -eq 0x02) {
        $method = [BitConverter]::ToUInt16($cd, $p + 10)
        $csize  = [BitConverter]::ToUInt32($cd, $p + 20)
        $usize  = [BitConverter]::ToUInt32($cd, $p + 24)
        $fnlen  = [BitConverter]::ToUInt16($cd, $p + 28)
        $exlen  = [BitConverter]::ToUInt16($cd, $p + 30)
        $lho    = [BitConverter]::ToUInt32($cd, $p + 42)
        $name   = [System.Text.Encoding]::UTF8.GetString($cd, $p + 46, $fnlen)
        $entries[$name] = @{ method = $method; csize = $csize; usize = $usize; lho = $lho }
        $p += 46 + $fnlen + $exlen
    }
    # 4c. 抽取 android_debug.apk / android_release.apk / version.txt
    foreach ($name in @("templates/android_debug.apk", "templates/android_release.apk", "templates/version.txt")) {
        $e = $entries[$name]
        if (-not $e) { Write-Warn2 "TPZ 中没有 $name"; continue }
        $tmpRaw = Join-Path $env:TEMP ("tpz_" + ($name -replace '[/\\]', '_'))
        # 本地头(30B)+文件名+可能的 extra 字段 + 压缩数据；多留 1KB 余量解析本地头
        $grabLen = [long]30 + $name.Length + 1024 + $e.csize
        Save-RangeFile $tpzUrl $e.lho $grabLen $tmpRaw ($name -replace '^templates/', '')
        # 解析本地头定位数据起点
        $raw = [System.IO.File]::ReadAllBytes($tmpRaw)
        if (-not ($raw[0] -eq 0x50 -and $raw[1] -eq 0x4B -and $raw[2] -eq 0x03 -and $raw[3] -eq 0x04)) {
            throw "$name 本地头校验失败"
        }
        $lfnlen = [BitConverter]::ToUInt16($raw, 26)
        $lexlen = [BitConverter]::ToUInt16($raw, 28)
        $dataOff = 30 + $lfnlen + $lexlen
        $outFile = Join-Path $tplDir ($name -replace '^templates/', '')
        if ($e.method -eq 8) {
            $ds = New-Object System.IO.Compression.DeflateStream((New-Object System.IO.MemoryStream($raw, $dataOff, $e.csize)), [System.IO.Compression.CompressionMode]::Decompress)
            $os = [System.IO.File]::Create($outFile)
            try { $ds.CopyTo($os) } finally { $os.Close(); $ds.Close() }
        } else {
            [System.IO.File]::WriteAllBytes($outFile, $raw[$dataOff..($dataOff + $e.csize - 1)])
        }
        Remove-Item $tmpRaw -Force
        $got = (Get-Item $outFile).Length
        if ($got -ne $e.usize) { Write-Warn2 "$name 大小校验不符（$got != $($e.usize)），请重跑" }
        else { Write-Ok "$name -> $outFile（$([math]::Round($got/1MB,1))MB）" }
        # 老版本布局兼容：Godot <4.7 读 <版本>\templates\ 子层
        if (-not (Test-Path $tplDirLegacy)) { New-Item -ItemType Directory -Path $tplDirLegacy -Force | Out-Null }
        Copy-Item $outFile (Join-Path $tplDirLegacy (Split-Path $outFile -Leaf)) -Force
    }
}

# ---------- 5. 写 Godot 编辑器设置（java / android sdk 路径） ----------

Write-Step "配置 Godot 编辑器设置…"
$running = Get-Process | Where-Object { $_.Name -like "Godot*" }
if ($running) {
    Write-Warn2 "Godot 正在运行，退出时会覆盖设置。请关闭 Godot 后重跑本脚本的这一步（脚本幂等）。"
} else {
    $esPath = Join-Path $env:APPDATA "Godot\editor_settings-$majMin.tres"
    $javaPath = $jdkDir -replace '\\', '/'
    $sdkPath2 = $sdkDir -replace '\\', '/'
    if (Test-Path $esPath) {
        $c = [System.IO.File]::ReadAllText($esPath)
        $c = [regex]::Replace($c, '(?m)^export/android/java_sdk_path\s*=\s*".*"$', "export/android/java_sdk_path = `"$javaPath`"")
        $c = [regex]::Replace($c, '(?m)^export/android/android_sdk_path\s*=\s*".*"$', "export/android/android_sdk_path = `"$sdkPath2`"")
        if ($c -notmatch 'export/android/java_sdk_path') {
            $c = $c -replace '(?m)^\[resource\]', "[resource]`nexport/android/java_sdk_path = `"$javaPath`"`nexport/android/android_sdk_path = `"$sdkPath2`""
        }
        [System.IO.File]::WriteAllText($esPath, $c)
        Write-Ok "已更新 $esPath"
    } else {
        # 从未打开过编辑器：生成最小设置文件
        $body = @"
[gd_resource type="EditorSettings" format=3]

[resource]
export/android/java_sdk_path = "$javaPath"
export/android/android_sdk_path = "$sdkPath2"
"@
        [System.IO.File]::WriteAllText($esPath, $body)
        Write-Ok "已创建 $esPath"
    }
}

# ---------- 6. 调试 keystore ----------

Write-Step "调试签名 keystore…"
$keystore = Join-Path $env:APPDATA "Godot\keystores\debug.keystore"
if (Test-Path $keystore) {
    Write-Ok "已存在：$keystore"
} else {
    $ksDir = Split-Path $keystore -Parent
    if (-not (Test-Path $ksDir)) { New-Item -ItemType Directory -Path $ksDir -Force | Out-Null }
    & (Join-Path $jdkDir "bin\keytool.exe") -genkeypair -keystore $keystore -storepass android -keypass android `
        -alias androiddebugkey -dname "CN=Android Debug,O=Android,C=US" -keyalg RSA -keysize 2048 -validity 10000 | Out-Null
    if (Test-Path $keystore) { Write-Ok "已生成：$keystore（口令 android / android）" }
}

# ---------- 汇总 ----------

Write-Host @"

============================================================
 Godot Android 导出工具链就绪（最小化安装）
   JDK17      $jdkDir
   AndroidSDK $sdkDir
   导出模板    $tplDir
   调试签名    $keystore
 下一步（游戏项目内）：
   1. 项目根放 export_presets.cfg（Android 预设，参考 skill 模板）
   2. 运行 skill 模板「导出安卓.bat」，产出 builds/*.apk
============================================================
"@ -ForegroundColor Green
