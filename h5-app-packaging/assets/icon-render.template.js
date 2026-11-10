/* ════════════════════════════════════════════════════════════════
   图标渲染脚本模板（Electron offscreen，无第三方依赖）
   ----------------------------------------------------------------
   前置：目标项目 desktop/ 已 npm install electron
   用法：
     1. 先写好 1024×1024 的 SVG 母版，路径见 SVG_PATH
     2. 把本文件复制到 desktop/ 下（必须在 electron 工程内运行）
     3. node ../../desktop/icon-render.js  （或直接 electron . 不行——这是独立脚本）
        正确运行方式：.\node_modules\electron\dist\electron.exe icon-render.js
   产出：
     mobile-app/icons/{72,96,144,192}.png
     desktop/build/icon.ico（单条目 256 PNG 压缩，Vista+ 合法）
   关键经验：不要在同一个 offscreen 窗口里 resize 取多帧（会取到空帧）；
   只渲染一张 1024 母版，再用 nativeImage.resize 缩放。
   ════════════════════════════════════════════════════════════════ */
const { app, BrowserWindow, nativeImage } = require("electron");
const path = require("path"), fs = require("fs");
app.commandLine.appendSwitch("disable-renderer-backgrounding");

/* ─────── 路径配置（复制后按实际项目改） ─────── */
const ROOT = path.join(__dirname, "..");
const SVG_PATH = path.join(ROOT, "mobile-app", "icons", "icon.svg");
const PNG_DIR = path.join(ROOT, "mobile-app", "icons");
const ICO_DIR = path.join(ROOT, "desktop", "build");
const PNG_SIZES = [72, 96, 144, 192]; // Android 四档
const ICO_PNG_SIZE = 256;
/* ──────────────────────────────────────────── */

const sleep = ms => new Promise(r => setTimeout(r, ms));

app.whenReady().then(async () => {
  const S = 1024;
  const svgB64 = fs.readFileSync(SVG_PATH).toString("base64");
  const html = `<body style="margin:0;padding:0;overflow:hidden">
  <img src="data:image/svg+xml;base64,${svgB64}" style="display:block;width:${S}px;height:${S}px"></body>`;

  const win = new BrowserWindow({
    width: S, height: S, show: false,
    backgroundColor: "#00000000",
    webPreferences: { offscreen: true, sandbox: true },
  });
  win.webContents.setFrameRate(1);
  let img = null;
  win.webContents.on("paint", (e, d, image) => { if (image && !image.isEmpty()) img = image; });
  await win.loadURL("data:text/html;base64," + Buffer.from(html).toString("base64"));
  for (let i = 0; i < 60 && (!img || img.getSize().width !== S); i++) {
    win.webContents.invalidate();
    await sleep(50);
  }
  if (!img) { console.error("渲染母版失败"); app.exit(1); }
  const master = nativeImage.createFromBuffer(img.toPNG());

  fs.mkdirSync(PNG_DIR, { recursive: true });
  fs.mkdirSync(ICO_DIR, { recursive: true });

  for (const s of PNG_SIZES) {
    const png = master.resize({ width: s, height: s, quality: "best" }).toPNG();
    fs.writeFileSync(path.join(PNG_DIR, s + ".png"), png);
    console.log("PNG", s, png.length);
  }
  const png256 = master.resize({ width: ICO_PNG_SIZE, height: ICO_PNG_SIZE, quality: "best" }).toPNG();

  // ICO：ICONDIR(6) + 1 个 ICONDIRENTRY(16) + PNG 数据
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0); // reserved
  header.writeUInt16LE(1, 2); // type=icon
  header.writeUInt16LE(1, 4); // count
  const entry = Buffer.alloc(16);
  entry.writeUInt8(0, 0); entry.writeUInt8(0, 1); // 256 宽/高记为 0
  entry.writeUInt8(0, 2); entry.writeUInt8(0, 3); // 0 色板
  entry.writeUInt16LE(1, 4);   // color planes
  entry.writeUInt16LE(32, 6);  // bpp
  entry.writeUInt32LE(png256.length, 8);
  entry.writeUInt32LE(22, 12); // 数据偏移 = 6+16
  const icoPath = path.join(ICO_DIR, "icon.ico");
  fs.writeFileSync(icoPath, Buffer.concat([header, entry, png256]));
  console.log("ICO", icoPath, 22 + png256.length);
  console.log("ICON_DONE");
  app.quit();
});
