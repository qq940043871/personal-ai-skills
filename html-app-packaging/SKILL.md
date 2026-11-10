---
name: html-app-packaging
description: 把纯静态 H5 游戏或网页零改造套壳为 Windows exe（Electron）与 Android APK（HBuilderX 5+App 云打包），以唯一事实源+强制同步+SHA-256 校验+产物闭环验证杜绝旧代码与漏文件。触发词 — H5 打包 exe、网页打包 APP、H5 游戏打包 APK、Electron 套壳、HBuilderX 云打包、静态页面封包。不用于含后端服务、原生模块或需要 iOS 的项目。
---

# H5/网页 → exe + APK 套壳打包

零改造把一个纯静态前端工程（HTML/CSS/JS，零网络请求或仅同源请求，存档走 localStorage）套壳双端发布。
核心资产是**一套源码 + 两个壳工程**，关键风险是"副本失真"——用强制同步与哈希校验消灭它。

## 1. 适用判断

| 情况 | 结论 |
|---|---|
| 纯静态页面/游戏（SVG/Canvas、WebAudio、localStorage、已含 touch/响应式） | 适用，直接走本流程 |
| 页面依赖外部 HTTP API、CDN 资源 | 先确认离线可用性；必要时把资源本地化（APK/exe 不能假设网络） |
| 需要文件系统/蓝牙/后台保活等原生能力 | 5+App 可加原生插件，但超出本 skill，需单独评估 |
| 要上 iOS | 停止。需 Mac + Apple 开发者账号，HBuilderX 也需 macOS + 证书 |
| 要上国内安卓商店 | 可出包但上架需软著，游戏类目需版号；默认走自用直装分发（公共测试证书） |

## 2. 目录契约（三目录，一事实源）

```
<project>/
├── <web>/          ① 唯一事实源（游戏/网页源码，所有改动只发生在这里）
├── desktop/        ② Electron 壳（自有文件仅 main.js / package.json / build/icon.ico）
│                     构建时 extraResources 直接引用 ../<web>，无需同步
└── mobile-app/     ③ HBuilderX 5+App 工程（manifest.json / icons/ / sync 脚本为自有）
                      其余全部是 <web>/ 的强制同步副本（云打包只认工程边界内文件）
```

铁律：**永远不手改副本**。副本是生成物，改了下次同步必被覆盖，且制造"哪个是最新"的混乱。

## 3. 操作流程

### 步骤 1 — 勘察源工程（必做，决定适配工作量）

- 找入口 HTML，记录所有 `<script src>` / `<link href>` 的 `?v=` 缓存版本号
- 确认有无外部请求（搜 `fetch(` `XMLHttpRequest` `http://` `https://`）、外部图片/音频
- 确认存档机制（localStorage key）、是否已有 touch 事件与响应式断点
- **竖/横屏用实测决定，不猜**：用 Electron offscreen 渲染按真机视口截图（脚本见 `assets/icon-render.template.js` 同款 offscreen 技术，或复用桌面 Chrome DevTools 手机模拟）。典型窄屏断点 560/980px

### 步骤 2 — 搭 desktop/ Electron 壳

复制 `assets/electron-main.template.js` → `desktop/main.js`，复制 `assets/desktop-package.template.json` → `desktop/package.json`，替换占位符。

关键配置（已被实测证明，勿"优化"）：
- **资源路径用 `fs.existsSync` 探测**（开发态 `../<web>/index.html`，安装态 `process.resourcesPath/<web>/index.html`），不要用 `app.isPackaged`——直接跑 electron.exe 时该判定会异常导致 ERR_FILE_NOT_FOUND
- `webPreferences` 三件套：`contextIsolation:true`、`sandbox:true`、`nodeIntegration:false`
- `package.json` 的 `build.files` 只放壳自身文件；`extraResources` 把 `../<web>` 整体复制进 `resources/<web>/`；win target 同时出 nsis（可选目录+快捷方式）和 portable（单文件）
- 首次装依赖与构建必须带国内镜像环境变量：
  `ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/`
  `ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/`

