/* ═══ 手机包同步脚本 —— 复制到 mobile-app/sync.mjs 直接可用 ═══
   把 ../__WEB_DIR__ 的最新文件全量同步到本目录（HBuilderX 5+App 工程根）。
   用法：node sync.mjs
   保留：manifest.json / sync.mjs / icons/ / unpackage/（HBuilderX 产物）。
   注意：本脚本只做"同步"，一致性校验在工程根 scripts/build.mjs 中做。 */
import { cpSync, rmSync, readdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const SRC_DIR = "__WEB_DIR__"; // 改为事实源目录名，如 game / web / dist

const root = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(root, "..", SRC_DIR);
if (!existsSync(path.join(src, "index.html"))) {
  console.error(`找不到 ../${SRC_DIR}/index.html，请确认目录结构`);
  process.exit(1);
}
const KEEP = new Set(["manifest.json", "sync.mjs", "icons", "unpackage"]);
for (const entry of readdirSync(root)) {
  if (!KEEP.has(entry)) rmSync(path.join(root, entry), { recursive: true, force: true });
}
cpSync(src, root, { recursive: true });
console.log(`已同步 ../${SRC_DIR} -> mobile-app/（保留 manifest.json 与 icons/）`);
