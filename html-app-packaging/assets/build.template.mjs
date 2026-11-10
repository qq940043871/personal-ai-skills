#!/usr/bin/env node
/* ════════════════════════════════════════════════════════════════
   一键打包脚本模板 —— 复制到工程根 scripts/build.mjs，改下面 CONFIG。
   用法：node scripts/build.mjs <exe | android | all>

   四道闸：源码存在性 → 强制同步+SHA-256 → 依赖自愈 → 产物闭环验证
   依赖 Node 18+（内置 fetch/crypto 不需要；只用内置模块）。
   ════════════════════════════════════════════════════════════════ */
import { spawnSync } from "node:child_process";
import { existsSync, statSync, readFileSync, readdirSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

/* ─────────── CONFIG（按项目修改） ─────────── */
const CONFIG = {
  webDir: "__WEB_DIR__",          // 事实源目录名（game / web / dist ...）
  desktopDir: "desktop",
  mobileDir: "mobile-app",
  exeArtifact: n => [`__APP_NAME__ Setup ${n}.exe`, `__APP_NAME__-绿色版-${n}.exe`], // n=version
  minExeMb: 50,                    // 低于此体积视为构建异常（Electron 空壳约 60MB+）
  iconSizes: [72, 96, 144, 192],
  requirePortrait: true,          // manifest 是否必须锁定竖屏
  hbuilderHints: [                // 常见安装路径探测，可增删
    "C:\\Program Files\\HBuilderX\\HBuilderX.exe",
    "C:\\Program Files (x86)\\HBuilderX\\HBuilderX.exe",
    path.join(process.env.LOCALAPPDATA || "", "Programs", "HBuilderX", "HBuilderX.exe"),
    "D:\\HBuilderX\\HBuilderX.exe",
  ],
};
/* ──────────────────────────────────────────── */

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WEB = path.join(ROOT, CONFIG.webDir);
const DESKTOP = path.join(ROOT, CONFIG.desktopDir);
const MOBILE = path.join(ROOT, CONFIG.mobileDir);

const c = {
  green: s => `\x1b[32m${s}\x1b[0m`, red: s => `\x1b[31m${s}\x1b[0m`,
  yellow: s => `\x1b[33m${s}\x1b[0m`, cyan: s => `\x1b[36m${s}\x1b[0m`,
  gray: s => `\x1b[90m${s}\x1b[0m`, bold: s => `\x1b[1m${s}\x1b[0m`,
};
const ok = m => console.log(c.green("  [OK]  ") + m);
const bad = m => console.log(c.red("  [失败] ") + m);
const warn = m => console.log(c.yellow("  [警告] ") + m);
const step = m => console.log("\n" + c.cyan("▶ " + m));
const die = m => { bad(m); console.log(c.red("\n打包中止。")); process.exit(1); };

// npm/npx 在 Windows 是 .cmd，必须 shell:true
function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: "inherit", shell: process.platform === "win32", ...opts });
  if (r.error) die(`无法执行 ${cmd}：${r.error.message}`);
  if (r.status !== 0) die(`命令失败（退出码 ${r.status}）：${cmd} ${args.join(" ")}`);
}
function runNode(args, cwd) {
  const r = spawnSync(process.execPath, args, { stdio: "inherit", cwd });
  if (r.status !== 0) die(`Node 执行失败（退出码 ${r.status}）`);
}

// 递归列文件：base 必须随递归透传，否则相对路径丢目录前缀
function listFiles(dir, base = dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) out.push(...listFiles(p, base));
    else out.push(path.relative(base, p).replace(/\\/g, "/"));
  }
  return out;
}
const sha256 = p => createHash("sha256").update(readFileSync(p)).digest("hex");
const fmtMb = p => (statSync(p).size / 1024 / 1024).toFixed(1);

function assertSource() {
  if (!existsSync(path.join(WEB, "index.html")))
    die(`找不到源码：${path.join(WEB, "index.html")}`);
  ok(`源码就位：${CONFIG.webDir}/index.html`);
}

