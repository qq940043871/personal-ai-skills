/* Electron 主进程模板 —— 复制到 desktop/main.js
   替换：__APP_NAME__、__WEB_DIR__（源码目录名，如 game / web / dist）、窗口尺寸
   勿改：资源路径用 fs.existsSync 探测；不要改用 app.isPackaged */
const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const fs = require("fs");

const WEB_DIR = "__WEB_DIR__";

function resolveGameIndex() {
  // 安装态：electron-builder 的 extraResources 把源码放到 resources/<WEB_DIR>/
  const installed = path.join(process.resourcesPath, WEB_DIR, "index.html");
  if (fs.existsSync(installed)) return installed;
  // 开发态：desktop/ 的上级目录
  return path.join(__dirname, "..", WEB_DIR, "index.html");
}

let win = null;

function createWindow() {
  win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 620,
    backgroundColor: "#FFF4E2", // 与页面底色一致，避免启动白/黑屏
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });
  win.setMenuBarVisibility(false);
  win.loadFile(resolveGameIndex());
  // 外链交给系统浏览器，应用内不开新窗
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });
}

// 单实例锁
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });
  app.whenReady().then(createWindow);
  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
}
