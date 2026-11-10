# 踩坑手册与边界说明

本文件记录被实测验证过的坑，复查同类问题时先看这里。

## Electron offscreen 截图/渲染

1. **隐藏窗口（show:false）capturePage 不刷新**：屏幕切换后 DOM/computedStyle 已变，截图仍是旧帧。
2. **窗口移出屏幕（x:-4000）会产出 0 字节帧**。
3. **正解**：`webPreferences:{offscreen:true}` + `setFrameRate(30)` + 监听 `paint` 事件保存 `image.toPNG()`，每帧内容正确。
4. **同一 offscreen 窗口 resize 后取多尺寸帧会拿到空数据**（size=0）。渲染多分辨率图标的正解：只渲染一张 1024 母版，用 `nativeImage.createFromBuffer(png).resize({quality:"best"})` 缩放。
5. 等待有效帧要轮询 `image.isEmpty()` 和 `image.getSize()`，上限约 3 秒，不要无阻塞地一次取帧。

## Electron 主进程

- **资源路径不要用 `app.isPackaged`**：electron.exe 被直接运行时该值判定异常，导致加载 file:// 报 ERR_FILE_NOT_FOUND。用 `fs.existsSync(path.join(process.resourcesPath, dir, "index.html"))` 探测，命中走安装态、否则回退开发态 `../`。
- executeJavaScript 多语句点击偶发不生效时，加 `app.commandLine.appendSwitch("disable-renderer-backgrounding")` 并使用 offscreen 模式。
- Windows 下 `spawnSync("npm", ...)` / `npx` 必须 `shell:true`（它们是 .cmd）。
- 国内网络装 electron/electron-builder 必配镜像，否则 electron 预构建包下载失败：
  - `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/`
  - `ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/`

## 图标

- 一张 1024 SVG 母版出全部尺寸：Android 72/96/144/192 PNG；Windows 用 256 PNG 直接封 ICO（ICONDIR+单 ICONDIRENTRY，宽高字节 256 记为 0）。Vista+ 的 Windows 全支持 PNG 压缩 ICO，electron-builder 接受。
- 图标设计：圆角方形底板（rx≈22%）兼容方形与圆形启动器遮罩；主体离边留足安全区；小尺寸（72px）必须再目检一次，五官/文字不挤。
- 配了 `build.icon` 后 nsis 的 installerIcon/uninstallerIcon 也要指向同一 ico，否则安装程序仍是默认 Electron 图标。
- 验证 ico 是否嵌入：PowerShell `[System.Drawing.Icon]::ExtractAssociatedIcon($exe)` 存 PNG 查看（注意该 API 只取 32px 帧，放大显糊不代表 ico 有问题）。

## HBuilderX 5+App / Android

- 云打包**只能**在 HBuilderX GUI 中由登录本人 DCloud 账号完成，没有命令行通道；免费档有每日次数限制与排队。
- 工程 `id`（DCloud AppID）无法代办，必须 GUI 内"重新获取"；脚本检测为空只警告不阻断。
- 自用直装选"DCloud 公共测试证书"；要上架须自有证书 + 软著（游戏类目另需版号）。
- 云打包只认工程目录边界内文件，不支持引用上级目录——这是必须 sync 副本的根因。不要尝试符号链接替代：HBuilderX 对软链识别不稳定，压缩/换机易断链。
- `manifest.json` 是严格 JSON；编辑时不要加注释或尾逗号。
- 权限最小化：无原生需求只留 VIBRATE；targetSdk 30 / minSdk 23 覆盖绝大多数在用机型。
- WebAudio 必须在用户首次手势后初始化——确认页面第一个主按钮（开始游戏类）的 click 里调用了音频 resume/init，否则手机上静音。
- 安装 APK 时手机会提示"未知来源"，属正常。

## 缓存与发版

- 静态资源靠入口 HTML 上的 `?v=` 查询串破缓存。**改了任何 css/js 必须 bump 对应版本号**，否则 WebView 用旧缓存，"代码没生效"类问题九成九是这个。
- 发版顺序：改源码 → bump 版本号 → `node scripts/build.mjs all`（android 的同步+哈希、exe 的构建+包内哈希都会兜底）。

## 存档与合规

- localStorage 存档随 App 卸载、WebView 清缓存而丢失。家庭自用可接受；要防丢需上 Capacitor Preferences / plus.io 原生持久化（超出本 skill 范围）。
- exe 未代码签名：SmartScreen 首次弹"未知发布者"（仍可运行），部分杀软对 portable 单文件版误报率更高。消除需购买 OV/EV 代码签名证书。
- Electron 包体积构成：Chromium 运行时约 150MB 解包 / 70~80MB 压缩，这是下限，不要尝试裁剪 dll/pak/locales。
- 若产物 exe 突然只有几百 KB：构建失败但进程返回 0 的异常情况，体积阈值校验（第四道闸）就是拦这个的。

## 不适用时的替代方案

| 需求 | 替代 |
|---|---|
| 追求更小体积/内存 | Tauri（Rust 工具链，系统 WebView，包体几 MB） |
| 需要原生能力/插件生态 | Capacitor（Android Studio 本地构建，需 JDK+SDK+Gradle） |
| 已有 React/Vue 工程 | 先产出静态 dist，再把 dist 当事实源走本流程 |
| 要上架 Google Play | Capacitor + AAB，本流程的 APK 不满足其上架要求 |