### 步骤 3 — 应用图标（一套 SVG 母版出双端）

1. 写 1024×1024 SVG（圆角矩形底板，兼容圆形/方形遮罩；主体留白边，小尺寸才不糊）
2. 用 `assets/icon-render.template.js`（Electron offscreen）渲染 1024 PNG 母版，再 `nativeImage.resize({quality:"best"})` 缩放
   - Android：72/96/144/192 PNG → `mobile-app/icons/`
   - Windows：256 PNG 直接封成**单条目 PNG 压缩 ICO**（Vista+ 合法，模板已实现）→ `desktop/build/icon.ico`，并在 package.json 配 `build.icon` 与 nsis 的 installerIcon/uninstallerIcon
3. 每个尺寸目检一遍，72px 下五官仍可辨才算过

### 步骤 4 — 搭 mobile-app/ HBuilderX 工程

复制 `assets/manifest.template.json`，替换名称/版本。已固化的正确项：
- `screenOrientation: ["portrait-primary"]`（实测竖屏可玩才锁；若实测横屏优则改 landscape）
- 状态栏 `style:"dark"` + 与页面一致的底色（沉浸栏不突兀）
- Android `minSdkVersion 23 / targetSdkVersion 30`，权限最小化（无特殊需求只留 VIBRATE）
- icons 四档路径

复制 `assets/sync.template.mjs` → `mobile-app/sync.mjs`：清空工程内除 KEEP 名单（`manifest.json`、同步脚本自身、`icons`、`unpackage`）外的一切，再全量复制源码。

**`id`（DCloud AppID）留空**——必须用户本人在 HBuilderX 可视化界面点"重新获取"，无法代办，脚本检测到为空只警告不阻断。

### 步骤 5 — 一键打包脚本（防错核心）

复制 `assets/build.template.mjs` → `scripts/build.mjs`，改顶部 CONFIG 后支持 `node scripts/build.mjs exe | android | all`，并配两个根目录 `.cmd` 双击入口（`chcp 65001` 处理中文、末尾 `pause`）。

四道闸缺一不可：
1. **源码存在性**：入口 HTML 不存在立即中止
2. **强制同步 + 逐文件 SHA-256 比对**（android）：先清空再复制，源/副本逐文件哈希一致；任何缺失/不一致中止并提示重跑，**不允许手动复制补救**
3. **依赖自愈**（exe）：检测 `node_modules/electron/dist/electron.exe`，缺失自动 `npm install --registry=https://registry.npmmirror.com`
4. **产物闭环验证**（exe）：两个 exe 存在 + 体积高于阈值（正常 60~90MB，阈值设 50MB）+ **包内 `win-unpacked/resources/<web>/index.html` 与源码哈希一致**——保证打出来的绝不是旧代码

实现纪律：
- 编排用 **Node 脚本**，不要用 PowerShell 复杂逻辑（三元、heredoc、编码都是坑）；cmd 仅做双击入口
- `spawnSync` 调 npm/npx 在 Windows 必须 `shell:true`；调 node 自身用 `process.execPath` 直跑
- 递归列文件时基准目录要随递归透传（`listFiles(dir, base=dir)`），否则相对路径丢目录前缀，哈希校验全部误报

### 步骤 6 — 验证与交付

- exe：启动冒烟（Start-Process，5 秒后进程存活且 MainWindowTitle 正确，然后杀掉）
- 视觉：offscreen 390×780（竖）/800×360（横）截标题页/设定页/主页三张图，人工目检
- 改了源码后：bump 入口 HTML 中改动文件的 `?v=` → 重跑 build 脚本（exe 构建自动取最新源码；android 走 sync）
- 交付时必须说明：未签名（SmartScreen 未知发布者、杀软可能误报）、localStorage 存档随卸载清除、APK 公共测试证书仅自用直装、HBuilderX 云打包免费档有每日次数/排队限制

## 4. 详细踩坑与边界

见 [references/pitfalls.md](references/pitfalls.md)：offscreen 截图三坑、WebAudio 触摸解锁、包体积构成、HBuilderX 云打包逐步操作、签名与上架合规。
