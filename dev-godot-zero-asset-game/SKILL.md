---
name: dev-godot-zero-asset-game
description: 用 Godot 4.x 从零开发 2D 小游戏（网格/魔塔、塔防、解谜、平台等）的完整工作流：零素材资产管线（像素精灵/合成音频/系统中文字体）、数据驱动架构、三重无头质量门、Windows 一键交付、Android APK 导出（工具链最小化自动安装）。当用户说「用 Godot 做个游戏」「开发一个 2D 小游戏」「做个魔塔/塔防/贪吃蛇/推箱子类游戏」「导出安卓 APK」，或要求为游戏项目补测试、加音效、做启动脚本时使用——即使用户没提 Godot，2D 小游戏需求也优先用本技能。
---

# Godot 零素材 2D 游戏开发工作流

从空目录到可双击游玩、带自检的 Godot 4.x 2D 游戏。核心原则：**零外部素材**（代码即资产）、**数据与逻辑分离**（策划内容只改 data/）、**每步都有无头验证**。

## 0. 环境检查（动手前必做）

1. 探测 Godot：`where godot` 失败后检查 `C:\Program Files\Godot\`。注意本机安装有**嵌套怪癖**：可执行文件在名为 `Godot_vX.Y.Z-stable_win64.exe` 的**文件夹**里，真实 exe 在其下一层。
2. 命令行一律用 `Godot_v*_win64_console.exe`（非 console 版在 CLI 下无输出）。
3. 版本要求 4.4+（用到 static var、SystemFont）。首次运行/增删脚本后必须 `--headless --path <项目> --import` 刷新类缓存，否则 class_name 解析失败。

## 1. 项目骨架

直接复用 `assets/templates/project.godot`（GL Compatibility 渲染、1280×720、方向键+WASD 输入映射、autoload 注册），改游戏名即可。目录约定：

```
<game>/
├── project.godot
├── scenes/main.tscn     ← 唯一场景：根节点+主脚本，UI 全部代码构建
├── scripts/
│   ├── main.gd          流程控制（标题/游戏/结算/命令行钩子）
│   ├── game_state.gd    autoload：数值账本/存档/快照回滚
│   ├── floor_map.gd     游戏主逻辑（按玩法改名）
│   ├── hud.gd           代码构建的 HUD
│   ├── combat.gd        纯函数规则（可无头测试）
│   ├── ui_kit.gd        中文字体+主题（模板原样复用）
│   ├── audio_manager.gd autoload「Sound」（模板原样复用）
│   └── data/            ⭐ 策划数据层：关卡/魔物/道具/价格/像素画
└── test/autotest.gd     数据层无头自检
```

加载顺序纪律：data 纯数据无依赖；combat 纯函数；game_state/floor_map 可引用 data；main 只做粘合。**改内容只动 data/，改规则后必须跑质量门。**

## 2. 零素材资产三件套

模板都在 `assets/templates/`，复制进项目后按游戏改内容：

- **`sprites.gd`（像素精灵）**：每个精灵 = 12×12 ASCII 像素画 + 调色板，`SpriteData.get_texture()` 运行时生成 `ImageTexture` 并缓存；绘制节点设 `texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST`，`draw_texture_rect(tex, Rect2(...), false, tint)` 放大。同一 rows 可配多套 colors（如一把钥匙配三色）。新游戏只改像素画字符串。
- **`audio_manager.gd`（合成音频）**：autoload「Sound」。启动后 0.3s 延迟合成（合成耗时，别放 _ready 同步做；也不要用 Thread——`-s` 测试模式会报线程未收尾）。`_osc(buf,start,dur,freq,wave,vol,rate)` 方波/三角/正弦/噪声 + 包络；SFX 直接混音成短 wav，BGM 用 `AudioStreamWAV.LOOP_FORWARD` 无缝循环。播放点挂在游戏事件上：拾取/开门/战斗胜/受阻/楼梯/失败/通关。
- **`ui_kit.gd`（中文字体）**：`SystemFont` 指向 `["Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "SimSun"]`，设为 Theme.default_font。所有 UI 代码构建，避免手写 .tscn 语法错。

## 3. 三重质量门（每个都做成命令行钩子）

main.gd `_ready` 末尾读 `OS.get_cmdline_user_args()`，分发三个钩子，测试时带 `--` 传参：

```bash
GODOT="C:\Program Files\Godot\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe"

# ① 数据自检：地图尺寸/字符合法性/实体计数 + 软锁检测 + 公式断言（不依赖场景与 autoload）
"$GODOT" --headless --path . --import
"$GODOT" --headless -s test/autotest.gd          # 期望 AUTOTEST PASS
# ② 集成冒烟：真实场景里走格子/战斗/切换/回滚/存档往返/购买
"$GODOT" --headless --path . -- autotest-smoke   # 期望 [smoke] PASS
# ③ 截图目检：窗口闪现数秒，SHOT_DIR 落 PNG，逐张读图检查
SHOT_DIR=.godot/shots "$GODOT" --path . -- screenshot
```

**软锁检测模式**（网格关卡类游戏的灵魂，见 `assets/templates/autotest.gd`）：贪心迭代 BFS——门视为不可通过，可达即捡钥匙；当存在「已达邻居的未开门且有钥匙」就开门重扫，直到无进展；最后断言楼梯与所有道具/怪可达。钥匙跨层结转累计校验。改任何地图后必跑。

冒烟钩子里 `_check(cond, msg)` 失败要 `quit(1)`；注意 `quit()` 只在帧末生效，同一帧后续语句仍会执行，所以失败后别依赖状态。测试钩子末尾**必须 `Game.clear_save()`**，否则测试存档会污染玩家的「继续游戏」。

## 4. Windows 一键交付

写 `启动游戏.bat` / `打开编辑器.bat` / `运行自检.bat` 放项目根。两个致命坑：

- **编码必须是 GBK**（系统代码页 936，UTF-8 中文会乱码）且**行尾必须 CRLF**（LF 会让 cmd 解析 goto/代码块错位，把单词后半截当命令执行）。Write 工具输出 UTF-8+LF，写完必须转换：

```powershell
powershell -NoProfile -Command 'Get-ChildItem -Filter *.bat | ForEach-Object { $c = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8); $c = $c -replace "`r`n","`n"; $c = $c -replace "`n","`r`n"; [System.IO.File]::WriteAllText($_.FullName, $c, [System.Text.Encoding]::GetEncoding(936)) }'
```

- bat 里路径含空格要引号；`--path "%~dp0."` 末尾补 `.` 防止尾反斜杠吞引号；找不到 Godot 时 echo 提示 + pause。写完实测：拉起进程 → `tasklist` 确认 → `taskkill //IM <exe> //F` 关闭。

## 5. GDScript 4.x 易踩坑清单

- `String.right(n)` 是**取末尾 n 个字符**，不是从下标 n 开始（`"key_y".right(1)` = "y"）。
- const 字典里**重复键**（sed 批量插入常见事故）只报 "Could not resolve external class member"，错误指向引用方而非定义方，先查定义文件。
- 无类型返回的函数返回 null 后再下标会报解析错；查询函数显式 `-> Variant`。
- 弹窗函数先 `_clear_overlay()` 再设 `_overlay_kind`，顺序反了会被清掉。
- JSON 存档读回全是 float 和无类型 Dictionary：数值字段逐个 `int()`，嵌套结构逐层重建。
- 自动加载单例命名（如 `Game`）不要再配 class_name，会冲突。

## 6. 设计平衡法（数值类游戏）

- 战斗公式写纯函数（勇者先手：`hits = ceil(敌HP/每击伤害)`，`损血 = (hits-1)×敌每击伤害`）。
- 用「每层入门属性估计表」跑断言：每只怪必须可击败且损血 < 估计 HP——魔物数值失衡在测试期就炸出来。
- 计步压力机制（侵蚀/倒计时类）：手工推演最优路线步数 ×2 安全系数定预算；压力源（如焦虑虫）放在主路径必经侧室而非深处；**必须**配首次进入的教学弹窗 + 过半/濒危阈值警报 + HUD 实时速率显示，否则玩家「没碰到却被判负」会觉得不公平。
- 拿过的东西、杀过的怪按楼层记入 `floor_state`，上下楼不刷新，天然防刷；核心失守类失败用进层快照回滚，不读档。

## 7. 交付节奏

每个里程碑结束：跑三重质量门 → 截图逐张目检 → 更新 README（玩法/运行/验证命令/改动规则）→ 设计文档记录公式与扩展指南。不主动 git commit。

## 8. Android 导出交付（可选）

### 8.1 一次性环境格式化（每台机器只做一次）

```powershell
pwsh -File <skill目录>/assets/scripts/setup_android.ps1
```

**最小化安装**（约 600MB，全在用户目录，免管理员、幂等可重跑、断点续传）：

- Temurin JDK 17 → `~/godot-android/jdk`（清华 TUNA 镜像；Godot 4.x 安卓导出必须 17+）
- Android cmdline-tools + platform-tools + build-tools 34 → `~/godot-android/android-sdk`（dl.google.com；**不装** Android Studio、platforms、gradle——预编译模板导出只需要 apksigner/adb/keytool）
- Godot 安卓导出模板 → `%APPDATA%\Godot\export_templates\<版本串>\android_{debug,release}.apk` + `version.txt`：**对官方 TPZ 做 HTTP Range 抽取**（EOCD→中央目录→按条目偏移范围下载→raw-deflate 解压），只拉约 220MB 安卓件，不用下 1.28GB 全量包。**Godot 4.7+ 在版本目录根层查找模板**（老版本为 `<版本串>\templates\` 子层），脚本两层都写、新老通吃
- 调试 keystore → `%APPDATA%\Godot\keystores\debug.keystore`（alias=`androiddebugkey`，storepass/keypass=`android`）
- 自动改写 `editor_settings-<大版本.小版本>.tres` 的 `export/android/java_sdk_path` 与 `android_sdk_path`

脚本会自动探测 Godot（含 `C:\Program Files\Godot` 的嵌套文件夹怪癖）。**改编辑器设置前 Godot 必须关闭**，否则退出时会覆盖回去（脚本检测到运行中会警告，重跑即可补上）。

国内网络坑（脚本已内置对策）：GitHub 直连常 <10KB/s 且中途断连——改走 `downloads.godotengine.org` 官方重定向（Hetzner 对象存储，支持 Range）；TUNA 对无浏览器 UA 的请求回 403；下载全部带 UA + 失败重连续传。**`.NET HttpWebRequest` 在 schannel SSL 流上 `ReadWriteTimeout` 可能不生效**（`Read()` 无限挂起、连接保持 ESTABLISHED、CPU 归零，实测在 Hetzner 源 120MB 处 64% 卡死）——范围下载必须用 `ReadAsync` + `Wait(90s)` 强制超时并并入重连计数；另外 `SetLength` 预分配的临时文件**大小恒等于目标大小，不能当下载进度看**，判断卡死要看进程 CPU 与 LastWriteTime。

### 8.2 每个项目的安卓交付五件套

1. **`export_presets.cfg`**（项目根）：复制 `assets/templates/export_presets.android.cfg`，改 4 处——`package/unique_name`（反域名至少三段小写字母）、`package/name`（显示名，可中文）、`export_path`（建议 `builds/<游戏名>.apk`）、keystore 路径里的 `CHANGEME`（本机用户名，正斜杠）。debug/release 默认都指 debug keystore：自家分发（扫码/网盘发 APK 给家人）够用且可装；要上 Google Play 才需要另配正式 release keystore。
2. **横屏设置**：`project.godot` 的 `[display]` 段加 `window/handheld/orientation=0`（横屏游戏）。
3. **ETC2 纹理压缩**：`project.godot` 的 `[rendering]` 段加 `textures/vram_compression/import_etc2_astc=true`——Android 导出的硬性前置校验，缺了直接报「导出 Android 版本需要 ETC2/ASTC 纹理压缩格式」。注意键名：**4.7 是 `vram_compression`**（旧版本为 `vram_compress`）。
4. **触屏输入**：键盘 action 在手机上不存在，必须补。网格类游戏推荐「滑动走格子（不抬手连续滑）+ 点按朝相对方向走一步 + 战斗演出点按跳过」模式——在 floor_map 类脚本的 `_unhandled_input` 处理 `InputEventScreenTouch/Drag`，复用 `input_locked`/`busy` 守卫，桌面版零回归（参考 magic-tower-td 的实现）。按钮类 UI（标题/商店/结算）Godot 自带触屏支持，无需改动。
5. **中文字体**：**SystemFont 在 Android 上不可靠**，`ui_kit.gd` 的字体函数必须加 Android 分支——`FontFile.load_dynamic_font("/system/fonts/NotoSansCJK-Regular.ttc")`（回退 `DroidSansFallback.ttf`），直接读设备系统字体，仍是零素材。不加必出豆腐块。

然后复制 `assets/templates/导出安卓.bat` 到项目根（GBK+CRLF 转换同第 4 节），双击产出 `builds/*.apk`。

### 8.3 验证

```powershell
# 无头导出（preset 名必须是 "Android"）
& $GODOT --headless --path . --import
& $GODOT --headless --path . --export-release "Android"     # 退出码非 0 或 builds 下无新 apk 即失败
# 签名与包信息校验（无需手动装 Java——用工具链里的）
& "$env:USERPROFILE\godot-android\android-sdk\build-tools\34.0.0\apksigner.bat" verify --print-certs builds\<游戏>.apk
```

产物体积应为模板 APK 基数（arm64-v7a+arm64 双架构约 50–60MB）+ 资源增量；有真机时 `adb install -r builds\<游戏>.apk` 实测触屏操作与中文字体渲染。

### 8.4 安卓导出坑清单

- 模板版本必须与编辑器**完全一致**（含 `.stable` 后缀），目录名即版本串，差一位都报「模板缺失」。
- **Godot 4.7+ 的模板查找路径是 `export_templates\<版本串>\android_*.apk`（版本目录根层，无 `templates\` 子层）**；报错信息里的路径就是唯一真相来源，按它放文件。
- ETC2 校验报「导出 Android 版本需要 ETC2/ASTC 纹理压缩格式」时，加 `textures/vram_compression/import_etc2_astc=true`（**4.7 键名是 compression**；写成旧版 `vram_compress` 不报错但不生效，`ProjectSettings.get_setting` 读自设值会假阳性通过）。
- `export_path` 指向的目录（如 `builds/`）必须先存在，Godot **不自动创建**，缺失时报「目标文件夹不存在或无法访问」。
- preset 的 `keystore/*` 三字段（路径/用户/口令）显式写全最稳；留空会回退 editor settings，链路多一环。
- `--export-release` = release 优化模板 + 指定 keystore 签名；`--export-debug` 模板未优化且更大，自家用前者。
- 导出前先 `--import`；CLI 无输出时检查是否误用了非 console 版 exe。
- bat 的 GBK 编码坑同第 4 节；APK 文件名含中文时 bat 里引用要加引号。