/* ═══════════════════ Windows exe ═══════════════════ */
function buildExe() {
  console.log(c.bold("\n── 目标：Windows 安装包 + 绿色版 ──"));
  step("1/4 检查源码");
  assertSource();

  step("2/4 检查桌面壳依赖（缺失自动安装）");
  if (!existsSync(path.join(DESKTOP, "node_modules", "electron", "dist", "electron.exe"))) {
    console.log(c.gray("  开始 npm install（淘宝镜像）…"));
    run("npm", ["install", "--registry=https://registry.npmmirror.com"], { cwd: DESKTOP });
    ok("依赖安装完成");
  } else ok("依赖已安装，跳过");

  step("3/4 electron-builder 构建");
  run("npx", ["electron-builder", "--win", "nsis", "portable"], {
    cwd: DESKTOP,
    env: {
      ...process.env,
      ELECTRON_MIRROR: "https://npmmirror.com/mirrors/electron/",
      ELECTRON_BUILDER_BINARIES_MIRROR: "https://npmmirror.com/mirrors/electron-builder-binaries/",
    },
  });

  step("4/4 产物闭环校验");
  const pkg = JSON.parse(readFileSync(path.join(DESKTOP, "package.json"), "utf8"));
  const dist = path.join(DESKTOP, "dist");
  for (const f of CONFIG.exeArtifact(pkg.version)) {
    const p = path.join(dist, f);
    if (!existsSync(p)) die(`缺少产物：${f}`);
    const mb = parseFloat(fmtMb(p));
    if (mb < CONFIG.minExeMb) die(`产物体积异常（${mb}MB < ${CONFIG.minExeMb}MB）：${f}`);
    ok(`${f}（${mb} MB）`);
  }
  const embedded = path.join(dist, "win-unpacked", "resources", CONFIG.webDir, "index.html");
  if (!existsSync(embedded)) die(`未找到包内入口：win-unpacked/resources/${CONFIG.webDir}/index.html`);
  if (sha256(path.join(WEB, "index.html")) !== sha256(embedded))
    die("包内 index.html 与源码哈希不一致，请删除 desktop/dist 后重试");
  ok("包内代码与源码哈希一致（确认不是旧代码）");
  console.log(`\n  产物目录：${c.bold(dist)}`);
}

/* ═══════════════════ Android 工程 ═══════════════════ */
function buildAndroid() {
  console.log(c.bold("\n── 目标：Android（HBuilderX 云打包前置同步与校验）──"));
  step("1/4 全量同步（保留 manifest.json / icons/ / unpackage/）");
  runNode([path.join(MOBILE, "sync.mjs")], MOBILE);

  step("2/4 逐文件 SHA-256 校验");
  let badCount = 0;
  for (const f of listFiles(WEB)) {
    const srcP = path.join(WEB, f), dstP = path.join(MOBILE, f);
    if (!existsSync(dstP)) { bad(`手机工程缺少文件：${f}`); badCount++; }
    else if (sha256(srcP) !== sha256(dstP)) { bad(`内容不一致：${f}`); badCount++; }
  }
  if (badCount) die(`${badCount} 个文件异常，请重新运行本脚本，切勿手动复制`);
  ok(`已校验 ${listFiles(WEB).length} 个文件，全部一致`);

  step("3/4 校验 manifest.json 与图标");
  const manifestPath = path.join(MOBILE, "manifest.json");
  if (!existsSync(manifestPath)) die("缺少 mobile-app/manifest.json");
  let m;
  try { m = JSON.parse(readFileSync(manifestPath, "utf8")); }
  catch (e) { die("manifest.json 不是合法 JSON：" + e.message); }
  if (!m.id) warn("DCloud AppID 为空 —— 首次打包须在 HBuilderX 中打开 manifest.json 点「重新获取」");
  else ok("DCloud AppID：" + m.id);
  const orient = m.plus?.screenOrientation;
  if (CONFIG.requirePortrait && (!Array.isArray(orient) || !orient.includes("portrait-primary")))
    warn("未锁定竖屏（portrait-primary），请检查 manifest");
  else ok("屏幕方向配置正确");
  for (const s of CONFIG.iconSizes) {
    const p = path.join(MOBILE, "icons", `${s}.png`);
    if (!existsSync(p)) die(`图标缺失：icons/${s}.png`);
    if (statSync(p).size < 1000) die(`图标文件过小（可能损坏）：icons/${s}.png`);
  }
  ok(`图标齐全（${CONFIG.iconSizes.join("/")}px）`);

  step("4/4 HBuilderX 云打包指引");
  const found = CONFIG.hbuilderHints.filter(existsSync);
  if (found.length) console.log(c.gray("  检测到 HBuilderX：" + found[0]));
  else warn("未在常见路径检测到 HBuilderX（装在其他位置可忽略）");
  console.log(`
  云打包必须登录本人 DCloud 账号，无法纯命令行完成：
  ${c.bold("1.")} HBuilderX → 文件 → 导入 → 从本地目录导入：${c.bold(MOBILE)}
  ${c.bold("2.")} 双击 manifest.json → 重新获取 DCloud AppID（仅首次）
  ${c.bold("3.")} 发行 → 原生 App-云打包 → Android → 公共测试证书（自用直装）→ 打包
  ${c.bold("4.")} 下载 APK 传手机安装（允许未知来源）
`);
  ok("Android 工程已与源码完全同步，随时可云打包");
}

const target = process.argv[2];
console.log(c.bold("一键打包 · 唯一事实源：" + CONFIG.webDir + "/"));
if (target === "exe") buildExe();
else if (target === "android") buildAndroid();
else if (target === "all") { buildExe(); buildAndroid(); }
else {
  console.log("用法: node scripts/build.mjs <exe | android | all>");
  process.exit(1);
}
console.log(c.green("\n全部完成。"));
